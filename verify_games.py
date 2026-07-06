"""비행 게임 허브 스모크 테스트"""
from app import create_app
from app.services.game_bridge import get_games, build_launcher_bat

app = create_app()
client = app.test_client()
errors = []
passed = 0


def check(cond, msg):
    global passed
    if cond:
        passed += 1
        print(f'  OK: {msg}')
    else:
        errors.append(msg)
        print(f'  FAIL: {msg}')


with app.app_context():
    print('=== Games Hub Verification ===')
    check(len(get_games()) >= 2, 'flight_games.json has 2+ games')
    bat = build_launcher_bat()
    check('fgfs' in bat and 'RKSI' in bat, 'launcher bat contains fgfs and airport')

    for path in ['/games', '/games/flightgear', '/games/play/geo-fs', '/api/games/catalog']:
        r = client.get(path)
        check(r.status_code == 200, f'GET {path} → {r.status_code}')

    r = client.get('/api/games/flightgear/launcher.bat')
    check(r.status_code == 200 and b'FlightGear' in r.data, 'launcher.bat download')

    r = client.post('/api/games/session/start', json={'game_id': 'geo-fs'})
    check(r.status_code == 200, 'session start')

    r = client.post('/api/games/session/complete', json={'game_id': 'geo-fs'})
    check(r.status_code == 200, 'session complete')

    r = client.post('/api/games/session/complete', json={'game_id': 'geo-fs'})
    check(r.status_code == 400, 'duplicate complete blocked')

print(f'\n=== Results: {passed} passed, {len(errors)} failed ===')
if errors:
    for e in errors:
        print(f'  - {e}')
    raise SystemExit(1)
print('All game checks passed!')