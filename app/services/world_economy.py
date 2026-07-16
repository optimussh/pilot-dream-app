"""세계 경제 · 스카이 타임즈 · 무역 · 유가 · 관광 · 요금실험 · 허브 · 편지 마일스톤"""
import hashlib
import random
from datetime import datetime

from app.models import db, FutureLetter, UserBadge, LogbookEntry
from app.services.gamification import load_json, today_str, week_key, get_total_hours, award_virtual_hours, log_activity
from app.services.economy import award_money, format_krw, get_wallet_summary

BASE_OIL = 80  # 가상 유가 지수 (달러/배럴 느낌의 교육용 숫자)


def _meta(prog):
    meta = prog._json('pilot_meta', {})
    edu = meta.setdefault('world_edu', {})
    defaults = {
        'airport_stamps': [],
        'trade_done': [],
        'trade_step': {},
        'night_sky_done': [],
        'hub_done': [],
        'tradeoff_date': '',
        'tradeoff_done': [],
        'pricing_plays': 0,
        'pricing_best': {},
        'economy_quiz': {},
        'ceo_report_week': '',
        'ceo_report_claimed': False,
        'parent_mode': False,
        'letter_milestones': {},
        'story_reads': [],
        'lessons_learned': [],
        'week_choices': {},
        'oil_override': None,
    }
    for k, v in defaults.items():
        if k not in edu:
            edu[k] = list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)
    return meta, edu


def _save(prog, meta):
    prog.set_json('pilot_meta', meta)
    db.session.commit()


def _seed_int(key, lo, hi):
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + h % (hi - lo + 1)


def _pick_weighted(events, key):
    if not events:
        return None
    total = sum(max(1, e.get('weight', 1)) for e in events)
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % max(1, total)
    acc = 0
    for e in events:
        acc += max(1, e.get('weight', 1))
        if h < acc:
            return e
    return events[-1]


def get_active_events(count=3):
    events = load_json('world_events.json')
    if not isinstance(events, list) or not events:
        return []
    wk = week_key()
    primary = _pick_weighted(events, f'{wk}-primary')
    picked = [primary] if primary else []
    # secondary deterministic
    pool = [e for e in events if e.get('id') != (primary or {}).get('id')]
    for i in range(count - 1):
        if not pool:
            break
        e = _pick_weighted(pool, f'{wk}-sec-{i}')
        if e:
            picked.append(e)
            pool = [x for x in pool if x.get('id') != e.get('id')]
    return picked


def get_oil_price(prog=None):
    """교육용 가상 유가. 주간 이벤트 반영."""
    events = get_active_events(3)
    oil = BASE_OIL
    for e in events:
        oil += e.get('oil_delta', 0)
    if prog:
        _, edu = _meta(prog)
        if edu.get('oil_override') is not None:
            oil = edu['oil_override']
    oil = max(45, min(140, oil))
    # 비용 배수: 80 기준 1.0
    cost_mult = round(0.75 + (oil / BASE_OIL) * 0.25, 3)
    # 장거리 추가 부담
    longhaul_fuel_mult = round(0.7 + (oil / BASE_OIL) * 0.3, 3)
    level = '낮음' if oil < 70 else ('보통' if oil < 95 else '높음')
    return {
        'price': oil,
        'base': BASE_OIL,
        'level': level,
        'cost_mult': cost_mult,
        'longhaul_fuel_mult': longhaul_fuel_mult,
        'label': f'${oil}/배럴급',
        'kid': f'지금 가상 기름값 지수 {oil} ({level})',
        'events_affecting': [
            {'id': e['id'], 'title': e.get('kid_title') or e.get('title'), 'delta': e.get('oil_delta', 0)}
            for e in events if e.get('oil_delta')
        ],
    }


def get_world_multipliers(prog=None):
    """노선 수익 등에 곱할 주간 배수."""
    events = get_active_events(3)
    m = {
        'demand_mult': 1.0,
        'longhaul_mult': 1.0,
        'cargo_mult': 1.0,
        'tourism_mult': 1.0,
        'route_boost_tokens': [],
        'route_penalty_tokens': [],
        'events': events,
    }
    for e in events:
        m['demand_mult'] *= e.get('demand_mult', 1.0)
        m['longhaul_mult'] *= e.get('longhaul_mult', 1.0)
        m['cargo_mult'] *= e.get('cargo_mult', 1.0)
        m['tourism_mult'] *= e.get('tourism_mult', 1.0)
        m['route_boost_tokens'].extend(e.get('route_boost') or [])
        m['route_penalty_tokens'].extend(e.get('route_penalty') or [])
    oil = get_oil_price(prog)
    m['oil'] = oil
    m['fuel_cost_mult'] = oil['cost_mult']
    m['longhaul_fuel_mult'] = oil['longhaul_fuel_mult']
    # 정규화 (너무 극단 방지)
    for k in ('demand_mult', 'longhaul_mult', 'cargo_mult', 'tourism_mult'):
        m[k] = round(max(0.7, min(1.4, m[k])), 3)
    return m


