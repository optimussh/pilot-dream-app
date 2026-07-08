from flask import Blueprint, render_template, jsonify, request
from app.services.gamification import get_or_create_progress
from app.services.economy import get_wallet_summary
from app.services.pilot_extras import (
    get_extras_summary, claim_captain_duty, submit_daily_airport_quiz,
    add_flight_journal, get_aircraft_codex, save_schedule_slot, claim_schedule_reward,
    get_fuel_quiz, submit_fuel_quiz, claim_on_time_tier, claim_weekly_demand,
)

bp = Blueprint('extras', __name__)


@bp.route('/captain-life')
def captain_life_page():
    return render_template('captain_life.html')


@bp.route('/api/extras/summary')
def summary_api():
    return jsonify(get_extras_summary(get_or_create_progress()))


@bp.route('/api/extras/captain-duty/claim', methods=['POST'])
def captain_duty_claim():
    ok, msg = claim_captain_duty(get_or_create_progress())
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/daily-airport/quiz', methods=['POST'])
def airport_quiz_api():
    data = request.get_json() or {}
    ok, result = submit_daily_airport_quiz(get_or_create_progress(), data.get('answer'))
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({'status': 'ok', **result, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/journal', methods=['POST'])
def journal_api():
    data = request.get_json() or {}
    ok, msg = add_flight_journal(get_or_create_progress(), data.get('entry_id'), data.get('text'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/codex')
def codex_api():
    return jsonify(get_aircraft_codex(get_or_create_progress()))


@bp.route('/api/extras/schedule', methods=['POST'])
def schedule_api():
    data = request.get_json() or {}
    ok, result = save_schedule_slot(
        get_or_create_progress(), data.get('slot_id'), data.get('aircraft_id')
    )
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({'status': 'ok', 'schedule': result})


@bp.route('/api/extras/schedule/claim', methods=['POST'])
def schedule_claim_api():
    ok, msg = claim_schedule_reward(get_or_create_progress())
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/fuel-quiz')
def fuel_quiz_get():
    q, err = get_fuel_quiz(get_or_create_progress())
    if err:
        return jsonify({'error': err}), 400
    if not q:
        return jsonify({'error': '오늘 퀴즈 한도 초과'}), 400
    return jsonify({'quiz': q})


@bp.route('/api/extras/fuel-quiz/submit', methods=['POST'])
def fuel_quiz_submit():
    data = request.get_json() or {}
    ok, result = submit_fuel_quiz(get_or_create_progress(), data.get('quiz_id'), data.get('answer'))
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({'status': 'ok', **result, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/on-time/claim', methods=['POST'])
def on_time_claim_api():
    data = request.get_json() or {}
    ok, msg = claim_on_time_tier(get_or_create_progress(), int(data.get('need', 0)))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})


@bp.route('/api/extras/demand/claim', methods=['POST'])
def demand_claim_api():
    ok, msg = claim_weekly_demand(get_or_create_progress())
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'wallet': get_wallet_summary(get_or_create_progress())})