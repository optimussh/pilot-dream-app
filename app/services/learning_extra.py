"""오늘의 학습 완료 후 추가 1회 학습(보상 50%)"""
from app.services.content_bank import daily_sample, lookup_by_ids

EXTRA_DAILY_LIMIT = 1
EXTRA_REWARD_RATIO = 0.5


def extra_key(activity):
    return f'{activity}_extra'


def extra_reward(amount):
    if amount <= 0:
        return 0
    return max(1, int(amount * EXTRA_REWARD_RATIO))


def extra_seed(activity, today):
    return f'{activity}-extra-{today}'


def is_extra_active(dl, activity):
    extra = dl.get(extra_key(activity), {})
    return bool(extra.get('ids')) and not extra.get('done')


def can_start_extra(dl, activity, daily_done):
    extra = dl.get(extra_key(activity), {})
    if extra.get('done'):
        return False, '오늘 추가 학습을 이미 마쳤습니다.'
    if is_extra_active(dl, activity):
        return True, 'resume'
    if not daily_done:
        return False, '먼저 오늘의 학습을 완료하세요.'
    if extra.get('rounds_started', 0) >= EXTRA_DAILY_LIMIT:
        return False, '오늘 추가 학습 한도에 도달했습니다.'
    return True, 'start'


def extra_meta(dl, activity, daily_done):
    extra = dl.get(extra_key(activity), {})
    can, _ = can_start_extra(dl, activity, daily_done)
    return {
        'can_extra': can and not is_extra_active(dl, activity),
        'extra_active': is_extra_active(dl, activity),
        'extra_done': bool(extra.get('done')),
    }


def start_extra_quiz(dl, bank, today, prepare_fn, count):
    exclude = set(dl.get('quiz', {}).get('ids', []))
    pool = [q for q in bank if q['id'] not in exclude] or list(bank)
    raw = daily_sample(pool, count, extra_seed('quiz', today))
    picked = prepare_fn(raw, extra_seed('quiz', today))
    extra = {
        'ids': [q['id'] for q in picked],
        'prepared': picked,
        'done': False,
        'rounds_started': 1,
    }
    dl[extra_key('quiz')] = extra
    return extra


def start_extra_flashcards(dl, bank, today, count):
    exclude = set(dl.get('flashcard', {}).get('ids', []))
    pool = [c for c in bank if c['id'] not in exclude] or list(bank)
    picked = daily_sample(pool, count, extra_seed('flashcard', today))
    extra = {
        'ids': [c['id'] for c in picked],
        'done': False,
        'rounds_started': 1,
    }
    dl[extra_key('flashcard')] = extra
    return extra, picked


def start_extra_scenarios(dl, bank, today, count):
    exclude = set(dl.get('scenarios', {}).get('ids', []))
    pool = [s for s in bank if s['id'] not in exclude] or list(bank)
    picked = daily_sample(pool, count, extra_seed('scenarios', today))
    extra = {
        'ids': [s['id'] for s in picked],
        'completed': [],
        'all_done': False,
        'bonus_awarded': False,
        'done': False,
        'rounds_started': 1,
    }
    dl[extra_key('scenarios')] = extra
    return extra, picked