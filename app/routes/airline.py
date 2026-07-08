from flask import Blueprint, render_template, jsonify, request
from app.services.gamification import get_or_create_progress
from app.services.economy import get_wallet_summary
from app.services.pilot_features import found_airline, get_airline_info
from app.services.airline_ops import (
    get_airline_dashboard, set_hub, set_mode, deploy_aircraft,
    create_route, assign_route_staff, delete_route, hire_crew,
    settle_weekly_revenue, get_flights_for_radar,
)
from app.services.space_ops import (
    get_space_status, found_space_division, buy_rocket, launch_mission,
)
from app.services.player_stats import get_player_stats, allocate_stat_point

bp = Blueprint('airline', __name__)


@bp.route('/airline')
def airline_page():
    return render_template('airline.html')


@bp.route('/api/airline/dashboard')
def dashboard_api():
    return jsonify(get_airline_dashboard(get_or_create_progress()))


@bp.route('/api/airline/found', methods=['POST'])
def found_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = found_airline(prog, data.get('name'), data.get('logo', '✈️'))
    if not ok:
        return jsonify({'error': msg}), 400
    try:
        from app.services.guide_service import auto_complete_on_activity
        auto_complete_on_activity(prog, 'airline_found')
    except Exception:
        pass
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog)})


@bp.route('/api/airline/hub', methods=['POST'])
def hub_api():
    data = request.get_json() or {}
    ok, msg = set_hub(get_or_create_progress(), data.get('hub_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/mode', methods=['POST'])
def mode_api():
    data = request.get_json() or {}
    ok, msg = set_mode(get_or_create_progress(), data.get('mode'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/deploy', methods=['POST'])
def deploy_api():
    data = request.get_json() or {}
    ok, msg = deploy_aircraft(
        get_or_create_progress(), data.get('aircraft_id'), data.get('hub_id')
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/route', methods=['POST'])
def route_create_api():
    data = request.get_json() or {}
    ok, msg = create_route(
        get_or_create_progress(),
        data.get('template_id'),
        data.get('aircraft_id'),
        data.get('flights_per_week', 7),
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/route/<route_id>', methods=['DELETE'])
def route_delete_api(route_id):
    ok, msg = delete_route(get_or_create_progress(), route_id)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/route/staff', methods=['POST'])
def route_staff_api():
    data = request.get_json() or {}
    ok, msg = assign_route_staff(
        get_or_create_progress(), data.get('route_id'), data.get('staff', {})
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/hire', methods=['POST'])
def hire_api():
    data = request.get_json() or {}
    ok, msg = hire_crew(get_or_create_progress(), data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/settle', methods=['POST'])
def settle_api():
    prog = get_or_create_progress()
    result = settle_weekly_revenue(prog, force=True)
    if not result:
        return jsonify({'error': '정산할 노선이 없어요.'}), 400
    return jsonify({'status': 'ok', **result, 'wallet': get_wallet_summary(prog)})


@bp.route('/api/airline/radar-flights')
def radar_flights_api():
    return jsonify(get_flights_for_radar(get_or_create_progress()))


@bp.route('/api/airline/space/found', methods=['POST'])
def space_found_api():
    ok, msg = found_space_division(get_or_create_progress())
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/space/buy-rocket', methods=['POST'])
def space_buy_api():
    data = request.get_json() or {}
    ok, msg = buy_rocket(get_or_create_progress(), data.get('rocket_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/airline/space/launch', methods=['POST'])
def space_launch_api():
    data = request.get_json() or {}
    ok, msg = launch_mission(get_or_create_progress(), data.get('mission_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/player/stats')
def stats_api():
    return jsonify(get_player_stats(get_or_create_progress()))


@bp.route('/api/player/stats/allocate', methods=['POST'])
def stats_allocate_api():
    data = request.get_json() or {}
    ok, msg = allocate_stat_point(get_or_create_progress(), data.get('stat_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'stats': get_player_stats(get_or_create_progress())})