"""경제 시스템: 급여, 학습 보상, 상점, 기체 해금/구매"""
import json
from datetime import datetime
from app.models import db, UserProgress, LogbookEntry, UserBadge
from app.services.gamification import load_json, get_total_hours, log_activity, get_or_create_progress

# ── 급여 & 보상 밸런스 ──
SALARY_PER_MILESTONE = 10_000_000
FLIGHTS_PER_SALARY = 20
SELL_RATIO = 0.6

LEARNING_REWARDS = {
    'quiz_90': 800_000,
    'quiz_80': 500_000,
    'quiz_50': 300_000,
    'quiz_done': 150_000,
    'mission': 250_000,
    'mission_all_bonus': 500_000,
    'flashcard': 80_000,
    'scenario_a': 600_000,
    'scenario_b': 400_000,
    'scenario_c': 200_000,
    'scenario_all_bonus': 800_000,
    'weekly': 1_500_000,
    'first_flight': 1_000_000,
    'letter': 300_000,
    'atc_practice': 100_000,
}

STARTER_AIRCRAFT = ['b737', 'a320']
HOUR_BOOST_PER_WON = 1 / 250_000  # ₩250,000 = 1시간 가속


def format_krw(amount):
    return f'₩{amount:,}'


def _tx_log(prog, tx_type, amount, detail):
    log = prog._json('transaction_log', [])
    log.append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().isoformat(),
        'type': tx_type,
        'amount': amount,
        'detail': detail,
        'balance': prog.wallet_balance or 0,
    })
    if len(log) > 100:
        log = log[-100:]
    prog.set_json('transaction_log', log)


def award_money(prog, amount, reason, tx_type='reward'):
    if amount <= 0:
        return 0
    prog.wallet_balance = (prog.wallet_balance or 0) + amount
    _tx_log(prog, tx_type, amount, reason)
    log_activity(prog, 'money', f'+{format_krw(amount)}: {reason}')
    return amount


def spend_money(prog, amount, reason, tx_type='purchase'):
    balance = prog.wallet_balance or 0
    if balance < amount:
        return False, f'잔액이 부족합니다. (필요: {format_krw(amount)}, 보유: {format_krw(balance)})'
    prog.wallet_balance = balance - amount
    _tx_log(prog, tx_type, -amount, reason)
    log_activity(prog, 'money', f'-{format_krw(amount)}: {reason}')
    return True, 'ok'


def get_effective_hours(prog):
    return get_total_hours(prog) + (prog.hour_boosts or 0)


def get_owned_aircraft(prog):
    owned = prog._json('owned_aircraft', STARTER_AIRCRAFT[:])
    for s in STARTER_AIRCRAFT:
        if s not in owned:
            owned.append(s)
    return list(dict.fromkeys(owned))


def get_aircraft_catalog():
    return {a['id']: a for a in load_json('aircraft.json')}


def get_shop_catalog():
    return {i['id']: i for i in load_json('shop_items.json')}


def aircraft_unlock_status(prog, aircraft_id):
    catalog = get_aircraft_catalog()
    ac = catalog.get(aircraft_id)
    if not ac:
        return None
    owned = get_owned_aircraft(prog)
    if aircraft_id in owned:
        return {
            **ac,
            'owned': True,
            'unlocked': True,
            'progress_pct': 100,
            'effective_hours': get_effective_hours(prog),
            'hours_remaining': 0,
            'discounted_price': 0,
        }
    req = ac.get('unlock_hours', 0)
    eff = get_effective_hours(prog)
    if req <= 0 or eff >= req:
        return {
            **ac,
            'owned': False,
            'unlocked': True,
            'progress_pct': 100,
            'effective_hours': eff,
            'hours_remaining': 0,
            'discounted_price': 0,
            'unlock_method': 'hours' if eff >= req and req > 0 else 'starter',
        }
    pct = min(99, int(eff / req * 100))
    base_price = ac.get('purchase_price', 0)
    discount = pct / 100 * 0.7
    discounted = max(int(base_price * (1 - discount)), int(base_price * 0.15))
    return {
        **ac,
        'owned': False,
        'unlocked': False,
        'progress_pct': pct,
        'effective_hours': eff,
        'hours_remaining': round(req - eff, 1),
        'discounted_price': discounted,
        'full_price': base_price,
    }


