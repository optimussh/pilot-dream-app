"""항공사 3층: 주식회사 조각 · NPC 투자 · 하늘 친구 시장 · 이사회

중독 방지:
- 시세/배당/이사회 = 주 단위
- 친구 시장 하루 최대 2회
- 산 주에는 같은 조각 못 팔기 (단타 무의미)
- 7일 보유 시 소액 인내 보너스
- 빚·레버리지·실시간 차트 없음
"""
import hashlib
from datetime import datetime, timedelta

from app.models import db
from app.services.gamification import load_json, week_key, today_str
from app.services.economy import award_money, spend_money, format_krw
from app.services.pilot_features import get_airline_info

TOTAL_SHARES = 100
ISSUE_MIN_LEVEL = 2
MARKET_DAILY_LIMIT = 2
HOLD_BONUS_DAYS = 7
HOLD_BONUS_MONEY = 40_000
WEEKLY_DIVIDEND_POOL_BASE = 180_000  # 내 회사 배당 풀 (주당 총액 기준 스케일)


def _ops_mod(prog):
    from app.services.airline_ops import _ops, _save_ops
    return _ops(prog), _save_ops


def ensure_invest(ops):
    inv = ops.setdefault('invest', {})
    defaults = {
        'shares_issued': False,
        'my_shares': 0,
        'total_shares': TOTAL_SHARES,
        'npc': {},  # npc_id -> shares
        'portfolio': {},  # firm_id -> {qty, buy_date, cost}
        'market_week': '',
        'prices': {},
        'price_why': {},
        'actions_date': '',
        'actions_today': 0,
        'dividend_week': '',
        'board_week': '',
        'board_card_id': '',
        'board_done': False,
        'board_last': None,
        'hold_bonus_log': [],
    }
    for k, v in defaults.items():
        if k not in inv:
            inv[k] = list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)
    return inv


def _seed_int(key, lo, hi):
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + h % (hi - lo + 1)


def _week_event_tags():
    """주간 수요 이벤트 태그 — 시세 이야기용"""
    events = load_json('weekly_demand_events.json') or []
    if not isinstance(events, list) or not events:
        return [], None
    wk = week_key()
    idx = _seed_int(f'invest-event-{wk}', 0, len(events) - 1)
    ev = events[idx]
    tags = list(ev.get('route_match') or [])
    if ev.get('cargo'):
        tags.append('화물')
    if ev.get('require_intl'):
        tags.append('국제')
    name = ev.get('name', '')
    return tags, {'id': ev.get('id'), 'name': name, 'icon': ev.get('icon', '📰'), 'desc': ev.get('desc', '')}


def _refresh_market_prices(inv):
    wk = week_key()
    if inv.get('market_week') == wk and inv.get('prices'):
        return
    firms = load_json('airline_market_firms.json') or []
    tags, event = _week_event_tags()
    tags_l = [t.lower() if isinstance(t, str) else str(t) for t in tags]
    prices = {}
    why = {}
    for f in firms:
        base = int(f.get('base_price', 80000))
        jitter = _seed_int(f"{wk}-{f['id']}-j", -8, 12)
        mult = 1.0 + jitter / 100.0
        hit = False
        for t in f.get('tags', []):
            if any(t in tg or tg in t for tg in tags if isinstance(tg, str)):
                hit = True
                break
            if t in tags:
                hit = True
                break
        if hit:
            mult *= 1.12
            why[f['id']] = f"이번 주 뉴스({event['name'] if event else '수요'})와 잘 맞아요!"
        else:
            why[f['id']] = f.get('kid', '차분한 한 주예요.')
        # 유가 비슷한 패널티: 장거리는 가끔 약세
        if f.get('sector') == '장거리' and _seed_int(f'{wk}-oil', 0, 3) == 0:
            mult *= 0.94
            why[f['id']] = '연료 생각이 나서 조용해요. (가상의 이야기)'
        prices[f['id']] = max(30_000, int(base * mult))
    inv['market_week'] = wk
    inv['prices'] = prices
    inv['price_why'] = why
    inv['week_event'] = event


