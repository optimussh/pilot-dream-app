from flask import Blueprint, render_template, jsonify, request
from app.models import db, UserProgress, FutureLetter, LogbookEntry
from app.services.gamification import (
    load_json, get_or_create_progress, get_daily_missions, complete_mission,
    get_weekly_challenges, complete_weekly, get_career_tree, get_growth_report,
    check_letter_unlock, award_virtual_hours, log_activity, get_total_hours,
    get_unlocked_content, try_unlock_badges, today_str, week_key,
    get_daily_learning, save_daily_learning, quiz_public
)
from app.services.economy import get_wallet_summary, salary_progress
from app.services.content_bank import (
    get_quiz_bank, get_flashcard_bank, get_scenario_bank,
    daily_sample, lookup_by_ids
)

QUIZ_PER_ROUND = 5
FLASHCARD_DAILY = 5
SCENARIO_DAILY = 4
from datetime import datetime

bp = Blueprint('learn', __name__)

ACTIVITY_MAP = {
    'm_logbook': 'logbook', 'm_atc': 'atc', 'm_radar': 'radar',
    'm_planner': 'planner', 'm_quiz': 'quiz', 'm_flashcard': 'flashcard',
    'm_aircraft': 'aircraft', 'm_scenario': 'scenario', 'm_career': 'career',
    'm_captain_day': 'captain_day',
}


@bp.route('/learn')
def learn_hub():
    return render_template('learn.html')


@bp.route('/quiz')
def quiz_page():
    return render_template('quiz.html')


@bp.route('/flashcards')
def flashcards_page():
    return render_template('flashcards.html')


@bp.route('/scenarios')
def scenarios_page():
    return render_template('scenarios.html')


@bp.route('/captain-day')
def captain_day_page():
    return render_template('captain_day.html')


@bp.route('/first-flight')
def first_flight_page():
    return render_template('first_flight.html')


# ==================== API ====================

@bp.route('/api/gamification/status')
def gamification_status():
    prog = get_or_create_progress()
    letter = FutureLetter.query.first()
    entries = LogbookEntry.query.all()
    logbook_hours = sum(e.hours for e in entries)
    return jsonify({
        'virtual_hours': prog.virtual_hours or 0,
        'total_hours': get_total_hours(prog),
        'logbook_hours': round(logbook_hours, 1),
        'streak_days': prog.streak_days or 0,
        'flashcard_streak': prog.flashcard_streak or 0,
        'daily_mission_streak': prog.daily_mission_streak or 0,
        'first_flight_done': prog.first_flight_done,
        'first_flight_step': prog.first_flight_step or 0,
        'daily_missions': get_daily_missions(prog),
        'weekly_challenges': get_weekly_challenges(prog),
        'career_tree': get_career_tree(prog),
        'unlocked_aircraft': get_unlocked_content(prog),
        'flashcards_learned_count': len(prog._json('flashcards_learned', [])),
        'has_letter': letter is not None,
        'letter_opened': letter.is_opened if letter else False,
        'growth_report': get_growth_report(prog, 30),
        'wallet': get_wallet_summary(prog),
        'salary': salary_progress(prog),
    })


@bp.route('/api/gamification/activity', methods=['POST'])
def track_activity():
    data = request.get_json() or {}
    activity_type = data.get('type')
    detail = data.get('detail', '')
    if not activity_type:
        return jsonify({'error': 'type required'}), 400
    prog = get_or_create_progress()
    log_activity(prog, activity_type, detail)
    return jsonify({'status': 'ok'})


@bp.route('/api/gamification/mission/complete', methods=['POST'])
def mission_complete():
    data = request.get_json() or {}
    mission_id = data.get('mission_id')
    prog = get_or_create_progress()
    activity_type = ACTIVITY_MAP.get(mission_id)
    if activity_type:
        today = today_str()
        log = prog._json('activity_log', [])
        has_activity = any(
            a.get('date') == today and a.get('type') == activity_type
            for a in log
        )
        if not has_activity and activity_type not in ('career', 'captain_day'):
            return jsonify({
                'error': '먼저 해당 활동을 해보세요!',
                'need_activity': activity_type
            }), 400
    hours, msg, money = complete_mission(prog, mission_id)
    if hours is None:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'virtual_hours': hours,
        'money_earned': money, 'wallet_balance': prog.wallet_balance or 0,
    })


