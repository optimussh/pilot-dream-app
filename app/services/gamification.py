"""게이미피케이션 핵심 로직: 미션, 화폐, 스트릭, 편지, 성장 리포트"""
import json
import os
import hashlib
from datetime import datetime, timedelta
from app.models import db, UserProgress, FutureLetter, UserBadge, LogbookEntry

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# data/*.json 디스크 읽기 캐시 (mtime 바뀌면 자동 갱신)
_json_cache = {}  # filename -> (mtime, data)
_json_by_id_cache = {}  # filename -> (mtime, {id: row})


def load_json(filename):
    """JSON 로드. 동일 파일이면 메모리 캐시 — 대시보드 렉 완화."""
    path = os.path.join(DATA_DIR, filename)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    hit = _json_cache.get(filename)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = []
    _json_cache[filename] = (mtime, data)
    return data


def load_json_by_id(filename, id_key='id'):
    """id → 행 dict 캐시 (crew_cards 등 반복 조회용)."""
    path = os.path.join(DATA_DIR, filename)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    hit = _json_by_id_cache.get(filename)
    if hit and hit[0] == mtime:
        return hit[1]
    rows = load_json(filename)
    if not isinstance(rows, list):
        by_id = {}
    else:
        by_id = {r[id_key]: r for r in rows if isinstance(r, dict) and id_key in r}
    _json_by_id_cache[filename] = (mtime, by_id)
    return by_id


def clear_json_cache():
    _json_cache.clear()
    _json_by_id_cache.clear()


def today_str():
    return datetime.now().strftime('%Y-%m-%d')


def week_key():
    return datetime.now().strftime('%Y-W%W')


def get_or_create_progress():
    prog = UserProgress.query.first()
    if not prog:
        prog = UserProgress()
        db.session.add(prog)
        db.session.commit()
    return prog


def update_daily_streak(prog):
    today = today_str()
    if prog.last_active_date == today:
        return
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if prog.last_active_date == yesterday:
        prog.streak_days = (prog.streak_days or 0) + 1
    elif prog.last_active_date != today:
        prog.streak_days = 1
    prog.last_active_date = today
    db.session.commit()


def log_activity(prog, activity_type, detail=''):
    log = prog._json('activity_log', [])
    log.append({
        'date': today_str(),
        'time': datetime.now().isoformat(),
        'type': activity_type,
        'detail': detail
    })
    if len(log) > 500:
        log = log[-500:]
    prog.set_json('activity_log', log)
    update_daily_streak(prog)
    db.session.commit()


def award_virtual_hours(prog, hours, reason):
    prog.virtual_hours = round((prog.virtual_hours or 0) + hours, 2)
    log_activity(prog, 'reward', f'+{hours}h: {reason}')
    check_letter_unlock(prog)
    try_unlock_badges(prog)
    db.session.commit()
    return prog.virtual_hours


def try_unlock_badges(prog):
    from app.routes.badges import get_all_badges
    unlocked = {b.badge_id for b in UserBadge.query.all()}
    entries = LogbookEntry.query.all()
    total_hours = sum(e.hours for e in entries) + (prog.virtual_hours or 0)
    flight_count = len(entries)
    missions = prog._json('completed_missions', {})
    all_mission_days = sum(1 for d, ids in missions.items() if len(ids) >= 3)
    quiz_hist = prog._json('quiz_history', [])
    scenarios = prog._json('scenario_progress', {})

    checks = {
        'first_flight_done': prog.first_flight_done,
        'quiz_passed': any(q.get('score', 0) >= 80 for q in quiz_hist),
        'scenario_done': any(s.get('completed') for s in scenarios.values()),
        'mission_streak_7': prog.daily_mission_streak >= 7,
        'weekly_done': len(prog._json('completed_weekly', {}).get(week_key(), [])) >= 2,
        'flashcard_20': len(prog._json('flashcards_learned', [])) >= 20,
    }

    for badge in get_all_badges():
        if badge['id'] in unlocked:
            continue
        req = badge.get('requirement', {})
        if req.get('type') != 'special':
            continue
        sid = req.get('id')
        if sid == 'first_flight_complete' and checks['first_flight_done']:
            _unlock(badge['id'])
        elif sid == 'quiz_captain' and checks['quiz_passed']:
            _unlock(badge['id'])
        elif sid == 'scenario_hero' and checks['scenario_done']:
            _unlock(badge['id'])
        elif sid == 'mission_streak_7' and checks['mission_streak_7']:
            _unlock(badge['id'])
        elif sid == 'weekly_champion' and checks['weekly_done']:
            _unlock(badge['id'])
        elif sid == 'word_pilot' and checks['flashcard_20']:
            _unlock(badge['id'])