def get_all_aircraft_status(prog):
    catalog = get_aircraft_catalog()
    return [aircraft_unlock_status(prog, aid) for aid in catalog]


def get_salary_bonuses():
    return load_json('salary_bonuses.json')


def _bonus_paid_set(prog):
    return set(prog._json('salary_bonuses_paid', []))


def _mark_bonus_paid(prog, bonus_id):
    paid = prog._json('salary_bonuses_paid', [])
    if bonus_id not in paid:
        paid.append(bonus_id)
        prog.set_json('salary_bonuses_paid', paid)


def _logbook_stats():
    entries = LogbookEntry.query.all()
    aircraft_types = {e.aircraft for e in entries if e.aircraft}
    routes = {e.route for e in entries if e.route}
    logbook_hours = sum(e.hours for e in entries)
    max_single = max((e.hours for e in entries), default=0)
    has_international = any(
        '-' in (e.route or '') and any(
            code in (e.route or '').upper()
            for code in ('ICN', 'GMP', 'PUS', 'CJU', 'CJJ', 'TAE', 'KWJ', 'RSU', 'USN', 'WJU')
        ) and len((e.route or '').split('-')) == 2
        and (e.route or '').split('-')[0].strip() != (e.route or '').split('-')[1].strip()
        for e in entries
    )
    intl_routes = [e for e in entries if e.route and '-' in e.route]
    for e in intl_routes:
        parts = [p.strip().upper() for p in e.route.split('-')]
        if len(parts) == 2 and parts[0] != parts[1]:
            korea = {'ICN', 'GMP', 'PUS', 'CJU', 'CJJ', 'TAE', 'KWJ', 'RSU', 'USN', 'WJU', 'KUV', 'MWX'}
            if (parts[0] in korea) != (parts[1] in korea):
                has_international = True
                break
    return {
        'flight_count': len(entries),
        'aircraft_variety': len(aircraft_types),
        'unique_routes': len(routes),
        'logbook_hours': logbook_hours,
        'max_single_hours': max_single,
        'has_international': has_international,
    }


def _bonus_met(prog, bonus, stats=None, extra=None):
    stats = stats or _logbook_stats()
    extra = extra or {}
    btype = bonus['type']
    val = bonus['value']
    if btype == 'flight_count':
        return stats['flight_count'] >= val
    if btype == 'total_hours':
        return get_total_hours(prog) >= val
    if btype == 'logbook_hours':
        return stats['logbook_hours'] >= val
    if btype == 'badge_count':
        return UserBadge.query.count() >= val
    if btype == 'aircraft_variety':
        return stats['aircraft_variety'] >= val
    if btype == 'single_flight_hours':
        return stats['max_single_hours'] >= val
    if btype == 'streak_days':
        return (prog.streak_days or 0) >= val
    if btype == 'mission_streak':
        return (prog.daily_mission_streak or 0) >= val
    if btype == 'flashcard_count':
        return len(prog._json('flashcards_learned', [])) >= val
    if btype == 'owned_aircraft':
        return len(get_owned_aircraft(prog)) >= val
    if btype == 'international_route':
        return stats['has_international']
    if btype == 'unique_routes':
        return stats['unique_routes'] >= val
    if btype == 'quiz_perfect':
        return extra.get('quiz_perfect', False) or any(
            q.get('score', 0) >= 100 for q in prog._json('quiz_history', [])
        )
    return False


def process_salary_bonuses(prog, extra=None):
    """달성 보너스 급여 일괄 체크. 새로 지급된 보너스 목록 반환."""
    paid = _bonus_paid_set(prog)
    stats = _logbook_stats()
    newly = []
    total = 0
    for bonus in get_salary_bonuses():
        bid = bonus['id']
        if bid in paid:
            continue
        if _bonus_met(prog, bonus, stats, extra):
            amount = bonus['amount']
            award_money(prog, amount, f"보너스: {bonus['title']}", 'bonus')
            _mark_bonus_paid(prog, bid)
            newly.append({**bonus, 'amount_paid': amount})
            total += amount
    if newly:
        db.session.commit()
    return newly, total