@bp.route('/api/gamification/weekly/complete', methods=['POST'])
def weekly_complete():
    data = request.get_json() or {}
    challenge_id = data.get('challenge_id')
    prog = get_or_create_progress()
    hours, msg, money = complete_weekly(prog, challenge_id)
    if hours is None:
        return jsonify({'error': msg}), 400
    return jsonify({
        'status': 'ok', 'message': msg, 'virtual_hours': hours,
        'money_earned': money, 'wallet_balance': prog.wallet_balance or 0,
    })


def _quiz_result_item(q, answers):
    user_ans = answers.get(q['id'])
    correct_idx = q['answer']
    is_correct = user_ans == correct_idx
    return {
        'id': q['id'],
        'correct': is_correct,
        'user_answer': user_ans,
        'correct_answer': correct_idx,
        'user_choice': q['choices'][user_ans] if user_ans is not None and 0 <= user_ans < len(q['choices']) else None,
        'correct_choice': q['choices'][correct_idx],
        'explanation': q.get('explanation', ''),
    }


@bp.route('/api/gamification/quiz/submit', methods=['POST'])
def quiz_submit():
    data = request.get_json() or {}
    answers = data.get('answers', {})
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    quiz_day = dl.get('quiz', {})
    question_ids = quiz_day.get('ids') or data.get('question_ids', list(answers.keys()))

    if quiz_day.get('done'):
        return jsonify({'error': '오늘의 퀴즈는 이미 완료했습니다. 내일 다시 도전하세요!'}), 400

    bank = get_quiz_bank()
    questions = lookup_by_ids(bank, question_ids)
    if not questions or len(questions) != len(question_ids):
        return jsonify({'error': '유효한 문항이 없습니다.'}), 400
    if len(answers) < len(questions):
        return jsonify({'error': '모든 문제에 답해주세요.'}), 400

    correct = sum(1 for q in questions if answers.get(q['id']) == q['answer'])
    score = round(correct / len(questions) * 100)
    results = [_quiz_result_item(q, answers) for q in questions]

    hist = prog._json('quiz_history', [])
    hist.append({'date': today_str(), 'score': score, 'correct': correct, 'total': len(questions)})
    prog.set_json('quiz_history', hist[-20:])
    log_activity(prog, 'quiz', f'score={score}')

    quiz_day.update({
        'ids': question_ids,
        'done': True,
        'score': score,
        'correct': correct,
        'answers': answers,
        'results': results,
    })
    dl['quiz'] = quiz_day
    save_daily_learning(prog, dl)

    if score >= 80:
        award_virtual_hours(prog, 1.0, f'오늘의 퀴즈 {score}점')
    elif score >= 50:
        award_virtual_hours(prog, 0.3, f'오늘의 퀴즈 {score}점')
    else:
        award_virtual_hours(prog, 0.1, f'오늘의 퀴즈 완료 ({score}점)')
    from app.services.economy import award_money, LEARNING_REWARDS
    if score >= 90:
        quiz_money = award_money(prog, LEARNING_REWARDS['quiz_90'], f'퀴즈 {score}점')
    elif score >= 80:
        quiz_money = award_money(prog, LEARNING_REWARDS['quiz_80'], f'퀴즈 {score}점')
    elif score >= 50:
        quiz_money = award_money(prog, LEARNING_REWARDS['quiz_50'], f'퀴즈 {score}점')
    else:
        quiz_money = award_money(prog, LEARNING_REWARDS['quiz_done'], f'퀴즈 완료 ({score}점)')
    try_unlock_badges(prog)
    db.session.commit()
    return jsonify({
        'score': score, 'correct': correct, 'total': len(questions),
        'results': results, 'pool_size': len(bank),
        'daily_done': True,
        'money_earned': quiz_money,
        'wallet_balance': prog.wallet_balance or 0,
    })