def _board_card_for_week():
    cards = load_json('airline_board_cards.json') or []
    if not cards:
        return None
    wk = week_key()
    idx = _seed_int(f'board-{wk}', 0, len(cards) - 1)
    return cards[idx]


def can_issue_shares(ops):
    level = int(ops.get('level', 1) or 1)
    routes = len([r for r in ops.get('routes', []) if r.get('active')])
    return level >= ISSUE_MIN_LEVEL or routes >= 1


def issue_shares(prog):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    if inv.get('shares_issued'):
        return False, '이미 회사 조각을 만들었어요!'
    if not can_issue_shares(ops):
        return False, f'항공사 Lv.{ISSUE_MIN_LEVEL} 이상이거나 노선이 있으면 조각을 만들 수 있어요.'
    inv['shares_issued'] = True
    inv['my_shares'] = TOTAL_SHARES
    inv['total_shares'] = TOTAL_SHARES
    inv['npc'] = {}
    _save(prog, ops)
    db.session.commit()
    return True, f'🎉 주식회사 조각 {TOTAL_SHARES}개 발행! 지금은 전부 내 몫(100%)이에요.'


def accept_npc_investor(prog, npc_id, accept=True):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    if not inv.get('shares_issued'):
        return False, '먼저 회사 조각을 발행하세요!'
    npcs = {n['id']: n for n in (load_json('airline_npc_investors.json') or [])}
    npc = npcs.get(npc_id)
    if not npc:
        return False, '투자자를 찾을 수 없어요.'
    if inv.get('npc', {}).get(npc_id):
        return False, '이미 이 친구와 제휴했어요.'
    if not accept:
        inv.setdefault('npc_declined', {})[npc_id] = week_key()
        _save(prog, ops)
        db.session.commit()
        return True, '괜찮아요. 거절해도 손해 없어요. 언제든 다시 생각할 수 있어요.'
    need = int(npc.get('shares', 5))
    if inv['my_shares'] < need:
        return False, '남은 내 조각이 부족해요.'
    min_lv = int(npc.get('min_level', 2))
    if int(ops.get('level', 1)) < min_lv:
        return False, f'항공사 Lv.{min_lv} 이상이면 만날 수 있어요.'
    inv['my_shares'] -= need
    inv.setdefault('npc', {})[npc_id] = need
    _save(prog, ops)
    db.session.commit()
    pct = round(need / TOTAL_SHARES * 100)
    return True, f'{npc["emoji"]} {npc["name"]}이(가) 조각 {need}개({pct}%)를 가져갔어요. 이제 함께 키워요!'


def _reset_daily_actions(inv):
    today = today_str()
    if inv.get('actions_date') != today:
        inv['actions_date'] = today
        inv['actions_today'] = 0


