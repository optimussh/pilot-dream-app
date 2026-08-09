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
from app.services.airline_treasury import (
    build_treasury_panel,
    deposit_capital,
    deposit_loan,
    recover_capital,
    recover_loan,
    borrow_from_company,
    repay_borrow,
)
from app.services.airline_invest import (
    build_invest_panel, issue_shares, accept_npc_investor, market_trade,
    claim_weekly_dividends, answer_board, get_glossary_public, buyback_npc_shares,
    set_dividend_policy, answer_value_quiz,
)
from app.services.airline_revenue import (
    accept_cargo, complete_cargo, toggle_lease, set_mro_desk, set_fleet_maintain,
    answer_briefing, toggle_codeshare, run_training, claim_seasonal,
    fetch_revenue_dashboard,
)
from app.services.cabin_meals import (
    set_cabin_policy, set_cabin_prep, toggle_cabin_slot, set_cabin_slots,
    set_signature, answer_cabin_feedback,
)
from app.services.space_ops import (
    get_space_status, found_space_division, buy_rocket, launch_mission, claim_space_contract,
)
from app.services.space_staff import (
    hire_space_crew, fire_space_crew, assign_launch_team, assign_desk,
    assign_rocket_lead, answer_space_quiz, transfer_airline_mechanic,
    build_staff_panel,
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


@bp.route('/api/airline/treasury')
def treasury_api():
    prog = get_or_create_progress()
    panel = build_treasury_panel(prog)
    if not panel:
        return jsonify({'error': '먼저 항공사를 창업해주세요!', 'treasury': None}), 400
    return jsonify({
        'treasury': panel,
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True, run_tick=False),
    })


def _treasury_action_response(prog, ok, msg):
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok',
        'message': msg,
        'treasury': build_treasury_panel(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True, run_tick=False),
    })


@bp.route('/api/airline/treasury/capital', methods=['POST'])
def treasury_capital_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    action = (data.get('action') or 'deposit').lower()
    amount = data.get('amount')
    if action in ('deposit', 'in'):
        ok, msg = deposit_capital(prog, amount)
    elif action in ('recover', 'out', 'withdraw'):
        ok, msg = recover_capital(prog, amount if amount is not None else None)
    else:
        return jsonify({'error': 'action은 deposit / recover 중 하나예요.'}), 400
    return _treasury_action_response(prog, ok, msg)


@bp.route('/api/airline/treasury/lend', methods=['POST'])
def treasury_lend_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    action = (data.get('action') or 'deposit').lower()
    amount = data.get('amount')
    if action in ('deposit', 'in', 'lend'):
        ok, msg = deposit_loan(prog, amount)
    elif action in ('recover', 'out', 'recall'):
        ok, msg = recover_loan(prog, amount if amount is not None else None)
    else:
        return jsonify({'error': 'action은 deposit / recover 중 하나예요.'}), 400
    return _treasury_action_response(prog, ok, msg)


@bp.route('/api/airline/treasury/borrow', methods=['POST'])
def treasury_borrow_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    action = (data.get('action') or 'borrow').lower()
    amount = data.get('amount')
    if action in ('borrow', 'in'):
        ok, msg = borrow_from_company(prog, amount)
    elif action in ('repay', 'out', 'pay'):
        ok, msg = repay_borrow(prog, amount if amount is not None else None)
    else:
        return jsonify({'error': 'action은 borrow / repay 중 하나예요.'}), 400
    return _treasury_action_response(prog, ok, msg)


@bp.route('/api/airline/invest')
def invest_api():
    prog = get_or_create_progress()
    panel = build_invest_panel(prog)
    if not panel:
        return jsonify({'error': '먼저 항공사를 창업해주세요!', 'invest_panel': None}), 400
    return jsonify({'invest_panel': panel, 'wallet': get_wallet_summary(prog)})


@bp.route('/api/airline/invest/glossary')
def invest_glossary_api():
    """쉬운 단어장 라이브러리 전용 (프론트 랜덤 5개용)"""
    return jsonify(get_glossary_public())


@bp.route('/api/airline/invest/issue', methods=['POST'])
def invest_issue_api():
    prog = get_or_create_progress()
    ok, msg = issue_shares(prog)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/npc', methods=['POST'])
