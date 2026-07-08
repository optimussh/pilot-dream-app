"""기장 생활 확장: 출근미션, 승무원카드, 공항, 일기, 도감, 스케줄, 연료퀴즈, 정시, 주간이벤트"""
import hashlib
import random
from datetime import datetime, timedelta
from app.models import db, LogbookEntry, UserBadge
from app.services.gamification import (
    load_json, get_total_hours, today_str, week_key, award_virtual_hours, log_activity,
)
from app.services.economy import (
    award_money, format_krw, get_owned_aircraft, get_aircraft_catalog,
    get_effective_hours, aircraft_unlock_status,
)

SCHEDULE_SLOTS = [
    'mon_am', 'mon_pm', 'tue_am', 'tue_pm', 'wed_am', 'wed_pm',
    'thu_am', 'thu_pm', 'fri_am', 'fri_pm', 'sat_am', 'sat_pm', 'sun_am', 'sun_pm',
]
SLOT_LABELS = {
    'mon_am': '월 오전', 'mon_pm': '월 오후', 'tue_am': '화 오전', 'tue_pm': '화 오후',
    'wed_am': '수 오전', 'wed_pm': '수 오후', 'thu_am': '목 오전', 'thu_pm': '목 오후',
    'fri_am': '금 오전', 'fri_pm': '금 오후', 'sat_am': '토 오전', 'sat_pm': '토 오후',
    'sun_am': '일 오전', 'sun_pm': '일 오후',
}
ON_TIME_KEYWORDS = ['정시', '정시 운항', 'on time', 'on-time', 'ontime']
KOREA_AIRPORTS = {'ICN', 'GMP', 'PUS', 'CJU', 'CJJ', 'TAE', 'KWJ', 'RSU', 'USN', 'WJU', 'KUV', 'MWX'}


def _meta(prog):
    default = {
        'captain_duty': {},
        'crew_unlocked': [],
        'crew_claimed': [],
        'airport_quiz_total': 0,
        'daily_airport': {},
        'flight_journals': [],
        'codex_stamps': [],
        'schedule_board': {},
        'fuel_quiz_history': [],
        'fuel_quiz_today': 0,
        'on_time_log': {},
        'demand_events': {},
        'demand_claims': [],
        'stats': {
            'fuel_quiz_total': 0, 'journal_total': 0, 'airport_quiz_total': 0,
            'demand_claim_total': 0, 'schedule_weeks_done': 0,
        },
    }
    meta = prog._json('pilot_meta', {})
    extras = meta.setdefault('pilot_extras', {})
    for k, v in default.items():
        if k == 'stats':
            extras.setdefault('stats', {})
            for sk, sv in v.items():
                extras['stats'].setdefault(sk, sv)
        else:
            extras.setdefault(k, v if not isinstance(v, (list, dict)) else (list(v) if isinstance(v, list) else dict(v)))
    return extras


def _save_meta(prog, extras):
    meta = prog._json('pilot_meta', {})
    meta['pilot_extras'] = extras
    prog.set_json('pilot_meta', meta)


def _ensure_daily_reset(extras):
    today = today_str()
    if extras.get('fuel_quiz_date') != today:
        extras['fuel_quiz_today'] = 0
        extras['fuel_quiz_date'] = today


def _week_logbook_count(prog):
    wk = week_key()
    start = datetime.strptime(wk + '-1', '%G-W%V-%u')
    dates = {(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)}
    return LogbookEntry.query.filter(LogbookEntry.date.in_(dates)).count()


def _is_intl_route(route):
    route = (route or '').upper().replace(' ', '')
    if '-' not in route:
        return False
    parts = [p.strip() for p in route.split('-')]
    if len(parts) != 2:
        return False
    korea = lambda p: p in KOREA_AIRPORTS or len(p) == 3
    return (parts[0] in KOREA_AIRPORTS) != (parts[1] in KOREA_AIRPORTS)


def _is_ontime(notes):
    n = (notes or '').lower()
    return any(k.lower() in n for k in ON_TIME_KEYWORDS)