def market_trade(prog, firm_id, action):
    """action: buy | sell — 하루 2회, 산 주 매도 불가"""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    if action not in ('buy', 'sell'):
        return False, '사기 또는 팔기만 할 수 있어요.'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    _refresh_market_prices(inv)
    _reset_daily_actions(inv)
    if inv['actions_today'] >= MARKET_DAILY_LIMIT:
        return False, f'오늘은 친구 시장 {MARKET_DAILY_LIMIT}번까지예요. 내일 또 만나요!'
    firms = {f['id']: f for f in (load_json('airline_market_firms.json') or [])}
    firm = firms.get(firm_id)
    if not firm:
        return False, '회사를 찾을 수 없어요.'
    price = int(inv['prices'].get(firm_id, firm.get('base_price', 80000)))
    port = inv.setdefault('portfolio', {})
    pos = port.get(firm_id) or {'qty': 0, 'buy_date': '', 'cost': 0}

    if action == 'buy':
        ok, err = spend_money(prog, price, f'친구 시장 매수: {firm["name"]}', 'invest')
        if not ok:
            return False, err
        if pos['qty'] <= 0:
            pos['buy_date'] = today_str()
            pos['cost'] = price
        else:
            # 추가 매수: 평균 단가 단순화
            pos['cost'] = int((pos['cost'] * pos['qty'] + price) / (pos['qty'] + 1))
        pos['qty'] = pos['qty'] + 1
        port[firm_id] = pos
        inv['actions_today'] += 1
        _save(prog, ops)
        db.session.commit()
        left = MARKET_DAILY_LIMIT - inv['actions_today']
        return True, f'{firm["emoji"]} {firm["name"]} 조각 1개 샀어요! ({format_krw(price)}) · 오늘 남은 횟수 {left}'

    # sell
    if pos.get('qty', 0) <= 0:
        return False, '가진 조각이 없어요.'
    buy_date = pos.get('buy_date') or ''
    if buy_date:
        try:
            d0 = datetime.strptime(buy_date[:10], '%Y-%m-%d')
            # 산 당일 매도 금지
            if d0.strftime('%Y-%m-%d') == today_str():
                return False, '오늘 산 조각은 오늘 팔 수 없어요. 기다려 보는 연습!'
            # 같은 주 매도도 막아서 단타 제거 (주간 리듬)
            if d0.strftime('%Y-W%W') == week_key():
                return False, '이번 주에 산 조각은 다음 주부터 팔 수 있어요.'
        except ValueError:
            pass
    pos['qty'] -= 1
    award_money(prog, price, f'친구 시장 매도: {firm["name"]}', 'invest')
    if pos['qty'] <= 0:
        port.pop(firm_id, None)
    else:
        port[firm_id] = pos
    inv['actions_today'] += 1
    # 7일 보유 보너스 (팔 때 한 번)
    bonus_msg = ''
    if buy_date:
        try:
            d0 = datetime.strptime(buy_date[:10], '%Y-%m-%d')
            days = (datetime.now() - d0).days
            key = f'{firm_id}:{buy_date}'
            if days >= HOLD_BONUS_DAYS and key not in inv.get('hold_bonus_log', []):
                award_money(prog, HOLD_BONUS_MONEY, f'인내 보너스: {firm["name"]}', 'invest')
                inv.setdefault('hold_bonus_log', []).append(key)
                inv['hold_bonus_log'] = inv['hold_bonus_log'][-40:]
                bonus_msg = f' · ⏳ {HOLD_BONUS_DAYS}일 인내 보너스 +{format_krw(HOLD_BONUS_MONEY)}!'
        except ValueError:
            pass
    _save(prog, ops)
    db.session.commit()
    left = MARKET_DAILY_LIMIT - inv['actions_today']
    return True, f'{firm["emoji"]} 조각 1개 팔았어요! ({format_krw(price)}){bonus_msg} · 오늘 남은 횟수 {left}'


def claim_weekly_dividends(prog):
    """내 회사 NPC 배당 + 포트폴리오 소액 배당 — 주 1회"""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!', 0
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    wk = week_key()
    if inv.get('dividend_week') == wk:
        return False, '이번 주 배당은 이미 받았어요!', 0
    total = 0
    parts = []
    # 내 회사: 내 지분 비율 × 풀
    if inv.get('shares_issued'):
        my_pct = inv.get('my_shares', 0) / max(1, inv.get('total_shares', TOTAL_SHARES))
        # 회사 레벨·노선에 따라 풀 소폭 증가
        pool = WEEKLY_DIVIDEND_POOL_BASE + int(ops.get('level', 1)) * 20_000
        if inv.get('board_last', {}).get('effect') == 'dividend_boost' and inv.get('board_week') == wk:
            pool = int(pool * 1.15)
        mine = int(pool * my_pct)
        if mine > 0:
            award_money(prog, mine, f'내 회사 배당 ({wk})', 'dividend')
            total += mine
            parts.append(f'내 회사 {format_krw(mine)}')
    # 친구 시장 보유분: 가격의 1.5% 수준 주 1회 (소액 교육용)
    _refresh_market_prices(inv)
    for fid, pos in list(inv.get('portfolio', {}).items()):
        qty = int(pos.get('qty', 0) or 0)
        if qty <= 0:
            continue
        price = int(inv['prices'].get(fid, 80000))
        div = max(5_000, int(price * 0.015) * qty)
        award_money(prog, div, f'친구 시장 배당 ({fid})', 'dividend')
        total += div
    inv['dividend_week'] = wk
    _save(prog, ops)
    db.session.commit()
    if total <= 0:
        return False, '받을 배당이 없어요. 조각을 발행하거나 친구 시장 조각을 가져보세요!', 0
    msg = f'💎 이번 주 배당 +{format_krw(total)}!'
    if parts:
        msg += ' (' + ', '.join(parts) + ')'
    return True, msg, total


