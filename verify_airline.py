"""Smoke test for airline, guide, player stats."""
from app import create_app

app = create_app()
c = app.test_client()
errors = []

for path in ['/airline', '/guide', '/api/airline/dashboard', '/api/guide/sections',
             '/api/guide/onboarding', '/api/player/stats', '/api/airline/radar-flights']:
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
    get_airline_dashboard(prog)
    get_space_status(prog)
    print("  OK: service layer")

if errors:
    raise SystemExit(1)
print("\nAll airline/guide checks passed!")