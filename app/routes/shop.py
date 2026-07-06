from flask import Blueprint, render_template, jsonify, request
from app.models import db
from app.services.gamification import get_or_create_progress, load_json
from app.services.economy import (
    get_wallet_summary, get_shop_catalog, get_all_aircraft_status,
    buy_item, sell_item, equip_avatar, buy_aircraft, accelerate_unlock,
    set_active_aircraft, equip_aircraft_deco, get_aircraft_catalog,
    format_krw, SELL_RATIO, get_effective_hours,
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
    return jsonify({
        'status': 'ok',
        'message': msg,
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