def apply_route_world_mult(route, mults):
    """노선 dict 또는 template 성격에 세계 이벤트 배수 적용 후 배수 반환."""
    if not mults:
        return 1.0
    rtype = (route.get('type') or '').lower()
    name = f"{route.get('route', '')} {route.get('name', '')}".upper()
    tokens = ' '.join(str(t).upper() for t in (
        mults.get('route_boost_tokens') or []
    ))
    pen_tokens = ' '.join(str(t).upper() for t in (
        mults.get('route_penalty_tokens') or []
    ))
    m = mults.get('demand_mult', 1.0)
    if rtype == 'longhaul':
        m *= mults.get('longhaul_mult', 1.0)
        m /= max(0.85, mults.get('longhaul_fuel_mult', 1.0))
    elif rtype == 'international':
        m *= (mults.get('tourism_mult', 1.0) * 0.5 + 0.5)
        m /= max(0.9, (mults.get('fuel_cost_mult', 1.0) * 0.3 + 0.7))
    elif rtype == 'cargo':
        m *= mults.get('cargo_mult', 1.0)
    elif rtype == 'domestic':
        m *= (mults.get('tourism_mult', 1.0) * 0.4 + 0.6)
        m /= max(0.92, (mults.get('fuel_cost_mult', 1.0) * 0.2 + 0.8))
    else:
        m /= max(0.9, (mults.get('fuel_cost_mult', 1.0) * 0.25 + 0.75))

    boost = 1.0
    for t in mults.get('route_boost_tokens') or []:
        t_up = str(t).upper()
        if t_up in name or t_up == rtype.upper() or t_up in (rtype,):
            boost = max(boost, 1.12)
        if t_up in ('LONGHAUL', 'INTERNATIONAL', 'DOMESTIC', 'CARGO') and t_up == rtype.upper():
            boost = max(boost, 1.1)
    for t in mults.get('route_penalty_tokens') or []:
        t_up = str(t).upper()
        if t_up in name or t_up == rtype.upper():
            boost *= 0.9
    return round(max(0.65, min(1.55, m * boost)), 3)


def get_sky_times(prog=None):
    """오늘의 하늘 신문 3면."""
    events = get_active_events(3)
    oil = get_oil_price(prog)
    month = datetime.now().month
    cal = load_json('tourism_calendar.json')
    month_row = next((c for c in cal if c.get('month') == month), None) if isinstance(cal, list) else None
    papers = []
    for i, e in enumerate(events[:3]):
        papers.append({
            'section': ['1면 헤드라인', '경제 브리핑', '현장 스케치'][i] if i < 3 else f'{i+1}면',
            'icon': e.get('icon', '📰'),
            'title': e.get('kid_title') or e.get('title'),
            'headline': e.get('headline'),
            'why': e.get('why'),
            'lesson': e.get('lesson'),
            'tip': e.get('tip'),
            'category': e.get('category'),
            'event_id': e.get('id'),
        })
    if month_row:
        papers.append({
            'section': '시즌 캘린더',
            'icon': month_row.get('icon', '📅'),
            'title': month_row.get('theme'),
            'headline': month_row.get('desc'),
            'why': f"이달 핫 노선: {', '.join(month_row.get('hot_routes', [])[:4])}",
            'lesson': month_row.get('economy'),
            'tip': '관광 시즌에 맞춰 노선·요금을 생각해 보세요.',
            'category': 'tourism',
            'event_id': f'month_{month}',
        })
    papers.append({
        'section': '유가 게이지',
        'icon': '⛽',
        'title': oil['kid'],
        'headline': f"가상 유가 지수 {oil['price']} (기준 {oil['base']})",
        'why': '기름값이 오르면 장거리 비행 이익이 줄 수 있어요.',
        'lesson': '원자재 가격 → 항공 비용',
        'tip': '항공사 탭에서 노선 수익이 유가에 반응해요.',
        'category': 'oil',
        'event_id': 'oil_gauge',
        'oil': oil,
    })
    return {
        'date': today_str(),
        'week': week_key(),
        'masthead': '스카이 타임즈',
        'subtitle': '하늘을 보면 세계 경제가 보여요',
        'papers': papers,
        'oil': oil,
        'events': events,
        'keyword_of_week': (events[0].get('lesson') if events else '수요와 공급')[:40],
    }


def get_tourism_calendar():
    cal = load_json('tourism_calendar.json')
    month = datetime.now().month
    items = cal if isinstance(cal, list) else []
    current = next((c for c in items if c.get('month') == month), None)
    return {'month': month, 'current': current, 'year': items}


