"""승무원 스펙·주급·보너스 검증"""
from app import create_app

app = create_app()

with app.app_context():
    from app.services.gamification import get_or_create_progress, load_json
    from app.services.crew_stats import (
        generate_crew_profile, specialty_match_mult, synergy_mult,
        calc_weekly_payroll, analyze_route_bonuses,
    )
    from app.services.airline_ops import enrich_routes, settle_weekly_revenue, _route_revenue_mult
    from app.services.pilot_extras import get_crew_cards

    cards = load_json('crew_cards.json')
    assert len(cards) >= 50

    c0 = cards[0]
    p1 = generate_crew_profile(c0)
    p2 = generate_crew_profile(c0)
    assert p1 == p2, 'profile must be deterministic'
    assert p1['grade'] in 'SABCD'
    assert p1['weekly_pay'] > 0
    print(f"  OK: profile {c0['name']} = {p1['grade']} ({p1['overall']})")

    cards_by_id = {c['id']: c for c in cards}
    intl_cap = next(c for c in cards if c.get('role') == '국제선 기장')
    crew_ids = [intl_cap['id']]
    m, labels = specialty_match_mult('international', crew_ids, cards_by_id)
    assert m > 1.0, 'intl specialty should match'
    print(f"  OK: specialty mult {m} ({labels})")

    prog = get_or_create_progress()
    crew_cards = get_crew_cards(prog)
    assert crew_cards[0].get('profile'), 'captain-life profile'
    print('  OK: captain-life crew profiles')

    ops = {'staff_pool': {'fa': [c0['id']]}}
    payroll, br = calc_weekly_payroll(ops)
    assert payroll > 0
    print(f'  OK: payroll {payroll}')

    route = {
        'type': 'international', 'staff': {'captain': intl_cap['id'], 'fa': []},
        'fa_need': 2, 'name': 'test',
    }
    bonus = analyze_route_bonuses(route, ops, cards_by_id)
    assert 'specialty_mult' in bonus
    mult, _, b = _route_revenue_mult(route, ops, cards_by_id)
    assert mult > 0.4
    print(f'  OK: route bonus combined {bonus["combined_bonus_pct"]}%')

    enriched = enrich_routes({'routes': [route]}, [{'id': intl_cap['id'], 'profile': p1, 'name': intl_cap['name'], 'emoji': '🌏'}])
    assert enriched[0].get('staff_detail') is not None
    print('  OK: enrich routes')

print('\nAll crew_stats checks passed!')