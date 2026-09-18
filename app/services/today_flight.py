"""Today's captain duty: one flight built from logbook habits + short play steps."""
from collections import Counter
from app.models import db, LogbookEntry
from app.services.gamification import today_str, log_activity, award_virtual_hours
from app.services.economy import award_money
from app.services.airport_quiz import AIRPORTS, submit_quiz_answer

STEP_REWARD = 50_000
COMPLETE_BONUS = 300_000
FALLBACK_ROUTE = 'ICN-CJU'
FALLBACK_FLIGHT = 'PD001'
FALLBACK_AIRCRAFT = 'B737-800'
FALLBACK_HOURS = 1.0

CORE_STEPS = [
    {'id': 'airport', 'emoji': '🔤', 'title': '공항 알아맞히기', 'kind': 'quiz',
     'blurb': '오늘 도착하는 도시는 어디일까요?'},
    {'id': 'refuel', 'emoji': '⛽', 'title': '기름 넣기', 'kind': 'minigame', 'game_id': 'refuel',
     'blurb': '넘치지 않게 딱 멈춰요!'},
    {'id': 'luggage', 'emoji': '🧳', 'title': '짐 싣기', 'kind': 'minigame', 'game_id': 'luggage',
     'blurb': '비행기가 기울지 않게 짐을 옮겨요!'},
    {'id': 'landing', 'emoji': '🛬', 'title': '활주로 맞추기', 'kind': 'minigame', 'game_id': 'landing',
     'blurb': '바람 속에서 가운데로!'},
    {'id': 'logbook', 'emoji': '📖', 'title': '로그에 찍기', 'kind': 'logbook',
     'blurb': '오늘 이 편이 기록에 남아요.'},
]

BONUS_STEPS = [
    {'id': 'checklist', 'emoji': '📋', 'title': '출발 전 점검', 'kind': 'checklist',
     'blurb': '세 가지만 확인해요.'},
    {'id': 'atc', 'emoji': '🎙️', 'title': '관제탑에 말하기', 'kind': 'atc',
     'blurb': '이 문장을 소리 내 읽어봐요.'},
]

MORE_CATALOG = [
    {'id': 'learn', 'href': '/learn', 'label': '학습', 'emoji': '🎓',
     'types': ['quiz', 'flashcard', 'scenario']},
    {'id': 'arcade', 'href': '/minigames', 'label': '아케이드', 'emoji': '🎮',
     'types': ['game']},
    {'id': 'world', 'href': '/world', 'label': '세계', 'emoji': '🌍',
     'types': ['pricing_lab', 'airport_codex', 'trade', 'economy_quiz', 'hub_mission']},
    {'id': 'captain_life', 'href': '/captain-life', 'label': '기장생활', 'emoji': '👑',
     'types': ['captain_duty']},
    {'id': 'shop', 'href': '/shop', 'label': '상점', 'emoji': '🏪',
     'types': ['shop']},
    {'id': 'radar', 'href': '/radar', 'label': '레이더', 'emoji': '📡',
     'types': ['radar']},
    {'id': 'atc', 'href': '/atc-english', 'label': '항공영어', 'emoji': '🎧',
     'types': ['atc']},
    {'id': 'aircraft', 'href': '/aircraft', 'label': '기종', 'emoji': '🛩️',
     'types': ['aircraft']},
    {'id': 'planner', 'href': '/flight-planner', 'label': '플래너', 'emoji': '🗺️',
     'types': ['planner']},
    {'id': 'badges', 'href': '/badges', 'label': '뱃지', 'emoji': '🏅',
     'types': []},
    {'id': 'medals', 'href': '/medals', 'label': '훈장', 'emoji': '🏆',
     'types': []},
    {'id': 'sim', 'href': '/simulation', 'label': '기장석', 'emoji': '🕹️',
     'types': ['sim']},
    {'id': 'career', 'href': '/korea-career', 'label': '커리어', 'emoji': '🇰🇷',
     'types': ['career']},
    {'id': 'guide', 'href': '/guide', 'label': '가이드', 'emoji': '📖',
     'types': []},
]

AIRPORT_BY_CODE = {a['code']: a for a in AIRPORTS}

ATC_LINE = {
    'en': 'Request pushback, please.',
    'ko': '푸시백 요청합니다.',
    'tip': '출발 전에 관제탑에 이렇게 말해요.',
}

