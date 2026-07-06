"""10가지 확장 기능: 시즌패스, 특가, 콤보, 랭크, 항공사, 미션상점, 선물, 스트릭, 도전, 명세서"""
import hashlib
import secrets
from datetime import datetime, timedelta
from app.models import db, UserProgress, LogbookEntry, UserBadge
from app.services.gamification import load_json, get_total_hours, today_str
from app.services.economy import (
    award_money, get_owned_aircraft, get_shop_catalog, format_krw,
    STARTER_AIRCRAFT,
)

# 초등학생용 쉬운 용어
KID_TERMS = {
    'unlock': '받을 수 있어요',
    'unlocked': '준비 완료',
    'locked': '아직 연습 중',
    'owned': '내 비행기',
    'practice_hours': '연습 시간',
    'practice_left': '더 연습 필요',
    'practice_boost': '연습 도우미',
    'hangar': '비행기 창고',
    'buy': '사기',
    'free_get': '무료로 받기',
    'accelerate': '연습 시간 채우기',
}


def get_meta(prog):
    default = {
        'season_key': datetime.now().strftime('%Y-%m'),
        'season_xp': 0,
        'season_claimed': [],
        'daily_shop_date': '',
        'daily_shop_ids': [],
        'combo_claimed': [],
        'route_challenges_done': [],
        'mission_shop_bought': [],
        'logbook_streak': 0,
        'last_logbook_date': '',
        'logbook_streak_bonus_paid': [],
        'airline_name': '',
        'airline_logo': '✈️',
        'airline_founded': False,
        'gift_inbox': [],
    }
    meta = prog._json('pilot_meta', {})
    for k, v in default.items():
        meta.setdefault(k, v)
    return meta


def save_meta(prog, meta):
    prog.set_json('pilot_meta', meta)


def kid_status(status):
    """기체 상태에 쉬운 용어 라벨 추가"""
    if not status:
        return status
    s = dict(status)
    if s.get('owned'):
        s['kid_label'] = KID_TERMS['owned']
        s['kid_action'] = '주력 설정'
    elif s.get('ready') or s.get('unlocked'):
        s['kid_label'] = KID_TERMS['unlocked']
        s['kid_action'] = KID_TERMS['free_get'] if (s.get('discounted_price') or 0) == 0 else KID_TERMS['buy']
    else:
        s['kid_label'] = KID_TERMS['locked']
        s['kid_action'] = KID_TERMS['accelerate']
    s['practice_hours'] = s.get('unlock_hours', 0)
    s['practice_left'] = s.get('hours_remaining', 0)
    return s


# ── 4. 파일럿 랭크 ──
def get_pilot_rank(prog):
    ranks = load_json('pilot_ranks.json')
    entries = LogbookEntry.query.count()
    hours = get_total_hours(prog)
    current = ranks[0]
    for r in ranks:
        if hours >= r.get('min_hours', 0) and entries >= r.get('min_flights', 0):
            current = r
    next_rank = None
    for r in ranks:
        if r['id'] != current['id'] and (
            r.get('min_hours', 0) > hours or r.get('min_flights', 0) > entries
        ):
            next_rank = r
            break
    return {**current, 'next_rank': next_rank, 'current_hours': hours, 'current_flights': entries}


def salary_multiplier(prog):
    return get_pilot_rank(prog).get('salary_mult', 1.0)


# ── 1. 시즌 패스 ──
def get_season_config():
    key = datetime.now().strftime('%Y-%m')
    data = load_json('season_pass.json')
    if isinstance(data, dict):
        return key, data.get(key, data.get('default', {}))
    return key, {}


def add_season_xp(prog, event, amount=None):
    meta = get_meta(prog)
    key, season = get_season_config()
    if meta['season_key'] != key:
        meta['season_key'] = key
        meta['season_xp'] = 0
        meta['season_claimed'] = []
    rules = season.get('xp_rules', {})
    xp_add = amount if amount is not None else rules.get(event, 0)
    if xp_add <= 0:
        save_meta(prog, meta)
        return []
    meta['season_xp'] = (meta.get('season_xp') or 0) + xp_add
    rewards = _claim_season_levels(prog, meta, season)
    save_meta(prog, meta)
    db.session.commit()
    return rewards


