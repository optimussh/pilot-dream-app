from flask import Blueprint, render_template, jsonify, request
from app.services.gamification import get_or_create_progress, load_json
from app.services.economy import get_wallet_summary
from app.services.pilot_features import found_airline, get_airline_info
from app.services.airline_ops import (
    get_airline_dashboard, set_hub, set_mode, deploy_aircraft,
    create_route, assign_route_staff, delete_route, hire_crew, fire_crew,
    settle_weekly_revenue, get_flights_for_radar, set_ancillary,
    get_hireable_crew, tick_airline_economy, get_crew_pool_meta,
)
from app.services.airline_company import allocate_weekly_profit, withdraw_company_vault
from app.services.airline_revenue import (
    accept_cargo, complete_cargo, toggle_lease, set_mro_desk, set_fleet_maintain,
    answer_briefing, toggle_codeshare, run_training, claim_seasonal,
    fetch_revenue_dashboard,
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
    light = request.args.get('light') in ('1', 'true', 'yes')
    # tick=1 일 때만 일일 수익 정산 (기본 대시보드는 가볍게)
    run_tick = request.args.get('tick') in ('1', 'true', 'yes')
    return jsonify(get_airline_dashboard(
        get_or_create_progress(), light=light, run_tick=run_tick,
    ))


@bp.route('/api/airline/tick', methods=['POST'])
def tick_api():
    """일일 운영 수익 정산 — 대시보드와 분리해 클릭 체감 개선"""
    prog = get_or_create_progress()
    result = tick_airline_economy(prog)
    return jsonify({
        'status': 'ok',
        'tick': result,
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True, run_tick=False),
    })


@bp.route('/api/airline/route-templates')
def route_templates_api():
    """노선 템플릿 지연 로드 (노선 탭 열 때)"""
    templates = load_json('airline_route_templates.json')
    return jsonify({
        'templates': templates if isinstance(templates, list) else [],
        'count': len(templates) if isinstance(templates, list) else 0,
    })


@bp.route('/api/airline/crew')
def crew_list_api():
    """채용 풀 전체 (채용 탭 열 때). slim 프로필로 잠긴 카드 포함."""
    prog = get_or_create_progress()
    crew = get_hireable_crew(prog, slim=True, only_active=False)
    return jsonify({
        'hireable_crew': crew,
        'crew_meta': get_crew_pool_meta(prog),
        'crew_full': True,
    })


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
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


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


@bp.route('/api/airline/ancillary', methods=['POST'])
def ancillary_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_ancillary(prog, data.get('tier', 'basic'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/company/allocate', methods=['POST'])
def company_allocate_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = allocate_weekly_profit(prog, data.get('choice'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/company/vault/withdraw', methods=['POST'])
def company_vault_withdraw_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    amount = data.get('amount')
    ok, msg = withdraw_company_vault(prog, amount if amount is not None else None)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/revenue')
def revenue_api():
    prog = get_or_create_progress()
    try:
        return jsonify(fetch_revenue_dashboard(prog))
    except Exception as e:
        return jsonify({'error': f'?�입??로드 ?�패: {e}', 'founded': get_airline_info(prog).get('founded')}), 500


@bp.route('/api/airline/revenue/cargo/accept', methods=['POST'])
def cargo_accept_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = accept_cargo(prog, data.get('offer_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/revenue/cargo/complete', methods=['POST'])
def cargo_complete_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, pay = complete_cargo(prog, data.get('offer_id'), data.get('answer'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'pay': pay,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/revenue/lease', methods=['POST'])
def lease_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = toggle_lease(prog, data.get('aircraft_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/revenue/mro', methods=['POST'])
def mro_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_mro_desk(prog, data.get('enabled', True))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/revenue/maintain', methods=['POST'])
def maintain_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_fleet_maintain(prog, data.get('enabled', True))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/revenue/briefing', methods=['POST'])
def briefing_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, fee = answer_briefing(prog, data.get('idx'), data.get('answer'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'fee': fee,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/revenue/codeshare', methods=['POST'])
def codeshare_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = toggle_codeshare(prog, data.get('partner_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/revenue/training', methods=['POST'])
def training_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, fee = run_training(prog, data.get('module_id'), data.get('answer'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'fee': fee,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/revenue/seasonal', methods=['POST'])
def seasonal_api():
    prog = get_or_create_progress()
    ok, msg, bonus = claim_seasonal(prog)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'bonus': bonus,
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


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
    prog = get_or_create_progress()
    ok, msg = assign_route_staff(prog, data.get('route_id'), data.get('staff', {}))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/route/staff/auto-assign', methods=['POST'])
def route_staff_auto_api():
    """모든 ?�성 ?�선??채용 직원???�덤·균등 배치"""
    from app.services.airline_ops import auto_assign_all_routes
    data = request.get_json() or {}
    prog = get_or_create_progress()
    max_per = data.get('max_per_crew')
    try:
        max_per = int(max_per) if max_per is not None else None
    except (TypeError, ValueError):
        max_per = None
    ok, msg, extra = auto_assign_all_routes(prog, max_per_crew=max_per)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok',
        'message': msg,
        'result': extra or {},
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/hire', methods=['POST'])
def hire_api():
    data = request.get_json() or {}
    ok, msg = hire_crew(get_or_create_progress(), data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    prog = get_or_create_progress()
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/fire', methods=['POST'])
def fire_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = fire_crew(prog, data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({'status': 'ok', 'message': msg, 'dashboard': get_airline_dashboard(prog, light=True)})


@bp.route('/api/airline/settle', methods=['POST'])
def settle_api():
    prog = get_or_create_progress()
    result = settle_weekly_revenue(prog, force=True)
    if not result:
        from app.services.pilot_features import get_airline_info
        if not get_airline_info(prog).get('founded'):
            return jsonify({'error': '먼�? ??��?��? 창업?�주?�요!'}), 400
        return jsonify({'error': '?�늘?� ?��? ?�영 ?�익??받았?�요. ?�일 ?�시 ?�인?�주?�요!'}), 400
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
    stats = get_player_stats(get_or_create_progress())
    payload = {'status': 'ok', 'stats': stats}
    if msg:
        payload['message'] = msg
    return jsonify(payload)