CHECKLIST_ITEMS = [
    {'id': 'c1', 'text': '날씨 봤어요'},
    {'id': 'c2', 'text': '연료 충분해요'},
    {'id': 'c3', 'text': '안전벨트 확인했어요'},
]


def _norm_route(route):
    raw = (route or '').upper().replace('→', '-').replace('–', '-').replace(' ', '')
    parts = [p for p in raw.split('-') if p]
    if len(parts) >= 2 and 3 <= len(parts[0]) <= 4 and 3 <= len(parts[1]) <= 4:
        return f'{parts[0]}-{parts[1]}'
    return None


def airport_label(code):
    row = AIRPORT_BY_CODE.get((code or '').upper())
    if row:
        return f"{row['country_emoji']} {row['city_kr']}"
    return code or '?'


def pick_route_from_entries(entries):
    """entries: iterable of objects with route, flight_number, aircraft, hours."""
    routes = Counter()
    by_route = {}
    for e in entries or []:
        key = _norm_route(getattr(e, 'route', None) or (e.get('route') if isinstance(e, dict) else ''))
        if not key:
            continue
        routes[key] += 1
        bucket = by_route.setdefault(key, {'flights': Counter(), 'ac': Counter(), 'hours': []})
        fn = getattr(e, 'flight_number', None) or (e.get('flight_number') if isinstance(e, dict) else '') or ''
        ac = getattr(e, 'aircraft', None) or (e.get('aircraft') if isinstance(e, dict) else '') or ''
        hrs = getattr(e, 'hours', None) if not isinstance(e, dict) else e.get('hours')
        if fn:
            bucket['flights'][fn] += 1
        if ac:
            bucket['ac'][ac] += 1
        try:
            if hrs and float(hrs) > 0:
                bucket['hours'].append(float(hrs))
        except (TypeError, ValueError):
            pass
    if not routes:
        origin, dest = FALLBACK_ROUTE.split('-')
        return {
            'route': FALLBACK_ROUTE,
            'origin': origin,
            'dest': dest,
            'origin_name': airport_label(origin),
            'dest_name': airport_label(dest),
            'flight_number': FALLBACK_FLIGHT,
            'aircraft': FALLBACK_AIRCRAFT,
            'hours': FALLBACK_HOURS,
        }
    route = routes.most_common(1)[0][0]
    origin, dest = route.split('-', 1)
    info = by_route[route]
    hours = round(sum(info['hours']) / len(info['hours']), 1) if info['hours'] else FALLBACK_HOURS
    return {
        'route': route,
        'origin': origin,
        'dest': dest,
        'origin_name': airport_label(origin),
        'dest_name': airport_label(dest),
        'flight_number': (info['flights'].most_common(1)[0][0] if info['flights'] else FALLBACK_FLIGHT),
        'aircraft': (info['ac'].most_common(1)[0][0] if info['ac'] else FALLBACK_AIRCRAFT),
        'hours': hours,
    }


def _duty_question(dest_code):
    target = AIRPORT_BY_CODE.get((dest_code or '').upper())
    if not target:
        target = AIRPORT_BY_CODE.get('CJU') or AIRPORTS[0]
    others = [a for a in AIRPORTS if a['code'] != target['code']]
    import random
    rng = random.Random(f"{today_str()}-{target['code']}")
    choices = [target] + rng.sample(others, min(3, len(others)))
    rng.shuffle(choices)
    return {
        'type': 'code_to_city',
        'target_code': target['code'],
        'prompt': f"{target['code']} 공항은 어느 도시인가요?",
        'hint': target['hint'],
        'choices': [{'code': c['code'], 'text': f"{c['country_emoji']} {c['city_kr']}"} for c in choices],
    }


def _empty_duty(flight):
    return {
        'date': today_str(),
        'flight': flight,
        'done': [],
        'skipped': [],
        'bonus_done': [],
        'logged': False,
        'bonus_claimed': False,
        'airport_q': _duty_question(flight.get('dest')),
        'checklist': [],
    }


def _load_duty(prog):
    meta = prog._json('pilot_meta', {})
    duty = meta.get('today_flight') or {}
    if duty.get('date') != today_str() or not duty.get('flight'):
        return None
    return duty


