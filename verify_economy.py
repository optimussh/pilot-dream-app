"""경제/상점 시스템 통합 검증"""
import json
from app import create_app
from app.models import db, UserProgress, LogbookEntry
from app.services.gamification import get_or_create_progress
from app.services.gamification import load_json
from app.services.economy import (
    award_money, buy_item, sell_item, process_salary, process_salary_bonuses,
    get_wallet_summary, get_all_aircraft_status, get_bonus_progress, claim_salary_bonus,
)

app = create_app()
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
    print('=== Economy System Verification ===')

    # Reset economy state for clean test
    LogbookEntry.query.delete()
    prog = UserProgress.query.first()
    if prog:
        prog.wallet_balance = 0
        prog.salary_milestones_paid = 0
        prog.hour_boosts = 0
        prog.inventory = '[]'
        prog.owned_aircraft = '["b737","a320"]'
        prog.set_json('owned_aircraft', ['b737', 'a320'])
        prog.set_json('inventory', [])
        db.session.commit()

    prog = get_or_create_progress()
    check(prog.wallet_balance == 0, 'wallet starts at 0')

    award_money(prog, 500000, 'test reward')
    db.session.commit()
    check(prog.wallet_balance == 500000, 'award_money works')

    items = load_json('shop_items.json')
    check(len(items) >= 150, f'shop has {len(items)} items')

    bonuses = load_json('salary_bonuses.json')
    check(len(bonuses) >= 20, f'salary bonuses: {len(bonuses)}')
    newly, total = process_salary_bonuses(prog)
    check(isinstance(newly, list), 'bonus check runs')

    progress = get_bonus_progress(prog)
    claimable = [b for b in progress if b.get('claimable')]
    if claimable:
        bid = claimable[0]['id']
        bal_before = prog.wallet_balance or 0
        ok, result = claim_salary_bonus(prog, bid)
        check(ok and result['amount_paid'] > 0, f'claim bonus: {bid}')
        check(bid not in [b['id'] for b in get_bonus_progress(prog) if b.get('claimable')], 'bonus no longer claimable')
        check((prog.wallet_balance or 0) > bal_before, 'wallet increased after claim')

    aircraft = load_json('aircraft.json')
    check(len(aircraft) >= 40, f'aircraft catalog has {len(aircraft)} types')

    statuses = get_all_aircraft_status(prog)
    check(len(statuses) == len(aircraft), 'aircraft status for all types')

    owned = [s for s in statuses if s.get('owned')]
    check(len(owned) >= 2, f'starter aircraft owned ({len(owned)})')

    # Buy avatar item
    ok, msg = buy_item(prog, 'av_cap_ke')
    check(ok, f'buy avatar: {msg}')
    inv = prog._json('inventory', [])
    check('av_cap_ke' in inv, 'avatar in inventory')

    # Sell avatar item
    ok, msg = sell_item(prog, 'av_cap_ke')
    check(ok, f'sell avatar: {msg}')
    check('av_cap_ke' not in prog._json('inventory', []), 'avatar removed after sell')

    # Salary on 20 flights
    for i in range(20):
        db.session.add(LogbookEntry(
            date='2026-07-01', flight_number=f'T{i:03d}',
            aircraft='B737-800', route='ICN-GMP', hours=1.5
        ))
    db.session.commit()
    result = process_salary(prog)
    check(result is not None and result['amount'] >= 10_000_000, 'salary at 20 flights')

    # Buy boost
    prog.wallet_balance = 5_000_000
    db.session.commit()
    ok, msg = buy_item(prog, 'boost_10h')
    check(ok and prog.hour_boosts == 10, f'buy boost: {msg}')

    wallet = get_wallet_summary(prog)
    check('balance_formatted' in wallet, 'wallet summary')
    check('salary' in wallet, 'salary in wallet')
    check('avatar_preview' in wallet, 'avatar preview')
    check('avatar_visual' in wallet, 'avatar visual')

    # API routes
    client = app.test_client()
    for path in ['/shop', '/hangar', '/api/economy/wallet', '/api/shop/items', '/api/hangar/aircraft']:
        r = client.get(path)
        check(r.status_code == 200, f'GET {path} → {r.status_code}')

    r = client.get('/api/aircraft')
    data = r.get_json()
    check(isinstance(data, list) and 'owned' in data[0], 'aircraft API enriched')

    print(f'\n=== Results: {passed} passed, {len(errors)} failed ===')
    if errors:
        for e in errors:
            print(f'  - {e}')
        raise SystemExit(1)
    print('All economy checks passed!')