def invest_npc_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = accept_npc_investor(prog, data.get('npc_id'), data.get('accept', True))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/buyback', methods=['POST'])
def invest_buyback_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = buyback_npc_shares(prog, data.get('npc_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/market', methods=['POST'])
def invest_market_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = market_trade(prog, data.get('firm_id'), data.get('action'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/dividend', methods=['POST'])
def invest_dividend_api():
    prog = get_or_create_progress()
    ok, msg, amount = claim_weekly_dividends(prog)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'amount': amount,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/board', methods=['POST'])
def invest_board_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = answer_board(prog, data.get('choice_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'wallet': get_wallet_summary(prog),
    })


@bp.route('/api/airline/invest/dividend-policy', methods=['POST'])
def invest_div_policy_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_dividend_policy(prog, data.get('policy'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'invest_panel': build_invest_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/invest/value-quiz', methods=['POST'])
def invest_value_quiz_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, detail = answer_value_quiz(prog, data.get('answer') or data.get('choice_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'detail': detail,
        'invest_panel': build_invest_panel(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
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


@bp.route('/api/airline/cabin/policy', methods=['POST'])
def cabin_policy_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_cabin_policy(prog, data.get('policy'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'revenue_panel': fetch_revenue_dashboard(prog).get('revenue_panel'),
    })


@bp.route('/api/airline/cabin/prep', methods=['POST'])
def cabin_prep_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = set_cabin_prep(prog, data.get('prep'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'revenue_panel': fetch_revenue_dashboard(prog).get('revenue_panel'),
    })


@bp.route('/api/airline/cabin/slot', methods=['POST'])
def cabin_slot_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    if data.get('slots') is not None:
        ok, msg = set_cabin_slots(prog, data.get('slots'))
    else:
        ok, msg = toggle_cabin_slot(prog, data.get('meal_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'revenue_panel': fetch_revenue_dashboard(prog).get('revenue_panel'),
    })


@bp.route('/api/airline/cabin/signature', methods=['POST'])
def cabin_signature_api():
    prog = get_or_create_progress()
    ok, msg = set_signature(prog)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'dashboard': get_airline_dashboard(prog, light=True),
        'revenue_panel': fetch_revenue_dashboard(prog).get('revenue_panel'),
    })


@bp.route('/api/airline/cabin/feedback', methods=['POST'])
def cabin_feedback_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, detail = answer_cabin_feedback(prog, data.get('answer') or data.get('choice_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'detail': detail,
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
        'revenue_panel': fetch_revenue_dashboard(prog).get('revenue_panel'),
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
    """미수령 수익 받기. 이미 받았으면 200 + already_done (오류 팝업 아님)."""
    prog = get_or_create_progress()
    if not get_airline_info(prog).get('founded'):
        return jsonify({'error': '먼저 항공사를 창업해주세요!'}), 400
    result = settle_weekly_revenue(prog, force=True)
    if not result:
        return jsonify({
            'status': 'already_done',
            'already_done': True,
            'ok': True,
            'income': 0,
            'gross': 0,
            'payroll': 0,
            'net': 0,
            'message': '지금은 받을 미수령 수익이 없어요. 내일 다시 확인해 주세요!',
            'wallet': get_wallet_summary(prog),
        })
    payload = {
        'ok': True,
        'status': result.get('status') or ('already_done' if result.get('already_done') else 'ok'),
        'already_done': bool(result.get('already_done')),
        'wallet': get_wallet_summary(prog),
        **result,
    }
    return jsonify(payload)


@bp.route('/api/airline/radar-flights')
def radar_flights_api():
    return jsonify(get_flights_for_radar(get_or_create_progress()))


@bp.route('/api/airline/space')
def space_status_api():
    return jsonify(get_space_status(get_or_create_progress()))


@bp.route('/api/airline/space/found', methods=['POST'])
def space_found_api():
    prog = get_or_create_progress()
    ok, msg = found_space_division(prog)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/buy-rocket', methods=['POST'])
def space_buy_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = buy_rocket(prog, data.get('rocket_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/launch', methods=['POST'])
def space_launch_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = launch_mission(
        prog, data.get('mission_id'),
        use_insurance=bool(data.get('use_insurance')),
        use_eco=bool(data.get('use_eco')),
    )
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/contract/claim', methods=['POST'])
def space_contract_claim_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = claim_space_contract(prog, data.get('contract_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/staff')
def space_staff_api():
    prog = get_or_create_progress()
    return jsonify({
        'staff': build_staff_panel(prog) if get_space_status(prog).get('founded') else None,
        'space': get_space_status(prog),
    })


@bp.route('/api/airline/space/hire', methods=['POST'])
def space_hire_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = hire_space_crew(prog, data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/fire', methods=['POST'])
def space_fire_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = fire_space_crew(prog, data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


@bp.route('/api/airline/space/team', methods=['POST'])
def space_team_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = assign_launch_team(prog, data.get('team') or data)
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
    })


@bp.route('/api/airline/space/desk', methods=['POST'])
def space_desk_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = assign_desk(prog, data.get('desk_id'), data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
    })


@bp.route('/api/airline/space/rocket-lead', methods=['POST'])
def space_rocket_lead_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = assign_rocket_lead(prog, data.get('rocket_id'), data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
    })


@bp.route('/api/airline/space/quiz', methods=['POST'])
def space_quiz_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg, detail = answer_space_quiz(prog, data.get('quiz_id'), data.get('answer'))
    if not ok:
        return jsonify({'error': msg, 'detail': detail}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'detail': detail,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
    })


@bp.route('/api/airline/space/transfer', methods=['POST'])
def space_transfer_api():
    data = request.get_json() or {}
    prog = get_or_create_progress()
    ok, msg = transfer_airline_mechanic(prog, data.get('crew_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg,
        'space': get_space_status(prog),
        'staff': build_staff_panel(prog),
        'wallet': get_wallet_summary(prog),
        'dashboard': get_airline_dashboard(prog, light=True),
    })


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