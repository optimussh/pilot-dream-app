"""항공사 부가 수입원: 화물·임대·MRO·브리핑·코드셰어·훈련원·시즌특선"""
import hashlib
import logging
import random
from app.models import db

logger = logging.getLogger(__name__)
from app.services.gamification import load_json, today_str, week_key
from app.services.economy import (
    get_owned_aircraft, get_aircraft_catalog, award_money, spend_money, format_krw,
)
from app.services.pilot_features import get_airline_info

CATEGORY_ORDER = ['리저널', '소형', '중형', '대형', '클래식', '화물기']
LEASE_DAILY = {'리저널': 45000, '소형': 65000, '중형': 95000, '대형': 140000, '클래식': 80000, '화물기': 120000}
MRO_SHOP_PER_MECHANIC = 95000
MAINT_COST_PER_AIRCRAFT = 55000
CONDITION_WEAR_PER_FLIGHT = 0.4
URGENCY_MULT = {'low': 1.0, 'normal': 1.15, 'high': 1.35}


def _cat_rank(cat):
    try:
        return CATEGORY_ORDER.index(cat)
    except ValueError:
        return 1


def _seed_int(key, lo, hi):
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + h % (hi - lo + 1)


def _json_cfg(filename, default=None):
    data = load_json(filename)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data
    return default if default is not None else {}


def _json_list(filename):
    data = load_json(filename)
    return data if isinstance(data, list) else []


def ensure_revenue_state(ops):
    rev = ops.setdefault('revenue', {})
    defaults = {
        'cargo_date': '',
        'cargo_offers': [],
        'cargo_accepted': [],
        'cargo_completed': [],
        'leased_aircraft': [],
        'fleet_condition': {},
        'mro_desk': False,
        'fleet_maintain': False,
        'briefing_date': '',
        'briefing_items': [],
        'briefing_done': [],
        'codeshare': {},
        'training_date': '',
        'training_done': [],
        'seasonal_week': '',
        'seasonal_claimed': False,
    }
    for k, v in defaults.items():
        if k not in rev:
            rev[k] = list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)
    return rev


def _aircraft_on_routes(ops):
    used = set()
    for r in ops.get('routes', []):
        if r.get('active') and r.get('aircraft_id'):
            used.add(r['aircraft_id'])
    return used


def _idle_aircraft(prog, ops):
    owned = get_owned_aircraft(prog)
    used = _aircraft_on_routes(ops)
    return [a for a in owned if a not in used]


def _sync_fleet_condition(prog, ops):
    rev = ensure_revenue_state(ops)
    cond = rev.setdefault('fleet_condition', {})
    for aid in get_owned_aircraft(prog):
        cond.setdefault(aid, 85)


def _apply_condition_wear(ops):
    rev = ensure_revenue_state(ops)
    cond = rev.get('fleet_condition', {})
    for r in ops.get('routes', []):
        if not r.get('active'):
            continue
        aid = r.get('aircraft_id')
        if not aid:
            continue
        wear = r.get('flights_per_week', 7) * CONDITION_WEAR_PER_FLIGHT
        cond[aid] = max(20, cond.get(aid, 85) - wear)


def _condition_mult(aid, ops):
    rev = ensure_revenue_state(ops)
    c = rev.get('fleet_condition', {}).get(aid, 85)
    if c >= 80:
        return 1.0
    if c >= 60:
        return 0.92
    if c >= 40:
        return 0.82
    return 0.7


def get_route_condition_mult(route, ops):
    aid = route.get('aircraft_id')
    if not aid:
        return 1.0
    return _condition_mult(aid, ops)