def get_flight_story(org_id=None, dest_id=None, route=None, callsign=None):
    stories = load_json('flight_stories.json')
    if not isinstance(stories, list):
        stories = []
    blob = f"{org_id or ''} {dest_id or ''} {route or ''} {callsign or ''}".upper()
    scored = []
    for s in stories:
        if s.get('id', '').endswith('default') or 'default' in (s.get('match') or []):
            continue
        hits = sum(1 for m in (s.get('match') or []) if str(m).upper() in blob)
        if hits:
            scored.append((hits, s))
    if scored:
        scored.sort(key=lambda x: -x[0])
        s = scored[0][1]
    else:
        defaults = [s for s in stories if 'default' in (s.get('match') or [])]
        if defaults:
            idx = _seed_int(f'{blob}-{today_str()}', 0, len(defaults) - 1)
            s = defaults[idx]
        else:
            s = {
                'id': 'fallback', 'emoji': '✈️', 'title': '하늘을 나는 이야기',
                'story': '이 비행에는 사람·화물·꿈이 함께 실려 있어요.',
                'economy': '항공은 이동과 무역을 이어 줘요.', 'type': 'general',
            }
    why = _why_this_flight(blob, s)
    return {
        'emoji': s.get('emoji', '✈️'),
        'title': s.get('title'),
        'story': s.get('story'),
        'economy': s.get('economy'),
        'type': s.get('type'),
        'why_title': why['title'],
        'why_text': why['text'],
        'story_id': s.get('id'),
    }


def _why_this_flight(blob, story):
    events = get_active_events(2)
    e0 = events[0] if events else {}
    type_map = {
        'tourism': ('관광 손님', '여행·휴가 수요가 이 노선을 만들었어요.'),
        'cargo': ('화물 수송', '무역 화물이 빠른 하늘길을 타고 있어요.'),
        'biz': ('비즈니스', '출장·회의 때문에 평일에도 비행이 떠요.'),
        'hub': ('허브 연결', '환승과 연결이 이 공항의 힘이에요.'),
        'domestic': ('국내 이동', '가까운 도시 사이 사람과 일정이 오가요.'),
        'human': ('사람 이야기', '만남·치료·가족 — 항공의 인간적 역할.'),
        'ops': ('항공 운영', '항공사 운영 자체도 큰 이동 경제예요.'),
    }
    t = story.get('type', 'general')
    title, text = type_map.get(t, ('하늘 위 연결', '사람·물건·돈이 움직이면 비행기가 떠요.'))
    if e0:
        text = f"{text} 이번 주 뉴스: {e0.get('kid_title') or e0.get('title')} — {e0.get('tip', '')}"
    return {'title': f"왜 이 비행이 떴을까? · {title}", 'text': text}


def get_airport_codex(prog):
    meta, edu = _meta(prog)
    stamps = set(edu.get('airport_stamps') or [])
    economy = load_json('airport_economy.json')
    facts = {a['id']: a for a in load_json('airport_daily_facts.json')} if isinstance(load_json('airport_daily_facts.json'), list) else {}
    items = []
    for a in (economy if isinstance(economy, list) else []):
        aid = a['id']
        fact = facts.get(aid, {})
        items.append({
            **a,
            'fact': fact.get('fact', ''),
            'stamped': aid in stamps,
        })
    return {
        'items': items,
        'stamped_count': len(stamps),
        'total': len(items),
        'parent_mode': edu.get('parent_mode', False),
    }


def stamp_airport(prog, airport_id):
    meta, edu = _meta(prog)
    economy = {a['id']: a for a in load_json('airport_economy.json')}
    if airport_id not in economy:
        return False, '공항을 찾을 수 없어요.'
    stamps = edu.setdefault('airport_stamps', [])
    if airport_id in stamps:
        return False, '이미 도장 찍은 공항이에요!'
    stamps.append(airport_id)
    _learn(edu, f"공항 {airport_id}: {economy[airport_id].get('economy', '')}")
    award_money(prog, 80000, f'공항 도감 {airport_id}')
    award_virtual_hours(prog, 0.1, f'공항 도감 {airport_id}')
    log_activity(prog, 'airport_codex', airport_id)
    _save(prog, meta)
    return True, f"{economy[airport_id].get('emoji', '')} {economy[airport_id].get('name')} 도장! +{format_krw(80000)}"


def get_trade_missions(prog):
    meta, edu = _meta(prog)
    done = set(edu.get('trade_done') or [])
    steps = edu.get('trade_step') or {}
    missions = load_json('trade_missions.json')
    out = []
    for m in (missions if isinstance(missions, list) else []):
        mid = m['id']
        step = int(steps.get(mid, 0))
        out.append({
            **m,
            'done': mid in done,
            'step': step,
            'total_steps': len(m.get('steps') or []),
            'current_step': (m.get('steps') or [None])[step] if step < len(m.get('steps') or []) else None,
        })
    return out