def get_bonus_progress(prog):
    paid = _bonus_paid_set(prog)
    stats = _logbook_stats()
    result = []
    for bonus in get_salary_bonuses():
        bid = bonus['id']
        achieved = bid in paid
        met = achieved or _bonus_met(prog, bonus, stats)
        current = _bonus_current(prog, bonus, stats)
        result.append({
            **bonus,
            'achieved': achieved,
            'met': met,
            'current': current,
            'target': bonus['value'],
            'amount_formatted': format_krw(bonus['amount']),
        })
    return result


def _bonus_current(prog, bonus, stats):
    btype = bonus['type']
    if btype == 'flight_count':
        return stats['flight_count']
    if btype == 'total_hours':
        return int(get_total_hours(prog))
    if btype == 'logbook_hours':
        return int(stats['logbook_hours'])
    if btype == 'badge_count':
        return UserBadge.query.count()
    if btype == 'aircraft_variety':
        return stats['aircraft_variety']
    if btype == 'single_flight_hours':
        return round(stats['max_single_hours'], 1)
    if btype == 'streak_days':
        return prog.streak_days or 0
    if btype == 'mission_streak':
        return prog.daily_mission_streak or 0
    if btype == 'flashcard_count':
        return len(prog._json('flashcards_learned', []))
    if btype == 'owned_aircraft':
        return len(get_owned_aircraft(prog))
    if btype == 'international_route':
        return 1 if stats['has_international'] else 0
    if btype == 'unique_routes':
        return stats['unique_routes']
    if btype == 'quiz_perfect':
        return 1 if any(q.get('score', 0) >= 100 for q in prog._json('quiz_history', [])) else 0
    return 0


def process_salary(prog):
    flight_count = LogbookEntry.query.count()
    due = flight_count // FLIGHTS_PER_SALARY
    paid = prog.salary_milestones_paid or 0
    if due <= paid:
        return None
    milestones = due - paid
    amount = milestones * SALARY_PER_MILESTONE
    prog.salary_milestones_paid = due
    award_money(prog, amount, f'급여일 ({flight_count}비행 달성 × {milestones}회)')
    db.session.commit()
    return {
        'amount': amount,
        'milestones': milestones,
        'flight_count': flight_count,
        'next_salary_at': (due + 1) * FLIGHTS_PER_SALARY,
    }


def process_all_rewards(prog, extra=None):
    """정기 급여 + 달성 보너스 한번에 처리"""
    salary = process_salary(prog)
    bonuses, bonus_total = process_salary_bonuses(prog, extra)
    return {
        'salary': salary,
        'bonuses': bonuses,
        'bonus_total': bonus_total,
    }


def salary_progress(prog):
    flight_count = LogbookEntry.query.count()
    paid = prog.salary_milestones_paid or 0
    next_at = (paid + 1) * FLIGHTS_PER_SALARY
    progress_in_cycle = flight_count % FLIGHTS_PER_SALARY
    return {
        'flight_count': flight_count,
        'flights_until_salary': next_at - flight_count,
        'progress_in_cycle': progress_in_cycle,
        'cycle_size': FLIGHTS_PER_SALARY,
        'salary_amount': SALARY_PER_MILESTONE,
        'total_salaries_paid': paid,
    }


def buy_aircraft(prog, aircraft_id):
    status = aircraft_unlock_status(prog, aircraft_id)
    if not status:
        return False, '기종을 찾을 수 없습니다.'
    if status['owned']:
        return False, '이미 보유 중인 기종입니다.'
    if status.get('unlocked') and status.get('purchase_price', 0) == 0:
        owned = get_owned_aircraft(prog)
        owned.append(aircraft_id)
        prog.set_json('owned_aircraft', owned)
        db.session.commit()
        return True, f'{status["name"]} 해금 완료!'
    price = status.get('discounted_price') or status.get('purchase_price', 0)
    if price <= 0:
        owned = get_owned_aircraft(prog)
        owned.append(aircraft_id)
        prog.set_json('owned_aircraft', owned)
        db.session.commit()
        return True, f'{status["name"]} 해금 완료!'
    ok, msg = spend_money(prog, price, f'기체 구매: {status["name"]}')
    if not ok:
        return False, msg
    owned = get_owned_aircraft(prog)
    owned.append(aircraft_id)
    prog.set_json('owned_aircraft', owned)
    db.session.commit()
    return True, f'{status["name"]} 구매 완료! ({format_krw(price)})'