def _get_rank_id(prog):
    try:
        from app.services.pilot_features import get_pilot_rank
        return get_pilot_rank(prog).get('id', 'trainee')
    except Exception:
        return 'trainee'


def _rank_order():
    return ['trainee', 'student', 'private', 'fo', 'captain', 'senior']


def _crew_unlock_met(prog, extras, card):
    req = card.get('unlock', {})
    rtype = req.get('type')
    val = req.get('value', 0)
    stats = extras.get('stats', {})
    if rtype == 'logbook_count':
        return LogbookEntry.query.count() >= val
    if rtype == 'quiz_done':
        return len(prog._json('quiz_history', [])) >= val
    if rtype == 'quiz_score':
        return any(q.get('score', 0) >= val for q in prog._json('quiz_history', []))
    if rtype == 'flashcard_count':
        return len(prog._json('flashcards_learned', [])) >= val
    if rtype == 'mission_count':
        total = sum(len(v) for v in prog._json('completed_missions', {}).values())
        return total >= val
    if rtype == 'rank_id':
        order = _rank_order()
        cur = _get_rank_id(prog)
        return order.index(cur) >= order.index(val) if val in order else False
    if rtype == 'owned_aircraft':
        return len(get_owned_aircraft(prog)) >= val
    if rtype == 'journal_count':
        return len(extras.get('flight_journals', [])) >= val
    if rtype == 'airport_quiz':
        return stats.get('airport_quiz_total', 0) >= val
    if rtype == 'schedule_week':
        return stats.get('schedule_weeks_done', 0) >= val
    if rtype == 'fuel_quiz':
        return stats.get('fuel_quiz_total', 0) >= val
    if rtype == 'demand_claim':
        return stats.get('demand_claim_total', 0) >= val
    if rtype == 'intl_route':
        return any(_is_intl_route(e.route) for e in LogbookEntry.query.all())
    if rtype == 'on_time_week':
        wk = week_key()
        return extras.get('on_time_log', {}).get(wk, 0) >= val
    if rtype == 'crew_count':
        return len(extras.get('crew_unlocked', [])) >= val
    return False


def check_crew_unlocks(prog):
    extras = _meta(prog)
    unlocked = set(extras.get('crew_unlocked', []))
    newly = []
    for card in load_json('crew_cards.json'):
        cid = card['id']
        if cid in unlocked:
            continue
        if _crew_unlock_met(prog, extras, card):
            unlocked.add(cid)
            newly.append(card)
    if newly:
        extras['crew_unlocked'] = list(unlocked)
        _save_meta(prog, extras)
        try:
            from app.services.player_stats import apply_activity_stats
            for _ in newly:
                apply_activity_stats(prog, 'crew_unlock')
        except Exception:
            pass
        db.session.commit()
    return newly


def get_crew_cards(prog):
    extras = _meta(prog)
    check_crew_unlocks(prog)
    unlocked = set(extras.get('crew_unlocked', []))
    result = []
    for card in load_json('crew_cards.json'):
        result.append({
            **card,
            'unlocked': card['id'] in unlocked,
            'can_unlock': _crew_unlock_met(prog, extras, card),
        })
    return result


# ── 1. 기장 출근 미션 ──
def get_captain_duty(prog):
    extras = _meta(prog)
    wk = week_key()
    duty = extras.setdefault('captain_duty', {})
    flights = _week_logbook_count(prog)
    claimed = duty.get('week') == wk and duty.get('claimed')
    done = flights >= 1
    return {
        'week': wk,
        'flights_this_week': flights,
        'need_flights': 1,
        'done': done,
        'claimed': claimed,
        'reward_money': 500000,
        'reward_hours': 1.0,
        'kid_desc': '이번 주 로그북에 비행 1번만 기록하면 기장 출근 완료!',
    }


