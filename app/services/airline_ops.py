"""항공사 CEO 운영: 허브·기재·노선·채용·정산"""
import uuid
from app.models import db, LogbookEntry
from app.services.gamification import load_json, week_key, today_str
from app.services.economy import (
    get_owned_aircraft, get_aircraft_catalog, award_money, format_krw, get_effective_hours,
)
from app.services.pilot_features import get_airline_info, get_meta, save_meta

HUBS = [
    {'id': 'ICN', 'name': '인천', 'emoji': '🇰🇷'},
    {'id': 'GMP', 'name': '김포', 'emoji': '🏙️'},
    {'id': 'PUS', 'name': '부산', 'emoji': '🌊'},
    {'id': 'CJU', 'name': '제주', 'emoji': '🏝️'},
]

CATEGORY_ORDER = ['리저널', '소형', '중형', '대형', '클래식', '화물기']

CREW_ROLE_MAP = {
    'crew_captain_kim': 'captain', 'crew_captain_choi': 'captain',
    'crew_fo_lee': 'fo', 'crew_fo_park': 'fo',
    'crew_fa_hana': 'fa', 'crew_fa_jun': 'fa',
    'crew_mechanic': 'mechanic', 'crew_dispatcher': 'dispatcher',
    'crew_atc': 'dispatcher', 'crew_fuel': 'ground',
}


def _ops(prog):
    meta = get_meta(prog)
    default = {
        'hub': 'ICN',
        'mode': 'fsc',
        'level': 1,
        'xp': 0,
        'reputation': 50,
        'fleet_deploy': {},
        'routes': [],
        'staff_pool': {},
        'last_settlement_week': '',
        'last_revenue': 0,
        'total_revenue': 0,
        'events_claimed': [],
    }
    ops = meta.setdefault('airline_ops', {})
    for k, v in default.items():
        ops.setdefault(k, v if not isinstance(v, (list, dict)) else (list(v) if isinstance(v, list) else dict(v)))
    return ops


def _save_ops(prog, ops):
    meta = get_meta(prog)
    meta['airline_ops'] = ops
    save_meta(prog, meta)


def _category_rank(cat):
    try:
        return CATEGORY_ORDER.index(cat)
    except ValueError:
        return 1


def _crew_unlocked(prog):
    from app.services.pilot_extras import _meta as pe_meta
    return set(pe_meta(prog).get('crew_unlocked', []))


def get_hireable_crew(prog):
    cards = load_json('crew_cards.json')
    unlocked = _crew_unlocked(prog)
    ops = _ops(prog)
    pool = ops.get('staff_pool', {})
    hired_ids = set()
    for ids in pool.values():
        if isinstance(ids, list):
            hired_ids.update(ids)
    result = []
    for card in cards:
        cid = card['id']
        role = CREW_ROLE_MAP.get(cid, 'fa')
        result.append({
            **card,
            'airline_role': role,
            'unlocked': cid in unlocked,
            'hired': cid in hired_ids,
        })
    return result