def advance_trade(prog, mission_id, quiz_answer=None):
    meta, edu = _meta(prog)
    missions = {m['id']: m for m in load_json('trade_missions.json')}
    m = missions.get(mission_id)
    if not m:
        return False, '미션 없음', None
    if mission_id in (edu.get('trade_done') or []):
        return False, '이미 완료한 무역 미션이에요.', None
    steps = m.get('steps') or []
    cur = int((edu.get('trade_step') or {}).get(mission_id, 0))
    if cur < len(steps):
        edu.setdefault('trade_step', {})[mission_id] = cur + 1
        _learn(edu, steps[cur].get('learn', ''))
        log_activity(prog, 'trade', f'{mission_id}:step{cur}')
        if cur + 1 < len(steps):
            _save(prog, meta)
            return True, f"단계 {cur+1}/{len(steps)} 완료! {steps[cur].get('learn', '')}", {
                'step': cur + 1, 'done': False, 'need_quiz': False
            }
        # finished steps → need quiz
        _save(prog, meta)
        return True, '마지막 퀴즈에 답해주세요!', {
            'step': cur + 1, 'done': False, 'need_quiz': True, 'quiz': m.get('quiz')
        }
    # quiz phase
    quiz = m.get('quiz') or {}
    if quiz_answer is None:
        return False, '퀴즈 답이 필요해요.', {'need_quiz': True, 'quiz': quiz}
    if int(quiz_answer) != int(quiz.get('answer', -1)):
        return False, '다시 생각해 볼까요? 힌트: 무역과 시간의 관계!', {'need_quiz': True, 'quiz': quiz}
    edu.setdefault('trade_done', []).append(mission_id)
    _learn(edu, m.get('lesson', ''))
    money = award_money(prog, m.get('reward_money', 300000), f'무역 미션 {m.get("title")}')
    award_virtual_hours(prog, m.get('reward_hours', 0.3), f'무역 {mission_id}')
    log_activity(prog, 'trade_complete', mission_id)
    _save(prog, meta)
    return True, f"무역 체인 완료! {m.get('lesson')} +{format_krw(money)}", {
        'done': True, 'money': money, 'lesson': m.get('lesson')
    }


def get_night_sky_list(prog):
    meta, edu = _meta(prog)
    done = set(edu.get('night_sky_done') or [])
    stories = load_json('night_sky_stories.json')
    return [{
        **s,
        'done': s['id'] in done,
        'chapter_count': len(s.get('chapters') or []),
    } for s in (stories if isinstance(stories, list) else [])]


def complete_night_sky(prog, story_id):
    meta, edu = _meta(prog)
    stories = {s['id']: s for s in load_json('night_sky_stories.json')}
    s = stories.get(story_id)
    if not s:
        return False, '스토리를 찾을 수 없어요.'
    if story_id in (edu.get('night_sky_done') or []):
        return False, '이미 읽은 밤하늘 항로예요.'
    edu.setdefault('night_sky_done', []).append(story_id)
    _learn(edu, s.get('economy_note', ''))
    money = award_money(prog, s.get('reward_money', 200000), f'밤하늘 항로 {s.get("title")}')
    award_virtual_hours(prog, s.get('reward_hours', 0.3), f'night_sky {story_id}')
    log_activity(prog, 'night_sky', story_id)
    _save(prog, meta)
    return True, f"{s.get('emoji', '🌙')} {s.get('title')} 완주! +{format_krw(money)}"


def run_pricing_lab(prog, scenario_id, price_pct):
    meta, edu = _meta(prog)
    cfg = load_json('pricing_lab.json')
    if not isinstance(cfg, dict):
        return False, '요금 실험실 설정 없음', None
    scenarios = {s['id']: s for s in cfg.get('scenarios', [])}
    sc = scenarios.get(scenario_id)
    if not sc:
        return False, '시나리오 없음', None
    try:
        pct = float(price_pct)
    except (TypeError, ValueError):
        return False, '가격 비율이 이상해요', None
    pct = max(0.5, min(1.6, pct))
    price = int(sc['base_price'] * pct)
    # demand response
    elast = float(sc.get('elasticity', 1.0))
    demand_factor = max(0.25, 1.0 - elast * (pct - 1.0))
    # world event tourism boost
    mults = get_world_multipliers(prog)
    demand_factor *= (0.85 + 0.15 * mults.get('tourism_mult', 1.0))
    passengers = int(min(sc['seats'], sc['base_demand'] * demand_factor))
    revenue = passengers * price
    cost = int(sc['cost_per_flight'] * mults.get('fuel_cost_mult', 1.0))
    profit = revenue - cost
    load_factor = round(passengers / sc['seats'] * 100, 1)
    edu['pricing_plays'] = edu.get('pricing_plays', 0) + 1
    best = edu.setdefault('pricing_best', {})
    prev = best.get(scenario_id)
    is_best = prev is None or profit > prev.get('profit', -10**18)
    if is_best:
        best[scenario_id] = {'profit': profit, 'pct': pct, 'load': load_factor}
    _learn(edu, sc.get('hint', '가격과 수요는 시소처럼 움직여요.'))
    # small reward once per day max 3
    reward = 0
    dl_key = f"pricing_{today_str()}"
    week_choices = edu.setdefault('week_choices', {})
    plays_today = week_choices.get(dl_key, 0)
    if plays_today < 3:
        reward = award_money(prog, 100000, '요금 실험실 학습')
        week_choices[dl_key] = plays_today + 1
        award_virtual_hours(prog, 0.1, 'pricing_lab')
    log_activity(prog, 'pricing_lab', scenario_id)
    _save(prog, meta)
    result = {
        'scenario': sc,
        'price': price,
        'price_pct': pct,
        'passengers': passengers,
        'seats': sc['seats'],
        'load_factor_pct': load_factor,
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'formatted_profit': format_krw(profit),
        'formatted_revenue': format_krw(revenue),
        'formatted_cost': format_krw(cost),
        'is_best': is_best,
        'lesson': sc.get('hint'),
        'oil_note': mults.get('oil', {}).get('kid'),
        'money_reward': reward,
        'kid_summary': (
            f"표 {format_krw(price)} → 손님 {passengers}명 (탑승률 {load_factor}%) · "
            f"이익 {format_krw(profit)}"
        ),
    }
    return True, '실험 완료!', result


