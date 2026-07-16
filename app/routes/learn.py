from flask import Blueprint, render_template, jsonify, request
from app.models import db, UserProgress, FutureLetter, LogbookEntry
from app.services.gamification import (
    load_json, get_or_create_progress, get_daily_missions, complete_mission,
    auto_claim_daily_mission,
    get_weekly_challenges, complete_weekly, get_career_tree, get_growth_report,
    check_letter_unlock, award_virtual_hours, log_activity, get_total_hours,
    get_unlocked_content, try_unlock_badges, today_str, week_key,
    get_daily_learning, save_daily_learning, quiz_public
)
from app.services.economy import (
    get_wallet_summary, salary_progress, process_salary_bonuses,
    award_money, LEARNING_REWARDS,
)
from app.services.learning_extra import (
    is_extra_active, can_start_extra, extra_meta, extra_reward, extra_seed,
    start_extra_quiz, start_extra_flashcards, start_extra_scenarios,
    extra_key,
)
from app.services.content_bank import (
    get_quiz_bank, get_flashcard_bank, get_scenario_bank,
    daily_sample, lookup_by_ids, prepare_quiz_questions,
    prepare_scenario, prepare_first_flight_steps,
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
    bonuses, bonus_total = process_salary_bonuses(prog)
    try:
        from app.services.pilot_extras import check_crew_unlocks
        check_crew_unlocks(prog)
    except Exception:
        pass
    try:
        from app.services.pilot_features import add_season_xp
        add_season_xp(prog, 'mission_done')
    except Exception:
        pass
    return jsonify({
        'status': 'ok', 'message': msg, 'virtual_hours': hours,
        'money_earned': money + bonus_total, 'bonuses': bonuses,
        'wallet_balance': prog.wallet_balance or 0,
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


def _quiz_money_for_score(score, is_extra=False):
    if score >= 90:
        amount = LEARNING_REWARDS['quiz_90']
    elif score >= 80:
        amount = LEARNING_REWARDS['quiz_80']
    elif score >= 50:
        amount = LEARNING_REWARDS['quiz_50']
    else:
        amount = LEARNING_REWARDS['quiz_done']
    if is_extra:
        amount = extra_reward(amount)
    label = f'퀴즈 {score}점' + (' (추가 학습)' if is_extra else '')
    return amount, label


def _as_answer_idx(val):
    """JSON/폼에서 문자열로 올 수 있는 답 인덱스를 int로 통일"""
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _quiz_result_item(q, answers):
    user_ans = _as_answer_idx(answers.get(q['id']))
    if user_ans is None:
        user_ans = _as_answer_idx(answers.get(str(q['id'])))
    correct_idx = int(q.get('answer', 0))
    is_correct = user_ans is not None and user_ans == correct_idx
    n = len(q.get('choices') or [])
    return {
        'id': q['id'],
        'correct': is_correct,
        'user_answer': user_ans,
        'correct_answer': correct_idx,
        'user_choice': q['choices'][user_ans] if user_ans is not None and 0 <= user_ans < n else None,
        'correct_choice': q['choices'][correct_idx] if 0 <= correct_idx < n else None,
        'explanation': q.get('explanation', ''),
    }


@bp.route('/api/gamification/quiz/submit', methods=['POST'])
def quiz_submit():
    data = request.get_json() or {}
    answers = data.get('answers', {})
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    is_extra = is_extra_active(dl, 'quiz')
    quiz_day = dl.get(extra_key('quiz') if is_extra else 'quiz', {})

    if is_extra:
        if quiz_day.get('done'):
            return jsonify({'error': '추가 퀴즈는 이미 완료했습니다.'}), 400
    elif dl.get('quiz', {}).get('done'):
        return jsonify({'error': '오늘의 퀴즈는 이미 완료했습니다. 한번 더 학습하기를 이용하세요!'}), 400

    question_ids = quiz_day.get('ids') or data.get('question_ids', list(answers.keys()))
    bank = get_quiz_bank()
    prepared = quiz_day.get('prepared')
    if prepared and len(prepared) == len(question_ids):
        questions = prepared
    else:
        raw = lookup_by_ids(bank, question_ids)
        seed = extra_seed('quiz', today_str()) if is_extra else today_str()
        questions = prepare_quiz_questions(raw, seed)
    if not questions or len(questions) != len(question_ids):
        return jsonify({'error': '유효한 문항이 없습니다.'}), 400
    # normalize answer keys/values (string/int mix from clients)
    answers = {
        str(k): _as_answer_idx(v)
        for k, v in (answers or {}).items()
    }
    answers = {k: v for k, v in answers.items() if v is not None}
    if len(answers) < len(questions):
        return jsonify({'error': '모든 문제에 답해주세요.'}), 400

    correct = sum(
        1 for q in questions
        if answers.get(str(q['id'])) == int(q.get('answer', 0))
    )
    score = round(correct / len(questions) * 100)
    results = [_quiz_result_item(q, answers) for q in questions]

    hist = prog._json('quiz_history', [])
    hist.append({
        'date': today_str(), 'score': score, 'correct': correct,
        'total': len(questions), 'extra': is_extra,
    })
    prog.set_json('quiz_history', hist[-20:])
    log_activity(prog, 'quiz', f'score={score}' + (' extra' if is_extra else ''))

    quiz_day.update({
        'ids': question_ids,
        'prepared': questions,
        'done': True,
        'score': score,
        'correct': correct,
        'answers': answers,
        'results': results,
        'money_earned': 0,
    })
    dl[extra_key('quiz') if is_extra else 'quiz'] = quiz_day
    save_daily_learning(prog, dl)

    hours = 1.0 if score >= 80 else 0.3 if score >= 50 else 0.1
    if is_extra:
        hours *= 0.5
    award_virtual_hours(prog, hours, f'{"추가 " if is_extra else ""}퀴즈 {score}점')

    amount, label = _quiz_money_for_score(score, is_extra)
    quiz_money = award_money(prog, amount, label)
    try_unlock_badges(prog)
    try:
        from app.services.pilot_extras import check_crew_unlocks
        check_crew_unlocks(prog)
    except Exception:
        pass
    mission_money = 0
    if not is_extra:
        try:
            from app.services.player_stats import apply_activity_stats
            from app.services.guide_service import auto_complete_on_activity
            apply_activity_stats(prog, 'quiz_high' if score >= 80 else 'quiz')
            auto_complete_on_activity(prog, 'learn_quiz')
        except Exception:
            pass
        mission_money = auto_claim_daily_mission(prog, 'm_quiz')
    bonus_extra = {'quiz_perfect': score >= 100} if not is_extra else {}
    bonuses, bonus_total = process_salary_bonuses(prog, bonus_extra)
    if is_extra:
        bonus_total = 0
        bonuses = []
    try:
        from app.services.pilot_features import add_season_xp
        add_season_xp(prog, 'quiz_done')
    except Exception:
        pass
    total_money = quiz_money + mission_money + bonus_total
    if not is_extra:
        quiz_day['money_earned'] = total_money
        dl['quiz'] = quiz_day
        save_daily_learning(prog, dl)
    db.session.commit()
    meta = extra_meta(dl, 'quiz', dl.get('quiz', {}).get('done', False))
    if is_extra:
        meta['extra_done'] = True
    return jsonify({
        'score': score, 'correct': correct, 'total': len(questions),
        'results': results, 'pool_size': len(bank),
        'daily_done': dl.get('quiz', {}).get('done', False) or (not is_extra),
        'mode': 'extra' if is_extra else 'daily',
        'money_earned': total_money,
        'mission_money': mission_money,
        'bonuses': bonuses,
        'wallet_balance': prog.wallet_balance or 0,
        **meta,
    })


@bp.route('/api/gamification/flashcard/learn', methods=['POST'])
def flashcard_learn():
    data = request.get_json() or {}
    card_ids = data.get('card_ids', [])
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    is_extra = is_extra_active(dl, 'flashcard')
    fc_day = dl.get(extra_key('flashcard') if is_extra else 'flashcard', {})

    if is_extra:
        if fc_day.get('done'):
            return jsonify({'error': '추가 학습은 이미 완료했습니다.'}), 400
    elif dl.get('flashcard', {}).get('done'):
        return jsonify({'error': '오늘의 학습을 이미 완료했습니다. 한번 더 학습하기를 이용하세요!'}), 400

    if not fc_day.get('ids'):
        fc_day['ids'] = card_ids
    elif set(card_ids) != set(fc_day['ids']):
        return jsonify({'error': '오늘의 카드 세트와 일치하지 않습니다.'}), 400

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
    if is_extra:
        award_virtual_hours(prog, len(card_ids) * 0.05, f'추가 플래시카드 {len(card_ids)}개')
        flash_money = award_money(
            prog,
            extra_reward(LEARNING_REWARDS['flashcard'] * len(card_ids)),
            f'추가 플래시카드 {len(card_ids)}개',
        )
    elif new_count > 0:
        award_virtual_hours(prog, new_count * 0.1, f'플래시카드 {new_count}개 학습')
        flash_money = award_money(prog, LEARNING_REWARDS['flashcard'] * new_count, f'플래시카드 {new_count}개')
    else:
        award_virtual_hours(prog, 0.1, '오늘의 플래시카드 학습')

    fc_day['done'] = True
    dl[extra_key('flashcard') if is_extra else 'flashcard'] = fc_day
    save_daily_learning(prog, dl)

    log_activity(prog, 'flashcard', f'learned={len(card_ids)}' + (' extra' if is_extra else ''))
    try_unlock_badges(prog)
    try:
        from app.services.pilot_extras import check_crew_unlocks
        check_crew_unlocks(prog)
    except Exception:
        pass
    mission_money = 0
    if not is_extra:
        if not flash_money and len(card_ids) > 0:
            flash_money = award_money(prog, LEARNING_REWARDS['flashcard'], '오늘의 플래시카드 완료')
        mission_money = auto_claim_daily_mission(prog, 'm_flashcard')
    bonuses, bonus_total = process_salary_bonuses(prog)
    if is_extra:
        bonus_total = 0
        bonuses = []
    season_rewards = []
    if new_count > 0 or is_extra:
        try:
            from app.services.pilot_features import add_season_xp
            season_rewards = add_season_xp(prog, 'flashcard', max(new_count, 1))
        except Exception:
            pass
    total_money = flash_money + mission_money + bonus_total
    fc_key = extra_key('flashcard') if is_extra else 'flashcard'
    fc_day = dl.get(fc_key, {})
    fc_day['money_earned'] = total_money
    dl[fc_key] = fc_day
    save_daily_learning(prog, dl)
    db.session.commit()
    meta = extra_meta(dl, 'flashcard', dl.get('flashcard', {}).get('done', False))
    if is_extra:
        meta['extra_done'] = True
    return jsonify({
        'learned_total': len(learned),
        'new_count': new_count,
        'streak': prog.flashcard_streak,
        'daily_done': dl.get('flashcard', {}).get('done', False) or (not is_extra),
        'mode': 'extra' if is_extra else 'daily',
        'money_earned': total_money,
        'mission_money': mission_money,
        'bonuses': bonuses,
        'season_rewards': season_rewards,
        'wallet_balance': prog.wallet_balance or 0,
        **meta,
    })


@bp.route('/api/gamification/flashcard/daily')
def flashcard_daily():
    bank = get_flashcard_bank()
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    today = today_str()
    is_extra = is_extra_active(dl, 'flashcard')
    fc_day = dl.get(extra_key('flashcard') if is_extra else 'flashcard', {})

    if is_extra and fc_day.get('ids'):
        picked = lookup_by_ids(bank, fc_day['ids'])
    elif fc_day.get('ids'):
        picked = lookup_by_ids(bank, fc_day['ids'])
    else:
        picked = daily_sample(bank, FLASHCARD_DAILY, today)
        fc_day = {'ids': [c['id'] for c in picked], 'done': False}
        dl['flashcard'] = fc_day
        save_daily_learning(prog, dl)
        db.session.commit()

    learned = set(prog._json('flashcards_learned', []))
    out = []
    for c in picked:
        item = dict(c)
        item['already_learned'] = c['id'] in learned
        out.append(item)

    daily_done = dl.get('flashcard', {}).get('done', False)
    meta = extra_meta(dl, 'flashcard', daily_done)
    reward_day = dl.get(extra_key('flashcard') if is_extra else 'flashcard', {})
    if is_extra and reward_day.get('done'):
        meta['extra_done'] = True
    return jsonify({
        'cards': out,
        'pool_size': len(bank),
        'count': len(out),
        'daily_done': daily_done and not is_extra,
        'mode': 'extra' if is_extra else 'daily',
        'money_earned': reward_day.get('money_earned', 0) if reward_day.get('done') else 0,
        'wallet_balance': prog.wallet_balance or 0,
        **meta,
    })


@bp.route('/api/gamification/scenario/complete', methods=['POST'])
def scenario_complete():
    data = request.get_json() or {}
    scenario_id = data.get('scenario_id')
    grade = data.get('grade', 'B')
    total_score = data.get('score', 0)
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    is_extra = is_extra_active(dl, 'scenarios')
    sc_day = dl.get(extra_key('scenarios') if is_extra else 'scenarios', {})
    daily_ids = sc_day.get('ids', [])

    if not daily_ids or scenario_id not in daily_ids:
        return jsonify({'error': '오늘의 훈련 시나리오가 아닙니다.'}), 400
    if scenario_id in sc_day.get('completed', []):
        return jsonify({'error': '이미 완료한 시나리오입니다.'}), 400

    scenarios = prog._json('scenario_progress', {})
    scenarios[scenario_id] = {
        'completed': True, 'grade': grade, 'score': total_score,
        'date': today_str(), 'extra': is_extra,
    }
    prog.set_json('scenario_progress', scenarios)

    completed_today = sc_day.get('completed', [])
    if scenario_id not in completed_today:
        completed_today.append(scenario_id)
    sc_day['completed'] = completed_today
    sc_day['all_done'] = len(completed_today) >= len(daily_ids) and len(daily_ids) > 0
    if is_extra and sc_day.get('all_done'):
        sc_day['done'] = True
    dl[extra_key('scenarios') if is_extra else 'scenarios'] = sc_day
    save_daily_learning(prog, dl)

    reward = 1.5 if grade == 'A' else 0.8 if grade == 'B' else 0.3
    if is_extra:
        reward *= 0.5
    award_virtual_hours(prog, reward, f'{"추가 " if is_extra else ""}시나리오 {scenario_id} ({grade})')
    sc_key = f'scenario_{grade.lower()}'
    base_money = LEARNING_REWARDS.get(sc_key, LEARNING_REWARDS['scenario_c'])
    scenario_money = award_money(
        prog,
        extra_reward(base_money) if is_extra else base_money,
        f'{"추가 " if is_extra else ""}시나리오 {grade}',
    )
    log_activity(prog, 'scenario', scenario_id + (' extra' if is_extra else ''))

    bonus_money = 0
    if sc_day.get('all_done') and not sc_day.get('bonus_awarded'):
        award_virtual_hours(prog, 0.5 if is_extra else 1.0, '비상 훈련 4개 완료' + (' (추가)' if is_extra else ''))
        bonus_amount = extra_reward(LEARNING_REWARDS['scenario_all_bonus']) if is_extra else LEARNING_REWARDS['scenario_all_bonus']
        bonus_money = award_money(prog, bonus_amount, '비상 훈련 4개 완료' + (' (추가)' if is_extra else ''))
        sc_day['bonus_awarded'] = True
        dl[extra_key('scenarios') if is_extra else 'scenarios'] = sc_day
        save_daily_learning(prog, dl)

    try_unlock_badges(prog)
    mission_money = 0
    if not is_extra:
        mission_money = auto_claim_daily_mission(prog, 'm_scenario')
    bonuses, bonus_total = process_salary_bonuses(prog)
    if is_extra:
        bonus_total = 0
        bonuses = []
    season_rewards = []
    try:
        from app.services.pilot_features import add_season_xp
        season_rewards = add_season_xp(prog, 'scenario_done')
    except Exception:
        pass
    total_money = scenario_money + bonus_money + mission_money + bonus_total
    sc_key = extra_key('scenarios') if is_extra else 'scenarios'
    sc_day = dl.get(sc_key, {})
    sc_day['session_money'] = sc_day.get('session_money', 0) + total_money
    if sc_day.get('all_done'):
        sc_day['money_earned'] = sc_day['session_money']
    dl[sc_key] = sc_day
    save_daily_learning(prog, dl)
    db.session.commit()
    daily_done = dl.get('scenarios', {}).get('all_done', False)
    meta = extra_meta(dl, 'scenarios', daily_done)
    if is_extra and sc_day.get('all_done'):
        meta['extra_done'] = True
    return jsonify({
        'status': 'ok',
        'reward_hours': reward,
        'completed_count': len(completed_today),
        'total': len(daily_ids),
        'daily_done': not is_extra and sc_day.get('all_done', False),
        'mode': 'extra' if is_extra else 'daily',
        'money_earned': total_money,
        'session_money': sc_day.get('session_money', 0),
        'mission_money': mission_money,
        'bonuses': bonuses,
        'season_rewards': season_rewards,
        'wallet_balance': prog.wallet_balance or 0,
        **meta,
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


@bp.route('/api/gamification/quiz/extra', methods=['POST'])
def quiz_extra():
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    daily_done = dl.get('quiz', {}).get('done', False)
    ok, msg = can_start_extra(dl, 'quiz', daily_done)
    if not ok:
        return jsonify({'error': msg}), 400
    if msg == 'resume':
        extra = dl.get(extra_key('quiz'), {})
        return jsonify({
            'status': 'ok', 'message': '진행 중인 추가 학습을 이어갑니다.',
            'mode': 'extra', **extra_meta(dl, 'quiz', daily_done),
        })
    bank = get_quiz_bank()
    start_extra_quiz(dl, bank, today_str(), prepare_quiz_questions, QUIZ_PER_ROUND)
    save_daily_learning(prog, dl)
    db.session.commit()
    return jsonify({
        'status': 'ok', 'message': '새로운 5문제가 준비되었습니다!',
        'mode': 'extra', **extra_meta(dl, 'quiz', daily_done),
    })


@bp.route('/api/gamification/flashcard/extra', methods=['POST'])
def flashcard_extra():
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    daily_done = dl.get('flashcard', {}).get('done', False)
    ok, msg = can_start_extra(dl, 'flashcard', daily_done)
    if not ok:
        return jsonify({'error': msg}), 400
    if msg == 'resume':
        return jsonify({
            'status': 'ok', 'message': '진행 중인 추가 학습을 이어갑니다.',
            'mode': 'extra', **extra_meta(dl, 'flashcard', daily_done),
        })
    bank = get_flashcard_bank()
    start_extra_flashcards(dl, bank, today_str(), FLASHCARD_DAILY)
    save_daily_learning(prog, dl)
    db.session.commit()
    return jsonify({
        'status': 'ok', 'message': '새로운 5장의 카드가 준비되었습니다!',
        'mode': 'extra', **extra_meta(dl, 'flashcard', daily_done),
    })


@bp.route('/api/gamification/scenarios/extra', methods=['POST'])
def scenarios_extra():
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    daily_done = dl.get('scenarios', {}).get('all_done', False)
    ok, msg = can_start_extra(dl, 'scenarios', daily_done)
    if not ok:
        return jsonify({'error': msg}), 400
    if msg == 'resume':
        return jsonify({
            'status': 'ok', 'message': '진행 중인 추가 훈련을 이어갑니다.',
            'mode': 'extra', **extra_meta(dl, 'scenarios', daily_done),
        })
    bank = get_scenario_bank()
    start_extra_scenarios(dl, bank, today_str(), SCENARIO_DAILY)
    save_daily_learning(prog, dl)
    db.session.commit()
    return jsonify({
        'status': 'ok', 'message': '새로운 4개 시나리오가 준비되었습니다!',
        'mode': 'extra', **extra_meta(dl, 'scenarios', daily_done),
    })


@bp.route('/api/gamification/quiz')
def get_quiz():
    bank = get_quiz_bank()
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    today = today_str()
    quiz_day = dl.get('quiz', {})
    daily_done = quiz_day.get('done', False)

    if is_extra_active(dl, 'quiz'):
        extra = dl.get(extra_key('quiz'), {})
        prepared = extra.get('prepared') or prepare_quiz_questions(
            lookup_by_ids(bank, extra.get('ids', [])), extra_seed('quiz', today)
        )
        return jsonify({
            'questions': [quiz_public(q) for q in prepared],
            'pool_size': len(bank),
            'count': len(prepared),
            'daily_done': daily_done,
            'mode': 'extra',
            'extra_active': True,
            **extra_meta(dl, 'quiz', daily_done),
        })

    if quiz_day.get('done'):
        prepared = quiz_day.get('prepared') or prepare_quiz_questions(
            lookup_by_ids(bank, quiz_day.get('ids', [])), today
        )
        return jsonify({
            'questions': [quiz_public(q) for q in prepared],
            'pool_size': len(bank),
            'count': len(prepared),
            'daily_done': True,
            'mode': 'daily',
            'score': quiz_day.get('score'),
            'correct': quiz_day.get('correct'),
            'results': quiz_day.get('results', []),
            'money_earned': quiz_day.get('money_earned'),
            'wallet_balance': prog.wallet_balance or 0,
            **extra_meta(dl, 'quiz', True),
        })

    if quiz_day.get('ids'):
        picked = prepare_quiz_questions(lookup_by_ids(bank, quiz_day['ids']), today)
        quiz_day['prepared'] = picked
        dl['quiz'] = quiz_day
        save_daily_learning(prog, dl)
        db.session.commit()
    else:
        raw = daily_sample(bank, QUIZ_PER_ROUND, f'quiz-{today}')
        picked = prepare_quiz_questions(raw, today)
        quiz_day = {'ids': [q['id'] for q in picked], 'prepared': picked, 'done': False}
        dl['quiz'] = quiz_day
        save_daily_learning(prog, dl)
        db.session.commit()

    return jsonify({
        'questions': [quiz_public(q) for q in picked],
        'pool_size': len(bank),
        'count': len(picked),
        'daily_done': False,
        'mode': 'daily',
        **extra_meta(dl, 'quiz', False),
    })


@bp.route('/api/gamification/scenarios')
def get_scenarios():
    bank = get_scenario_bank()
    prog = get_or_create_progress()
    dl = get_daily_learning(prog)
    today = today_str()
    is_extra = is_extra_active(dl, 'scenarios')
    sc_day = dl.get(extra_key('scenarios') if is_extra else 'scenarios', {})
    daily_done = dl.get('scenarios', {}).get('all_done', False)
    seed = extra_seed('scenarios', today) if is_extra else today

    if sc_day.get('ids'):
        picked = lookup_by_ids(bank, sc_day['ids'])
    elif is_extra:
        picked = []
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
        item = prepare_scenario(s, seed)
        item['completed_today'] = s['id'] in completed_today
        out.append(item)

    reward_day = dl.get(extra_key('scenarios') if is_extra else 'scenarios', {})
    meta = extra_meta(dl, 'scenarios', daily_done)
    extra_day = dl.get(extra_key('scenarios'), {})
    if extra_day.get('done'):
        meta['extra_done'] = True
    all_complete = sc_day.get('all_done', False) and len(sc_day.get('ids', [])) > 0
    show_reward = (all_complete and not is_extra) or (is_extra and all_complete)
    return jsonify({
        'scenarios': out,
        'pool_size': len(bank),
        'count': len(out),
        'completed_count': len(completed_today),
        'total': len(out),
        'daily_done': all_complete and not is_extra,
        'mode': 'extra' if is_extra else 'daily',
        'money_earned': reward_day.get('money_earned', 0) if show_reward else 0,
        'session_money': reward_day.get('session_money', 0),
        'wallet_balance': prog.wallet_balance or 0,
        **meta,
    })


@bp.route('/api/gamification/first-flight')
def get_first_flight():
    prog = get_or_create_progress()
    return jsonify({
        'steps': prepare_first_flight_steps(load_json('first_flight.json')),
        'current_step': prog.first_flight_step or 0,
        'done': prog.first_flight_done
    })


@bp.route('/api/gamification/captain-day')
def get_captain_day():
    return jsonify(load_json('captain_day.json'))