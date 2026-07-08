"""가이드·온보딩"""
from app.models import db
from app.services.gamification import load_json

ONBOARDING_STEPS = [
    {'id': 'welcome', 'title': '환영해요!', 'emoji': '👋', 'action': '/guide', 'kid_text': '가이드를 잠깐 읽어볼까요?'},
    {'id': 'first_learn', 'title': '첫 공부', 'emoji': '📚', 'action': '/learn', 'kid_text': '퀴즈 1번만 풀어보세요!'},
    {'id': 'first_flight', 'title': '첫 비행 기록', 'emoji': '📖', 'action': '/logbook', 'kid_text': '로그북에 비행을 적어보세요!'},
    {'id': 'captain_life', 'title': '기장 생활', 'emoji': '👑', 'action': '/captain-life', 'kid_text': '출근 미션을 확인해요!'},
    {'id': 'hangar', 'title': '비행기 창고', 'emoji': '✈️', 'action': '/hangar', 'kid_text': '내 비행기를 클릭해서 꾸며보세요!'},
    {'id': 'airline', 'title': '항공사 (CEO)', 'emoji': '🏢', 'action': '/airline', 'kid_text': '비행기 10대면 항공사를 만들 수 있어요!'},
    {'id': 'stats', 'title': '내 능력', 'emoji': '📊', 'action': '/guide#stats', 'kid_text': '6가지 능력이 자라고 있어요!'},
]


def _onboard(prog):
    pm = prog._json('pilot_meta', {})
    ob = pm.setdefault('onboarding', {
        'completed': [], 'dismissed': False, 'started_at': '',
    })
    ob.setdefault('completed', [])
    return ob


def get_guide_sections():
    return load_json('guide_sections.json') or []


def get_onboarding_state(prog):
    ob = _onboard(prog)
    completed = set(ob.get('completed', []))
    steps = []
    for i, s in enumerate(ONBOARDING_STEPS):
        steps.append({
            **s,
            'done': s['id'] in completed,
            'current': s['id'] not in completed and all(
                ONBOARDING_STEPS[j]['id'] in completed for j in range(i)
            ),
        })
    total = len(ONBOARDING_STEPS)
    done_count = sum(1 for s in steps if s['done'])
    return {
        'steps': steps,
        'completed_count': done_count,
        'total': total,
        'pct': int(done_count / total * 100) if total else 0,
        'dismissed': ob.get('dismissed', False),
        'all_done': done_count >= total,
        'show_banner': not ob.get('dismissed') and done_count < total,
    }


def complete_onboarding_step(prog, step_id):
    valid = {s['id'] for s in ONBOARDING_STEPS}
    if step_id not in valid:
        return False, '단계를 찾을 수 없어요.'
    pm = prog._json('pilot_meta', {})
    ob = _onboard(prog)
    completed = list(ob.get('completed', []))
    if step_id not in completed:
        completed.append(step_id)
    ob['completed'] = completed
    pm['onboarding'] = ob
    prog.set_json('pilot_meta', pm)
    db.session.commit()
    try:
        from app.services.player_stats import apply_activity_stats
        apply_activity_stats(prog, 'season')  # small imagination bump on milestones
    except Exception:
        pass
    return True, '잘했어요! 다음 단계로 가볼까요?'


def dismiss_onboarding(prog):
    pm = prog._json('pilot_meta', {})
    ob = _onboard(prog)
    ob['dismissed'] = True
    pm['onboarding'] = ob
    prog.set_json('pilot_meta', pm)
    db.session.commit()
    return True, '알겠어요! 가이드 메뉴에서 언제든 볼 수 있어요.'


def auto_complete_on_activity(prog, activity_key):
    """활동 시 온보딩 자동 체크"""
    mapping = {
        'learn_quiz': 'first_learn',
        'logbook': 'first_flight',
        'captain_life': 'captain_life',
        'hangar': 'hangar',
        'airline_found': 'airline',
    }
    step = mapping.get(activity_key)
    if step:
        complete_onboarding_step(prog, step)