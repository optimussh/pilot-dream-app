from flask import Blueprint, render_template, jsonify, request
from app.models import db
from app.services.gamification import get_or_create_progress, load_json
from app.services.economy import (
    get_wallet_summary, get_shop_catalog, get_all_aircraft_status,
    buy_item, sell_item, equip_avatar, buy_aircraft, accelerate_unlock,
    set_active_aircraft, equip_aircraft_deco, get_aircraft_catalog,
    format_krw, SELL_RATIO, get_effective_hours, get_bonus_progress,
    process_salary_bonuses,
)

bp = Blueprint('shop', __name__)


@bp.route('/shop')
def shop_page():
    return render_template('shop.html')


@bp.route('/hangar')
def hangar_page():
    return render_template('shop.html', default_tab='hangar')


@bp.route('/api/economy/wallet')
def wallet_api():
    prog = get_or_create_progress()
    return jsonify(get_wallet_summary(prog))


@bp.route('/api/economy/bonuses')
def bonuses_api():
    prog = get_or_create_progress()
    bonuses = get_bonus_progress(prog)
    by_cat = {}
    for b in bonuses:
        by_cat.setdefault(b.get('category', '기타'), []).append(b)
    return jsonify({
        'bonuses': bonuses,
        'by_category': by_cat,
        'achieved': sum(1 for b in bonuses if b['achieved']),
        'total': len(bonuses),
    })


@bp.route('/api/economy/cosmetics')
def cosmetics_api():
    """레이더/대시보드용 장착 코스메틱"""
    prog = get_or_create_progress()
    wallet = get_wallet_summary(prog)
    catalog = get_shop_catalog()
    active = prog.active_aircraft or 'b737'
    loadouts = prog._json('aircraft_loadouts', {})
    deco = loadouts.get(active, {})
    trail = catalog.get(deco.get('trail'), {})
    livery = catalog.get(deco.get('livery'), {})
    radar_skin = None
    for iid in prog._json('inventory', []):
        item = catalog.get(iid, {})
        if item.get('slot') == 'radar_skin':
            equipped_radar = deco.get('radar_skin') or iid
            if equipped_radar == iid or not deco.get('radar_skin'):
                radar_skin = item
    if deco.get('radar_skin'):
        radar_skin = catalog.get(deco['radar_skin'], radar_skin or {})
    return jsonify({
        'active_aircraft': active,
        'active_aircraft_name': wallet.get('active_aircraft_name'),
        'trail_color': trail.get('color', '#a855f7'),
        'livery_color': livery.get('color', ''),
        'radar_skin': radar_skin,
        'avatar_preview': wallet.get('avatar_preview'),
    })


@bp.route('/api/shop/items')
def shop_items_api():
    items = load_json('shop_items.json')
    catalog = get_shop_catalog()
    prog = get_or_create_progress()
    inventory = set(prog._json('inventory', []))
    equipped = prog._json('equipped_avatar', {})
    equipped_vals = set(equipped.values())
    categories = {}
    for item in items:
        cat = item.get('category', 'other')
        entry = {**item, 'owned': item['id'] in inventory, 'equipped': item['id'] in equipped_vals}
        entry['sell_price'] = int(item.get('price', 0) * SELL_RATIO) if item.get('sellable', True) else 0
        categories.setdefault(cat, []).append(entry)
    return jsonify({
        'categories': categories,
        'balance': prog.wallet_balance or 0,
        'balance_formatted': format_krw(prog.wallet_balance or 0),
    })


@bp.route('/api/hangar/aircraft')
def hangar_aircraft_api():
    prog = get_or_create_progress()
    statuses = get_all_aircraft_status(prog)
    catalog = get_aircraft_catalog()
    loadouts = prog._json('aircraft_loadouts', {})
    shop = get_shop_catalog()
    for st in statuses:
        aid = st['id']
        st['is_active'] = (prog.active_aircraft or 'b737') == aid
        deco = loadouts.get(aid, {})
        st['loadout_details'] = {
            slot: {**shop.get(iid, {}), 'id': iid} if iid else None
            for slot, iid in deco.items()
        }
    by_category = {}
    for st in statuses:
        cat = st.get('category', '기타')
        by_category.setdefault(cat, []).append(st)
    return jsonify({
        'aircraft': statuses,
        'by_category': by_category,
        'owned_count': sum(1 for s in statuses if s.get('owned')),
        'total_count': len(catalog),
        'active_aircraft': prog.active_aircraft or 'b737',
        'hour_boosts': prog.hour_boosts or 0,
        'effective_hours': get_effective_hours(prog),
        'balance': prog.wallet_balance or 0,
    })