def _claim_season_levels(prog, meta, season):
    claimed = []
    levels = season.get('levels', [])
    done = set(meta.get('season_claimed', []))
    xp = meta.get('season_xp', 0)
    for lv in levels:
        lid = lv['level']
        if lid in done or xp < lv.get('xp', 0):
            continue
        done.add(lid)
        if lv.get('reward_money'):
            award_money(prog, lv['reward_money'], f"시즌 Lv{lid}: {lv.get('label', '')}")
        if lv.get('reward_item'):
            inv = prog._json('inventory', [])
            if lv['reward_item'] not in inv:
                inv.append(lv['reward_item'])
                prog.set_json('inventory', inv)
        claimed.append(lv)
    meta['season_claimed'] = list(done)
    return claimed


def get_season_status(prog):
    key, season = get_season_config()
    meta = get_meta(prog)
    if meta['season_key'] != key:
        meta['season_xp'] = 0
        meta['season_claimed'] = []
        meta['season_key'] = key
        save_meta(prog, meta)
    levels = season.get('levels', [])
    xp = meta.get('season_xp', 0)
    current_lv = 0
    for lv in levels:
        if xp >= lv.get('xp', 0):
            current_lv = lv['level']
    next_lv = next((l for l in levels if l['level'] > current_lv), None)
    return {
        'season_key': key,
        'title': season.get('title', '시즌'),
        'icon': season.get('icon', '✈️'),
        'desc': season.get('desc', ''),
        'xp': xp,
        'current_level': current_lv,
        'next_level': next_lv,
        'levels': levels,
        'claimed': meta.get('season_claimed', []),
    }


# ── 2. 일일 특가 ──
def get_daily_shop(prog):
    meta = get_meta(prog)
    today = today_str()
    all_items = load_json('shop_items.json')
    purchasable = [i for i in all_items if i.get('category') != 'boost' and i.get('sellable', True)]
    if meta.get('daily_shop_date') != today or not meta.get('daily_shop_ids'):
        seed = hashlib.md5(f'daily-{today}'.encode()).hexdigest()
        h = int(seed, 16)
        picks = []
        used = set()
        for j in range(min(3, len(purchasable))):
            idx = (h + j * 13) % len(purchasable)
            while purchasable[idx]['id'] in used:
                idx = (idx + 1) % len(purchasable)
            used.add(purchasable[idx]['id'])
            picks.append(purchasable[idx]['id'])
        meta['daily_shop_date'] = today
        meta['daily_shop_ids'] = picks
        save_meta(prog, meta)
        db.session.commit()
    catalog = {i['id']: i for i in all_items}
    result = []
    for iid in meta.get('daily_shop_ids', []):
        if iid in catalog:
            item = dict(catalog[iid])
            item['daily_discount'] = 0.3
            item['sale_price'] = int(item['price'] * 0.7)
            item['kid_label'] = '오늘만 싸게!'
            result.append(item)
    return result


# ── 3. 기체 콤보 ──
def check_aircraft_combos(prog):
    owned = set(get_owned_aircraft(prog))
    meta = get_meta(prog)
    claimed = set(meta.get('combo_claimed', []))
    newly = []
    for combo in load_json('aircraft_combos.json'):
        cid = combo['id']
        if cid in claimed:
            continue
        need = set(combo.get('aircraft', []))
        if need.issubset(owned):
            claimed.add(cid)
            if combo.get('reward_money'):
                award_money(prog, combo['reward_money'], f"콤보 달성: {combo['name']}")
            if combo.get('reward_item'):
                inv = prog._json('inventory', [])
                if combo['reward_item'] not in inv:
                    inv.append(combo['reward_item'])
                    prog.set_json('inventory', inv)
            newly.append(combo)
    if newly:
        meta['combo_claimed'] = list(claimed)
        save_meta(prog, meta)
        db.session.commit()
    return newly