def claim_captain_duty(prog):
    status = get_captain_duty(prog)
    if status['claimed']:
        return False, '이번 주 보상은 이미 받았어요!'
    if not status['done']:
        return False, '이번 주 비행 기록이 필요해요! 로그북에 비행을 적어주세요.'
    extras = _meta(prog)
    wk = week_key()
    extras['captain_duty'] = {'week': wk, 'claimed': True, 'claimed_at': today_str()}
    _save_meta(prog, extras)
    award_money(prog, status['reward_money'], '기장 출근 미션')
    award_virtual_hours(prog, status['reward_hours'], '기장 출근 미션')
    log_activity(prog, 'captain_duty', wk)
    db.session.commit()
    return True, f'👑 기장 출근 완료! {format_krw(status["reward_money"])} + {status["reward_hours"]}h'


# ── 2. 오늘의 공항 ──
def get_daily_airport(prog):
    extras = _meta(prog)
    today = today_str()
    facts = load_json('airport_daily_facts.json')
    if not facts:
        return None
    seed = hashlib.md5(f'airport-{today}'.encode()).hexdigest()
    idx = int(seed, 16) % len(facts)
    ap = dict(facts[idx])
    done = extras.get('daily_airport', {}).get('date') == today and extras['daily_airport'].get('done')
    ap['quiz_done'] = done
    ap['reward_money'] = 150000
    return ap


def submit_daily_airport_quiz(prog, answer_idx):
    ap = get_daily_airport(prog)
    if not ap:
        return False, '오늘의 공항 정보가 없어요.'
    extras = _meta(prog)
    today = today_str()
    if extras.get('daily_airport', {}).get('date') == today and extras['daily_airport'].get('done'):
        return False, '오늘 공항 퀴즈는 이미 풀었어요!'
    quiz = ap.get('quiz', {})
    correct = quiz.get('answer', 0)
    is_correct = int(answer_idx) == correct
    extras['daily_airport'] = {
        'date': today, 'airport_id': ap['id'], 'done': True, 'correct': is_correct,
    }
    extras['stats']['airport_quiz_total'] = extras['stats'].get('airport_quiz_total', 0) + 1
    _save_meta(prog, extras)
    money = ap['reward_money'] if is_correct else 50000
    award_money(prog, money, f"오늘의 공항 퀴즈: {ap['name']}")
    if is_correct:
        award_virtual_hours(prog, 0.2, f"공항 학습: {ap['id']}")
    check_crew_unlocks(prog)
    db.session.commit()
    msg = f'{"✅ 정답!" if is_correct else "아쉬워요!"} {ap["name"]} — {format_krw(money)}'
    return True, {'message': msg, 'correct': is_correct, 'explanation': ap.get('fact', '')}


# ── 3. 비행 일기 ──
def add_flight_journal(prog, entry_id, text):
    text = (text or '').strip()
    if len(text) < 5:
        return False, '일기를 5글자 이상 써주세요!'
    extras = _meta(prog)
    journals = extras.get('flight_journals', [])
    if any(j.get('entry_id') == entry_id for j in journals):
        return False, '이 비행에는 이미 일기를 썼어요!'
    entry = LogbookEntry.query.get(entry_id)
    if not entry:
        return False, '비행 기록을 찾을 수 없어요.'
    journals.append({
        'entry_id': entry_id, 'text': text[:300], 'date': today_str(),
        'route': entry.route, 'flight_number': entry.flight_number,
    })
    extras['flight_journals'] = journals[-50:]
    extras['stats']['journal_total'] = len(journals)
    _save_meta(prog, extras)
    award_money(prog, 100000, '비행 일기 작성')
    award_virtual_hours(prog, 0.1, '비행 일기')
    check_crew_unlocks(prog)
    db.session.commit()
    return True, '✈️ 비행 일기 저장! +₩100,000'


def get_flight_journals(prog, limit=10):
    extras = _meta(prog)
    return extras.get('flight_journals', [])[-limit:]