def _save_duty(prog, duty):
    meta = prog._json('pilot_meta', {})
    meta['today_flight'] = duty
    prog.set_json('pilot_meta', meta)


def get_today_duty(prog, entries=None):
    duty = _load_duty(prog)
    if not duty:
        if entries is None:
            entries = LogbookEntry.query.all()
        flight = pick_route_from_entries(entries)
        duty = _empty_duty(flight)
        _save_duty(prog, duty)
        try:
            db.session.commit()
        except Exception:
            pass
    return _public_duty(duty)


def _public_duty(duty):
    done = set(duty.get('done') or [])
    skipped = set(duty.get('skipped') or [])
    bonus_done = set(duty.get('bonus_done') or [])
    core_ids = [s['id'] for s in CORE_STEPS]
    finished = all(i in done or i in skipped for i in core_ids)
    steps = []
    for s in CORE_STEPS:
        steps.append({
            **s,
            'done': s['id'] in done,
            'skipped': s['id'] in skipped,
        })
    bonus = []
    for s in BONUS_STEPS:
        bonus.append({**s, 'done': s['id'] in bonus_done})
    flight = duty.get('flight') or {}
    next_step = None
    for s in steps:
        if not s['done'] and not s['skipped']:
            next_step = s['id']
            break
    return {
        'date': duty.get('date'),
        'flight': flight,
        'steps': steps,
        'bonus': bonus,
        'airport_q': duty.get('airport_q'),
        'checklist_items': CHECKLIST_ITEMS,
        'checklist_done': duty.get('checklist') or [],
        'atc': ATC_LINE,
        'core_done': len([s for s in steps if s['done'] or s['skipped']]),
        'core_total': len(CORE_STEPS),
        'complete': finished,
        'logged': bool(duty.get('logged')),
        'next_step': next_step,
        'bonus_claimed': bool(duty.get('bonus_claimed')),
    }


def skip_step(prog, step_id):
    if not _load_duty(prog):
        get_today_duty(prog)
    duty = _load_duty(prog)
    if not duty:
        return False, '오늘의 편이 없어요.', None
    ids = {s['id'] for s in CORE_STEPS} | {s['id'] for s in BONUS_STEPS}
    if step_id not in ids:
        return False, '없는 단계예요.', None
    if step_id in (duty.get('done') or []):
        return True, '이미 끝낸 단계예요.', _public_duty(duty)
    skipped = duty.setdefault('skipped', [])
    if step_id not in skipped and step_id in {s['id'] for s in CORE_STEPS}:
        skipped.append(step_id)
    if step_id in {s['id'] for s in BONUS_STEPS}:
        bd = duty.setdefault('bonus_done', [])
        if step_id not in bd:
            bd.append(step_id)
    _save_duty(prog, duty)
    log_activity(prog, 'today_flight', f'skip:{step_id}')
    try:
        db.session.commit()
    except Exception:
        pass
    return True, '이 단계는 건너뛰었어요.', _public_duty(duty)


