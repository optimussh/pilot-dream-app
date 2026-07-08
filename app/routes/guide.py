from flask import Blueprint, render_template, jsonify, request
from app.services.gamification import get_or_create_progress
from app.services.guide_service import (
    get_guide_sections, get_onboarding_state,
    complete_onboarding_step, dismiss_onboarding,
)
from app.services.player_stats import get_player_stats

bp = Blueprint('guide', __name__)


@bp.route('/guide')
def guide_page():
    try:
        from app.services.guide_service import complete_onboarding_step
        complete_onboarding_step(get_or_create_progress(), 'welcome')
    except Exception:
        pass
    return render_template('guide.html')


@bp.route('/api/guide/sections')
def sections_api():
    return jsonify({'sections': get_guide_sections()})


@bp.route('/api/guide/onboarding')
def onboarding_api():
    prog = get_or_create_progress()
    return jsonify({
        'onboarding': get_onboarding_state(prog),
        'stats': get_player_stats(prog),
    })


@bp.route('/api/guide/onboarding/complete', methods=['POST'])
def onboarding_complete_api():
    data = request.get_json() or {}
    ok, msg = complete_onboarding_step(get_or_create_progress(), data.get('step_id'))
    if not ok:
        return jsonify({'error': msg}), 400
    prog = get_or_create_progress()
    return jsonify({
        'status': 'ok',
        'message': msg,
        'onboarding': get_onboarding_state(prog),
    })


@bp.route('/api/guide/onboarding/dismiss', methods=['POST'])
def onboarding_dismiss_api():
    ok, msg = dismiss_onboarding(get_or_create_progress())
    return jsonify({'status': 'ok', 'message': msg})