def get_pricing_lab_info(prog):
    cfg = load_json('pricing_lab.json')
    meta, edu = _meta(prog)
    return {
        'scenarios': cfg.get('scenarios', []) if isinstance(cfg, dict) else [],
        'price_options_pct': cfg.get('price_options_pct', [0.7, 1.0, 1.3]) if isinstance(cfg, dict) else [1.0],
        'plays': edu.get('pricing_plays', 0),
        'best': edu.get('pricing_best', {}),
        'oil': get_oil_price(prog),
    }


def get_hub_missions(prog):
    meta, edu = _meta(prog)
    done = set(edu.get('hub_done') or [])
    missions = load_json('hub_missions.json')
    return [{**m, 'done': m['id'] in done} for m in (missions if isinstance(missions, list) else [])]


def complete_hub_mission(prog, mission_id, answer):
    meta, edu = _meta(prog)
    missions = {m['id']: m for m in load_json('hub_missions.json')}
    m = missions.get(mission_id)
    if not m:
        return False, '미션 없음'
    if mission_id in (edu.get('hub_done') or []):
        return False, '이미 완료했어요.'
    quiz = m.get('quiz') or {}
    if int(answer) != int(quiz.get('answer', -1)):
        return False, '다시 생각해 볼까요? 허브는 연결의 힘!'
    edu.setdefault('hub_done', []).append(mission_id)
    _learn(edu, (m.get('lessons') or ['허브 학습'])[0])
    money = award_money(prog, m.get('reward_money', 300000), f"허브 미션 {m.get('title')}")
    award_virtual_hours(prog, m.get('reward_hours', 0.3), f'hub {mission_id}')
    log_activity(prog, 'hub_mission', mission_id)
    _save(prog, meta)
    return True, f"허브 미션 완료! +{format_krw(money)}"


def get_tradeoffs(prog):
    meta, edu = _meta(prog)
    items = load_json('ops_tradeoffs.json')
    today = today_str()
    done_today = edu.get('tradeoff_date') == today
    done_ids = set(edu.get('tradeoff_done') or []) if done_today else set()
    # daily 1 featured
    if isinstance(items, list) and items:
        idx = _seed_int(f'tradeoff-{today}', 0, len(items) - 1)
        featured = items[idx]
    else:
        featured = None
    return {
        'items': items if isinstance(items, list) else [],
        'featured': featured,
        'done_ids_today': list(done_ids),
        'can_play': not done_today or len(done_ids) < 2,
    }