def hire_crew(prog, crew_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    cards = {c['id']: c for c in load_json('crew_cards.json')}
    if crew_id not in cards:
        return False, '동료를 찾을 수 없어요.'
    if crew_id not in _crew_unlocked(prog):
        return False, '아직 만날 수 없는 동료예요. 기장생활에서 조건을 달성하세요!'
    role = CREW_ROLE_MAP.get(crew_id, 'fa')
    ops = _ops(prog)
    pool = ops.setdefault('staff_pool', {})
    role_list = pool.setdefault(role, [])
    if crew_id in role_list:
        return False, '이미 우리 항공사에 있어요!'
    role_list.append(crew_id)
    ops['staff_pool'] = pool
    _save_ops(prog, ops)
    try:
        from app.services.player_stats import apply_activity_stats
        apply_activity_stats(prog, 'airline_hire')
    except Exception:
        pass
    db.session.commit()
    return True, f'{cards[crew_id]["emoji"]} {cards[crew_id]["name"]} 채용 완료!'


def set_hub(prog, hub_id):
    if hub_id not in {h['id'] for h in HUBS}:
        return False, '허브를 찾을 수 없어요.'
    ops = _ops(prog)
    ops['hub'] = hub_id
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'허브가 {hub_id}로 설정됐어요!'


def set_mode(prog, mode):
    if mode not in ('lcc', 'fsc'):
        return False, 'LCC 또는 FSC를 선택해주세요.'
    ops = _ops(prog)
    ops['mode'] = mode
    _save_ops(prog, ops)
    db.session.commit()
    label = '저가항공(LCC)' if mode == 'lcc' else '전통항공(FSC)'
    return True, f'운영 모드: {label}'


def deploy_aircraft(prog, aircraft_id, hub_id=None):
    owned = get_owned_aircraft(prog)
    if aircraft_id not in owned:
        return False, '보유하지 않은 기체예요.'
    catalog = get_aircraft_catalog()
    if aircraft_id not in catalog:
        return False, '기체 정보 없음'
    ops = _ops(prog)
    hub = hub_id or ops.get('hub', 'ICN')
    if hub not in {h['id'] for h in HUBS}:
        hub = 'ICN'
    deploy = ops.setdefault('fleet_deploy', {})
    deploy[aircraft_id] = hub
    ops['fleet_deploy'] = deploy
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'{catalog[aircraft_id]["name"]} → {hub} 배치 완료!'


def _route_staff_score(route, ops):
    staff = route.get('staff', {})
    pool = ops.get('staff_pool', {})
    score = 0.0
    caps = pool.get('captain', [])
    fos = pool.get('fo', [])
    fas = pool.get('fa', [])
    if staff.get('captain') and staff['captain'] in caps:
        score += 0.25
    if staff.get('fo') and staff['fo'] in fos:
        score += 0.25
    fa_need = route.get('fa_need', 2)
    fa_assigned = len([f for f in staff.get('fa', []) if f in fas])
    score += 0.25 * min(1.0, fa_assigned / max(fa_need, 1))
    if staff.get('mechanic') and pool.get('mechanic'):
        score += 0.15
    if staff.get('dispatcher') and pool.get('dispatcher'):
        score += 0.1
    return min(1.0, score)


def create_route(prog, template_id, aircraft_id, flights_per_week=7):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    templates = {t['id']: t for t in load_json('airline_route_templates.json')}
    tpl = templates.get(template_id)
    if not tpl:
        return False, '노선을 찾을 수 없어요.'
    owned = get_owned_aircraft(prog)
    if aircraft_id not in owned:
        return False, '이 비행기를 먼저 구매하세요!'
    catalog = get_aircraft_catalog()
    ac = catalog.get(aircraft_id, {})
    min_cat = tpl.get('min_category', '소형')
    if _category_rank(ac.get('category', '소형')) < _category_rank(min_cat):
        return False, f'이 노선은 {min_cat} 이상 기체가 필요해요!'
    ops = _ops(prog)
    routes = ops.get('routes', [])
    if len(routes) >= 12:
        return False, '노선은 최대 12개까지예요!'
    pool = ops.get('staff_pool', {})
    fos = pool.get('fo', [])
    route = {
        'id': str(uuid.uuid4())[:8],
        'template_id': template_id,
        'route': tpl['route'],
        'name': tpl['name'],
        'type': tpl.get('type', 'domestic'),
        'aircraft_id': aircraft_id,
        'flights_per_week': min(14, max(1, int(flights_per_week))),
        'demand': tpl.get('demand', 50),
        'fa_need': tpl.get('fa_need', 2),
        'active': True,
        'staff': {
            'captain': pool.get('captain', [None])[0] if pool.get('captain') else None,
            'fo': fos[0] if fos else None,
            'fa': pool.get('fa', [])[:tpl.get('fa_need', 2)],
            'mechanic': bool(pool.get('mechanic')),
            'dispatcher': bool(pool.get('dispatcher')),
        },
    }
    routes.append(route)
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'노선 {tpl["name"]} 개설!'


def assign_route_staff(prog, route_id, staff):
    ops = _ops(prog)
    routes = ops.get('routes', [])
    route = next((r for r in routes if r['id'] == route_id), None)
    if not route:
        return False, '노선을 찾을 수 없어요.'
    pool = ops.get('staff_pool', {})
    new_staff = dict(route.get('staff', {}))
    if 'captain' in staff:
        c = staff['captain']
        if c and c not in pool.get('captain', []):
            return False, '채용된 기장만 배치할 수 있어요.'
        new_staff['captain'] = c or None
    if 'fo' in staff:
        f = staff['fo']
        if f and f not in pool.get('fo', []):
            return False, '채용된 부기장만 배치할 수 있어요.'
        new_staff['fo'] = f or None
    if 'fa' in staff:
        fa_list = staff['fa'] if isinstance(staff['fa'], list) else []
        pool_fa = set(pool.get('fa', []))
        new_staff['fa'] = [f for f in fa_list if f in pool_fa]
    if 'mechanic' in staff:
        new_staff['mechanic'] = bool(staff['mechanic']) and bool(pool.get('mechanic'))
    if 'dispatcher' in staff:
        new_staff['dispatcher'] = bool(staff['dispatcher']) and bool(pool.get('dispatcher'))
    route['staff'] = new_staff
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    return True, '승무 배치 완료!'


def delete_route(prog, route_id):
    ops = _ops(prog)
    routes = [r for r in ops.get('routes', []) if r['id'] != route_id]
    if len(routes) == len(ops.get('routes', [])):
        return False, '노선을 찾을 수 없어요.'
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    return True, '노선을 정리했어요.'


def settle_weekly_revenue(prog, force=False):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return None
    ops = _ops(prog)
    wk = week_key()
    if ops.get('last_settlement_week') == wk and not force:
        return None
    routes = [r for r in ops.get('routes', []) if r.get('active')]
    if not routes:
        ops['last_settlement_week'] = wk
        _save_ops(prog, ops)
        db.session.commit()
        return {'revenue': 0, 'week': wk, 'routes': 0}

    mode = ops.get('mode', 'fsc')
    mode_mult = 0.85 if mode == 'lcc' else 1.0
    catalog = get_aircraft_catalog()
    total = 0
    details = []
    for r in routes:
        ac = catalog.get(r.get('aircraft_id', ''), {})
        cat_mult = {'소형': 1.0, '중형': 1.4, '대형': 1.8, '화물기': 1.5, '리저널': 0.9, '클래식': 1.2}.get(
            ac.get('category', ''), 1.0)
        staff_mult = 0.4 + 0.6 * _route_staff_score(r, ops)
        base = r.get('demand', 50) * 8000 * r.get('flights_per_week', 7) / 7
        revenue = int(base * cat_mult * staff_mult * mode_mult)
        if r.get('type') == 'international':
            revenue = int(revenue * 1.3)
        elif r.get('type') == 'longhaul':
            revenue = int(revenue * 1.8)
        total += revenue
        details.append({'route': r.get('name'), 'money': revenue, 'staff_pct': int(staff_mult * 100)})

    log_bonus = min(500000, LogbookEntry.query.count() * 5000)
    total += log_bonus

    award_money(prog, total, f'항공사 주간 수익 ({wk})')
    ops['last_settlement_week'] = wk
    ops['last_revenue'] = total
    ops['total_revenue'] = ops.get('total_revenue', 0) + total
    xp_gain = min(50, len(routes) * 5 + total // 500000)
    ops['xp'] = ops.get('xp', 0) + xp_gain
    while ops['xp'] >= ops.get('level', 1) * 80:
        ops['xp'] -= ops.get('level', 1) * 80
        ops['level'] = ops.get('level', 1) + 1
        ops['reputation'] = min(100, ops.get('reputation', 50) + 5)
    _save_ops(prog, ops)
    try:
        from app.services.player_stats import apply_activity_stats
        apply_activity_stats(prog, 'airline_settle')
    except Exception:
        pass
    db.session.commit()
    return {
        'revenue': total,
        'week': wk,
        'routes': len(routes),
        'details': details,
        'log_bonus': log_bonus,
        'formatted': format_krw(total),
        'level': ops.get('level', 1),
    }


def get_flights_for_radar(prog):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return []
    ops = _ops(prog)
    catalog = get_aircraft_catalog()
    flights = []
    for i, r in enumerate(ops.get('routes', [])[:8]):
        if not r.get('active'):
            continue
        parts = (r.get('route') or 'ICN-CJU').split('-')
        if len(parts) != 2:
            continue
        ac = catalog.get(r.get('aircraft_id', 'b737'), {})
        flights.append({
            'callsign': f"{info.get('logo', '✈')[:2]}{100 + i}",
            'org_id': parts[0].strip(),
            'dest_id': parts[1].strip(),
            'ac_name': ac.get('name', r.get('aircraft_id', '')),
            'is_korea': True,
            'airline_name': info.get('name', ''),
            'is_airline_flight': True,
        })
    return flights


def get_airline_dashboard(prog):
    info = get_airline_info(prog)
    ops = _ops(prog)
    settle_weekly_revenue(prog)
    owned = get_owned_aircraft(prog)
    catalog = get_aircraft_catalog()
    fleet = []
    for aid in owned:
        ac = catalog.get(aid, {})
        fleet.append({
            'id': aid,
            'name': ac.get('name', aid),
            'category': ac.get('category', ''),
            'hub': ops.get('fleet_deploy', {}).get(aid, ops.get('hub', 'ICN')),
        })
    templates = load_json('airline_route_templates.json')
    roles = load_json('airline_staff_roles.json')
    try:
        from app.services.space_ops import get_space_status
        space = get_space_status(prog)
    except Exception:
        space = {'unlocked': False}
    try:
        from app.services.player_stats import get_player_stats
        pstats = get_player_stats(prog)
    except Exception:
        pstats = {}
    from app.services.economy import get_wallet_summary
    return {
        'wallet': {'balance': prog.wallet_balance or 0},
        'airline': info,
        'ops': {
            **ops,
            'hubs': HUBS,
            'fleet': fleet,
            'route_templates': templates,
            'staff_roles': roles,
            'hireable_crew': get_hireable_crew(prog),
        },
        'player_stats': pstats,
        'space': space,
    }