def _generate_cargo_offers(date_key):
    cfg = _json_cfg('airline_cargo_contracts.json')
    templates = cfg.get('templates', [])
    routes = cfg.get('routes', [])
    if not templates or not routes:
        return []
    offers = []
    for i in range(cfg.get('daily_limit', 3)):
        tpl = templates[_seed_int(f'{date_key}-tpl-{i}', 0, len(templates) - 1)]
        rt = routes[_seed_int(f'{date_key}-rt-{i}', 0, len(routes) - 1)]
        dist_mult = 1 + rt.get('dist_km', 500) / 5000
        pay = int(tpl['base_pay'] * dist_mult * URGENCY_MULT.get(tpl.get('urgency', 'normal'), 1))
        oid = f'cargo_{date_key}_{i}'
        quiz_pool = cfg.get('quiz', [])
        quiz_item = None
        if quiz_pool:
            quiz_item = quiz_pool[_seed_int(f'{oid}-quiz', 0, len(quiz_pool) - 1)]
        offers.append({
            'id': oid,
            'template_id': tpl['id'],
            'name': tpl['name'],
            'emoji': tpl['emoji'],
            'route': rt['route'],
            'route_name': rt['name'],
            'weight_t': tpl['weight_t'],
            'urgency': tpl['urgency'],
            'min_category': tpl['min_category'],
            'pay': pay,
            'fuel_hint': tpl.get('fuel_hint', ''),
            'quiz': quiz_item,
            'status': 'open',
        })
    return offers


def _ensure_cargo_offers(ops):
    rev = ensure_revenue_state(ops)
    today = today_str()
    if rev.get('cargo_date') != today:
        rev['cargo_date'] = today
        rev['cargo_offers'] = _generate_cargo_offers(today)
        rev['cargo_accepted'] = []
        rev['cargo_completed'] = []
    offers = rev.get('cargo_offers', [])
    accepted = set(rev.get('cargo_accepted', []))
    completed = set(rev.get('cargo_completed', []))
    for o in offers:
        oid = o['id']
        if oid in completed:
            o['status'] = 'done'
        elif oid in accepted:
            o['status'] = 'active'
        else:
            o['status'] = 'open'
    return offers


def _ensure_briefings(ops):
    rev = ensure_revenue_state(ops)
    today = today_str()
    if rev.get('briefing_date') != today:
        pool = _json_list('airline_briefings.json')
        if not pool:
            rev['briefing_items'] = []
        else:
            idxs = list(range(len(pool)))
            random.seed(int(hashlib.md5(today.encode()).hexdigest()[:8], 16))
            random.shuffle(idxs)
            pick = idxs[:5]
            rev['briefing_items'] = [{**pool[i], 'idx': i} for i in pick]
        rev['briefing_date'] = today
        rev['briefing_done'] = []
    return rev.get('briefing_items', [])


def _current_season_event():
    events = _json_list('weekly_demand_events.json')
    if not events:
        return None
    wk = week_key()
    idx = _seed_int(f'season-{wk}', 0, len(events) - 1)
    ev = events[idx]
    return {**ev, 'week': wk}