# ── 4. 기종 도감 ──
def get_aircraft_codex(prog):
    catalog = get_aircraft_catalog()
    owned = set(get_owned_aircraft(prog))
    eff = get_effective_hours(prog)
    stamps = set(_meta(prog).get('codex_stamps', []))
    result = []
    for aid, ac in catalog.items():
        st = aircraft_unlock_status(prog, aid)
        discovered = aid in owned or st.get('unlocked') or st.get('owned')
        if discovered and aid not in stamps:
            stamps.add(aid)
    extras = _meta(prog)
    if stamps - set(extras.get('codex_stamps', [])):
        extras['codex_stamps'] = list(stamps)
        _save_meta(prog, extras)
        db.session.commit()
    from app.services.economy import build_loadout_details, get_aircraft_cosmetics
    for aid, ac in catalog.items():
        st = aircraft_unlock_status(prog, aid)
        discovered = aid in stamps
        loadout = build_loadout_details(prog, aid) if aid in owned else {}
        vis = get_aircraft_cosmetics(prog, aid) if aid in owned else {}
        result.append({
            'id': aid,
            'name': ac.get('name', aid),
            'manufacturer': ac.get('manufacturer', ''),
            'category': ac.get('category', ''),
            'type': ac.get('type', ''),
            'region': ac.get('region', ''),
            'illustration': ac.get('illustration', ''),
            'discovered': discovered,
            'owned': aid in owned,
            'ready': st.get('unlocked') or st.get('owned'),
            'progress_pct': st.get('progress_pct', 0),
            'loadout_details': loadout,
            'livery_color': vis.get('livery_color', ''),
            'sticker_emoji': vis.get('sticker_emoji', ''),
            'trail_color': vis.get('trail_color', ''),
        })
    discovered_count = sum(1 for r in result if r['discovered'])
    return {
        'aircraft': result,
        'discovered': discovered_count,
        'total': len(result),
        'owned': len(owned),
    }


# ── 5. 가상 스케줄 보드 ──
def get_schedule_board(prog):
    extras = _meta(prog)
    wk = week_key()
    board = extras.get('schedule_board', {})
    if board.get('week') != wk:
        board = {'week': wk, 'slots': {}}
    owned = get_owned_aircraft(prog)
    catalog = get_aircraft_catalog()
    slots = []
    filled = 0
    for sid in SCHEDULE_SLOTS:
        ac_id = board.get('slots', {}).get(sid)
        ac_info = None
        if ac_id and ac_id in catalog:
            ac_info = {**catalog[ac_id], 'id': ac_id}
            filled += 1
        slots.append({
            'slot_id': sid, 'label': SLOT_LABELS.get(sid, sid),
            'aircraft_id': ac_id, 'aircraft': ac_info,
        })
    complete = filled >= len(SCHEDULE_SLOTS)
    claimed = board.get('claimed') and board.get('week') == wk
    return {
        'week': wk,
        'slots': slots,
        'filled': filled,
        'total_slots': len(SCHEDULE_SLOTS),
        'complete': complete,
        'claimed': claimed,
        'owned_aircraft': [{**catalog[a], 'id': a} for a in owned if a in catalog],
        'reward_money': 300000,
    }


def save_schedule_slot(prog, slot_id, aircraft_id):
    if slot_id not in SCHEDULE_SLOTS:
        return False, '잘못된 시간표 칸이에요.'
    owned = get_owned_aircraft(prog)
    if aircraft_id and aircraft_id not in owned:
        return False, '내 비행기만 배치할 수 있어요!'
    extras = _meta(prog)
    wk = week_key()
    board = extras.get('schedule_board', {})
    if board.get('week') != wk:
        board = {'week': wk, 'slots': {}, 'claimed': False}
    board['slots'] = board.get('slots', {})
    if aircraft_id:
        board['slots'][slot_id] = aircraft_id
    else:
        board['slots'].pop(slot_id, None)
    extras['schedule_board'] = board
    _save_meta(prog, extras)
    db.session.commit()
    status = get_schedule_board(prog)
    return True, status