def complete_step(prog, step_id, payload=None):
    payload = payload or {}
    duty = _load_duty(prog)
    if not duty:
        get_today_duty(prog)
        duty = _load_duty(prog)
    if not duty:
        return False, '오늘의 편이 없어요.', None

    core_ids = {s['id'] for s in CORE_STEPS}
    bonus_ids = {s['id'] for s in BONUS_STEPS}
    if step_id not in core_ids and step_id not in bonus_ids:
        return False, '없는 단계예요.', None

    money = 0
    msg = '완료!'

    if step_id == 'airport':
        answer = payload.get('answer_code')
        q = duty.get('airport_q') or {}
        if not answer:
            return False, '답을 골라 주세요.', None
        correct = answer == q.get('target_code')
        if not correct:
            return False, '다시 골라 볼까요? 힌트: ' + (q.get('hint') or ''), _public_duty(duty)
        try:
            submit_quiz_answer(prog, 'duty_q', True, q.get('target_code'))
        except Exception:
            pass

    if step_id == 'logbook' and not duty.get('logged'):
        ok, log_msg, _entry = _write_logbook(prog, duty['flight'])
        if not ok:
            return False, log_msg, None
        duty['logged'] = True

    if step_id == 'checklist':
        items = payload.get('items') or duty.get('checklist') or []
        duty['checklist'] = list(items)
        if len(duty['checklist']) < len(CHECKLIST_ITEMS):
            return False, '세 가지를 모두 체크해 주세요.', _public_duty(duty)

    first_time = False
    if step_id in core_ids:
        done = duty.setdefault('done', [])
        skipped = duty.setdefault('skipped', [])
        if step_id in skipped:
            skipped.remove(step_id)
        if step_id not in done:
            done.append(step_id)
            first_time = True
    else:
        bd = duty.setdefault('bonus_done', [])
        if step_id not in bd:
            bd.append(step_id)
            first_time = True

    if first_time:
        award_money(prog, STEP_REWARD, f'오늘의 편: {step_id}')
        money += STEP_REWARD
        msg = f'좋아요! +{STEP_REWARD:,}원'

    complete_now = False
    if all(s in (duty.get('done') or []) or s in (duty.get('skipped') or [])
           for s in core_ids) and not duty.get('bonus_claimed'):
        # require logbook actually done (not only skipped) for the big bonus
        if 'logbook' in (duty.get('done') or []):
            duty['bonus_claimed'] = True
            award_money(prog, COMPLETE_BONUS, '오늘의 편 완료')
            award_virtual_hours(prog, 0.5, '오늘의 편 완료')
            money += COMPLETE_BONUS
            msg = f'오늘 편 착륙! +{COMPLETE_BONUS:,}원'
            complete_now = True
            try:
                from app.services.gamification import auto_claim_daily_mission
                auto_claim_daily_mission(prog, 'm_captain_day')
            except Exception:
                pass

    _save_duty(prog, duty)
    log_activity(prog, 'today_flight', f'complete:{step_id}')
    try:
        db.session.commit()
    except Exception:
        pass
    public = _public_duty(duty)
    public['money_earned'] = money
    public['just_finished'] = complete_now
    return True, msg, public


def _write_logbook(prog, flight):
    fn = (flight.get('flight_number') or FALLBACK_FLIGHT)[:20]
    route = flight.get('route') or FALLBACK_ROUTE
    ac = flight.get('aircraft') or FALLBACK_AIRCRAFT
    try:
        hours = float(flight.get('hours') or FALLBACK_HOURS)
    except (TypeError, ValueError):
        hours = FALLBACK_HOURS
    if hours <= 0:
        hours = FALLBACK_HOURS
    existing = LogbookEntry.query.filter_by(
        date=today_str(), flight_number=fn, route=route
    ).first()
    if existing:
        return True, '이미 오늘 이 편이 기록돼 있어요.', existing
    entry = LogbookEntry(
        date=today_str(),
        flight_number=fn,
        aircraft=ac,
        route=route,
        hours=hours,
        notes='오늘의 편',
    )
    db.session.add(entry)
    log_activity(prog, 'logbook', fn)
    try:
        from app.services.economy import process_all_rewards
        process_all_rewards(prog)
    except Exception:
        pass
    return True, '로그북에 남겼어요!', entry


def rank_more_items(prog):
    log = prog._json('activity_log', [])
    type_counts = Counter((e.get('type') or '') for e in log)
    meta = prog._json('pilot_meta', {})
    extras = {
        'arcade': 0,
        'world': 0,
        'captain_life': 0,
    }
    mg = meta.get('minigames') or {}
    for g in mg.values():
        if isinstance(g, dict):
            extras['arcade'] += int(g.get('played') or 0)
    we = meta.get('world_edu') or {}
    extras['world'] += int(we.get('pricing_plays') or 0)
    extras['world'] += len(we.get('airport_stamps') or [])
    pe = meta.get('pilot_extras') or {}
    extras['captain_life'] += len(pe.get('fuel_quiz_history') or [])
    extras['captain_life'] += len(pe.get('crew_unlocked') or []) // 20

    scored = []
    for i, item in enumerate(MORE_CATALOG):
        score = 0
        for t in item.get('types') or []:
            score += type_counts.get(t, 0)
        score += extras.get(item['id'], 0)
        # stable default: unused items keep catalog order via tiny reverse index
        scored.append((score, -i, item))
    scored.sort(reverse=True)
    out = []
    for score, _neg, item in scored:
        out.append({
            'id': item['id'],
            'href': item['href'],
            'label': item['label'],
            'emoji': item['emoji'],
            'score': score,
        })
    return out