def passive_income_weekly(prog, ops, routes, route_gross=0):
    """임대·MRO·코드셰어·시즌·훈련원 패시브 수입 (주간)"""
    rev = ensure_revenue_state(ops)
    _sync_fleet_condition(prog, ops)
    catalog = get_aircraft_catalog()
    pool = ops.get('staff_pool', {})

    lease_weekly = 0
    for aid in rev.get('leased_aircraft', []):
        ac = catalog.get(aid, {})
        daily = LEASE_DAILY.get(ac.get('category', '소형'), 60000)
        lease_weekly += daily * 7

    mro_weekly = 0
    mechs = len(pool.get('mechanic', []))
    if rev.get('mro_desk') and mechs > 0:
        mro_weekly = MRO_SHOP_PER_MECHANIC * mechs

    codeshare_weekly = 0
    partners = _json_list('airline_codeshare_partners.json')
    intl = sum(1 for r in routes if r.get('type') in ('international', 'longhaul'))
    cargo_n = sum(1 for r in routes if r.get('type') == 'cargo')
    enabled = rev.get('codeshare', {})
    for p in partners:
        if not enabled.get(p['id']):
            continue
        if p.get('min_cargo_routes') and cargo_n < p['min_cargo_routes']:
            continue
        if p.get('min_intl_routes') and intl < p['min_intl_routes']:
            continue
        codeshare_weekly += int(p.get('weekly_base', 0) * (p.get('share_pct', 40) / 40))

    seasonal_weekly = 0
    season = _current_season_event()
    if season and rev.get('seasonal_week') == season['week']:
        match = 0
        for r in routes:
            if not r.get('active'):
                continue
            route_str = r.get('route', '') + ' ' + r.get('name', '')
            for token in season.get('route_match', []):
                if token and token in route_str:
                    match += 1
                    break
            if season.get('cargo') and r.get('type') == 'cargo':
                match += 1
            if season.get('require_intl') and r.get('type') in ('international', 'longhaul'):
                match += 1
        if match:
            seasonal_weekly = int(season.get('bonus_money', 300000) * min(match, 3) / 7)

    training_passive = 0
    fos = len(pool.get('fo', [])) + len(pool.get('captain', []))
    if fos >= 2:
        training_passive = 45000 * min(fos, 4)

    maintain_cost = 0
    if rev.get('fleet_maintain'):
        active_ac = {r.get('aircraft_id') for r in routes if r.get('active') and r.get('aircraft_id')}
        maintain_cost = MAINT_COST_PER_AIRCRAFT * len(active_ac)

    total = lease_weekly + mro_weekly + codeshare_weekly + seasonal_weekly + training_passive - maintain_cost
    return total, {
        'lease': lease_weekly,
        'mro_shop': mro_weekly,
        'codeshare_partners': codeshare_weekly,
        'seasonal': seasonal_weekly,
        'training_passive': training_passive,
        'maintain_cost': maintain_cost,
        'leased_count': len(rev.get('leased_aircraft', [])),
        'mechanics': mechs,
    }


def get_revenue_panel(prog, ops):
    """수입원 탭 UI용 상태"""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return None
    rev = ensure_revenue_state(ops)
    _sync_fleet_condition(prog, ops)
    routes = [r for r in ops.get('routes', []) if r.get('active')]
    catalog = get_aircraft_catalog()
    owned = get_owned_aircraft(prog)
    used = _aircraft_on_routes(ops)
    idle = [a for a in owned if a not in used]

    cargo_offers = _ensure_cargo_offers(ops)
    briefings = _ensure_briefings(ops)
    season = _current_season_event()
    if rev.get('seasonal_week') != season['week'] if season else '':
        rev['seasonal_week'] = season['week'] if season else ''
        rev['seasonal_claimed'] = False

    school = _json_cfg('airline_flight_school.json')
    today = today_str()
    if rev.get('training_date') != today:
        rev['training_date'] = today
        rev['training_done'] = []

    fleet_rows = []
    for aid in owned:
        ac = catalog.get(aid, {})
        fleet_rows.append({
            'id': aid,
            'name': ac.get('name', aid),
            'category': ac.get('category', ''),
            'condition': rev.get('fleet_condition', {}).get(aid, 85),
            'on_route': aid in used,
            'leased': aid in rev.get('leased_aircraft', []),
            'lease_daily': LEASE_DAILY.get(ac.get('category', '소형'), 60000),
        })

    passive_total, passive_detail = passive_income_weekly(prog, ops, routes)
    partners = _json_list('airline_codeshare_partners.json')
    partner_rows = []
    intl = sum(1 for r in routes if r.get('type') in ('international', 'longhaul'))
    cargo_n = sum(1 for r in routes if r.get('type') == 'cargo')
    for p in partners:
        ok = True
        if p.get('min_intl_routes') and intl < p['min_intl_routes']:
            ok = False
        if p.get('min_cargo_routes') and cargo_n < p['min_cargo_routes']:
            ok = False
        partner_rows.append({
            **p,
            'enabled': rev.get('codeshare', {}).get(p['id'], False),
            'eligible': ok,
            'weekly_est': int(p.get('weekly_base', 0) * (p.get('share_pct', 40) / 40)) if ok else 0,
        })

    return {
        'cargo_offers': cargo_offers,
        'cargo_done': len(rev.get('cargo_completed', [])),
        'cargo_limit': _json_cfg('airline_cargo_contracts.json').get('daily_limit', 3),
        'briefings': briefings,
        'briefing_done': rev.get('briefing_done', []),
        'fleet': fleet_rows,
        'idle_count': len(idle),
        'mro_desk': rev.get('mro_desk', False),
        'fleet_maintain': rev.get('fleet_maintain', False),
        'mechanics': len(ops.get('staff_pool', {}).get('mechanic', [])),
        'codeshare_partners': partner_rows,
        'school_modules': school.get('modules', []),
        'training_done': rev.get('training_done', []),
        'training_limit': school.get('daily_limit', 3),
        'training_requires_fo': len(ops.get('staff_pool', {}).get('fo', [])) > 0,
        'seasonal': season,
        'seasonal_claimed': rev.get('seasonal_claimed', False),
        'passive_weekly': passive_total,
        'passive_detail': passive_detail,
        'passive_formatted': format_krw(passive_total),
        'quiz_pool': _json_cfg('airline_cargo_contracts.json').get('quiz', []),
        'ancillary': ops.get('ancillary', 'basic'),
    }