def claim_schedule_reward(prog):
    status = get_schedule_board(prog)
    if status['claimed']:
        return False, '이번 주 스케줄 보상은 이미 받았어요!'
    if not status['complete']:
        return False, f'시간표를 모두 채워주세요! ({status["filled"]}/{status["total_slots"]})'
    extras = _meta(prog)
    board = extras['schedule_board']
    board['claimed'] = True
    extras['schedule_board'] = board
    extras['stats']['schedule_weeks_done'] = extras['stats'].get('schedule_weeks_done', 0) + 1
    _save_meta(prog, extras)
    award_money(prog, status['reward_money'], '주간 스케줄 완성')
    award_virtual_hours(prog, 0.5, '스케줄 보드 완성')
    check_crew_unlocks(prog)
    db.session.commit()
    return True, f'📅 스케줄 완성! {format_krw(status["reward_money"])}'


# ── 6. 연료·좌석 퀴즈 ──
FUEL_QUESTIONS = [
    {'id': 'fuel1', 'route': 'ICN-CJU', 'aircraft': 'B737-800', 'hours': 1.0, 'distance': 450,
     'question': 'ICN→제주, B737, 1시간 비행. 연료는 대략 몇 톤 필요할까요?',
     'choices': ['약 3~5톤', '약 50톤', '약 0.1톤', '연료 불필요'], 'answer': 0,
     'explain': '단거리 국내선은 3~5톤 정도 연료를 씁니다.'},
    {'id': 'fuel2', 'route': 'ICN-NRT', 'aircraft': 'B737-800', 'hours': 2.3, 'distance': 1200,
     'question': 'ICN→도쿄, 2.3시간. 연료는?',
     'choices': ['약 8~12톤', '약 1톤', '약 100톤', '승객이 들고 감'], 'answer': 0,
     'explain': '단거리 국제선은 8~12톤 정도.'},
    {'id': 'fuel3', 'route': 'ICN-JFK', 'aircraft': 'B777-300ER', 'hours': 14.0, 'distance': 11000,
     'question': 'ICN→뉴욕 장거리 14시간. B777 연료는?',
     'choices': ['약 100~150톤', '약 5톤', '약 500톤', '1톤이면 충분'], 'answer': 0,
     'explain': '장거리 대형기는 100톤 이상 연료를 싣습니다.'},
    {'id': 'fuel4', 'route': 'ICN-GMP', 'aircraft': 'A320', 'hours': 0.5, 'distance': 40,
     'question': 'ICN→김포 30분 비행. 승객 150명. 좌석은?',
     'choices': ['150석 모두 사용 가능', '15석만', '1500석', '좌석 없음'], 'answer': 0,
     'explain': 'A320은 보통 150~180석입니다.'},
    {'id': 'fuel5', 'route': 'ICN-SYD', 'aircraft': 'B787-9', 'hours': 10.0, 'distance': 8300,
     'question': '인천→시드니 10시간. 연료 계획 시 꼭 넣어야 할 것은?',
     'choices': ['예비연료(Reserve)', '기내식만', '면세품', 'Wi-Fi'], 'answer': 0,
     'explain': '항상 예비연료+대체공항 연료를 포함해야 안전합니다.'},
    {'id': 'fuel6', 'route': 'GMP-CJU', 'aircraft': 'B737-800', 'hours': 1.0, 'distance': 450,
     'question': '김포→제주 1시간. 비행 전 연료 검사는 누가 하나요?',
     'choices': ['기장·부기장·정비사 팀', '승객', '관광객', '아무도 안 함'], 'answer': 0,
     'explain': '연료는 조종사와 정비사가 함께 확인합니다.'},
]


def get_fuel_quiz(prog):
    extras = _meta(prog)
    _ensure_daily_reset(extras)
    _save_meta(prog, extras)
    today = today_str()
    done_today = extras.get('fuel_quiz_today', 0)
    if done_today >= 3:
        return None, '오늘 연료 퀴즈는 3개까지! 내일 다시 도전해요.'
    seed = f'fuel-{today}-{done_today}'
    rng = random.Random(seed)
    q = dict(rng.choice(FUEL_QUESTIONS))
    q.pop('answer', None)
    return q, None


