"""Green aviation: status/toggle must not 500; fleet from owned_aircraft."""
import json
from app.services.green_aviation import get_green_status, toggle_eco_option


class FakeProg:
    """Mirrors UserProgress._json without a wallet column (the production bug)."""

    def __init__(self):
        self.wallet_balance = 10_000_000
        self.owned_aircraft = json.dumps(['b737', 'a320'])
        self.pilot_meta = '{}'
        self.transaction_log = '[]'
        self.activity_log = '[]'

    def _json(self, field, default):
        try:
            return json.loads(getattr(self, field) or json.dumps(default))
        except (json.JSONDecodeError, TypeError):
            return default

    def set_json(self, field, value):
        setattr(self, field, json.dumps(value, ensure_ascii=False))


def test_green_status_does_not_read_missing_wallet_column():
    status = get_green_status(FakeProg())
    assert status['eco_meals'] is False
    assert status['recycling'] is False
    assert status['saf'] is False
    # base 10 + 5 per owned aircraft (2 starters)
    assert status['points'] == 20, status
    assert 'level_name' in status


def test_toggle_eco_meals_updates_flags_and_points():
    prog = FakeProg()
    # Pre-claim levels so scoring does not try to award money (needs DB streak).
    prog.set_json('pilot_meta', {
        'green': {
            'points': 0, 'level': 1, 'eco_meals': False, 'recycling': False,
            'saf': False, 'claimed_levels': [2, 3, 4],
        }
    })
    ok, msg = toggle_eco_option(prog, 'eco_meals')
    assert ok, msg
    status = get_green_status(prog)
    assert status['eco_meals'] is True
    assert status['points'] == 35, status  # 10 + 15 + 10
    ok, msg = toggle_eco_option(prog, 'eco_meals')
    assert ok, msg
    status = get_green_status(prog)
    assert status['eco_meals'] is False
    assert status['points'] == 20, status


def test_toggle_unknown_option_is_safe():
    prog = FakeProg()
    ok, msg = toggle_eco_option(prog, 'not_a_real_option')
    assert not ok
    assert msg
    status = get_green_status(prog)
    assert status['eco_meals'] is False
    assert status['points'] == 20, status


def test_http_green_toggle_and_related_apis():
    """Flask test client: green GET/POST, plus other new pages that share the same error toast."""
    from app import create_app
    from app.models import db
    from app.services.gamification import get_or_create_progress

    app = create_app()
    c = app.test_client()
    errors = []

    def check(cond, msg, body=''):
        if cond:
            print(f'  OK: {msg}')
        else:
            errors.append(msg)
            snippet = (body or '')[:400].replace('\n', ' ')
            print(f'FAIL: {msg} {snippet}')

    with app.app_context():
        from app.services.gamification import today_str
        prog = get_or_create_progress()
        original = {
            'pilot_meta': prog.pilot_meta,
            'wallet_balance': prog.wallet_balance,
            'transaction_log': prog.transaction_log,
            'activity_log': prog.activity_log,
            'last_active_date': prog.last_active_date,
        }
        # Already-active today + levels claimed: toggle must persist without streak/reward commits.
        meta = prog._json('pilot_meta', {})
        green = meta.get('green') or {}
        green.update({
            'eco_meals': False, 'recycling': False, 'saf': False,
            'claimed_levels': [2, 3, 4],
        })
        meta['green'] = green
        prog.set_json('pilot_meta', meta)
        prog.last_active_date = today_str()
        db.session.commit()

    try:
        r = c.get('/api/airline/green')
        check(r.status_code == 200, f'GET /api/airline/green -> {r.status_code}', r.get_data(as_text=True))
        g0 = r.get_json() or {}
        check('eco_meals' in g0 and 'points' in g0, f'green payload keys={list(g0)[:8]}')

        r = c.post('/api/airline/green/toggle', json={'option': 'eco_meals'})
        check(r.status_code == 200, f'POST green/toggle eco_meals -> {r.status_code}', r.get_data(as_text=True))
        d = r.get_json() or {}
        check(d.get('status') == 'ok' and isinstance(d.get('green'), dict), f'toggle json status={d.get("status")}')
        toggled = (d.get('green') or {}).get('eco_meals')
        check(toggled is True or toggled is False, f'toggle eco_meals={toggled}')
        check(toggled != g0.get('eco_meals'), f'toggle flipped {g0.get("eco_meals")} -> {toggled}')

        r2 = c.get('/api/airline/green')
        g2 = r2.get_json() or {}
        check(r2.status_code == 200 and g2.get('eco_meals') == toggled,
              f'persist eco_meals={g2.get("eco_meals")} expected={toggled}')

        r = c.post('/api/airline/green/toggle', json={'option': 'recycling'})
        check(r.status_code == 200, f'POST green/toggle recycling -> {r.status_code}', r.get_data(as_text=True))

        r = c.post('/api/airline/green/toggle', json={})
        check(r.status_code == 400, f'POST green/toggle empty -> {r.status_code}', r.get_data(as_text=True))

        r = c.get('/airline')
        check(r.status_code == 200, f'GET /airline -> {r.status_code}', r.get_data(as_text=True))
    finally:
        with app.app_context():
            prog = get_or_create_progress()
            prog.pilot_meta = original['pilot_meta']
            prog.wallet_balance = original['wallet_balance']
            prog.transaction_log = original['transaction_log']
            prog.activity_log = original['activity_log']
            prog.last_active_date = original['last_active_date']
            db.session.commit()

    if errors:
        print(f'\n{len(errors)} HTTP checks failed')
        raise SystemExit(1)


if __name__ == '__main__':
    test_green_status_does_not_read_missing_wallet_column()
    print('  OK: get_green_status (no wallet column)')
    test_toggle_eco_meals_updates_flags_and_points()
    print('  OK: toggle eco_meals on/off')
    test_toggle_unknown_option_is_safe()
    print('  OK: unknown option does not crash')
    print('All green unit checks passed!')
    print('\n=== HTTP / related APIs ===')
    test_http_green_toggle_and_related_apis()
    print('All green HTTP checks passed!')

