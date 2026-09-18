from flask import Blueprint, jsonify, request
from app.services.gamification import get_or_create_progress, save_progress
from app.services.economy import get_wallet_summary
from app.services.today_flight import get_today_duty, complete_step, skip_step, rank_more_items

bp = Blueprint('duty', __name__)


@bp.route('/api/duty/today')
def duty_today_api():
    return jsonify(get_today_duty(get_or_create_progress()))


@bp.route('/api/duty/complete', methods=['POST'])
def duty_complete_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, duty = complete_step(prog, data.get('step_id'), data)
    if not ok:
        return jsonify({'error': msg, 'duty': duty}), 400
    save_progress(prog)
    return jsonify({'status': 'ok', 'message': msg, 'duty': duty, 'wallet': get_wallet_summary(prog)})


@bp.route('/api/duty/skip', methods=['POST'])
def duty_skip_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, duty = skip_step(prog, data.get('step_id'))
    if not ok:
        return jsonify({'error': msg, 'duty': duty}), 400
    save_progress(prog)
    return jsonify({'status': 'ok', 'message': msg, 'duty': duty})


@bp.route('/api/nav/more')
def nav_more_api():
    return jsonify({'items': rank_more_items(get_or_create_progress())})
