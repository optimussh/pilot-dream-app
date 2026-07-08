"""Smoke test for 기장 생활 (pilot_extras) APIs."""
from app import create_app

app = create_app()
client = app.test_client()
errors = []


def check(method, path, expect=200, json_body=None):
    if method == 'GET':
        r = client.get(path)
    else:
        r = client.post(path, json=json_body or {})
    ok = r.status_code == expect
    label = 'OK' if ok else 'FAIL'
    print(f"  {label}: {method} {path} → {r.status_code}")
    if not ok:
        errors.append(f"{method} {path} (got {r.status_code}, want {expect})")
    return r


print("=== Page ===")
check('GET', '/captain-life')

print("\n=== Summary & read APIs ===")
r = check('GET', '/api/extras/summary')
if r.status_code == 200:
    data = r.get_json()
    for key in (
        'captain_duty', 'daily_airport', 'crew_cards', 'codex',
        'schedule', 'on_time', 'weekly_demand', 'fuel_quiz_remaining',
    ):
        if key not in data:
            print(f"  FAIL: summary missing key '{key}'")
            errors.append(f"summary missing {key}")
        else:
            print(f"  OK: summary has '{key}'")

check('GET', '/api/extras/codex')
check('GET', '/api/extras/fuel-quiz')

print("\n=== Service imports ===")
with app.app_context():
    from app.services.pilot_extras import (
        get_extras_summary, get_crew_cards, get_aircraft_codex,
        get_fuel_quiz, FUEL_QUESTIONS,
    )
    from app.services.gamification import get_or_create_progress
    prog = get_or_create_progress()
    summary = get_extras_summary(prog)
    assert summary['crew_cards'], 'crew_cards empty'
    assert summary['codex']['total'] > 0, 'codex empty'
    q, err = get_fuel_quiz(prog)
    assert q and not err, f'fuel quiz failed: {err}'
    assert len(FUEL_QUESTIONS) >= 3
    print("  OK: service layer checks passed")

print("\n=== Data files ===")
with app.app_context():
    from app.services.gamification import load_json
    for fname in ('crew_cards.json', 'airport_daily_facts.json', 'weekly_demand_events.json'):
        data = load_json(fname)
        if not data:
            print(f"  FAIL: {fname} empty")
            errors.append(fname)
        else:
            print(f"  OK: {fname} ({len(data)} items)")

if errors:
    print(f"\nFailed ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    raise SystemExit(1)

print("\nAll pilot_extras checks passed!")