def accelerate_unlock(prog, aircraft_id, money_amount):
    status = aircraft_unlock_status(prog, aircraft_id)
    if not status:
        return False, '기종을 찾을 수 없습니다.'
    if status['owned'] or status.get('unlocked'):
        return False, '이미 해금된 기종입니다.'
    if money_amount <= 0:
        return False, '금액을 입력해주세요.'
    ok, msg = spend_money(prog, money_amount, f'해금 가속: {status["name"]}')
    if not ok:
        return False, msg
    hours_added = money_amount * HOUR_BOOST_PER_WON
    prog.hour_boosts = round((prog.hour_boosts or 0) + hours_added, 2)
    db.session.commit()
    new_status = aircraft_unlock_status(prog, aircraft_id)
    return True, {
        'message': f'+{round(hours_added, 1)}시간 가속 적용! (총 부스트: {prog.hour_boosts}h)',
        'hours_added': round(hours_added, 1),
        'new_status': new_status,
        'auto_unlocked': new_status.get('unlocked', False),
    }


def buy_item(prog, item_id):
    catalog = get_shop_catalog()
    item = catalog.get(item_id)
    if not item:
        return False, '아이템을 찾을 수 없습니다.'
    inventory = prog._json('inventory', [])
    if item_id in inventory and not item.get('stackable'):
        return False, '이미 보유한 아이템입니다.'
    price = item.get('price', 0)
    ok, msg = spend_money(prog, price, f'구매: {item["name"]}')
    if not ok:
        return False, msg
    if item.get('category') == 'boost':
        hours = item.get('boost_hours', 0)
        prog.hour_boosts = round((prog.hour_boosts or 0) + hours, 2)
    else:
        if item_id not in inventory:
            inventory.append(item_id)
        prog.set_json('inventory', inventory)
    db.session.commit()
    return True, f'{item["name"]} 구매 완료!'


def sell_item(prog, item_id):
    catalog = get_shop_catalog()
    item = catalog.get(item_id)
    if not item:
        return False, '아이템을 찾을 수 없습니다.'
    if not item.get('sellable', True):
        return False, '판매할 수 없는 아이템입니다.'
    inventory = prog._json('inventory', [])
    if item_id not in inventory:
        return False, '보유하지 않은 아이템입니다.'
    equipped = prog._json('equipped_avatar', {})
    loadouts = prog._json('aircraft_loadouts', {})
    for slot, val in equipped.items():
        if val == item_id:
            return False, '장착 중인 아이템은 먼저 해제해주세요.'
    for ac_id, deco in loadouts.items():
        for slot, val in (deco or {}).items():
            if val == item_id:
                return False, '기체에 장착 중인 아이템은 먼저 해제해주세요.'
    sell_price = int(item.get('price', 0) * SELL_RATIO)
    inventory.remove(item_id)
    prog.set_json('inventory', inventory)
    award_money(prog, sell_price, f'판매: {item["name"]}', 'sell')
    db.session.commit()
    return True, f'{item["name"]} 판매 완료! (+{format_krw(sell_price)})'


def equip_avatar(prog, slot, item_id):
    catalog = get_shop_catalog()
    inventory = prog._json('inventory', [])
    equipped = prog._json('equipped_avatar', {})
    if item_id and item_id not in inventory:
        return False, '보유하지 않은 아이템입니다.'
    if item_id:
        item = catalog.get(item_id)
        if not item or item.get('category') != 'avatar':
            return False, '아바타 아이템이 아닙니다.'
        if item.get('slot') != slot:
            return False, f'이 아이템은 {item.get("slot")} 슬롯용입니다.'
    if item_id:
        equipped[slot] = item_id
    else:
        equipped.pop(slot, None)
    prog.set_json('equipped_avatar', equipped)
    db.session.commit()
    return True, '장착 완료!'