def _unlock(badge_id):
    if UserBadge.query.filter_by(badge_id=badge_id).first():
        return
    db.session.add(UserBadge(badge_id=badge_id))


def _seeded_pick(pool, seed, count):
    if not pool:
        return []
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    indices = []
    n = len(pool)
    for i in range(count):
        indices.append((h + i * 7) % n)
    seen = set()
    result = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            result.append(pool[idx])
    i = 0
    while len(result) < count and i < n:
        if i not in seen:
            result.append(pool[i])
        i += 1
    return result[:count]


def get_daily_missions(prog):
    pool = load_json('missions.json')
    today = today_str()
    missions = _seeded_pick(pool, f'daily-{today}', 3)
    completed = prog._json('completed_missions', {}).get(today, [])
    for m in missions:
        m['completed'] = m['id'] in completed
    return missions


def complete_mission(prog, mission_id):
    from app.services.economy import award_money, LEARNING_REWARDS
    pool = {m['id']: m for m in load_json('missions.json')}
    if mission_id not in pool:
        return None, '미션을 찾을 수 없습니다.', 0
    today = today_str()
    missions = prog._json('completed_missions', {})
    day_list = missions.get(today, [])
    if mission_id in day_list:
        return prog.virtual_hours, '이미 완료한 미션입니다.', 0
    daily = get_daily_missions(prog)
    if mission_id not in [m['id'] for m in daily]:
        return None, '오늘의 미션이 아닙니다.', 0
    day_list.append(mission_id)
    missions[today] = day_list
    prog.set_json('completed_missions', missions)
    reward = pool[mission_id].get('reward_hours', 0.5)
    award_virtual_hours(prog, reward, f"미션: {pool[mission_id]['title']}")
    money = award_money(prog, LEARNING_REWARDS['mission'], f"미션: {pool[mission_id]['title']}")
    if len(day_list) >= 3:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if prog.last_all_missions_date == yesterday:
            prog.daily_mission_streak = (prog.daily_mission_streak or 0) + 1
        elif prog.last_all_missions_date != today:
            prog.daily_mission_streak = 1
        prog.last_all_missions_date = today
        award_virtual_hours(prog, 1.0, '오늘의 미션 전부 완료 보너스')
        money += award_money(prog, LEARNING_REWARDS['mission_all_bonus'], '오늘의 미션 전부 완료 보너스')
    db.session.commit()
    return prog.virtual_hours, '미션 완료!', money


def auto_claim_daily_mission(prog, mission_id):
    """학습 완료 시 오늘의 해당 미션 보상을 자동 수령."""
    today = today_str()
    completed = prog._json('completed_missions', {}).get(today, [])
    if mission_id in completed:
        return 0
    daily = get_daily_missions(prog)
    if mission_id not in [m['id'] for m in daily]:
        return 0
    hours, msg, money = complete_mission(prog, mission_id)
    if hours is None:
        return 0
    return money


def get_weekly_challenges(prog):
    pool = load_json('weekly_challenges.json')
    wk = week_key()
    challenges = _seeded_pick(pool, f'weekly-{wk}', 2)
    completed = prog._json('completed_weekly', {}).get(wk, [])
    for c in challenges:
        c['completed'] = c['id'] in completed
    return challenges