def fetch_revenue_dashboard(prog):
    """수입원 패널 생성 후 상태 저장"""
    from app.services.airline_ops import _ops, _save_ops, estimate_weekly_revenue
    info = get_airline_info(prog)
    if not info.get('founded'):
        return {
            'founded': False,
            'error': '먼저 항공사를 창업해주세요!',
            'revenue_panel': None,
        }
    ops = _ops(prog)
    try:
        panel = get_revenue_panel(prog, ops)
        _save_ops(prog, ops)
        db.session.commit()
        preview = estimate_weekly_revenue(prog, ops)
        return {
            'founded': True,
            'revenue_panel': panel,
            'revenue_preview': preview,
            'ancillary': ops.get('ancillary', 'basic'),
            'wallet': {'balance': prog.wallet_balance or 0},
        }
    except Exception:
        logger.exception('fetch_revenue_dashboard failed')
        db.session.rollback()
        raise


def accept_cargo(prog, offer_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    _ensure_cargo_offers(ops)
    offers = {o['id']: o for o in rev.get('cargo_offers', [])}
    if offer_id not in offers:
        return False, '화물 계약을 찾을 수 없어요.'
    if offer_id in rev.get('cargo_completed', []):
        return False, '이미 완료한 계약이에요.'
    if offer_id in rev.get('cargo_accepted', []):
        return False, '이미 수락한 계약이에요.'
    limit = _json_cfg('airline_cargo_contracts.json').get('daily_limit', 3)
    if len(rev.get('cargo_accepted', [])) >= limit:
        return False, '오늘은 더 이상 계약을 받을 수 없어요.'
    rev['cargo_accepted'] = rev.get('cargo_accepted', []) + [offer_id]
    _save_ops(prog, ops)
    db.session.commit()
    o = offers[offer_id]
    return True, f'{o["emoji"]} {o["name"]} ({o["route_name"]}) 계약 수락! 퀴즈 통과 후 {format_krw(o["pay"])}'


def complete_cargo(prog, offer_id, answer_idx):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!', 0
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    _ensure_cargo_offers(ops)
    offers = {o['id']: o for o in rev.get('cargo_offers', [])}
    if offer_id not in offers:
        return False, '화물 계약을 찾을 수 없어요.', 0
    if offer_id not in rev.get('cargo_accepted', []):
        return False, '먼저 계약을 수락해주세요!', 0
    if offer_id in rev.get('cargo_completed', []):
        return False, '이미 완료했어요.', 0
    o = offers[offer_id]
    q = o.get('quiz') or {'answer': 0}
    try:
        ans = int(answer_idx)
    except (TypeError, ValueError):
        ans = -1
    if ans != q.get('answer', 0):
        tip = q.get('tip', '다시 도전해보세요!')
        return False, f'오답! {tip}', 0
    pay = o['pay']
    award_money(prog, pay, f'화물 계약: {o["name"]} ({o["route"]})')
    rev['cargo_completed'] = rev.get('cargo_completed', []) + [offer_id]
    ops['xp'] = ops.get('xp', 0) + 4
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'✅ 화물 운송 완료! +{format_krw(pay)}', pay


def toggle_lease(prog, aircraft_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    owned = get_owned_aircraft(prog)
    if aircraft_id not in owned:
        return False, '보유하지 않은 기체예요.'
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    if aircraft_id in _aircraft_on_routes(ops):
        return False, '노선에 배치된 기체는 임대할 수 없어요.'
    leased = list(rev.get('leased_aircraft', []))
    catalog = get_aircraft_catalog()
    ac = catalog.get(aircraft_id, {})
    if aircraft_id in leased:
        leased.remove(aircraft_id)
        rev['leased_aircraft'] = leased
        _save_ops(prog, ops)
        db.session.commit()
        return True, f'{ac.get("name", aircraft_id)} 임대 종료'
    leased.append(aircraft_id)
    rev['leased_aircraft'] = leased
    daily = LEASE_DAILY.get(ac.get('category', '소형'), 60000)
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'{ac.get("name", aircraft_id)} 임대 시작! (약 {format_krw(daily)}/일)'


def set_mro_desk(prog, enabled):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    mechs = len(ops.get('staff_pool', {}).get('mechanic', []))
    if enabled and mechs < 1:
        return False, '정비사를 먼저 채용하세요!'
    rev['mro_desk'] = bool(enabled)
    _save_ops(prog, ops)
    db.session.commit()
    if enabled:
        return True, f'MRO 정비 데스크 오픈! (정비사 {mechs}명 · 주 {format_krw(MRO_SHOP_PER_MECHANIC * mechs)})'
    return True, 'MRO 데스크를 닫았어요.'


def set_fleet_maintain(prog, enabled):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    rev['fleet_maintain'] = bool(enabled)
    _save_ops(prog, ops)
    db.session.commit()
    if enabled:
        return True, f'정기 정비 계약 ON — 기체 상태 유지 (주간 비용 발생)'
    return True, '정기 정비 계약 OFF — 정비 안 하면 수익이 줄어요.'


def answer_briefing(prog, briefing_idx, answer_idx):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    items = _ensure_briefings(ops)
    if briefing_idx in rev.get('briefing_done', []):
        return False, '이미 완료한 브리핑이에요.', 0
    item = next((b for b in items if b.get('idx') == briefing_idx), None)
    if not item:
        return False, '브리핑을 찾을 수 없어요.', 0
    try:
        ans = int(answer_idx)
    except (TypeError, ValueError):
        ans = -1
    if ans != item.get('answer', 0):
        return False, f'오답! {item.get("tip", "")}', 0
    fee = item.get('fee', 80000)
    award_money(prog, fee, f'브리핑 수수료: {item.get("flight", "")}')
    done = list(rev.get('briefing_done', []))
    done.append(briefing_idx)
    rev['briefing_done'] = done
    ops['xp'] = ops.get('xp', 0) + 2
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'✅ 브리핑 완료! +{format_krw(fee)}', fee


def toggle_codeshare(prog, partner_id):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    partners = {p['id']: p for p in _json_list('airline_codeshare_partners.json')}
    if partner_id not in partners:
        return False, '제휴사를 찾을 수 없어요.'
    cs = rev.setdefault('codeshare', {})
    p = partners[partner_id]
    new_val = not cs.get(partner_id, False)
    routes = [r for r in ops.get('routes', []) if r.get('active')]
    intl = sum(1 for r in routes if r.get('type') in ('international', 'longhaul'))
    cargo_n = sum(1 for r in routes if r.get('type') == 'cargo')
    if new_val:
        if p.get('min_intl_routes') and intl < p['min_intl_routes']:
            return False, f'국제선 노선 {p["min_intl_routes"]}개 이상 필요해요.'
        if p.get('min_cargo_routes') and cargo_n < p['min_cargo_routes']:
            return False, f'화물 노선 {p["min_cargo_routes"]}개 이상 필요해요.'
    cs[partner_id] = new_val
    rev['codeshare'] = cs
    _save_ops(prog, ops)
    db.session.commit()
    label = '제휴 시작' if new_val else '제휴 종료'
    return True, f'{p["emoji"]} {p["name"]} 코드셰어 {label}'


def run_training(prog, module_id, answer_idx):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    school = _json_cfg('airline_flight_school.json')
    today = today_str()
    if rev.get('training_date') != today:
        rev['training_date'] = today
        rev['training_done'] = []
    if module_id in rev.get('training_done', []):
        return False, '오늘은 이미 이 과정을 마쳤어요.', 0
    if len(rev.get('training_done', [])) >= school.get('daily_limit', 3):
        return False, '오늘 훈련 한도를 다 썼어요.', 0
    if not ops.get('staff_pool', {}).get('fo', []):
        return False, '부기장을 채용하면 훈련원을 운영할 수 있어요!', 0
    modules = {m['id']: m for m in school.get('modules', [])}
    if module_id not in modules:
        return False, '훈련 과정을 찾을 수 없어요.', 0
    m = modules[module_id]
    try:
        ans = int(answer_idx)
    except (TypeError, ValueError):
        ans = -1
    if ans != m.get('answer', 0):
        return False, '오답! 다시 훈련해보세요.', 0
    fee = m.get('fee', 150000)
    award_money(prog, fee, f'훈련원: {m["name"]}')
    done = list(rev.get('training_done', []))
    done.append(module_id)
    rev['training_done'] = done
    ops['xp'] = ops.get('xp', 0) + m.get('xp_airline', 2)
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'🎓 {m["name"]} 훈련 완료! +{format_krw(fee)}', fee


def claim_seasonal(prog):
    from app.services.airline_ops import _ops, _save_ops
    ops = _ops(prog)
    rev = ensure_revenue_state(ops)
    season = _current_season_event()
    if not season:
        return False, '이번 주 시즌 이벤트가 없어요.', 0
    if rev.get('seasonal_week') != season['week']:
        rev['seasonal_week'] = season['week']
        rev['seasonal_claimed'] = False
    if rev.get('seasonal_claimed'):
        return False, '이번 주 시즌 보너스는 이미 받았어요.', 0
    routes = [r for r in ops.get('routes', []) if r.get('active')]
    match = 0
    for r in routes:
        route_str = r.get('route', '') + ' ' + r.get('name', '')
        for token in season.get('route_match', []):
            if token and token in route_str:
                match += 1
                break
        if season.get('cargo') and r.get('type') == 'cargo':
            match += 1
        if season.get('require_intl') and r.get('type') in ('international', 'longhaul'):
            match += 1
    if match < 1:
        return False, f'{season.get("name", "시즌")}에 맞는 노선을 먼저 개설하세요!', 0
    bonus = int(season.get('bonus_money', 400000) * min(match, 3))
    award_money(prog, bonus, f'시즌 특선: {season.get("name", "")}')
    rev['seasonal_claimed'] = True
    rev['seasonal_week'] = season['week']
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'{season.get("icon", "🎉")} 시즌 보너스 +{format_krw(bonus)}!', bonus


def tick_revenue_maintenance(prog, ops):
    """주간 기체 마모·정비 반영 (정산 시 호출)"""
    rev = ensure_revenue_state(ops)
    _sync_fleet_condition(prog, ops)
    wk = week_key()
    if ops.get('last_maint_week') == wk:
        return
    _apply_condition_wear(ops)
    if rev.get('fleet_maintain'):
        for aid in rev.get('fleet_condition', {}):
            rev['fleet_condition'][aid] = min(100, rev['fleet_condition'][aid] + 15)
    ops['last_maint_week'] = wk