def submit_fuel_quiz(prog, quiz_id, answer_idx):
    extras = _meta(prog)
    _ensure_daily_reset(extras)
    today = today_str()
    if extras.get('fuel_quiz_today', 0) >= 3:
        return False, '오늘은 3개까지 풀었어요!'
    q = next((x for x in FUEL_QUESTIONS if x['id'] == quiz_id), None)
    if not q:
        return False, '문제를 찾을 수 없어요.'
    correct = int(answer_idx) == q['answer']
    extras['fuel_quiz_today'] = extras.get('fuel_quiz_today', 0) + 1
    extras['fuel_quiz_history'] = (extras.get('fuel_quiz_history', []) + [{
        'date': today, 'id': quiz_id, 'correct': correct,
    }])[-30:]
    extras['stats']['fuel_quiz_total'] = extras['stats'].get('fuel_quiz_total', 0) + 1
    _save_meta(prog, extras)
    money = 200000 if correct else 50000
    award_money(prog, money, f'연료 퀴즈: {q["route"]}')
    if correct:
        award_virtual_hours(prog, 0.15, '연료 퀴즈 정답')
    check_crew_unlocks(prog)
    db.session.commit()
    return True, {
        'correct': correct,
        'message': f'{"✅" if correct else "❌"} {q["explain"]} {format_krw(money)}',
        'remaining_today': 3 - extras['fuel_quiz_today'],
    }


# ── 7. 정시률 챌린지 ──
def get_on_time_challenge(prog):
    extras = _meta(prog)
    wk = week_key()
    count = extras.get('on_time_log', {}).get(wk, 0)
    tiers = [
        {'need': 1, 'money': 200000, 'label': '정시 1회'},
        {'need': 3, 'money': 500000, 'label': '정시 3회'},
        {'need': 5, 'money': 1000000, 'label': '정시 5회'},
    ]
    claimed = set(extras.get('on_time_claimed', {}).get(wk, []))
    return {
        'week': wk,
        'count': count,
        'tiers': [{**t, 'claimed': t['need'] in claimed, 'reached': count >= t['need']} for t in tiers],
        'kid_tip': '로그북 특이사항에 「정시 운항」을 선택하면 카운트돼요!',
    }


def claim_on_time_tier(prog, need):
    extras = _meta(prog)
    wk = week_key()
    status = get_on_time_challenge(prog)
    tier = next((t for t in status['tiers'] if t['need'] == need), None)
    if not tier:
        return False, '보상을 찾을 수 없어요.'
    if tier['claimed']:
        return False, '이미 받았어요!'
    if not tier['reached']:
        return False, f'정시 비행이 {need}회 필요해요! (현재 {status["count"]}회)'
    claimed = extras.setdefault('on_time_claimed', {})
    wk_list = claimed.setdefault(wk, [])
    wk_list.append(need)
    extras['on_time_claimed'] = claimed
    _save_meta(prog, extras)
    award_money(prog, tier['money'], f'정시 챌린지 {need}회')
    check_crew_unlocks(prog)
    db.session.commit()
    return True, f'⏰ {tier["label"]} 달성! {format_krw(tier["money"])}'


# ── 8. 주간 수요 이벤트 ──
def _pick_weekly_demand():
    events = load_json('weekly_demand_events.json')
    wk = week_key()
    seed = hashlib.md5(f'demand-{wk}'.encode()).hexdigest()
    idx = int(seed, 16) % len(events)
    return dict(events[idx])