# ── 5. 항공사 창업 ──
def get_airline_info(prog):
    meta = get_meta(prog)
    owned_count = len(get_owned_aircraft(prog))
    can_found = owned_count >= 10
    return {
        'name': meta.get('airline_name') or '',
        'logo': meta.get('airline_logo') or '✈️',
        'founded': meta.get('airline_founded', False),
        'can_found': can_found,
        'owned_count': owned_count,
        'need_count': 10,
        'kid_hint': '비행기 10대 모으면 내 항공사를 만들 수 있어요!' if not can_found else '항공사 이름을 지어보세요!',
    }


def found_airline(prog, name, logo='✈️'):
    info = get_airline_info(prog)
    if not info['can_found']:
        return False, '비행기 10대가 필요해요!'
    name = (name or '').strip()[:30]
    if len(name) < 2:
        return False, '항공사 이름을 2글자 이상 지어주세요!'
    meta = get_meta(prog)
    if meta.get('airline_founded'):
        meta['airline_name'] = name
        meta['airline_logo'] = logo[:4]
        save_meta(prog, meta)
        db.session.commit()
        return True, f'{logo} {name} 이름이 바뀌었어요!'
    meta['airline_name'] = name
    meta['airline_logo'] = logo[:4]
    meta['airline_founded'] = True
    save_meta(prog, meta)
    award_money(prog, 5_000_000, f'항공사 창업 축하: {name}')
    inv = prog._json('inventory', [])
    if 'lv_rainbow' not in inv:
        inv.append('lv_rainbow')
        prog.set_json('inventory', inv)
    db.session.commit()
    return True, f'🎉 {logo} {name} 항공사가 탄생했어요! +₩5,000,000'


# ── 6. 미션 연계 상점 ──
def get_mission_shop_status(prog):
    today = today_str()
    dl = prog._json('daily_learning', {})
    if dl.get('date') != today:
        dl = {'date': today}
    missions = prog._json('completed_missions', {}).get(today, [])
    quiz_score = dl.get('quiz', {}).get('score', 0)
    quiz_done = dl.get('quiz', {}).get('done', False)
    sc_done = len(dl.get('scenarios', {}).get('completed', []))
    log_today = LogbookEntry.query.filter_by(date=today).count()
    flash_today = sum(
        1 for a in prog._json('activity_log', [])
        if a.get('date') == today and a.get('type') == 'flashcard'
    )
    meta = get_meta(prog)
    bought = set(meta.get('mission_shop_bought', []))
    result = []
    for ms in load_json('mission_shop.json'):
        req = ms.get('requirements', {})
        met = True
        checks = {}
        if req.get('quiz_score_min'):
            checks['quiz'] = quiz_done and quiz_score >= req['quiz_score_min']
            met = met and checks['quiz']
        if req.get('logbook_today'):
            checks['logbook'] = log_today >= req['logbook_today']
            met = met and checks['logbook']
        if req.get('flashcard_today'):
            checks['flashcard'] = flash_today >= req['flashcard_today']
            met = met and checks['flashcard']
        if req.get('mission_today'):
            checks['mission'] = len(missions) >= req['mission_today']
            met = met and checks['mission']
        if req.get('scenario_today'):
            checks['scenario'] = sc_done >= req['scenario_today']
            met = met and checks['scenario']
        result.append({
            **ms,
            'requirements_met': met,
            'already_bought': ms['id'] in bought,
            'checks': checks,
            'kid_label': '조건 달성! 특가로 살 수 있어요' if met else '오늘의 미션을 완료해보세요',
        })
    return result