@bp.route('/api/shop/buy', methods=['POST'])
def shop_buy():
    data = request.get_json() or {}
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({'error': 'item_id 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = buy_item(prog, item_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok',
        'message': msg,
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/shop/sell', methods=['POST'])
def shop_sell():
    data = request.get_json() or {}
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({'error': 'item_id 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = sell_item(prog, item_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok',
        'message': msg,
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/shop/equip', methods=['POST'])
def shop_equip():
    data = request.get_json() or {}
    slot = data.get('slot')
    item_id = data.get('item_id')
    if not slot:
        return jsonify({'error': 'slot 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = equip_avatar(prog, slot, item_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok',
        'message': msg,
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/hangar/buy', methods=['POST'])
def hangar_buy():
    data = request.get_json() or {}
    aircraft_id = data.get('aircraft_id')
    if not aircraft_id:
        return jsonify({'error': 'aircraft_id 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = buy_aircraft(prog, aircraft_id)
    if not ok:
        return jsonify({'error': msg}), 400
    bonuses, bonus_total = process_salary_bonuses(prog)
    try:
        from app.services.pilot_features import check_aircraft_combos
        combos = check_aircraft_combos(prog)
    except Exception:
        combos = []
    return jsonify({
        'status': 'ok',
        'message': msg,
        'bonuses': bonuses,
        'bonus_total': bonus_total,
        'combos': combos,
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/hangar/accelerate', methods=['POST'])
def hangar_accelerate():
    data = request.get_json() or {}
    aircraft_id = data.get('aircraft_id')
    amount = int(data.get('amount', 0))
    if not aircraft_id or amount <= 0:
        return jsonify({'error': 'aircraft_id와 amount 필요'}), 400
    prog = get_or_create_progress()
    ok, result = accelerate_unlock(prog, aircraft_id, amount)
    if not ok:
        return jsonify({'error': result}), 400
    resp = {
        'status': 'ok',
        'wallet': get_wallet_summary(prog),
    }
    if isinstance(result, dict):
        resp.update(result)
    else:
        resp['message'] = result
    return jsonify(resp)


@bp.route('/api/hangar/set-active', methods=['POST'])
def hangar_set_active():
    data = request.get_json() or {}
    aircraft_id = data.get('aircraft_id')
    if not aircraft_id:
        return jsonify({'error': 'aircraft_id 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = set_active_aircraft(prog, aircraft_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'active_aircraft': aircraft_id})


@bp.route('/api/hangar/equip-deco', methods=['POST'])
def hangar_equip_deco():
    data = request.get_json() or {}
    aircraft_id = data.get('aircraft_id')
    slot = data.get('slot')
    item_id = data.get('item_id')
    if not aircraft_id or not slot:
        return jsonify({'error': 'aircraft_id, slot 필요'}), 400
    prog = get_or_create_progress()
    ok, msg = equip_aircraft_deco(prog, aircraft_id, slot, item_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/payslip')
def payslip_page():
    return render_template('payslip.html')


@bp.route('/api/features/summary')
def features_summary_api():
    from app.services.pilot_features import get_features_summary
    return jsonify(get_features_summary(get_or_create_progress()))


@bp.route('/api/features/season')
def season_api():
    from app.services.pilot_features import get_season_status
    return jsonify(get_season_status(get_or_create_progress()))


@bp.route('/api/features/daily-shop')
def daily_shop_api():
    from app.services.pilot_features import get_daily_shop
    return jsonify({'items': get_daily_shop(get_or_create_progress())})


@bp.route('/api/features/daily-shop/buy', methods=['POST'])
def daily_shop_buy():
    from app.services.pilot_features import get_daily_shop
    from app.services.economy import spend_money
    data = request.get_json() or {}
    item_id = data.get('item_id')
    prog = get_or_create_progress()
    daily = {i['id']: i for i in get_daily_shop(prog)}
    if item_id not in daily:
        return jsonify({'error': '오늘의 특가 상품이 아니에요!'}), 400
    item = daily[item_id]
    price = item.get('sale_price', item['price'])
    inv = prog._json('inventory', [])
    if item_id in inv:
        return jsonify({'error': '이미 가지고 있어요!'}), 400
    ok, msg = spend_money(prog, price, f"오늘의 특가: {item['name']}")
    if not ok:
        return jsonify({'error': msg}), 400
    inv.append(item_id)
    prog.set_json('inventory', inv)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f"{item['name']} 특가 구매 완료!"})


@bp.route('/api/features/mission-shop')
def mission_shop_api():
    from app.services.pilot_features import get_mission_shop_status
    return jsonify({'items': get_mission_shop_status(get_or_create_progress())})


@bp.route('/api/features/mission-shop/buy', methods=['POST'])
def mission_shop_buy_api():
    from app.services.pilot_features import buy_mission_shop_item
    prog = get_or_create_progress()
    ok, msg = buy_mission_shop_item(prog, (request.get_json() or {}).get('mission_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(prog)})


@bp.route('/api/features/routes')
def routes_api():
    from app.services.pilot_features import get_route_challenge_status
    return jsonify({'challenges': get_route_challenge_status(get_or_create_progress())})


@bp.route('/api/features/airline', methods=['GET', 'POST'])
def airline_api():
    from app.services.pilot_features import get_airline_info, found_airline
    prog = get_or_create_progress()
    if request.method == 'GET':
        return jsonify(get_airline_info(prog))
    data = request.get_json() or {}
    ok, msg = found_airline(prog, data.get('name'), data.get('logo', '✈️'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'airline': get_airline_info(prog)})


@bp.route('/api/features/gift/create', methods=['POST'])
def gift_create_api():
    from app.services.pilot_features import create_gift_code
    data = request.get_json() or {}
    ok, result = create_gift_code(get_or_create_progress(), data.get('item_id'), data.get('message', ''), data.get('from_name', '파일럿'))
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({'status': 'ok', **result})


@bp.route('/api/features/gift/redeem', methods=['POST'])
def gift_redeem_api():
    from app.services.pilot_features import redeem_gift_code
    ok, msg = redeem_gift_code(get_or_create_progress(), (request.get_json() or {}).get('code'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/economy/payslip')
def payslip_api():
    from app.services.pilot_features import get_payslip
    return jsonify(get_payslip(get_or_create_progress(), request.args.get('month')))