from flask import Blueprint, render_template, jsonify, request, Response
from app.services.gamification import get_or_create_progress
from app.services.economy import get_wallet_summary
from app.services.game_bridge import (
    get_catalog, get_game, enrich_game, start_session, complete_session,
    build_launcher_bat, build_launcher_mac, AIRCRAFT_FG_MAP,
)

bp = Blueprint('games', __name__)


@bp.route('/games')
def games_hub():
    return render_template('games/hub.html')


@bp.route('/games/<game_id>')
def game_detail(game_id):
    prog = get_or_create_progress()
    game = enrich_game(prog, get_game(game_id))
    if not game:
        return render_template('games/hub.html'), 404
    if game.get('type') == 'iframe':
        return render_template('games/play.html', game=game)
    return render_template('games/detail.html', game=game)


@bp.route('/games/play/<game_id>')
def game_play(game_id):
    game = get_game(game_id)
    if not game or game.get('type') != 'iframe':
        return render_template('games/hub.html'), 404
    return render_template('games/play.html', game=game)


@bp.route('/api/games/catalog')
def catalog_api():
    prog = get_or_create_progress()
    return jsonify({'games': get_catalog(prog)})


@bp.route('/api/games/<game_id>')
def game_api(game_id):
    prog = get_or_create_progress()
    game = enrich_game(prog, get_game(game_id))
    if not game:
        return jsonify({'error': '게임을 찾을 수 없어요.'}), 404
    return jsonify(game)


@bp.route('/api/games/session/start', methods=['POST'])
def session_start_api():
    data = request.get_json() or {}
    game_id = data.get('game_id')
    if not game_id:
        return jsonify({'error': 'game_id 필요'}), 400
    ok, result = start_session(get_or_create_progress(), game_id)
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({'status': 'ok', **result})


@bp.route('/api/games/session/complete', methods=['POST'])
def session_complete_api():
    data = request.get_json() or {}
    game_id = data.get('game_id')
    if not game_id:
        return jsonify({'error': 'game_id 필요'}), 400
    prog = get_or_create_progress()
    ok, result = complete_session(prog, game_id)
    if not ok:
        return jsonify({'error': result}), 400
    return jsonify({
        'status': 'ok',
        **result,
        'wallet': get_wallet_summary(prog),
    })


def _launcher_params():
    prog = get_or_create_progress()
    game = get_game('flightgear') or {}
    launcher = game.get('launcher', {})
    aircraft = request.args.get('aircraft')
    if not aircraft:
        active = prog.active_aircraft or 'b737'
        aircraft = AIRCRAFT_FG_MAP.get(active, launcher.get('aircraft', 'c172p'))
    airport = request.args.get('airport', launcher.get('airport', 'RKSI'))
    return aircraft, airport


@bp.route('/api/games/flightgear/launcher.bat')
def launcher_bat():
    aircraft, airport = _launcher_params()
    content = build_launcher_bat(aircraft, airport)
    return Response(
        content,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=PilotDream_FlightGear_시작.bat'},
    )


@bp.route('/api/games/flightgear/launcher.command')
def launcher_mac():
    aircraft, airport = _launcher_params()
    content = build_launcher_mac(aircraft, airport)
    return Response(
        content,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=PilotDream_FlightGear_시작.command'},
    )