def buy_mission_shop_item(prog, mission_id):
    from app.services.economy import spend_money
    status_list = get_mission_shop_status(prog)
    ms = next((m for m in status_list if m['id'] == mission_id), None)
    if not ms:
        return False, '상품을 찾을 수 없어요.'
    if ms['already_bought']:
        return False, '이미 샀어요!'
    if not ms['requirements_met']:
        return False, '아직 오늘의 조건을 다 못 채웠어요!'
    price = ms.get('discount_price', 0)
    ok, msg = spend_money(prog, price, f"특별 세트: {ms['name']}")
    if not ok:
        return False, msg
    item_id = ms.get('reward_item')
    if item_id:
        inv = prog._json('inventory', [])
        if item_id not in inv:
            inv.append(item_id)
            prog.set_json('inventory', inv)
    meta = get_meta(prog)
    bought = meta.get('mission_shop_bought', [])
    bought.append(mission_id)
    meta['mission_shop_bought'] = bought
    save_meta(prog, meta)
    db.session.commit()
    return True, f"{ms['name']} 구매 완료!"


# ── 7. 선물 코드 ──
def create_gift_code(prog, item_id, message='', from_name='파일럿'):
    catalog = get_shop_catalog()
    if item_id not in catalog:
        return False, '아이템이 없어요.'
    inv = prog._json('inventory', [])
    if item_id not in inv:
        return False, '가진 아이템만 선물할 수 있어요.'
    if catalog[item_id].get('category') == 'boost':
        return False, '연습 도우미는 선물할 수 없어요.'
    inv.remove(item_id)
    prog.set_json('inventory', inv)
    code = 'GIFT-' + secrets.token_hex(4).upper()
    meta = get_meta(prog)
    gifts = meta.get('gift_codes_created', [])
    gifts.append({
        'code': code, 'item_id': item_id, 'message': message[:100],
        'from_name': from_name[:20], 'created': today_str(), 'redeemed': False,
    })
    meta['gift_codes_created'] = gifts[-50:]
    meta.setdefault('gift_pool', {})[code] = {
        'item_id': item_id, 'message': message[:100],
        'from_name': from_name[:20],
    }
    save_meta(prog, meta)
    db.session.commit()
    return True, {'code': code, 'item_name': catalog[item_id]['name']}


def redeem_gift_code(prog, code):
    code = (code or '').strip().upper()
    meta = get_meta(prog)
    pool = meta.get('gift_pool', {})
    if code not in pool:
        return False, '선물 코드가 없거나 이미 사용했어요.'
    gift = pool.pop(code)
    inv = prog._json('inventory', [])
    item_id = gift['item_id']
    if item_id not in inv:
        inv.append(item_id)
        prog.set_json('inventory', inv)
    inbox = meta.get('gift_inbox', [])
    inbox.append({**gift, 'code': code, 'received': today_str()})
    meta['gift_inbox'] = inbox[-20:]
    for g in meta.get('gift_codes_created', []):
        if g.get('code') == code:
            g['redeemed'] = True
    save_meta(prog, meta)
    db.session.commit()
    catalog = get_shop_catalog()
    name = catalog.get(item_id, {}).get('name', item_id)
    return True, f'🎁 선물 도착! {name}'


