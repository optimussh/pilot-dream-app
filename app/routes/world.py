"""세계 경제 · 꿈 유지 · 운영 아카데미 API & 페이지"""
from flask import Blueprint, render_template, jsonify, request
from app.services.gamification import get_or_create_progress
from app.services.economy import get_wallet_summary
from app.services import world_economy as we

bp = Blueprint('world', __name__)


@bp.route('/world')
def world_page():
    return render_template('world.html')


@bp.route('/api/world/summary')
def summary_api():
    return jsonify(we.get_world_hub_summary(get_or_create_progress()))


@bp.route('/api/world/sky-times')
def sky_times_api():
    return jsonify(we.get_sky_times(get_or_create_progress()))


@bp.route('/api/world/events')
def events_api():
    prog = get_or_create_progress()
    mults = we.get_world_multipliers(prog)
    return jsonify({
        'events': mults.get('events'),
        'multipliers': {
            'demand': mults.get('demand_mult'),
            'longhaul': mults.get('longhaul_mult'),
            'cargo': mults.get('cargo_mult'),
            'tourism': mults.get('tourism_mult'),
            'fuel_cost': mults.get('fuel_cost_mult'),
        },
        'oil': mults.get('oil'),
    })


@bp.route('/api/world/oil')
def oil_api():
    return jsonify(we.get_oil_price(get_or_create_progress()))


@bp.route('/api/world/tourism')
def tourism_api():
    return jsonify(we.get_tourism_calendar())


@bp.route('/api/world/flight-story')
def flight_story_api():
    org = request.args.get('org')
    dest = request.args.get('dest')
    route = request.args.get('route')
    callsign = request.args.get('callsign')
    return jsonify(we.get_flight_story(org, dest, route, callsign))


@bp.route('/api/world/airport-codex')
def airport_codex_api():
    return jsonify(we.get_airport_codex(get_or_create_progress()))


@bp.route('/api/world/airport-codex/stamp', methods=['POST'])
def airport_stamp_api():
    data = request.get_json() or {}
    ok, msg = we.stamp_airport(get_or_create_progress(), data.get('airport_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'codex': we.get_airport_codex(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/trade')
def trade_list_api():
    return jsonify({'missions': we.get_trade_missions(get_or_create_progress())})


@bp.route('/api/world/trade/advance', methods=['POST'])
def trade_advance_api():
    data = request.get_json() or {}
    ok, msg, extra = we.advance_trade(
        get_or_create_progress(), data.get('mission_id'), data.get('answer')
    )
    if not ok:
        return jsonify({'error': msg, **(extra or {})}), 400
    return jsonify({
        'status': 'ok', 'message': msg, **(extra or {}),
        'missions': we.get_trade_missions(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/night-sky')
def night_sky_api():
    return jsonify({'stories': we.get_night_sky_list(get_or_create_progress())})


@bp.route('/api/world/night-sky/complete', methods=['POST'])
def night_sky_complete_api():
    data = request.get_json() or {}
    ok, msg = we.complete_night_sky(get_or_create_progress(), data.get('story_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'stories': we.get_night_sky_list(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/pricing')
def pricing_info_api():
    return jsonify(we.get_pricing_lab_info(get_or_create_progress()))


@bp.route('/api/world/pricing/run', methods=['POST'])
def pricing_run_api():
    data = request.get_json() or {}
    ok, msg, result = we.run_pricing_lab(
        get_or_create_progress(), data.get('scenario_id'), data.get('price_pct', 1.0)
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'result': result,
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/hub-missions')
def hub_missions_api():
    return jsonify({'missions': we.get_hub_missions(get_or_create_progress())})


@bp.route('/api/world/hub-missions/complete', methods=['POST'])
def hub_complete_api():
    data = request.get_json() or {}
    ok, msg = we.complete_hub_mission(
        get_or_create_progress(), data.get('mission_id'), data.get('answer')
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'missions': we.get_hub_missions(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/tradeoffs')
def tradeoffs_api():
    return jsonify(we.get_tradeoffs(get_or_create_progress()))


@bp.route('/api/world/tradeoffs/choose', methods=['POST'])
def tradeoff_choose_api():
    data = request.get_json() or {}
    ok, msg, extra = we.choose_tradeoff(
        get_or_create_progress(), data.get('tradeoff_id'), data.get('choice_id')
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, **(extra or {}),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/alliance')
def alliance_api():
    return jsonify(we.get_alliance_map(get_or_create_progress()))


@bp.route('/api/world/economy-quiz')
def economy_quiz_api():
    q = we.get_economy_quiz(get_or_create_progress())
    return jsonify(q or {'questions': []})


@bp.route('/api/world/economy-quiz/submit', methods=['POST'])
def economy_quiz_submit_api():
    data = request.get_json() or {}
    ok, msg, extra = we.submit_economy_quiz(
        get_or_create_progress(), data.get('question_id'), data.get('answer')
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, **(extra or {}),
        'quiz': we.get_economy_quiz(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/letters')
def letters_api():
    return jsonify(we.get_letter_milestones(get_or_create_progress()))


@bp.route('/api/world/letters/milestone', methods=['POST'])
def letter_milestone_api():
    data = request.get_json() or {}
    ok, msg = we.write_milestone_letter(
        get_or_create_progress(), data.get('milestone_id'), data.get('text')
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'letters': we.get_letter_milestones(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/ceo-report')
def ceo_report_api():
    return jsonify(we.build_ceo_report(get_or_create_progress()))


@bp.route('/api/world/ceo-report/claim', methods=['POST'])
def ceo_claim_api():
    ok, msg = we.claim_ceo_report(get_or_create_progress())
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'report': we.build_ceo_report(get_or_create_progress()),
        'wallet': get_wallet_summary(get_or_create_progress()),
    })


@bp.route('/api/world/parent')
def parent_api():
    return jsonify(we.get_parent_summary(get_or_create_progress()))


@bp.route('/api/world/parent/mode', methods=['POST'])
def parent_mode_api():
    data = request.get_json() or {}
    ok, msg = we.set_parent_mode(get_or_create_progress(), data.get('enabled', True))
    return jsonify({'status': 'ok', 'message': msg, 'parent': we.get_parent_summary(get_or_create_progress())})