def choose_tradeoff(prog, tradeoff_id, choice_id):
    meta, edu = _meta(prog)
    items = {t['id']: t for t in load_json('ops_tradeoffs.json')}
    t = items.get(tradeoff_id)
    if not t:
        return False, '선택지를 찾을 수 없어요.', None
    today = today_str()
    if edu.get('tradeoff_date') != today:
        edu['tradeoff_date'] = today
        edu['tradeoff_done'] = []
    if tradeoff_id in (edu.get('tradeoff_done') or []):
        return False, '오늘은 이미 이 선택을 했어요.', None
    if len(edu.get('tradeoff_done') or []) >= 2:
        return False, '오늘은 결정 2개까지! 내일 또 만나요.', None
    choice = next((c for c in t.get('choices', []) if c['id'] == choice_id), None)
    if not choice:
        return False, '잘못된 선택', None
    edu.setdefault('tradeoff_done', []).append(tradeoff_id)
    _learn(edu, choice.get('lesson', ''))
    money_delta = int(choice.get('money_delta', 0))
    if money_delta > 0:
        award_money(prog, money_delta, f"운영 결정: {t.get('title')}")
    elif money_delta < 0:
        from app.services.economy import spend_money
        spend_money(prog, abs(money_delta), f"운영 결정 비용: {t.get('title')}", 'ops')
    # reputation on airline if founded
    try:
        from app.services.pilot_features import get_airline_info, get_meta as pf_meta, save_meta as pf_save
        if get_airline_info(prog).get('founded'):
            m2 = pf_meta(prog)
            ops = m2.setdefault('airline_ops', {})
            ops['reputation'] = max(0, min(100, ops.get('reputation', 50) + int(choice.get('reputation_delta', 0))))
            # fleet condition bump if any
            rev = ops.setdefault('revenue', {})
            cond = rev.setdefault('fleet_condition', {})
            for aid in list(cond.keys())[:5]:
                cond[aid] = max(40, min(100, cond.get(aid, 85) + int(choice.get('condition_delta', 0))))
            pf_save(prog, m2)
    except Exception:
        pass
    log_activity(prog, 'tradeoff', f'{tradeoff_id}:{choice_id}')
    award_virtual_hours(prog, 0.15, 'ops_tradeoff')
    _save(prog, meta)
    return True, choice.get('lesson', '좋은 결정 연습!'), {
        'choice': choice,
        'money_delta': money_delta,
        'lesson': choice.get('lesson'),
    }


def get_alliance_map(prog):
    partners = load_json('airline_codeshare_partners.json')
    codeshare_state = {}
    try:
        from app.services.pilot_features import get_meta as pf_meta
        ops = pf_meta(prog).get('airline_ops', {})
        codeshare_state = (ops.get('revenue') or {}).get('codeshare') or {}
    except Exception:
        pass
    nodes = [
        {'id': 'ME', 'name': '우리 항공사', 'emoji': '🏠', 'region': '한국', 'x': 50, 'y': 50, 'self': True}
    ]
    edges = []
    region_pos = {
        '동남아': (70, 70), '유럽': (25, 35), '일본': (75, 40), '화물': (50, 80),
    }
    for i, p in enumerate(partners if isinstance(partners, list) else []):
        pos = region_pos.get(p.get('region'), (30 + i * 15, 30 + (i % 3) * 20))
        active = bool(codeshare_state.get(p['id']))
        nodes.append({
            'id': p['id'],
            'name': p.get('name'),
            'emoji': p.get('emoji'),
            'region': p.get('region'),
            'desc': p.get('desc'),
            'share_pct': p.get('share_pct'),
            'active': active,
            'x': pos[0],
            'y': pos[1],
            'self': False,
        })
        edges.append({
            'from': 'ME', 'to': p['id'], 'active': active,
            'label': f"{p.get('share_pct', 0)}% 공유" if active else '미연결',
        })
    return {
        'nodes': nodes,
        'edges': edges,
        'lesson': '코드셰어는 서로 손님을 연결해 더 멀리 보내 주는 제휴예요. 내 비행기가 없어도 파트너 노선으로 네트워크가 커져요.',
        'kid': '친구 항공사와 손을 잡으면 세계 지도가 넓어져요!',
    }


def get_economy_quiz(prog):
    meta, edu = _meta(prog)
    bank = load_json('economy_quiz.json')
    if not isinstance(bank, list) or not bank:
        return None
    eq = edu.get('economy_quiz') or {}
    today = today_str()
    if eq.get('date') != today:
        ids = [q['id'] for q in bank]
        # 5 questions
        rng = random.Random(f'eq-{today}')
        pick = rng.sample(ids, min(5, len(ids)))
        eq = {'date': today, 'ids': pick, 'answers': {}, 'done': False, 'score': 0}
        edu['economy_quiz'] = eq
        _save(prog, meta)
    by_id = {q['id']: q for q in bank}
    questions = []
    for qid in eq.get('ids', []):
        q = by_id.get(qid)
        if not q:
            continue
        questions.append({
            'id': q['id'],
            'question': q['question'],
            'choices': q['choices'],
            'answered': qid in (eq.get('answers') or {}),
            'user_answer': (eq.get('answers') or {}).get(qid),
        })
    return {
        'date': eq.get('date'),
        'done': eq.get('done', False),
        'score': eq.get('score', 0),
        'total': len(questions),
        'questions': questions,
        'parent_blurb': '아이와 함께: 수요·공급, 유가, 무역, 허브 개념을 퀴즈로 복습해요.',
    }


