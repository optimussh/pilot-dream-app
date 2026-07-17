"""Smoke test for airline, guide, player stats."""
from app import create_app

app = create_app()
c = app.test_client()
errors = []

for path in ['/airline', '/guide', '/api/airline/dashboard', '/api/airline/revenue',
             '/api/airline/invest', '/api/airline/route-templates', '/api/airline/crew',
             '/api/guide/sections', '/api/guide/onboarding', '/api/player/stats',
             '/api/airline/radar-flights']:
    r = c.get(path)
    ok = r.status_code == 200
    print(f"  {'OK' if ok else 'FAIL'}: GET {path} -> {r.status_code}")
    if not ok:
        errors.append(path)

with app.app_context():
    from app.services.gamification import get_or_create_progress
    from app.services.airline_ops import get_airline_dashboard, settle_weekly_revenue
    from app.services.player_stats import get_player_stats, add_stat_xp
    from app.services.guide_service import get_guide_sections, get_onboarding_state
    from app.services.space_ops import get_space_status
    prog = get_or_create_progress()
    assert len(get_guide_sections()) >= 10
    assert get_player_stats(prog)['stats']
    assert get_onboarding_state(prog)['total'] >= 5
    add_stat_xp(prog, 'flying', 10)
    dash = get_airline_dashboard(prog)
    from app.services.airline_revenue import fetch_revenue_dashboard
    from app.services.airline_company import build_company_board, allocate_weekly_profit
    rev = fetch_revenue_dashboard(prog)
    assert rev.get('revenue_panel'), 'revenue_panel missing'
    assert len(rev['revenue_panel'].get('cargo_offers', [])) == 3, 'cargo offers'
    assert len(rev['revenue_panel'].get('briefings', [])) == 5, 'briefings'
    print(f"  OK: revenue panel ({len(rev['revenue_panel']['cargo_offers'])} cargo, {len(rev['revenue_panel']['briefings'])} briefings)")
    if dash.get('airline', {}).get('founded'):
        cb = dash['ops'].get('company_board') or build_company_board(prog)
        assert cb and cb.get('story') and len(cb['story']) == 3, 'company board story'
        assert 'allocation' in cb, 'company allocation'
        print(f"  OK: company board (vault={cb.get('vault', 0)}, alloc_done={cb['allocation'].get('done')})")
        from app.services.airline_invest import build_invest_panel, issue_shares
        inv = build_invest_panel(prog)
        assert inv and inv.get('market') and len(inv['market']) >= 4, 'invest market'
        assert inv.get('shares') is not None, 'invest shares'
        print(f"  OK: invest panel (firms={len(inv['market'])}, issued={inv['shares'].get('issued')})")
        if inv['shares'].get('can_issue'):
            ok, msg = issue_shares(prog)
            assert ok, msg
            inv2 = build_invest_panel(prog)
            assert inv2['shares']['issued'] and inv2['shares']['my_pct'] == 100
            print('  OK: issue shares 100%')
        r = c.get('/api/guide/sections')
        secs = (r.get_json() or {}).get('sections') or []
        assert any(s.get('id') == 'company_layer2' for s in secs), 'guide company_layer2'
        assert any(s.get('id') == 'invest_layer3' for s in secs), 'guide invest_layer3'
        print('  OK: guide has company_layer2 + invest_layer3')
    # 대시보드는 only_active — 전체 풀은 /api/airline/crew
    from app.services.airline_ops import get_hireable_crew
    full_crew = get_hireable_crew(prog, slim=True, only_active=False)
    assert len(full_crew) >= 50, 'full crew pool'
    active = dash['ops']['hireable_crew']
    print(f"  OK: dashboard crew active={len(active)} full_pool={len(full_crew)}")
    rcrew = c.get('/api/airline/crew')
    assert rcrew.status_code == 200 and len(rcrew.get_json().get('hireable_crew', [])) >= 50
    print('  OK: lazy crew API')
    rt = c.get('/api/airline/route-templates')
    assert rt.status_code == 200 and len(rt.get_json().get('templates', [])) >= 10
    print('  OK: lazy route-templates API')
    unlocked = [c for c in full_crew if c.get('unlocked')]
    if unlocked:
        from app.services.airline_ops import hire_crew, fire_crew
        from app.services.pilot_features import get_airline_info
        if get_airline_info(prog).get('founded'):
            cid = unlocked[0]['id']
            h_ok, _ = hire_crew(prog, cid)
            if h_ok:
                ok, _ = fire_crew(prog, cid)
                assert ok, 'fire_crew failed'
                print(f'  OK: fire_crew ({unlocked[0]["name"]})')
            else:
                print('  SKIP: fire_crew (already hired)')
        else:
            print('  SKIP: fire_crew (airline not founded)')
    get_space_status(prog)
    print("  OK: service layer")

if errors:
    raise SystemExit(1)
print("\nAll airline/guide checks passed!")