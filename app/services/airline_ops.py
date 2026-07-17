"""항공사 CEO 운영: 허브·기재·노선·채용·정산"""
import uuid
from datetime import datetime
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

ROLE_TO_AIRLINE = {
    '기장': 'captain', '국제선 기장': 'captain', '화물기장': 'captain', '최고 기장': 'captain',
    '부기장': 'fo', '조종 학생': 'fo',
    '승무원': 'fa',
    '정비사': 'mechanic',
    '운항관리': 'dispatcher', '관제사': 'dispatcher', '정시 전문': 'dispatcher',
    '연료사': 'ground', '비행 학생': 'ground',
}


def _airline_role_for_crew(card):
    return card.get('airline_role') or ROLE_TO_AIRLINE.get(card.get('role'), 'fa')


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
        'last_daily_income_date': '',
        'income_week': '',
        'week_income_accrued': 0,
        'last_payroll_week': '',
        'last_revenue': 0,
        'last_gross_revenue': 0,
        'last_payroll': 0,
        'last_net_revenue': 0,
        'total_revenue': 0,
        'events_claimed': [],
        'last_maint_week': '',
        'revenue': {},
        'company_vault': 0,
        'allocation_week': '',
        'last_allocation': None,
        'reinvest_boost_week': '',
        'reinvest_boost_pct': 0,
        'staff_bonus_week': '',
        'allocable_pool': 0,
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
    """기장생활에서 해금한 동료 ID 집합. 조회 시 해금 조건도 다시 검사."""
    from app.services.pilot_extras import _meta as pe_meta, check_crew_unlocks
    try:
        check_crew_unlocks(prog)
    except Exception:
        pass
    return set(pe_meta(prog).get('crew_unlocked', []))


def get_hireable_crew(prog, slim=True, only_active=False):
    """기장생활에서 만난(해금된) 동료만 채용 가능. unlocked=True 가 채용 버튼.

    slim=True: 미해금 카드는 프로필 생략.
    only_active=True: 해금·채용된 동료만 반환 (대시보드 기본 — 300명 전체 제외).
    """
    from app.services.crew_stats import generate_crew_profile
    from app.services.pilot_extras import _ease_crew_value
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
        role = _airline_role_for_crew(card)
        is_unlocked = cid in unlocked
        is_hired = cid in hired_ids
        if only_active and not is_unlocked and not is_hired:
            continue
        req = card.get('unlock') or {}
        eased = _ease_crew_value(req.get('type'), req.get('value', 0))
        tip = card.get('bonus_tip') or ''
        if req.get('type') and not card.get('free_unlock'):
            tip = f"조건(완화): {req.get('type')} ≥ {eased}" + (f' · {tip}' if tip else '')
        if slim and not is_unlocked and not is_hired:
            profile = {
                'grade': '—', 'overall': 0, 'skills': [], 'weekly_pay': 0,
                'specialty': '', 'kid_summary': tip or '아직 만남 조건 미달성',
                'hire_tip': tip, 'grade_emoji': '🔒',
            }
        else:
            profile = generate_crew_profile(card)
        result.append({
            **card,
            'airline_role': role,
            'unlocked': is_unlocked,
            'hired': is_hired,
            'profile': profile,
            'hire_ready': is_unlocked and not is_hired,
            'unlock_eased_value': eased,
            'bonus_tip': tip or card.get('bonus_tip', ''),
        })
    result.sort(key=lambda c: (
        0 if c['hired'] else (1 if c['unlocked'] else 2),
        -c['profile'].get('overall', 0),
        c['name'],
    ))
    return result


def get_crew_pool_meta(prog):
    cards = load_json('crew_cards.json')
    unlocked = _crew_unlocked(prog)
    ops = _ops(prog)
    hired = set()
    for ids in ops.get('staff_pool', {}).values():
        if isinstance(ids, list):
            hired.update(ids)
    return {
        'pool_total': len(cards) if isinstance(cards, list) else 0,
        'unlocked_count': len(unlocked),
        'hired_count': len(hired),
        'locked_count': max(0, (len(cards) if isinstance(cards, list) else 0) - len(unlocked)),
    }