@bp.route('/api/gamification/flashcard/learn', methods=['POST'])
def flashcard_learn():
    data = request.get_json() or {}
    card_ids = data.get('card_ids', [])
    prog = get_or_create_progress()
    learned = prog._json('flashcards_learned', [])
    new_count = 0
    for cid in card_ids:
        if cid not in learned:
            learned.append(cid)
            new_count += 1
    prog.set_json('flashcards_learned', learned)
    from datetime import timedelta
    today = today_str()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if prog.last_flashcard_date == yesterday:
        prog.flashcard_streak = (prog.flashcard_streak or 0) + 1
    elif prog.last_flashcard_date != today:
        prog.flashcard_streak = 1
    prog.last_flashcard_date = today
    flash_money = 0
    if new_count > 0:
        award_virtual_hours(prog, new_count * 0.1, f'플래시카드 {new_count}개 학습')
        from app.services.economy import award_money, LEARNING_REWARDS
        flash_money = award_money(prog, LEARNING_REWARDS['flashcard'] * new_count, f'플래시카드 {new_count}개')
    log_activity(prog, 'flashcard', f'learned={len(card_ids)}')
    try_unlock_badges(prog)
    db.session.commit()
    return jsonify({
        'learned_total': len(learned),
        'new_count': new_count,
        'streak': prog.flashcard_streak,
        'money_earned': flash_money,
        'wallet_balance': prog.wallet_balance or 0,
    })


@bp.route('/api/gamification/flashcard/daily')
def flashcard_daily():
    bank = get_flashcard_bank()
    daily = daily_sample(bank, FLASHCARD_DAILY, today_str())
    prog = get_or_create_progress()
    learned = set(prog._json('flashcards_learned', []))
    out = []
    for c in daily:
        item = dict(c)
        item['already_learned'] = c['id'] in learned
        out.append(item)
    return jsonify({
        'cards': out,
        'pool_size': len(bank),
        'count': len(out)
    })


@bp.route('/api/gamification/scenario/complete', methods=['POST'])
def scenario_complete():
    data = request.get_json() or {}
    scenario_id = data.get('scenario_id')
    grade = data.get('grade', 'B')
    total_score = data.get('score', 0)
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    sc_day = dl.get('scenarios', {})
    daily_ids = sc_day.get('ids', [])

    if daily_ids and scenario_id not in daily_ids:
        return jsonify({'error': '오늘의 훈련 시나리오가 아닙니다.'}), 400

    scenarios = prog._json('scenario_progress', {})
    scenarios[scenario_id] = {
        'completed': True, 'grade': grade, 'score': total_score,
        'date': today_str()
    }
    prog.set_json('scenario_progress', scenarios)

    completed_today = sc_day.get('completed', [])
    if scenario_id not in completed_today:
        completed_today.append(scenario_id)
    sc_day['completed'] = completed_today
    sc_day['all_done'] = len(completed_today) >= len(daily_ids) and len(daily_ids) > 0
    dl['scenarios'] = sc_day
    save_daily_learning(prog, dl)

    reward = 1.5 if grade == 'A' else 0.8 if grade == 'B' else 0.3
    award_virtual_hours(prog, reward, f'시나리오 {scenario_id} ({grade})')
    from app.services.economy import award_money, LEARNING_REWARDS
    sc_key = f'scenario_{grade.lower()}'
    scenario_money = award_money(prog, LEARNING_REWARDS.get(sc_key, LEARNING_REWARDS['scenario_c']), f'시나리오 {grade}')
    log_activity(prog, 'scenario', scenario_id)

    bonus_money = 0
    if sc_day.get('all_done') and not sc_day.get('bonus_awarded'):
        award_virtual_hours(prog, 1.0, '오늘의 비상 훈련 4개 완료')
        bonus_money = award_money(prog, LEARNING_REWARDS['scenario_all_bonus'], '비상 훈련 4개 완료')
        sc_day['bonus_awarded'] = True
        dl['scenarios'] = sc_day
        save_daily_learning(prog, dl)

    try_unlock_badges(prog)
    db.session.commit()
    return jsonify({
        'status': 'ok',
        'reward_hours': reward,
        'completed_count': len(completed_today),
        'total': len(daily_ids),
        'daily_done': sc_day.get('all_done', False),
        'money_earned': scenario_money + bonus_money,
        'wallet_balance': prog.wallet_balance or 0,
    })


@bp.route('/api/gamification/first-flight/step', methods=['POST'])
def first_flight_step():
    data = request.get_json() or {}
    step = int(data.get('step', 0))
    prog = get_or_create_progress()
    steps = load_json('first_flight.json')
    max_step = len(steps)
    prog.first_flight_step = max(prog.first_flight_step or 0, step)
    first_flight_money = 0
    if step >= max_step and not prog.first_flight_done:
        prog.first_flight_done = True
        award_virtual_hours(prog, 2.0, '첫 비행 튜토리얼 완료')
        from app.services.economy import award_money, LEARNING_REWARDS
        first_flight_money = award_money(prog, LEARNING_REWARDS['first_flight'], '첫 비행 튜토리얼 완료')
        try_unlock_badges(prog)
    log_activity(prog, 'first_flight', f'step={step}')
    db.session.commit()
    return jsonify({
        'step': prog.first_flight_step,
        'done': prog.first_flight_done,
        'virtual_hours': prog.virtual_hours,
        'money_earned': first_flight_money,
        'wallet_balance': prog.wallet_balance or 0,
    })


