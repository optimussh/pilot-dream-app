"""End-to-end smoke: today's flight, nav, and core pages must not 500."""
import json
from app import create_app
from app.models import db, LogbookEntry
from app.services.gamification import get_or_create_progress, today_str

app = create_app()
c = app.test_client()
errors = []
ok_n = 0


def check(cond, msg, body=''):
    global ok_n
    if cond:
        ok_n += 1
        print(f'  OK: {msg}')
    else:
        errors.append(msg)
        print(f'FAIL: {msg} {(body or "")[:240].replace(chr(10), " ")}')


print('=== pages ===')
pages = [
    '/', '/captain-day', '/logbook', '/airline', '/learn', '/quiz',
    '/flashcards', '/scenarios', '/captain-life', '/shop', '/hangar',
    '/radar/', '/atc-english', '/flight-planner', '/minigames',
    '/badges', '/medals', '/korea-career', '/guide', '/world',
    '/airport-quiz', '/checklist', '/future-aviation', '/first-flight',
]
for path in pages:
    r = c.get(path, follow_redirects=True)
    check(r.status_code == 200, f'GET {path} -> {r.status_code}', r.get_data(as_text=True))

print('\n=== APIs ===')
apis = [
    '/api/duty/today', '/api/nav/more', '/api/airline/green',
    '/api/airline/dashboard?light=1', '/api/gamification/status',
    '/api/economy/wallet', '/api/minigames/stats', '/api/medals/status',
    '/api/player/stats', '/api/guide/sections',
]
for path in apis:
    r = c.get(path)
    check(r.status_code == 200, f'GET {path} -> {r.status_code}', r.get_data(as_text=True))

print('\n=== duty flow (restore after) ===')
with app.app_context():
    prog = get_or_create_progress()
    original_meta = prog.pilot_meta
    original_wallet = prog.wallet_balance
    original_log = prog.activity_log
    log_ids_before = {e.id for e in LogbookEntry.query.all()}

try:
    r = c.get('/api/duty/today')
    d = r.get_json() or {}
    check(r.status_code == 200 and d.get('flight'), 'duty payload')
    q = d.get('airport_q') or {}
    dest = (d.get('flight') or {}).get('dest')
    check(q.get('target_code') == dest or dest not in ('JFK', 'CJU', 'GMP', 'ICN'),
          f'quiz target={q.get("target_code")} dest={dest}')

    # wrong answer stays 400
    r = c.post('/api/duty/complete', json={'step_id': 'airport', 'answer_code': 'ZZZ'})
    check(r.status_code == 400, f'wrong airport -> {r.status_code}')

    # skip remaining minigames, complete logbook
    for sid in ('airport', 'refuel', 'luggage', 'landing'):
        c.post('/api/duty/skip', json={'step_id': sid})
    r = c.post('/api/duty/complete', json={'step_id': 'logbook'})
    body = r.get_data(as_text=True)
    check(r.status_code == 200, f'logbook complete -> {r.status_code}', body)
    duty = (r.get_json() or {}).get('duty') or {}
    check(duty.get('logged') or duty.get('complete'), f'logged/complete {duty.get("logged")} {duty.get("complete")}')

    r = c.post('/api/duty/complete', json={'step_id': 'atc'})
    check(r.status_code == 200, f'bonus atc -> {r.status_code}', r.get_data(as_text=True))

    r = c.post('/api/duty/complete', json={'step_id': 'checklist', 'items': ['c1']})
    check(r.status_code == 400, f'partial checklist -> {r.status_code}')
    r = c.post('/api/duty/complete', json={'step_id': 'checklist', 'items': ['c1', 'c2', 'c3']})
    check(r.status_code == 200, f'full checklist -> {r.status_code}', r.get_data(as_text=True))

    r = c.post('/api/airline/green/toggle', json={'option': 'eco_meals'})
    check(r.status_code == 200, f'green toggle -> {r.status_code}', r.get_data(as_text=True))
    c.post('/api/airline/green/toggle', json={'option': 'eco_meals'})

    r = c.post('/api/minigames/submit', json={'game_id': 'refuel', 'score': 10, 'is_win': False})
    check(r.status_code in (200, 400), f'minigame submit -> {r.status_code}')
finally:
    with app.app_context():
        prog = get_or_create_progress()
        prog.pilot_meta = original_meta
        prog.wallet_balance = original_wallet
        prog.activity_log = original_log
        db.session.commit()
        for e in LogbookEntry.query.all():
            if e.id not in log_ids_before:
                db.session.delete(e)
        db.session.commit()
        after = {e.id for e in LogbookEntry.query.all()}
        check(after == log_ids_before, f'logbook restored {len(log_ids_before)}->{len(after)}')

print('\n=== nav more ===')
r = c.get('/api/nav/more')
items = (r.get_json() or {}).get('items') or []
hrefs = [i.get('href') for i in items]
check('/minigames' in hrefs and '/learn' in hrefs and '/world' in hrefs, f'more hrefs {hrefs[:6]}')
for it in items[:4]:
    rr = c.get(it['href'], follow_redirects=True)
    check(rr.status_code == 200, f'more[{it["id"]}] {it["href"]} -> {rr.status_code}')

print(f'\n=== Results: {ok_n} passed, {len(errors)} failed ===')
for e in errors:
    print(f'  - {e}')
if errors:
    raise SystemExit(1)
print('All smoke checks passed!')