def answer_board(prog, choice_id):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    wk = week_key()
    card = _board_card_for_week()
    if not card:
        return False, '이사회 카드가 없어요.'
    if inv.get('board_week') == wk and inv.get('board_done'):
        return False, '이번 주 이사회는 끝났어요. 다음 주에 만나요!'
    choice = None
    for ch in card.get('choices', []):
        if ch.get('id') == choice_id:
            choice = ch
            break
    if not choice:
        return False, '선택지를 골라주세요.'
    effect = choice.get('effect', 'none')
    msg = f'{card.get("emoji", "📋")} 이사회 결정: {choice.get("label")}'
    if effect == 'reputation':
        ops['reputation'] = min(100, int(ops.get('reputation', 50)) + 2)
        msg += ' · 평판 +2'
    elif effect == 'reinvest_soft':
        ops['reinvest_boost_week'] = wk
        ops['reinvest_boost_pct'] = max(int(ops.get('reinvest_boost_pct') or 0), 4)
        msg += ' · 성장 보너스(작음)'
    elif effect == 'vault_soft':
        bal = prog.wallet_balance or 0
        move = min(80_000, bal)
        if move > 0:
            ok, _ = spend_money(prog, move, f'이사회 저축 ({wk})', 'company_vault')
            if ok:
                ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + move
                msg += f' · 금고 +{format_krw(move)}'
    elif effect == 'staff_soft':
        cost = min(60_000, prog.wallet_balance or 0)
        if cost >= 20_000:
            ok, _ = spend_money(prog, cost, f'이사회 직원 배려 ({wk})', 'salary')
            if ok:
                ops['reputation'] = min(100, int(ops.get('reputation', 50)) + 2)
                ops['staff_bonus_week'] = wk
                msg += f' · 직원 배려 · 평판 +2'
    elif effect == 'xp':
        ops['xp'] = int(ops.get('xp', 0) or 0) + 5
        msg += ' · 회사 경험치 +5'
    elif effect == 'patience':
        award_money(prog, 25_000, '인내 학습 보너스', 'invest')
        msg += f' · 인내 학습 +{format_krw(25000)}'
    elif effect == 'learn':
        award_money(prog, 30_000, '분산 개념 학습', 'invest')
        msg += f' · 배움 보너스 +{format_krw(30000)}'
    elif effect == 'dividend_boost':
        msg += ' · 이번 주 배당이 조금 커질 수 있어요'
    inv['board_week'] = wk
    inv['board_card_id'] = card['id']
    inv['board_done'] = True
    inv['board_last'] = {
        'card_id': card['id'],
        'choice_id': choice_id,
        'label': choice.get('label'),
        'effect': effect,
        'week': wk,
    }
    _save(prog, ops)
    db.session.commit()
    return True, msg