def submit_economy_quiz(prog, question_id, answer):
    meta, edu = _meta(prog)
    bank = {q['id']: q for q in load_json('economy_quiz.json')}
    eq = edu.get('economy_quiz') or {}
    if eq.get('date') != today_str():
        get_economy_quiz(prog)
        meta, edu = _meta(prog)
        eq = edu.get('economy_quiz') or {}
    if eq.get('done'):
        return False, '오늘 경제 퀴즈는 끝났어요!', None
    q = bank.get(question_id)
    if not q or question_id not in (eq.get('ids') or []):
        return False, '문제가 없어요.', None
    if question_id in (eq.get('answers') or {}):
        return False, '이미 답한 문제예요.', None
    correct = int(answer) == int(q.get('answer', -1))
    eq.setdefault('answers', {})[question_id] = int(answer)
    if correct:
        eq['score'] = eq.get('score', 0) + 1
        _learn(edu, q.get('explanation', ''))
    money = 0
    if len(eq['answers']) >= len(eq.get('ids') or []):
        eq['done'] = True
        score = eq.get('score', 0)
        total = len(eq['ids'])
        if score >= total:
            money = award_money(prog, 500000, '경제 퀴즈 만점')
        elif score >= total * 0.6:
            money = award_money(prog, 300000, '경제 퀴즈 통과')
        else:
            money = award_money(prog, 150000, '경제 퀴즈 참여')
        award_virtual_hours(prog, 0.25, 'economy_quiz')
        log_activity(prog, 'economy_quiz', f'{score}/{total}')
    edu['economy_quiz'] = eq
    _save(prog, meta)
    return True, q.get('explanation', ''), {
        'correct': correct,
        'explanation': q.get('explanation'),
        'score': eq.get('score', 0),
        'done': eq.get('done', False),
        'money': money,
    }


def get_letter_milestones(prog):
    meta, edu = _meta(prog)
    milestones = load_json('future_letter_milestones.json')
    done = edu.get('letter_milestones') or {}
    hours = get_total_hours(prog)
    badges = UserBadge.query.count()
    first = bool(prog.first_flight_done)
    airline = False
    try:
        from app.services.pilot_features import get_airline_info
        airline = bool(get_airline_info(prog).get('founded'))
    except Exception:
        pass
    lessons = len(edu.get('lessons_learned') or [])
    out = []
    for m in (milestones if isinstance(milestones, list) else []):
        req = m.get('require') or {}
        unlocked = False
        rtype = req.get('type')
        if rtype == 'first_flight':
            unlocked = first
        elif rtype == 'hours':
            unlocked = hours >= req.get('value', 0)
        elif rtype == 'badges':
            unlocked = badges >= req.get('value', 0)
        elif rtype == 'airline_founded':
            unlocked = airline
        elif rtype == 'economy_lessons':
            unlocked = lessons >= req.get('value', 0)
        entry = done.get(m['id'])
        out.append({
            **m,
            'unlocked': unlocked,
            'completed': bool(entry),
            'response': (entry or {}).get('text'),
            'completed_at': (entry or {}).get('at'),
        })
    letter = FutureLetter.query.first()
    return {
        'has_root_letter': letter is not None,
        'root_opened': letter.is_opened if letter else False,
        'root_content': letter.content if letter and letter.is_opened else None,
        'milestones': out,
        'hours': hours,
        'badges': badges,
    }


def write_milestone_letter(prog, milestone_id, text):
    meta, edu = _meta(prog)
    milestones = {m['id']: m for m in load_json('future_letter_milestones.json')}
    m = milestones.get(milestone_id)
    if not m:
        return False, '마일스톤 없음'
    status = {x['id']: x for x in get_letter_milestones(prog)['milestones']}
    st = status.get(milestone_id)
    if not st or not st.get('unlocked'):
        return False, '아직 열리지 않은 마일스톤이에요.'
    if st.get('completed'):
        return False, '이미 작성했어요.'
    text = (text or '').strip()
    if len(text) < 5:
        return False, '한 줄 이상 적어주세요.'
    edu.setdefault('letter_milestones', {})[milestone_id] = {
        'text': text, 'at': datetime.now().isoformat(),
    }
    money = award_money(prog, 200000, f"미래 편지 마일스톤 {m.get('title')}")
    award_virtual_hours(prog, 0.2, f'letter_ml {milestone_id}')
    log_activity(prog, 'letter_milestone', milestone_id)
    _save(prog, meta)
    return True, f"{m.get('future_voice', '')} +{format_krw(money)}"