def get_weekly_demand(prog):
    extras = _meta(prog)
    wk = week_key()
    stored = extras.get('demand_events', {})
    if stored.get('week') != wk:
        evt = _pick_weekly_demand()
        stored = {'week': wk, 'event': evt, 'matches': 0}
        extras['demand_events'] = stored
        _save_meta(prog, extras)
        db.session.commit()
    evt = stored.get('event', {})
    claim_key = f'{wk}:{evt.get("id")}'
    claimed = claim_key in extras.get('demand_claims', [])
    return {
        'week': wk,
        'event': evt,
        'matches': stored.get('matches', 0),
        'claimed': claimed,
        'can_claim': stored.get('matches', 0) >= 1 and not claimed,
    }


def _demand_matches_entry(evt, entry):
    route = (entry.route or '').upper()
    notes = entry.notes or ''
    hours = entry.hours or 0
    if evt.get('require_ontime') and not _is_ontime(notes):
        return False
    if evt.get('min_hours') and hours < evt['min_hours']:
        return False
    if evt.get('max_hours') and hours > evt['max_hours']:
        return False
    if evt.get('require_intl') and not _is_intl_route(route):
        return False
    if evt.get('cargo') and hours < (evt.get('min_hours') or 2):
        return hours >= 2
    for pat in evt.get('route_match', []):
        if pat.upper() in route or pat in (entry.route or ''):
            return True
    if evt.get('cargo'):
        return hours >= evt.get('min_hours', 2)
    if not evt.get('route_match') and not evt.get('require_intl'):
        return evt.get('min_hours', 0) <= hours
    return False


def claim_weekly_demand(prog):
    status = get_weekly_demand(prog)
    if status['claimed']:
        return False, '이번 주 이벤트 보상은 이미 받았어요!'
    if not status['can_claim']:
        return False, '조건에 맞는 비행을 먼저 기록해주세요!'
    extras = _meta(prog)
    wk = week_key()
    evt = status['event']
    claim_key = f'{wk}:{evt["id"]}'
    claims = extras.get('demand_claims', [])
    claims.append(claim_key)
    extras['demand_claims'] = claims[-30:]
    extras['stats']['demand_claim_total'] = extras['stats'].get('demand_claim_total', 0) + 1
    _save_meta(prog, extras)
    award_money(prog, evt.get('bonus_money', 300000), f'주간 이벤트: {evt["name"]}')
    award_virtual_hours(prog, evt.get('bonus_hours', 0.2), f'주간 이벤트: {evt["name"]}')
    check_crew_unlocks(prog)
    db.session.commit()
    return True, f'{evt.get("icon", "🎉")} {evt["name"]} 보상! {format_krw(evt.get("bonus_money", 0))}'


def process_logbook_extras(prog, entry):
    """로그북 추가 시 호출 — 정시, 주간이벤트, 기장출근 진행"""
    extras = _meta(prog)
    wk = week_key()
    results = {}

    if _is_ontime(entry.notes):
        ot = extras.setdefault('on_time_log', {})
        ot[wk] = ot.get(wk, 0) + 1
        results['on_time'] = ot[wk]

    evt_data = extras.get('demand_events', {})
    if evt_data.get('week') == wk:
        evt = evt_data.get('event', {})
        if _demand_matches_entry(evt, entry):
            evt_data['matches'] = evt_data.get('matches', 0) + 1
            results['demand_match'] = evt.get('name')
            extras['demand_events'] = evt_data

    _save_meta(prog, extras)
    check_crew_unlocks(prog)
    db.session.commit()
    return results


def get_extras_summary(prog):
    extras = _meta(prog)
    _ensure_daily_reset(extras)
    _save_meta(prog, extras)
    return {
        'captain_duty': get_captain_duty(prog),
        'daily_airport': get_daily_airport(prog),
        'crew_cards': get_crew_cards(prog),
        'crew_unlocked_count': len(_meta(prog).get('crew_unlocked', [])),
        'journals': get_flight_journals(prog, 5),
        'codex': get_aircraft_codex(prog),
        'schedule': get_schedule_board(prog),
        'on_time': get_on_time_challenge(prog),
        'weekly_demand': get_weekly_demand(prog),
        'fuel_quiz_remaining': max(0, 3 - _meta(prog).get('fuel_quiz_today', 0)),
    }