# ── 8. 비행 스트릭 ──
def update_logbook_streak(prog, flight_date=None):
    today = flight_date or today_str()
    meta = get_meta(prog)
    last = meta.get('last_logbook_date', '')
    yesterday = (datetime.strptime(today, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    if last == today:
        return []
    if last == yesterday:
        meta['logbook_streak'] = (meta.get('logbook_streak') or 0) + 1
    else:
        meta['logbook_streak'] = 1
    meta['last_logbook_date'] = today
    rewards = []
    streak = meta['logbook_streak']
    paid = set(meta.get('logbook_streak_bonus_paid', []))
    bonuses = {3: 500_000, 7: 2_000_000, 14: 5_000_000, 30: 15_000_000}
    for days, amount in bonuses.items():
        key = f'streak_{days}'
        if streak >= days and key not in paid:
            paid.add(key)
            award_money(prog, amount, f'연속 비행 {days}일 보너스!')
            rewards.append({'days': days, 'amount': amount})
    meta['logbook_streak_bonus_paid'] = list(paid)
    save_meta(prog, meta)
    db.session.commit()
    return rewards


# ── 9. 노선 도전 ──
def check_route_challenges(prog, entry=None):
    meta = get_meta(prog)
    done = set(meta.get('route_challenges_done', []))
    entries = [entry] if entry else LogbookEntry.query.all()
    newly = []
    for ch in load_json('route_challenges.json'):
        cid = ch['id']
        if cid in done:
            continue
        matched = False
        if ch.get('min_hours'):
            for e in entries:
                if e.hours >= ch['min_hours']:
                    matched = True
                    break
        elif ch.get('route_match'):
            for e in entries:
                route = (e.route or '').upper().replace(' ', '').replace('→', '-').replace('—', '-')
                for pattern in ch['route_match']:
                    p = pattern.upper()
                    if p in route or route == p:
                        matched = True
                        break
                if matched:
                    break
        if matched:
            done.add(cid)
            if ch.get('reward_money'):
                award_money(prog, ch['reward_money'], f"노선 도전: {ch['name']}")
            if ch.get('reward_item'):
                inv = prog._json('inventory', [])
                if ch['reward_item'] not in inv:
                    inv.append(ch['reward_item'])
                    prog.set_json('inventory', inv)
            newly.append(ch)
    if newly:
        meta['route_challenges_done'] = list(done)
        save_meta(prog, meta)
        db.session.commit()
    return newly


def get_route_challenge_status(prog):
    meta = get_meta(prog)
    done = set(meta.get('route_challenges_done', []))
    return [{**ch, 'completed': ch['id'] in done} for ch in load_json('route_challenges.json')]


# ── 10. 급여 명세서 ──
def get_payslip(prog, month=None):
    month = month or datetime.now().strftime('%Y-%m')
    txs = prog._json('transaction_log', [])
    month_txs = [t for t in txs if (t.get('date') or '')[:7] == month]
    income = sum(t['amount'] for t in month_txs if t.get('amount', 0) > 0)
    expense = sum(-t['amount'] for t in month_txs if t.get('amount', 0) < 0)
    by_type = {}
    for t in month_txs:
        tp = t.get('type', 'other')
        by_type[tp] = by_type.get(tp, 0) + t.get('amount', 0)
    rank = get_pilot_rank(prog)
    airline = get_airline_info(prog)
    entries = LogbookEntry.query.filter(LogbookEntry.date.like(f'{month}%')).count()
    return {
        'month': month,
        'month_label': f'{month[:4]}년 {int(month[5:])}월',
        'transactions': month_txs,
        'total_income': income,
        'total_expense': expense,
        'net': income - expense,
        'by_type': by_type,
        'flight_count': entries,
        'rank': rank,
        'airline': airline,
        'balance': prog.wallet_balance or 0,
        'kid_title': '나의 파일럿 월급 명세서',
    }


def process_logbook_extras(prog, entry):
    """로그북 추가 시 모든 확장 기능 트리거"""
    results = {
        'season': add_season_xp(prog, 'logbook_flight'),
        'combos': check_aircraft_combos(prog),
        'routes': check_route_challenges(prog, entry),
        'streak': update_logbook_streak(prog, entry.date),
    }
    mult = salary_multiplier(prog)
    if mult > 1.0:
        bonus = int(200_000 * (mult - 1))
        if bonus > 0:
            award_money(prog, bonus, f'{get_pilot_rank(prog)["name"]} 등급 보너스')
            results['rank_bonus'] = bonus
    db.session.commit()
    return results


def get_features_summary(prog):
    return {
        'kid_terms': KID_TERMS,
        'rank': get_pilot_rank(prog),
        'season': get_season_status(prog),
        'daily_shop': get_daily_shop(prog),
        'airline': get_airline_info(prog),
        'mission_shop': get_mission_shop_status(prog),
        'route_challenges': get_route_challenge_status(prog),
        'logbook_streak': get_meta(prog).get('logbook_streak', 0),
        'gift_inbox': get_meta(prog).get('gift_inbox', [])[-5:],
    }