def build_ceo_report(prog):
    meta, edu = _meta(prog)
    wk = week_key()
    mults = get_world_multipliers(prog)
    oil = mults.get('oil') or get_oil_price(prog)
    sky = get_sky_times(prog)
    events = mults.get('events') or []
    # activity this week rough
    log = prog._json('activity_log', [])
    week_acts = [a for a in log if (a.get('date') or '') >= today_str()[:8]]  # soft filter
    trade_n = len(edu.get('trade_done') or [])
    hub_n = len(edu.get('hub_done') or [])
    night_n = len(edu.get('night_sky_done') or [])
    lessons = edu.get('lessons_learned') or []
    good = []
    if trade_n:
        good.append(f'무역 미션 {trade_n}개 완료')
    if hub_n:
        good.append(f'허브 학습 {hub_n}개')
    if night_n:
        good.append(f'밤하늘 항로 {night_n}편')
    if edu.get('pricing_plays'):
        good.append(f'요금 실험 {edu.get("pricing_plays")}회')
    if not good:
        good.append('이번 주 세계 탭에서 첫 미션을 해보세요!')
    news_impact = []
    for e in events[:3]:
        news_impact.append({
            'title': e.get('kid_title') or e.get('title'),
            'tip': e.get('tip'),
            'lesson': e.get('lesson'),
        })
    next_hint = events[0].get('tip') if events else '관광 시즌 노선을 살펴보세요.'
    claimed = edu.get('ceo_report_week') == wk and edu.get('ceo_report_claimed')
    parent_keywords = []
    for L in lessons[-5:]:
        parent_keywords.append(L[:48])
    if not parent_keywords:
        parent_keywords = [e.get('lesson', '')[:48] for e in events[:3]]
    return {
        'week': wk,
        'title': '주간 미니 CEO 리포트',
        'oil': oil,
        'good_choices': good,
        'news_impact': news_impact,
        'next_hint': next_hint,
        'keyword_of_week': sky.get('keyword_of_week'),
        'lessons_count': len(lessons),
        'parent_keywords': parent_keywords,
        'claimed': claimed,
        'can_claim': not claimed,
    }


def claim_ceo_report(prog):
    meta, edu = _meta(prog)
    wk = week_key()
    if edu.get('ceo_report_week') == wk and edu.get('ceo_report_claimed'):
        return False, '이번 주 리포트 보상은 이미 받았어요.'
    edu['ceo_report_week'] = wk
    edu['ceo_report_claimed'] = True
    money = award_money(prog, 250000, '주간 CEO 리포트')
    award_virtual_hours(prog, 0.2, 'ceo_report')
    log_activity(prog, 'ceo_report', wk)
    _save(prog, meta)
    return True, f'리포트 확인! +{format_krw(money)}'


def set_parent_mode(prog, enabled):
    meta, edu = _meta(prog)
    edu['parent_mode'] = bool(enabled)
    _save(prog, meta)
    return True, '부모 모드 ' + ('ON' if enabled else 'OFF')


def get_parent_summary(prog):
    meta, edu = _meta(prog)
    report = build_ceo_report(prog)
    sky = get_sky_times(prog)
    return {
        'enabled': edu.get('parent_mode', False),
        'today_headline': (sky.get('papers') or [{}])[0].get('title'),
        'keywords': report.get('parent_keywords') or [],
        'talk_prompts': [
            '오늘 신문에 나온 비행기 소식 중 뭐가 제일 재밌었어?',
            '기름값이 오르면 여행 값이 왜 달라질까?',
            '제주랑 미국 비행은 손님 종류가 어떻게 다를까?',
            '허브 공항이 왜 필요할까 같이 그려볼까?',
        ],
        'lessons_learned': (edu.get('lessons_learned') or [])[-8:],
    }


def _learn(edu, text):
    if not text:
        return
    lessons = edu.setdefault('lessons_learned', [])
    if text not in lessons:
        lessons.append(text)
    if len(lessons) > 80:
        edu['lessons_learned'] = lessons[-80:]


def get_world_hub_summary(prog):
    sky = get_sky_times(prog)
    mults = get_world_multipliers(prog)
    meta, edu = _meta(prog)
    return {
        'sky_times': sky,
        'oil': mults.get('oil'),
        'events': mults.get('events'),
        'multipliers': {
            'demand': mults.get('demand_mult'),
            'longhaul': mults.get('longhaul_mult'),
            'cargo': mults.get('cargo_mult'),
            'tourism': mults.get('tourism_mult'),
            'fuel_cost': mults.get('fuel_cost_mult'),
        },
        'tourism': get_tourism_calendar(),
        'stats': {
            'trade_done': len(edu.get('trade_done') or []),
            'hub_done': len(edu.get('hub_done') or []),
            'night_sky': len(edu.get('night_sky_done') or []),
            'stamps': len(edu.get('airport_stamps') or []),
            'lessons': len(edu.get('lessons_learned') or []),
            'pricing_plays': edu.get('pricing_plays', 0),
        },
        'parent_mode': edu.get('parent_mode', False),
        'ceo_report': build_ceo_report(prog),
        'wallet': get_wallet_summary(prog),
    }


def story_for_logbook_route(route):
    if not route:
        return get_flight_story()
    parts = str(route).replace('→', '-').replace('–', '-').split('-')
    org = parts[0].strip() if parts else ''
    dest = parts[1].strip() if len(parts) > 1 else ''
    return get_flight_story(org_id=org, dest_id=dest, route=route)