def build_invest_panel(prog, ops=None):
    from app.services.airline_ops import _ops
    info = get_airline_info(prog)
    if not info.get('founded'):
        return None
    ops = ops or _ops(prog)
    inv = ensure_invest(ops)
    _refresh_market_prices(inv)
    _reset_daily_actions(inv)
    level = int(ops.get('level', 1) or 1)
    issued = bool(inv.get('shares_issued'))
    my = int(inv.get('my_shares', 0) or 0)
    total = int(inv.get('total_shares', TOTAL_SHARES) or TOTAL_SHARES)
    my_pct = round(my / max(1, total) * 100, 1)

    npcs_data = load_json('airline_npc_investors.json') or []
    npc_rows = []
    for n in npcs_data:
        taken = inv.get('npc', {}).get(n['id'])
        declined = inv.get('npc_declined', {}).get(n['id'])
        npc_rows.append({
            **n,
            'joined': bool(taken),
            'held_shares': taken or 0,
            'declined': bool(declined),
            'eligible': level >= int(n.get('min_level', 2)),
            'available': issued and not taken and not declined and level >= int(n.get('min_level', 2)),
        })

    firms = load_json('airline_market_firms.json') or []
    port = inv.get('portfolio', {})
    market = []
    for f in firms:
        fid = f['id']
        pos = port.get(fid) or {}
        qty = int(pos.get('qty', 0) or 0)
        price = int(inv['prices'].get(fid, f.get('base_price', 80000)))
        buy_date = pos.get('buy_date', '')
        hold_days = 0
        can_sell = False
        if qty > 0 and buy_date:
            try:
                d0 = datetime.strptime(buy_date[:10], '%Y-%m-%d')
                hold_days = (datetime.now() - d0).days
                can_sell = d0.strftime('%Y-%m-%d') != today_str() and d0.strftime('%Y-W%W') != week_key()
            except ValueError:
                can_sell = True
        market.append({
            **f,
            'price': price,
            'price_formatted': format_krw(price),
            'why': inv.get('price_why', {}).get(fid, f.get('kid', '')),
            'owned': qty,
            'hold_days': hold_days,
            'can_sell': can_sell and qty > 0,
            'near_hold_bonus': qty > 0 and hold_days < HOLD_BONUS_DAYS,
            'hold_bonus_days': HOLD_BONUS_DAYS,
        })

    board = _board_card_for_week()
    board_ui = None
    if board:
        board_ui = {
            **board,
            'done': inv.get('board_week') == week_key() and inv.get('board_done'),
            'last': inv.get('board_last'),
        }

    return {
        'shares': {
            'issued': issued,
            'can_issue': (not issued) and can_issue_shares(ops),
            'my_shares': my,
            'total': total,
            'my_pct': my_pct,
            'issue_hint': f'Lv.{ISSUE_MIN_LEVEL}+ 또는 노선 1개 이상이면 조각 발행 가능',
            'kid': '회사 조각 = 회사를 나누어 갖는 몫. 지금은 교육용 놀이예요.',
        },
        'npc_investors': npc_rows,
        'market': market,
        'market_meta': {
            'actions_today': inv.get('actions_today', 0),
            'actions_left': max(0, MARKET_DAILY_LIMIT - inv.get('actions_today', 0)),
            'daily_limit': MARKET_DAILY_LIMIT,
            'week_event': inv.get('week_event'),
            'kid_rules': [
                f'하루 최대 {MARKET_DAILY_LIMIT}번만 사고/팔 수 있어요',
                '산 주에는 팔 수 없어요 (단타 없음)',
                f'{HOLD_BONUS_DAYS}일 이상 가지면 인내 보너스!',
                '시세는 일주일에 한 번만 바뀌어요',
            ],
        },
        'dividend': {
            'claimed_this_week': inv.get('dividend_week') == week_key(),
            'available': inv.get('dividend_week') != week_key() and (
                issued or any(int((p or {}).get('qty', 0) or 0) > 0 for p in port.values())
            ),
        },
        'board': board_ui,
        'terms': [
            {'word': '회사 조각', 'meaning': '주식처럼 회사를 나누는 몫'},
            {'word': '조각 주인', 'meaning': '주주 — 조각을 가진 사람'},
            {'word': '배당', 'meaning': '회사가 잘되면 돌아오는 용돈'},
            {'word': '투자', 'meaning': '나중에 도움이 될 수 있게 지금 넣는 돈'},
            {'word': '리스크', 'meaning': '날씨처럼 결과가 흔들릴 수 있음'},
        ],
        'kid_summary': (
            '기장·CEO에 이어, 함께 키우는 회사와 천천히 투자하는 연습을 해요. '
            '매일 확인하지 않아도 괜찮아요 — 일주일에 한 번이면 충분!'
        ),
    }