def hire_crew(prog, crew_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    cards = {c['id']: c for c in load_json('crew_cards.json')}
    if crew_id not in cards:
        return False, '동료를 찾을 수 없어요.'
    # 해금 재검사 후 채용 (기장생활 체크 반영)
    unlocked = _crew_unlocked(prog)
    if crew_id not in unlocked:
        return False, '아직 만날 수 없는 동료예요. 기장생활에서 조건을 달성하세요!'
    role = _airline_role_for_crew(cards[crew_id])
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
    from app.services.crew_stats import generate_crew_profile
    prof = generate_crew_profile(cards[crew_id])
    return True, f'{cards[crew_id]["emoji"]} {cards[crew_id]["name"]} 채용! ({prof["grade"]}등급 · 주급 {format_krw(prof["weekly_pay"])})'


def _clear_crew_from_routes(ops, crew_id):
    for route in ops.get('routes', []):
        staff = route.setdefault('staff', {})
        if staff.get('captain') == crew_id:
            staff['captain'] = None
        if staff.get('fo') == crew_id:
            staff['fo'] = None
        if staff.get('mechanic') == crew_id:
            staff['mechanic'] = None
        if staff.get('dispatcher') == crew_id:
            staff['dispatcher'] = None
        fa = staff.get('fa', [])
        if isinstance(fa, list):
            staff['fa'] = [f for f in fa if f != crew_id]


def fire_crew(prog, crew_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사를 먼저 창업해주세요!'
    cards = {c['id']: c for c in load_json('crew_cards.json')}
    if crew_id not in cards:
        return False, '동료를 찾을 수 없어요.'
    ops = _ops(prog)
    pool = ops.get('staff_pool', {})
    role = _airline_role_for_crew(cards[crew_id])
    role_list = pool.get(role, [])
    if crew_id not in role_list:
        return False, '채용되어 있지 않아요.'
    role_list.remove(crew_id)
    pool[role] = role_list
    ops['staff_pool'] = pool
    _clear_crew_from_routes(ops, crew_id)
    _save_ops(prog, ops)
    db.session.commit()
    card = cards[crew_id]
    return True, f'{card["emoji"]} {card["name"]} 해고 완료. 노선 배치에서도 제외됐어요.'


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


def _crew_power_sort(crew_id):
    from app.services.crew_stats import crew_power
    return crew_power(crew_id)


def _best_in_pool(pool_list):
    if not pool_list:
        return None
    return max(pool_list, key=_crew_power_sort)


def _resolve_staff_id(staff, key, pool, pool_key):
    val = staff.get(key)
    plist = pool.get(pool_key, [])
    if isinstance(val, str):
        return val if val in plist else None
    if val is True and plist:
        return _best_in_pool(plist)
    return None


def _route_staff_score(route, ops):
    from app.services.crew_stats import crew_power
    staff = route.get('staff', {})
    pool = ops.get('staff_pool', {})
    score = 0.0
    caps = set(pool.get('captain', []))
    fos = set(pool.get('fo', []))
    fas = set(pool.get('fa', []))

    cap = _resolve_staff_id(staff, 'captain', pool, 'captain')
    if cap and cap in caps:
        score += 0.28 * crew_power(cap)

    fo = _resolve_staff_id(staff, 'fo', pool, 'fo')
    if fo and fo in fos:
        score += 0.22 * crew_power(fo)

    fa_need = route.get('fa_need', 2)
    fa_list = staff.get('fa', [])
    fa_assigned = [f for f in fa_list if isinstance(f, str) and f in fas]
    if fa_assigned:
        avg_fa = sum(crew_power(f) for f in fa_assigned) / len(fa_assigned)
        fill = min(1.0, len(fa_assigned) / max(fa_need, 1))
        score += 0.22 * fill * avg_fa

    mech = _resolve_staff_id(staff, 'mechanic', pool, 'mechanic')
    if mech:
        score += 0.14 * crew_power(mech)

    disp = _resolve_staff_id(staff, 'dispatcher', pool, 'dispatcher')
    if disp:
        score += 0.14 * crew_power(disp)

    return min(1.0, score)


def _route_revenue_mult(route, ops, cards_by_id):
    from app.services.crew_stats import analyze_route_bonuses
    staff_mult = 0.4 + 0.6 * _route_staff_score(route, ops)
    try:
        from app.services.airline_company import get_staff_bonus_active
        if get_staff_bonus_active(ops):
            staff_mult = min(1.05, staff_mult * 1.04)
    except Exception:
        pass
    bonus = analyze_route_bonuses(route, ops, cards_by_id)
    extra = bonus['specialty_mult'] * bonus['synergy_mult']
    return staff_mult * extra, staff_mult, bonus


def _category_revenue_mult(category):
    return {'소형': 1.0, '중형': 1.4, '대형': 1.8, '화물기': 1.5, '리저널': 0.9, '클래식': 1.2}.get(category, 1.0)


ANCILLARY_MULT = {'off': 1.0, 'basic': 1.06, 'premium': 1.12}
CARGO_DESK_PER_ROUTE_DAILY = 80_000
CODESHARE_PER_INTL_DAILY = 25_000
CODESHARE_DAILY_CAP = 150_000


def _route_display_meta(route, catalog, templates_by_id):
    tpl = templates_by_id.get(route.get('template_id'), {})
    ac = catalog.get(route.get('aircraft_id', ''), {})
    return {
        'region': route.get('region') or tpl.get('kid_label', '기타'),
        'min_category': route.get('min_category') or tpl.get('min_category', '소형'),
        'aircraft_name': ac.get('name', route.get('aircraft_id', '')),
        'aircraft_category': ac.get('category', ''),
    }


def _side_income_weekly(ops, routes, route_gross, prog=None):
    """부가서비스·화물데스크·코드셰어·임대·MRO 등 노선 외 부가 수입 (주간 환산)"""
    ancillary = ops.get('ancillary', 'basic')
    mult = ANCILLARY_MULT.get(ancillary, 1.0)
    ancillary_extra = int(route_gross * (mult - 1.0)) if route_gross and mult > 1.0 else 0
    cargo_routes = sum(1 for r in routes if r.get('type') == 'cargo')
    cargo_weekly = cargo_routes * CARGO_DESK_PER_ROUTE_DAILY * 7
    intl_count = sum(1 for r in routes if r.get('type') in ('international', 'longhaul'))
    codeshare_daily = min(CODESHARE_DAILY_CAP, intl_count * CODESHARE_PER_INTL_DAILY) if intl_count >= 2 else 0
    codeshare_passive = codeshare_daily * 7
    extra_passive = 0
    extra_detail = {}
    if prog:
        from app.services.airline_revenue import passive_income_weekly
        extra_passive, extra_detail = passive_income_weekly(prog, ops, routes, route_gross)
    total = ancillary_extra + cargo_weekly + codeshare_passive + extra_passive
    return total, {
        'ancillary_tier': ancillary,
        'ancillary': ancillary_extra,
        'cargo_desk': cargo_weekly,
        'codeshare': codeshare_passive,
        'cargo_routes': cargo_routes,
        'intl_routes': intl_count,
        **extra_detail,
    }


def _calc_single_route_revenue(route, ops, catalog, cards_by_id, world_mults=None):
    """노선 1개 주간 매출 (정산·미리보기 공통)"""
    mode = ops.get('mode', 'fsc')
    mode_mult = 0.85 if mode == 'lcc' else 1.0
    ac = catalog.get(route.get('aircraft_id', ''), {})
    cat_mult = _category_revenue_mult(ac.get('category', ''))
    combined_mult, staff_mult, bonus = _route_revenue_mult(route, ops, cards_by_id)
    from app.services.airline_revenue import get_route_condition_mult
    cond_mult = get_route_condition_mult(route, ops)
    base = route.get('demand', 50) * 9000 * route.get('flights_per_week', 7) / 7
    revenue = int(base * cat_mult * combined_mult * mode_mult * cond_mult)
    if route.get('type') == 'international':
        revenue = int(revenue * 1.3)
    elif route.get('type') == 'longhaul':
        revenue = int(revenue * 1.8)
    try:
        from app.services.airline_company import get_reinvest_mult
        revenue = int(revenue * get_reinvest_mult(ops))
    except Exception:
        pass
    # 세계 경제 이벤트 · 유가 반영
    if world_mults:
        try:
            from app.services.world_economy import apply_route_world_mult
            w = apply_route_world_mult(route, world_mults)
            revenue = int(revenue * w)
        except Exception:
            pass
    return revenue, staff_mult, bonus


def estimate_weekly_revenue(prog, ops=None):
    """이번 주 예상 매출·주급·순수익 (실제 정산 전 미리보기)"""
    from app.services.crew_stats import calc_weekly_payroll
    from app.services.gamification import load_json
    ops = ops or _ops(prog)
    cards_by_id = {c['id']: c for c in load_json('crew_cards.json')}
    catalog = get_aircraft_catalog()
    routes = [r for r in ops.get('routes', []) if r.get('active')]
    world_mults = None
    oil_info = None
    try:
        from app.services.world_economy import get_world_multipliers
        world_mults = get_world_multipliers(prog)
        oil_info = world_mults.get('oil')
    except Exception:
        world_mults = None
    gross = 0
    per_route = []
    for r in routes:
        revenue, staff_mult, bonus = _calc_single_route_revenue(
            r, ops, catalog, cards_by_id, world_mults=world_mults
        )
        gross += revenue
        per_route.append({
            'route_id': r.get('id'),
            'name': r.get('name'),
            'money': revenue,
            'staff_pct': int(staff_mult * 100),
            'bonus_pct': bonus.get('combined_bonus_pct', 0),
        })
    log_bonus = min(500000, LogbookEntry.query.count() * 5000)
    route_gross = gross
    side_weekly, side_detail = _side_income_weekly(ops, routes, route_gross, prog)
    gross += log_bonus + side_weekly
    payroll, payroll_breakdown = calc_weekly_payroll(ops)
    from app.services.crew_stats import assigned_crew_ids
    assigned = len(assigned_crew_ids(ops))
    hired = sum(len(v) for v in ops.get('staff_pool', {}).values() if isinstance(v, list))
    return {
        'gross': gross,
        'route_gross': route_gross,
        'payroll': payroll,
        'net': gross - payroll,
        'log_bonus': log_bonus,
        'side_income': side_detail,
        'side_income_total': side_weekly,
        'active_routes': len(routes),
        'per_route': per_route,
        'assigned_crew': assigned,
        'hired_crew': hired,
        'formatted_gross': format_krw(gross),
        'formatted_payroll': format_krw(payroll),
        'formatted_net': format_krw(gross - payroll),
        'formatted_side': format_krw(side_weekly),
        'world_oil': oil_info,
        'world_demand_mult': (world_mults or {}).get('demand_mult'),
    }


def _enrich_staff_detail(staff, hireable_by_id, ops):
    pool = ops.get('staff_pool', {})
    detail = {}
    for key, pool_key in [('captain', 'captain'), ('fo', 'fo'), ('mechanic', 'mechanic'), ('dispatcher', 'dispatcher')]:
        cid = _resolve_staff_id(staff, key, pool, pool_key)
        if cid:
            c = hireable_by_id.get(cid, {})
            detail[key] = {
                'id': cid,
                'name': c.get('name', cid),
                'emoji': c.get('emoji', ''),
                'grade': (c.get('profile') or {}).get('grade', '?'),
                'specialty': (c.get('profile') or {}).get('specialty', ''),
            }
        else:
            detail[key] = None
    detail['fa'] = []
    for fid in staff.get('fa', []) or []:
        if not isinstance(fid, str):
            continue
        c = hireable_by_id.get(fid, {})
        detail['fa'].append({
            'id': fid,
            'name': c.get('name', fid),
            'emoji': c.get('emoji', ''),
            'grade': (c.get('profile') or {}).get('grade', '?'),
            'specialty': (c.get('profile') or {}).get('specialty', ''),
        })
    return detail


def enrich_routes(ops, hireable_crew):
    from app.services.crew_stats import analyze_route_bonuses
    from app.services.gamification import load_json
    cards_by_id = {c['id']: c for c in load_json('crew_cards.json')}
    hireable_by_id = {c['id']: c for c in hireable_crew}
    catalog = get_aircraft_catalog()
    templates_by_id = {t['id']: t for t in load_json('airline_route_templates.json')}
    enriched = []
    for r in ops.get('routes', []):
        bonus = analyze_route_bonuses(r, ops, cards_by_id)
        staff_mult = 0.4 + 0.6 * _route_staff_score(r, ops)
        meta = _route_display_meta(r, catalog, templates_by_id)
        enriched.append({
            **r,
            **meta,
            'staff_detail': _enrich_staff_detail(r.get('staff', {}), hireable_by_id, ops),
            'bonus_preview': bonus,
            'staff_efficiency_pct': int(staff_mult * 100),
            'total_bonus_pct': int((staff_mult * bonus['specialty_mult'] * bonus['synergy_mult'] - 1) * 100),
        })
    return enriched


def get_route_filter_meta(routes):
    """노선 탭 필터용 카테고리 목록"""
    regions = sorted({r.get('region', '기타') for r in routes})
    types = sorted({r.get('type', 'domestic') for r in routes})
    aircraft = sorted({
        r.get('aircraft_category') or r.get('aircraft_name', '미지정') for r in routes
    })
    return {'regions': regions, 'types': types, 'aircraft_categories': aircraft}


def set_ancillary(prog, tier):
    if tier not in ANCILLARY_MULT:
        return False, '부가서비스 단계를 선택해주세요.'
    ops = _ops(prog)
    ops['ancillary'] = tier
    _save_ops(prog, ops)
    db.session.commit()
    labels = {'off': '없음', 'basic': '기본(수하물·좌석)', 'premium': '프리미엄(기내식·Wi-Fi)'}
    pct = int((ANCILLARY_MULT[tier] - 1) * 100)
    return True, f'부가서비스: {labels[tier]}' + (f' (노선 매출 +{pct}%)' if pct else '')


def _deduct_payroll(prog, ops, amount, wk):
    from app.services.economy import spend_money
    if amount <= 0:
        return 0, True, ''
    balance = prog.wallet_balance or 0
    if balance >= amount:
        ok, _ = spend_money(prog, amount, f'항공사 주급 ({wk})', 'salary')
        return (amount if ok else 0), ok, ''
    paid = 0
    if balance > 0:
        ok, _ = spend_money(prog, balance, f'항공사 주급 일부 ({wk})', 'salary')
        paid = balance if ok else 0
    ops['reputation'] = max(0, ops.get('reputation', 50) - 8)
    short = amount - paid
    return paid, False, f'주급 {format_krw(short)} 미지급 — 평판 하락!'


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
    if len(routes) >= 100:
        return False, '노선은 최대 100개까지예요!'
    pool = ops.get('staff_pool', {})
    fos = pool.get('fo', [])
    route = {
        'id': str(uuid.uuid4())[:8],
        'template_id': template_id,
        'route': tpl['route'],
        'name': tpl['name'],
        'type': tpl.get('type', 'domestic'),
        'region': tpl.get('kid_label', '기타'),
        'min_category': tpl.get('min_category', '소형'),
        'aircraft_id': aircraft_id,
        'flights_per_week': min(14, max(1, int(flights_per_week))),
        'demand': tpl.get('demand', 50),
        'fa_need': tpl.get('fa_need', 2),
        'active': True,
        'staff': {
            'captain': _best_in_pool(pool.get('captain', [])),
            'fo': _best_in_pool(fos),
            'fa': sorted(pool.get('fa', []), key=lambda cid: _crew_power_sort(cid), reverse=True)[:tpl.get('fa_need', 2)],
            'mechanic': _best_in_pool(pool.get('mechanic', [])),
            'dispatcher': _best_in_pool(pool.get('dispatcher', [])),
        },
    }
    routes.append(route)
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    rev, _staff, _bonus = _calc_single_route_revenue(
        route, ops, get_aircraft_catalog(),
        {c['id']: c for c in load_json('crew_cards.json')},
    )
    tick = tick_airline_economy(prog, force=True)
    msg = f'노선 {tpl["name"]} 개설! 예상 주간 매출 {format_krw(rev)}'
    if tick and tick.get('daily_income'):
        msg += f' · 운영 수익 +{format_krw(tick["daily_income"])}'
    return True, msg


# 수동 배치: 제한 없음 (같은 사람이 여러 노선 가능)
# 일괄 랜덤 배치: 한 명당 이 개수까지 우선 배분 (인원 부족 시 초과 허용)
MAX_ROUTES_PER_CREW_AUTO = 5


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
        m = staff['mechanic']
        if m and m not in pool.get('mechanic', []):
            return False, '채용된 정비사만 배치할 수 있어요.'
        new_staff['mechanic'] = m or None
    if 'dispatcher' in staff:
        d = staff['dispatcher']
        if d and d not in pool.get('dispatcher', []):
            return False, '채용된 운항관리만 배치할 수 있어요.'
        new_staff['dispatcher'] = d or None
    route['staff'] = new_staff
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    from app.services.crew_stats import analyze_route_bonuses
    cards_by_id = {c['id']: c for c in load_json('crew_cards.json')}
    bonus = analyze_route_bonuses(route, ops, cards_by_id)
    msg = '승무 배치 완료!'
    if bonus.get('combined_bonus_pct', 0) > 0:
        msg += f' (특기·시너지 +{bonus["combined_bonus_pct"]}%)'
    return True, msg


def auto_assign_all_routes(prog, max_per_crew=None):
    """채용된 직원을 모든 활성 노선에 랜덤·균등 배치.

    - 한 명당 기본 최대 max_per_crew(기본 5)개 노선까지 우선 배분
    - 인원이 부족하면 그 이상은 초과 배치 허용 (빈 자리 방지)
    - 노선 순서를 섞어 매번 결과가 달라짐
    """
    import random
    from collections import defaultdict

    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!', None

    ops = _ops(prog)
    pool = ops.get('staff_pool', {})
    routes = [r for r in ops.get('routes', []) if r.get('active', True)]
    if not routes:
        return False, '배치할 노선이 없어요. 먼저 노선을 개설하세요!', None

    hired_total = sum(len(v) for v in pool.values() if isinstance(v, list))
    if hired_total <= 0:
        return False, '채용된 직원이 없어요. 채용 탭에서 동료를 뽑아주세요!', None

    limit = max(1, int(max_per_crew if max_per_crew is not None else MAX_ROUTES_PER_CREW_AUTO))
    load = defaultdict(int)

    def pick(role_key, n=1, allow_over=False):
        ids = list(pool.get(role_key, []) or [])
        if not ids or n <= 0:
            return []
        # 적게 배치된 사람 우선, 동점이면 랜덤
        random.shuffle(ids)
        ids.sort(key=lambda cid: (load[cid], -_crew_power_sort(cid)))
        picked = []
        for cid in ids:
            if not allow_over and load[cid] >= limit:
                continue
            if cid in picked:
                continue
            picked.append(cid)
            if len(picked) >= n:
                break
        # 부족하면 상한 무시하고 채움
        if len(picked) < n:
            for cid in ids:
                if cid in picked:
                    continue
                picked.append(cid)
                if len(picked) >= n:
                    break
        return picked[:n]

    random.shuffle(routes)
    filled_roles = 0
    empty_slots = 0
    for route in routes:
        fa_need = max(1, int(route.get('fa_need', 2) or 2))
        cap = pick('captain', 1)
        fo = pick('fo', 1)
        fa = pick('fa', fa_need)
        # 승무원 부족 시 상한 무시 재시도
        if len(fa) < fa_need:
            fa = pick('fa', fa_need, allow_over=True)
        mech = pick('mechanic', 1)
        disp = pick('dispatcher', 1)
        # 기장/부기장 등도 비면 상한 무시
        if not cap:
            cap = pick('captain', 1, allow_over=True)
        if not fo:
            fo = pick('fo', 1, allow_over=True)
        if not mech:
            mech = pick('mechanic', 1, allow_over=True)
        if not disp:
            disp = pick('dispatcher', 1, allow_over=True)

        staff = {
            'captain': cap[0] if cap else None,
            'fo': fo[0] if fo else None,
            'fa': fa,
            'mechanic': mech[0] if mech else None,
            'dispatcher': disp[0] if disp else None,
        }
        route['staff'] = staff
        for cid in [staff['captain'], staff['fo'], staff['mechanic'], staff['dispatcher']] + list(staff['fa'] or []):
            if cid:
                load[cid] += 1
                filled_roles += 1
        if not staff['captain']:
            empty_slots += 1
        if not staff['fo']:
            empty_slots += 1
        empty_slots += max(0, fa_need - len(staff['fa'] or []))

    ops['routes'] = ops.get('routes', [])
    _save_ops(prog, ops)
    db.session.commit()

    max_load = max(load.values()) if load else 0
    people = len(load)
    msg = (
        f'🎲 전체 {len(routes)}개 노선에 직원 {people}명 랜덤 배치 완료! '
        f'(1인 우선 한도 {limit}노선 · 실제 최대 {max_load}노선)'
    )
    if empty_slots:
        msg += f' · 빈 자리 {empty_slots}곳(채용 더 필요)'
    return True, msg, {
        'routes': len(routes),
        'people_assigned': people,
        'max_load': max_load,
        'preferred_limit': limit,
        'empty_slots': empty_slots,
        'load_sample': dict(sorted(load.items(), key=lambda x: -x[1])[:8]),
    }


def delete_route(prog, route_id):
    ops = _ops(prog)
    routes = [r for r in ops.get('routes', []) if r['id'] != route_id]
    if len(routes) == len(ops.get('routes', [])):
        return False, '노선을 찾을 수 없어요.'
    ops['routes'] = routes
    _save_ops(prog, ops)
    db.session.commit()
    return True, '노선을 정리했어요.'


def _days_since_income(last_date, today):
    if not last_date:
        return 1
    try:
        d0 = datetime.strptime(last_date, '%Y-%m-%d')
        d1 = datetime.strptime(today, '%Y-%m-%d')
    except ValueError:
        return 1
    delta = (d1 - d0).days
    if delta <= 0:
        return 0
    return min(delta, 7)


def tick_airline_economy(prog, force=False):
    """활성 노선 → 일일 운영 수익 자동 적립. 채용 인원 → 주 1회 주급 차감."""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return None

    ops = _ops(prog)
    today = today_str()
    wk = week_key()
    from app.services.airline_revenue import tick_revenue_maintenance
    tick_revenue_maintenance(prog, ops)
    routes = [r for r in ops.get('routes', []) if r.get('active')]

    if ops.get('income_week') != wk:
        ops['income_week'] = wk
        ops['week_income_accrued'] = 0

    preview = estimate_weekly_revenue(prog, ops) if routes else None
    weekly_gross = (preview or {}).get('gross', 0)
    daily_rate = max(0, weekly_gross // 7)

    daily_income = 0
    days_accrued = 0
    details = (preview or {}).get('per_route', [])

    if routes and daily_rate > 0:
        days_accrued = _days_since_income(ops.get('last_daily_income_date'), today)
        if force and days_accrued == 0:
            days_accrued = 1
        if days_accrued > 0:
            remaining = max(0, weekly_gross - ops.get('week_income_accrued', 0))
            daily_income = min(remaining, daily_rate * days_accrued)
            if daily_income > 0:
                award_money(prog, daily_income, f'노선 운영 수익 ({today})')
                ops['last_daily_income_date'] = today
                ops['week_income_accrued'] = ops.get('week_income_accrued', 0) + daily_income
                ops['total_revenue'] = ops.get('total_revenue', 0) + daily_income

    from app.services.crew_stats import calc_weekly_payroll
    payroll, payroll_breakdown = calc_weekly_payroll(ops)
    paid = 0
    payroll_ok = True
    payroll_warn = ''
    if payroll > 0 and ops.get('last_payroll_week') != wk:
        paid, payroll_ok, payroll_warn = _deduct_payroll(prog, ops, payroll, wk)
        ops['last_payroll_week'] = wk
        ops['last_settlement_week'] = wk

    if daily_income <= 0 and paid <= 0:
        return None

    net = daily_income - paid
    ops['last_gross_revenue'] = daily_income
    ops['last_payroll'] = paid
    ops['last_net_revenue'] = net
    ops['last_revenue'] = net
    try:
        from app.services.airline_company import note_profit_for_allocation
        note_profit_for_allocation(ops, net)
    except Exception:
        pass

    if daily_income > 0 and routes:
        xp_gain = min(10, len(routes) + daily_income // 100000)
        ops['xp'] = ops.get('xp', 0) + xp_gain
        while ops['xp'] >= ops.get('level', 1) * 80:
            ops['xp'] -= ops.get('level', 1) * 80
            ops['level'] = ops.get('level', 1) + 1
            ops['reputation'] = min(100, ops.get('reputation', 50) + 2)

    _save_ops(prog, ops)
    if daily_income > 0:
        try:
            from app.services.player_stats import apply_activity_stats
            apply_activity_stats(prog, 'airline_settle')
        except Exception:
            pass
    db.session.commit()

    return {
        'revenue': net,
        'gross': daily_income,
        'payroll': paid,
        'net': net,
        'week': wk,
        'routes': len(routes),
        'days_accrued': days_accrued,
        'daily_rate': daily_rate,
        'weekly_gross': weekly_gross,
        'details': details,
        'payroll_breakdown': payroll_breakdown[:8],
        'payroll_ok': payroll_ok,
        'payroll_warning': payroll_warn,
        'formatted': format_krw(net),
        'formatted_gross': format_krw(daily_income),
        'formatted_payroll': format_krw(paid),
        'formatted_net': format_krw(net),
        'auto': True,
    }


def settle_weekly_revenue(prog, force=False):
    """수동 정산 — 일일 자동 수익을 즉시 받거나(미수령분) 주급 정산."""
    if not get_airline_info(prog).get('founded'):
        return None
    ops = _ops(prog)
    if not force and ops.get('last_daily_income_date') == today_str():
        routes = [r for r in ops.get('routes', []) if r.get('active')]
        if routes:
            return None
    result = tick_airline_economy(prog, force=True)
    if result:
        result['auto'] = False
        return result
    if not force:
        return None
    wk = week_key()
    from app.services.crew_stats import calc_weekly_payroll
    payroll, payroll_breakdown = calc_weekly_payroll(ops)
    if payroll <= 0 or ops.get('last_payroll_week') == wk:
        return None
    paid, ok, warn = _deduct_payroll(prog, ops, payroll, wk)
    ops['last_payroll_week'] = wk
    ops['last_settlement_week'] = wk
    ops['last_payroll'] = paid
    ops['last_net_revenue'] = -paid
    ops['last_revenue'] = -paid
    _save_ops(prog, ops)
    db.session.commit()
    return {
        'revenue': -paid,
        'gross': 0,
        'payroll': paid,
        'net': -paid,
        'week': wk,
        'routes': 0,
        'payroll_ok': ok,
        'payroll_warning': warn,
        'payroll_breakdown': payroll_breakdown[:8],
        'formatted': format_krw(-paid),
        'formatted_gross': format_krw(0),
        'formatted_payroll': format_krw(paid),
        'formatted_net': format_krw(-paid),
        'auto': False,
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
            'callsign': f"AL{100 + i}",
            'org_id': parts[0].strip(),
            'dest_id': parts[1].strip(),
            'ac_name': ac.get('name', r.get('aircraft_id', '')),
            'route_name': r.get('name', ''),
            'is_korea': True,
            'airline_name': info.get('name', ''),
            'airline_logo': info.get('logo', '✈️'),
            'is_airline_flight': True,
        })
    return flights


def get_airline_dashboard(prog, light=False, run_tick=False):
    """항공사 대시보드 (빠른 기본 경로).

    - run_tick: True일 때만 일일 수익 tick (기본 False — 별도 /tick API)
    - light: 템플릿·수입원·전체 승무원 풀 생략
    - 승무원은 해금·채용분만 (only_active). 전체 풀은 /api/airline/crew
    - 노선 템플릿은 /api/airline/route-templates
    """
    info = get_airline_info(prog)
    ops = _ops(prog)
    wk = week_key()
    economy_tick = None
    if info.get('founded') and run_tick:
        economy_tick = tick_airline_economy(prog)
        if economy_tick:
            ops = _ops(prog)
    revenue_preview = estimate_weekly_revenue(prog, ops) if info.get('founded') else None
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
    roles = load_json('airline_staff_roles.json')
    # 대시보드: 해금·채용분만 (잠긴 300명 제외)
    hireable = get_hireable_crew(prog, slim=True, only_active=True)
    crew_meta = get_crew_pool_meta(prog)
    from app.services.crew_stats import calc_weekly_payroll
    payroll_total, payroll_breakdown = calc_weekly_payroll(ops)
    enriched_routes = enrich_routes(ops, hireable)
    try:
        from app.services.space_ops import get_space_status
        space = get_space_status(prog)
    except Exception:
        space = {'unlocked': False}
    try:
        from app.services.player_stats import get_player_stats
        pstats = {} if light else get_player_stats(prog)
    except Exception:
        pstats = {}
    company_board = None
    if info.get('founded'):
        try:
            from app.services.airline_company import build_company_board
            company_board = build_company_board(prog, ops, revenue_preview)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('company_board load failed')
    return {
        'wallet': {'balance': prog.wallet_balance or 0},
        'economy_tick': economy_tick,
        'airline': info,
        'light': light,
        'ops': {
            **ops,
            'hubs': HUBS,
            'fleet': fleet,
            'routes': enriched_routes,
            'route_templates': [],  # 지연 로드
            'staff_roles': roles,
            'hireable_crew': hireable,
            'crew_meta': crew_meta,
            'crew_full': False,
            'payroll_preview': {
                'weekly_total': payroll_total,
                'weekly_formatted': format_krw(payroll_total),
                'hired_count': crew_meta.get('hired_count', 0),
                'breakdown': payroll_breakdown[:10],
            },
            'revenue_preview': revenue_preview,
            'route_filters': get_route_filter_meta(enriched_routes),
            'ancillary': ops.get('ancillary', 'basic'),
            'settlement': {
                'week': wk,
                'already_settled': ops.get('last_settlement_week') == wk,
                'last_gross': ops.get('last_gross_revenue', 0),
                'last_payroll': ops.get('last_payroll', 0),
                'last_net': ops.get('last_net_revenue', ops.get('last_revenue', 0)),
            },
            'revenue_panel': None,  # 수입원 탭 전용 API
            'company_board': company_board,
            'company_vault': ops.get('company_vault', 0),
        },
        'player_stats': pstats,
        'space': space,
    }