@bp.route('/api/gamification/letter', methods=['GET', 'POST'])
def future_letter():
    if request.method == 'POST':
        data = request.get_json() or {}
        content = (data.get('content') or '').strip()
        if len(content) < 10:
            return jsonify({'error': '편지를 조금 더 길게 써주세요 (10자 이상)'}), 400
        existing = FutureLetter.query.first()
        if existing:
            return jsonify({'error': '이미 편지를 작성했습니다.'}), 400
        letter = FutureLetter(content=content)
        db.session.add(letter)
        prog = get_or_create_progress()
        log_activity(prog, 'letter', 'written')
        award_virtual_hours(prog, 0.5, '미래의 나에게 편지 작성')
        from app.services.economy import award_money, LEARNING_REWARDS
        letter_money = award_money(prog, LEARNING_REWARDS['letter'], '미래의 나에게 편지')
        db.session.commit()
        return jsonify({'status': 'ok', 'money_earned': letter_money, 'wallet_balance': prog.wallet_balance or 0})
    letter = FutureLetter.query.first()
    if not letter:
        return jsonify({'exists': False})
    prog = get_or_create_progress()
    check_letter_unlock(prog)
    return jsonify({
        'exists': True,
        'content': letter.content if letter.is_opened else None,
        'written_at': letter.written_at.isoformat() if letter.written_at else None,
        'is_opened': letter.is_opened,
        'locked_message': '100시간, 뱃지 3개, 또는 첫 비행 완료 시 열립니다!' if not letter.is_opened else None
    })


@bp.route('/api/gamification/quiz')
def get_quiz():
    bank = get_quiz_bank()
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    today = today_str()
    quiz_day = dl.get('quiz', {})

    if quiz_day.get('done'):
        questions = lookup_by_ids(bank, quiz_day.get('ids', []))
        return jsonify({
            'questions': [quiz_public(q) for q in questions],
            'pool_size': len(bank),
            'count': len(questions),
            'daily_done': True,
            'score': quiz_day.get('score'),
            'correct': quiz_day.get('correct'),
            'results': quiz_day.get('results', []),
        })

    if quiz_day.get('ids'):
        picked = lookup_by_ids(bank, quiz_day['ids'])
    else:
        picked = daily_sample(bank, QUIZ_PER_ROUND, f'quiz-{today}')
        quiz_day = {'ids': [q['id'] for q in picked], 'done': False}
        dl['quiz'] = quiz_day
        save_daily_learning(prog, dl)
        db.session.commit()

    return jsonify({
        'questions': [quiz_public(q) for q in picked],
        'pool_size': len(bank),
        'count': len(picked),
        'daily_done': False,
    })


@bp.route('/api/gamification/scenarios')
def get_scenarios():
    bank = get_scenario_bank()
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    today = today_str()
    sc_day = dl.get('scenarios', {})

    if sc_day.get('ids'):
        picked = lookup_by_ids(bank, sc_day['ids'])
    else:
        picked = daily_sample(bank, SCENARIO_DAILY, f'scenario-{today}')
        sc_day = {
            'ids': [s['id'] for s in picked],
            'completed': [],
            'all_done': False,
        }
        dl['scenarios'] = sc_day
        save_daily_learning(prog, dl)
        db.session.commit()

    completed_today = set(sc_day.get('completed', []))
    out = []
    for s in picked:
        item = dict(s)
        item['completed_today'] = s['id'] in completed_today
        out.append(item)

    return jsonify({
        'scenarios': out,
        'pool_size': len(bank),
        'count': len(out),
        'completed_count': len(completed_today),
        'total': len(out),
        'daily_done': sc_day.get('all_done', False),
    })


@bp.route('/api/gamification/first-flight')
def get_first_flight():
    prog = get_or_create_progress()
    return jsonify({
        'steps': load_json('first_flight.json'),
        'current_step': prog.first_flight_step or 0,
        'done': prog.first_flight_done
    })


@bp.route('/api/gamification/captain-day')
def get_captain_day():
    return jsonify(load_json('captain_day.json'))