def complete_weekly(prog, challenge_id):
    from app.services.economy import award_money, LEARNING_REWARDS
    pool = {c['id']: c for c in load_json('weekly_challenges.json')}
    if challenge_id not in pool:
        return None, '챌린지를 찾을 수 없습니다.', 0
    wk = week_key()
    weekly = prog._json('completed_weekly', {})
    wk_list = weekly.get(wk, [])
    if challenge_id in wk_list:
        return prog.virtual_hours, '이미 완료했습니다.', 0
    active = [c['id'] for c in get_weekly_challenges(prog)]
    if challenge_id not in active:
        return None, '이번 주 챌린지가 아닙니다.', 0
    wk_list.append(challenge_id)
    weekly[wk] = wk_list
    prog.set_json('completed_weekly', weekly)
    reward = pool[challenge_id].get('reward_hours', 2.0)
    award_virtual_hours(prog, reward, f"주간 챌린지: {pool[challenge_id]['title']}")
    money = award_money(prog, LEARNING_REWARDS['weekly'], f"주간: {pool[challenge_id]['title']}")
    db.session.commit()
    return prog.virtual_hours, '챌린지 완료!', money


def get_career_tree(prog):
    tree = load_json('career_tree.json')
    entries = LogbookEntry.query.all()
    logbook_hours = sum(e.hours for e in entries)
    total = logbook_hours + (prog.virtual_hours or 0)
    badge_count = UserBadge.query.count()
    result = []
    for stage in tree:
        req = stage.get('requirement', {})
        met = True
        if req.get('hours') and total < req['hours']:
            met = False
        if req.get('badges') and badge_count < req['badges']:
            met = False
        if req.get('first_flight') and not prog.first_flight_done:
            met = False
        if req.get('quiz') and not any(
            q.get('score', 0) >= 70 for q in prog._json('quiz_history', [])
        ):
            met = False
        result.append({**stage, 'unlocked': met, 'current_hours': round(total, 1)})
    return result


def get_growth_report(prog, days=30):
    log = prog._json('activity_log', [])
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    recent = [a for a in log if a.get('date', '') >= cutoff]
    entries = LogbookEntry.query.filter(LogbookEntry.date >= cutoff).all()
    by_type = {}
    for a in recent:
        t = a.get('type', 'other')
        by_type[t] = by_type.get(t, 0) + 1
    return {
        'period_days': days,
        'activities': len(recent),
        'logbook_flights': len(entries),
        'logbook_hours': round(sum(e.hours for e in entries), 1),
        'virtual_hours_earned': prog.virtual_hours or 0,
        'by_type': by_type,
        'streak_days': prog.streak_days or 0,
        'badges': UserBadge.query.count(),
        'highlights': _build_highlights(recent, entries, prog)
    }


def _build_highlights(activities, entries, prog):
    highlights = []
    if entries:
        highlights.append(f'비행 기록 {len(entries)}회를 남겼어요.')
    mission_count = sum(
        1 for a in activities if a.get('type') == 'reward' and '미션' in a.get('detail', '')
    )
    if mission_count:
        highlights.append(f'오늘의 미션 보상을 {mission_count}번 받았어요.')
    if prog.first_flight_done:
        highlights.append('첫 비행 튜토리얼을 완료했어요!')
    if not highlights:
        highlights.append('이번 기간 학습을 시작해볼까요? 미션부터 도전해보세요!')
    return highlights


def check_letter_unlock(prog):
    letter = FutureLetter.query.first()
    if not letter or letter.is_opened:
        return False
    entries = LogbookEntry.query.all()
    total = sum(e.hours for e in entries) + (prog.virtual_hours or 0)
    badges = UserBadge.query.count()
    should_open = (
        total >= 10 or badges >= 3 or prog.first_flight_done
        or (prog.daily_mission_streak or 0) >= 3
    )
    if should_open and not letter.is_opened:
        letter.is_opened = True
        letter.opened_at = datetime.utcnow()
        db.session.commit()
        return True
    return False


def get_total_hours(prog):
    entries = LogbookEntry.query.all()
    return round(sum(e.hours for e in entries) + (prog.virtual_hours or 0), 1)


def get_daily_learning(prog):
    dl = prog._json('daily_learning', {})
    today = today_str()
    if dl.get('date') != today:
        return {'date': today}
    return dl


def save_daily_learning(prog, data):
    data['date'] = today_str()
    prog.set_json('daily_learning', data)
    return data


def quiz_public(q):
    """클라이언트에 정답 인덱스 노출 방지"""
    return {k: v for k, v in q.items() if k != 'answer'}


def get_unlocked_content(prog):
    try:
        from app.services.economy import get_unlocked_aircraft_names
        return get_unlocked_aircraft_names(prog)
    except Exception:
        base = ['Boeing 737-800', 'Airbus A320-200']
        return base