def set_active_aircraft(prog, aircraft_id):
    owned = get_owned_aircraft(prog)
    if aircraft_id not in owned:
        return False, '보유하지 않은 기종입니다.'
    prog.active_aircraft = aircraft_id
    db.session.commit()
    return True, '주력 기체 변경 완료!'


def equip_aircraft_deco(prog, aircraft_id, slot, item_id):
    owned = get_owned_aircraft(prog)
    if aircraft_id not in owned:
        return False, '보유하지 않은 기종입니다.'
    catalog = get_shop_catalog()
    inventory = prog._json('inventory', [])
    loadouts = prog._json('aircraft_loadouts', {})
    ac_loadout = loadouts.get(aircraft_id, {})
    if item_id:
        if item_id not in inventory:
            return False, '보유하지 않은 아이템입니다.'
        item = catalog.get(item_id)
        if not item or item.get('category') not in ('livery', 'deco', 'lounge'):
            return False, '장식 아이템이 아닙니다.'
        applies = item.get('applies_to', [])
        if applies and aircraft_id not in applies and '*' not in applies:
            return False, '이 기종에 적용할 수 없는 아이템입니다.'
        ac_loadout[slot] = item_id
    else:
        ac_loadout.pop(slot, None)
    loadouts[aircraft_id] = ac_loadout
    prog.set_json('aircraft_loadouts', loadouts)
    db.session.commit()
    return True, '기체 장식 적용 완료!'


def get_wallet_summary(prog):
    inv = prog._json('inventory', [])
    catalog = get_shop_catalog()
    equipped = prog._json('equipped_avatar', {})
    loadouts = prog._json('aircraft_loadouts', {})
    active = prog.active_aircraft or 'b737'
    ac_catalog = get_aircraft_catalog()
    return {
        'balance': prog.wallet_balance or 0,
        'balance_formatted': format_krw(prog.wallet_balance or 0),
        'hour_boosts': prog.hour_boosts or 0,
        'effective_hours': get_effective_hours(prog),
        'salary': salary_progress(prog),
        'bonuses': get_bonus_progress(prog),
        'bonuses_achieved': sum(1 for b in get_bonus_progress(prog) if b['achieved']),
        'bonuses_total': len(get_salary_bonuses()),
        'owned_aircraft': get_owned_aircraft(prog),
        'active_aircraft': active,
        'active_aircraft_name': ac_catalog.get(active, {}).get('name', active),
        'inventory_count': len(inv),
        'inventory': [
            {**catalog[i], 'id': i} for i in inv if i in catalog
        ],
        'equipped_avatar': {
            slot: {**catalog.get(iid, {}), 'id': iid} if iid else None
            for slot, iid in equipped.items()
        },
        'aircraft_loadouts': loadouts,
        'transactions': list(reversed(prog._json('transaction_log', [])[-20:])),
        'avatar_preview': build_avatar_preview(equipped, catalog),
    }


def build_avatar_preview(equipped, catalog):
    defaults = {'head': '👨‍✈️', 'uniform': '', 'accessory': '', 'wings': ''}
    parts = []
    for slot in ('wings', 'head', 'uniform', 'accessory'):
        iid = equipped.get(slot)
        if iid and iid in catalog:
            parts.append(catalog[iid].get('emoji', defaults.get(slot, '')))
        elif slot == 'head':
            parts.append('👨‍✈️')
    return ' '.join(p for p in parts if p)


def get_unlocked_aircraft_names(prog):
    """대시보드/레이더용 — 보유 + 해금된 기종 이름 목록"""
    catalog = get_aircraft_catalog()
    owned = get_owned_aircraft(prog)
    names = []
    for aid in owned:
        if aid in catalog:
            names.append(catalog[aid]['name'])
    for aid, ac in catalog.items():
        if aid not in owned:
            st = aircraft_unlock_status(prog, aid)
            if st and st.get('unlocked'):
                names.append(ac['name'])
    return list(dict.fromkeys(names))