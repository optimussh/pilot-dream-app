"""항공사 3층: 주식회사 조각 · NPC 투자 · 하늘 친구 시장 · 이사회

중독 방지:
- 시세/배당/이사회 = 주 단위
- 친구 시장 하루 최대 7회
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

TOTAL_SHARES = 100  # 최초 발행 단위
ISSUE_MIN_LEVEL = 2
ISSUE_BATCH = 50  # 추가 발행 묶음
MAX_TOTAL_SHARES = 500
MARKET_DAILY_LIMIT = 7
HOLD_BONUS_DAYS = 7
HOLD_BONUS_MONEY = 40_000
WEEKLY_DIVIDEND_POOL_BASE = 180_000  # 폴백 최소 배당 풀
DIVIDEND_OF_WEEKLY_NET = 0.22  # 주간 순이익의 약 22%를 배당 풀로
VALUATION_MULT_MIN = 10.0
VALUATION_MULT_MAX = 20.0
# 매각 시 내재가치 대비 프리미엄(교육: 성장주 프리미엄)
SALE_PREMIUM_MIN = 1.05
SALE_PREMIUM_MAX = 1.35
# 자사주 매입 시 할증(협상 할인 — 교육용)
BUYBACK_DISCOUNT = 0.92
BUYBACK_DAILY_LIMIT = 1
BUYBACK_MAX_CASH_RATIO = 0.25  # 지갑의25% 초과 매입 불가


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


def estimate_company_valuation(prog, ops=None, inv=None):
    """회사 가치 = (예상 주간 수입 기준) × 10~20배 + 일일 시세 변동.

    교육: PER(배수) 개념 — 이익에 배수를 곱해 회사 값을 매긴다.
    배당 정책이 공격적이면 배수↓ (배당 vs 성장 트레이드오프).
    """
    from app.services.airline_ops import estimate_weekly_revenue, _ops as ops_fn
    ops = ops or ops_fn(prog)
    if inv is None:
        inv = ensure_invest(ops)
    preview = estimate_weekly_revenue(prog, ops) or {}
    weekly_gross = max(0, int(preview.get('gross', 0) or 0))
    weekly_net = int(preview.get('net', 0) or 0)
    level = int(ops.get('level', 1) or 1)
    rep = max(0, min(100, int(ops.get('reputation', 50) or 50)))
    total = max(1, int(inv.get('total_shares') or TOTAL_SHARES))

    base = max(weekly_net, int(weekly_gross * 0.3), 80_000)
    mult = 10.0 + min(8.0, max(0, level - 1) * 0.55) + (rep / 100.0) * 2.0
    # 배당 vs 성장: dividend_policy 0=성장(배수↑) 1=균형 2=고배당(배수↓)
    policy = int(inv.get('dividend_policy') or 1)
    if policy == 0:
        mult += 1.2
        policy_kid = '성장 중시 → PER 배수↑'
    elif policy == 2:
        mult -= 1.5
        policy_kid = '고배당 중시 → PER 배수↓ (이익을 지금 나눠 줌)'
    else:
        policy_kid = '균형 배당 · 성장'
    mult = max(VALUATION_MULT_MIN, min(VALUATION_MULT_MAX, mult))
    fair_value = int(base * mult)

    day = today_str()
    jitter_pct = _seed_int(f'co-val-{day}-{level}', -5, 8)
    # 공시 보너스: 순익이 플러스면 시세 가산
    if weekly_net > 0:
        jitter_pct += _seed_int(f'co-news-{day}', 0, 3)
    market_value = max(fair_value // 2, int(fair_value * (100 + jitter_pct) / 100))
    share_fair = max(1, fair_value // total)
    share_market = max(1, market_value // total)

    return {
        'valuation': market_value,
        'fair_value': fair_value,
        'valuation_formatted': format_krw(market_value),
        'fair_value_formatted': format_krw(fair_value),
        'multiple': round(mult, 1),
        'multiple_min': VALUATION_MULT_MIN,
        'multiple_max': VALUATION_MULT_MAX,
        'base_earnings': base,
        'base_formatted': format_krw(base),
        'weekly_gross': weekly_gross,
        'weekly_net': weekly_net,
        'weekly_gross_formatted': format_krw(weekly_gross),
        'weekly_net_formatted': format_krw(weekly_net),
        'share_price': share_market,
        'share_price_fair': share_fair,
        'share_price_formatted': format_krw(share_market),
        'share_price_fair_formatted': format_krw(share_fair),
        'day_change_pct': jitter_pct,
        'total_shares': total,
        'dividend_policy': policy,
        'policy_kid': policy_kid,
        'kid': (
            f'공정가치 ≈ 주간 이익 기준({format_krw(base)}) × PER {round(mult, 1)}배 = {format_krw(fair_value)}. '
            f'오늘 시세 {jitter_pct:+d}% → {format_krw(market_value)}. '
            f'주당 {format_krw(share_market)} (총 {total}주). {policy_kid}'
        ),
    }


def _sale_premium_mult(ops):
    """성장·평판이 좋으면 매각 프리미엄 ↑ (교육: 프리미엄 밸류에이션)."""
    level = int(ops.get('level', 1) or 1)
    rep = max(0, min(100, int(ops.get('reputation', 50) or 50)))
    t = min(1.0, (level - 1) / 15.0) * 0.6 + (rep / 100.0) * 0.4
    return SALE_PREMIUM_MIN + (SALE_PREMIUM_MAX - SALE_PREMIUM_MIN) * t


def _sale_proceeds_for_shares(valuation, shares, total_shares=None, premium=1.0):
    total = max(1, int(total_shares or TOTAL_SHARES))
    shares = max(0, int(shares or 0))
    intrinsic = valuation * shares / total
    return max(0, int(intrinsic * float(premium or 1.0)))


def _estimate_weekly_company_dividend_pool(prog, ops, inv):
    """내 회사 주간 배당 풀 — 운영 이익 연동 + 배당 정책."""
    from app.services.airline_ops import estimate_weekly_revenue
    preview = estimate_weekly_revenue(prog, ops) or {}
    weekly_net = int(preview.get('net', 0) or 0)
    weekly_gross = max(0, int(preview.get('gross', 0) or 0))
    policy = int(inv.get('dividend_policy') or 1)
    # 0 성장: 배당 적게, 2 고배당: 많이
    rate = {0: 0.12, 1: DIVIDEND_OF_WEEKLY_NET, 2: 0.38}.get(policy, DIVIDEND_OF_WEEKLY_NET)
    pool = max(
        int(max(0, weekly_net) * rate),
        int(weekly_gross * (0.04 if policy == 0 else 0.08 if policy == 1 else 0.12)),
        WEEKLY_DIVIDEND_POOL_BASE + int(ops.get('level', 1)) * 20_000,
    )
    if inv.get('board_last', {}).get('effect') == 'dividend_boost' and inv.get('board_week') == week_key():
        pool = int(pool * 1.15)
    return pool, weekly_net, weekly_gross


def _backfill_npc_sale_proceeds(prog, ops, inv):
    """예전에 지분만 넘기고 매각대금이 없던 기록을 한 번 보전 지급."""
    if inv.get('sale_proceeds_backfill_v1'):
        return 0
    npc_map = inv.get('npc') or {}
    paid_log = inv.setdefault('npc_sale_proceeds', {})
    if not npc_map:
        inv['sale_proceeds_backfill_v1'] = True
        return 0
    val = estimate_company_valuation(prog, ops)
    total_paid = 0
    for npc_id, shares in list(npc_map.items()):
        if paid_log.get(npc_id):
            continue
        total_s = max(1, int(inv.get('total_shares') or TOTAL_SHARES))
        proceeds = _sale_proceeds_for_shares(val['valuation'], shares, total_s, premium=1.0)
        if proceeds <= 0:
            paid_log[npc_id] = {'shares': int(shares), 'proceeds': 0, 'backfill': True}
            continue
        award_money(prog, proceeds, f'지분 매각 대금 보전 ({npc_id})', 'invest')
        paid_log[npc_id] = {
            'shares': int(shares),
            'proceeds': proceeds,
            'backfill': True,
            'valuation': val['valuation'],
            'multiple': val['multiple'],
        }
        total_paid += proceeds
    inv['sale_proceeds_backfill_v1'] = True
    return total_paid


def issue_shares(prog):
    """최초 발행 또는 추가 발행(유상증자 맛보기)."""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    if not can_issue_shares(ops):
        return False, f'항공사 Lv.{ISSUE_MIN_LEVEL} 이상이거나 노선이 있으면 조각을 만들 수 있어요.'

    # 최초 발행
    if not inv.get('shares_issued'):
        inv['shares_issued'] = True
        inv['my_shares'] = TOTAL_SHARES
        inv['total_shares'] = TOTAL_SHARES
        inv['npc'] = {}
        _save(prog, ops)
        db.session.commit()
        return True, f'🎉 주식회사 조각 {TOTAL_SHARES}개 최초 발행! 지금은 전부 내 몫(100%)이에요.'

    # 추가 발행 — 신주는 일단 내 몫으로 (교육: 증자)
    total = int(inv.get('total_shares') or TOTAL_SHARES)
    my_before = int(inv.get('my_shares') or 0)
    pct_before = round(100 * my_before / max(1, total), 1)
    if total >= MAX_TOTAL_SHARES:
        return False, f'조각은 최대 {MAX_TOTAL_SHARES}개까지예요. (지금 {total}개)'
    add = min(ISSUE_BATCH, MAX_TOTAL_SHARES - total)
    inv['total_shares'] = total + add
    inv['my_shares'] = my_before + add
    inv['issues_count'] = int(inv.get('issues_count') or 1) + 1
    # 희석 로그 (교육 UI)
    my_after = inv['my_shares']
    tot = inv['total_shares']
    pct_after = round(100 * my_after / tot, 1)
    inv['last_dilution'] = {
        'add': add,
        'total_before': total,
        'total_after': tot,
        'my_before': my_before,
        'my_after': my_after,
        'pct_before': pct_before,
        'pct_after': pct_after,
        'day': today_str(),
        'kid': (
            f'증자 전 내 지분 {pct_before}% → 후 {pct_after}%. '
            f'내 주식 수는 {my_before}→{my_after}로 늘고, 회사 파이(총 주식)도 {total}→{tot}!'
        ),
    }
    _save(prog, ops)
    db.session.commit()
    return True, (
        f'📈 추가 발행 +{add}개! 내 지분 {pct_before}%→{pct_after}% '
        f'(주식 수 {my_before}→{my_after}, 총 {total}→{tot}). '
        f'희석=파이가 커지며 비율이 바뀔 수 있어요. 지금은 신주를 내가 받아 비율이 유지·상승해요.'
    )


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
        return False, '이미 이 친구와 제휴했어요. 지분을 되사려면 매입을 눌러 보세요!'
    if not accept:
        inv.setdefault('npc_declined', {})[npc_id] = week_key()
        _save(prog, ops)
        db.session.commit()
        return True, '괜찮아요. 거절해도 손해 없어요. 언제든 다시 생각할 수 있어요.'
    need = int(npc.get('shares', 5))
    if inv['my_shares'] < need:
        return False, '남은 내 조각이 부족해요. 추가 발행을 해 보세요!'
    min_lv = int(npc.get('min_level', 2))
    if int(ops.get('level', 1)) < min_lv:
        return False, f'항공사 Lv.{min_lv} 이상이면 만날 수 있어요.'
    total = max(1, int(inv.get('total_shares') or TOTAL_SHARES))
    val = estimate_company_valuation(prog, ops, inv)
    prem = _sale_premium_mult(ops)
    intrinsic = int(val['valuation'] * need / total)
    proceeds = _sale_proceeds_for_shares(val['valuation'], need, total, premium=prem)
    inv['my_shares'] -= need
    inv.setdefault('npc', {})[npc_id] = need
    inv.setdefault('npc_sale_proceeds', {})[npc_id] = {
        'shares': need,
        'proceeds': proceeds,
        'intrinsic': intrinsic,
        'premium': round(prem, 3),
        'valuation': val['valuation'],
        'multiple': val['multiple'],
        'week': week_key(),
    }
    if proceeds > 0:
        award_money(prog, proceeds, f'지분 매각: {npc["name"]}', 'invest')
    _save(prog, ops)
    db.session.commit()
    pct = round(need / total * 100, 1)
    prem_pct = int(round((prem - 1) * 100))
    return True, (
        f'{npc["emoji"]} {npc["name"]}이(가) 조각 {need}개({pct}%)를 가져갔어요! '
        f'내재가치 {format_krw(intrinsic)} + 성장 프리미엄 약 {prem_pct}% → '
        f'매각 대금 +{format_krw(proceeds)} '
        f'(시총 {val["valuation_formatted"]} · PER {val["multiple"]}배)'
    )


def buyback_npc_shares(prog, npc_id):
    """NPC 지분 매입 — 하루 1회, 지갑의25% 한도."""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    held = int((inv.get('npc') or {}).get(npc_id) or 0)
    if held <= 0:
        return False, '이 투자자가 가진 조각이 없어요.'
    today = today_str()
    if inv.get('buyback_date') == today and int(inv.get('buybacks_today') or 0) >= BUYBACK_DAILY_LIMIT:
        return False, f'자사주/지분 매입은 하루 {BUYBACK_DAILY_LIMIT}번까지예요. 내일 또!'
    npcs = {n['id']: n for n in (load_json('airline_npc_investors.json') or [])}
    npc = npcs.get(npc_id) or {'name': npc_id, 'emoji': '🤝'}
    total = max(1, int(inv.get('total_shares') or TOTAL_SHARES))
    val = estimate_company_valuation(prog, ops, inv)
    cost = _sale_proceeds_for_shares(val['valuation'], held, total, premium=BUYBACK_DISCOUNT)
    bal = int(getattr(prog, 'wallet_balance', 0) or 0)
    max_cash = int(bal * BUYBACK_MAX_CASH_RATIO)
    if cost > max_cash and bal > 0:
        return False, (
            f'현금의 {int(BUYBACK_MAX_CASH_RATIO*100)}%({format_krw(max_cash)})를 넘는 매입은 위험해요. '
            f'(필요 {format_krw(cost)}) 조금 모아 오세요!'
        )
    ok, err = spend_money(prog, cost, f'지분 매입: {npc.get("name")}', 'invest')
    if not ok:
        return False, err
    inv['my_shares'] = int(inv.get('my_shares') or 0) + held
    inv['npc'].pop(npc_id, None)
    if inv.get('buyback_date') != today:
        inv['buyback_date'] = today
        inv['buybacks_today'] = 0
    inv['buybacks_today'] = int(inv.get('buybacks_today') or 0) + 1
    inv.setdefault('buyback_log', []).append({
        'npc_id': npc_id, 'shares': held, 'cost': cost, 'day': today,
    })
    inv['buyback_log'] = inv['buyback_log'][-30:]
    _save(prog, ops)
    db.session.commit()
    pct = round(held / total * 100, 1)
    return True, (
        f'🔄 {npc.get("emoji", "")} {npc.get("name")} 지분 {held}개({pct}%)를 '
        f'{format_krw(cost)}에 되샀어요! (약 {int((1-BUYBACK_DISCOUNT)*100)}% 할인 · 하루 {BUYBACK_DAILY_LIMIT}회 · 현금 {int(BUYBACK_MAX_CASH_RATIO*100)}% 한도)'
    )


def set_dividend_policy(prog, policy):
    """0=성장 1=균형 2=고배당 — PER 배수와 배당 풀에 영향."""
    policy = int(policy if policy is not None else 1)
    if policy not in (0, 1, 2):
        return False, '성장(0) · 균형(1) · 고배당(2) 중 골라 주세요.'
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    if not inv.get('shares_issued'):
        return False, '먼저 조각을 발행하세요!'
    inv['dividend_policy'] = policy
    labels = {0: '성장 중시 (배당↓ PER↑)', 1: '균형', 2: '고배당 (배당↑ PER↓)'}
    _save(prog, ops)
    db.session.commit()
    return True, f'📊 배당 정책: {labels[policy]}. 회사 가치 배수와 배당이 달라져요!'


def answer_value_quiz(prog, choice_id):
    """오버/언더 밸류 퀴즈 — 친구 시장 평균 vs 내 PER."""
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    wk = week_key()
    if inv.get('value_quiz_week') == wk and inv.get('value_quiz_done'):
        return False, '이번 주 밸류 퀴즈는 끝났어요!', {}
    _refresh_market_prices(inv)
    prices = list((inv.get('prices') or {}).values()) or [80000]
    mkt_avg = int(sum(prices) / len(prices))
    val = estimate_company_valuation(prog, ops, inv)
    my_price = val['share_price']
    # 교육용: 내 주가가 시장 평균보다 높으면 "고평가 쪽"
    truth = 'over' if my_price > mkt_avg * 1.05 else ('under' if my_price < mkt_avg * 0.95 else 'fair')
    ok = (choice_id == truth) or (choice_id == 'fair' and truth == 'fair')
    inv['value_quiz_week'] = wk
    inv['value_quiz_done'] = True
    inv['value_quiz_last'] = {'truth': truth, 'choice': choice_id, 'ok': ok}
    reward = 0
    if ok:
        reward = 80_000
        award_money(prog, reward, '밸류 퀴즈 정답', 'invest')
    _save(prog, ops)
    db.session.commit()
    explain = {
        'over': '내 주가가 친구 시장 평균보다 높아요 → 상대적으로 비싸 보일 수 있어요(고평가 쪽).',
        'under': '내 주가가 평균보다 낮아요 → 싸 보일 수 있어요(저평가 쪽).',
        'fair': '평균과 비슷해요 → 적정에 가까워요.',
    }
    msg = ('정답! ' if ok else '아쉬워요. ') + explain.get(truth, '')
    if ok:
        msg += f' +{format_krw(reward)}'
    return True, msg, {
        'truth': truth,
        'my_price': my_price,
        'market_avg': mkt_avg,
        'ok': ok,
        'reward': reward,
    }


def build_disclosure_card(prog, ops, inv, val):
    """공시 한 줄 뉴스."""
    day = today_str()
    net = val.get('weekly_net') or 0
    chg = val.get('day_change_pct') or 0
    if net > 200_000:
        headline = f'【공시】 주간 순익 양호 → 시세 {chg:+d}% 반영'
    elif net < 0:
        headline = f'【공시】 주간 순익 부진 우려 → 시세 {chg:+d}%'
    else:
        headline = f'【공시】 안정 운항 중 · 시세 {chg:+d}%'
    return {
        'date': day,
        'headline': headline,
        'body': (
            f"예상 주간 매출 {val.get('weekly_gross_formatted')} · 순익 {val.get('weekly_net_formatted')}. "
            f"PER {val.get('multiple')}배 · 시총 {val.get('valuation_formatted')}."
        ),
        'kid': '공시=회사가 실적을 알려 주는 소식. 좋은 소식은 주가에 도움이 될 수 있어요.',
    }


def build_ceo_report(prog, ops, inv, val):
    """주간 CEO 리포트 — 항공 이익 + 우주 + 인원·인건비 + 회사 가치."""
    from app.services.airline_ops import estimate_weekly_revenue
    preview = estimate_weekly_revenue(prog, ops) or {}
    space_rev = 0
    sat = 0
    space_staff_n = 0
    space_payroll = 0
    space_payroll_paid = 0
    try:
        from app.services.space_ops import _space
        from app.services.space_staff import _hired_count, estimate_weekly_payroll, _ensure_staff_defaults
        sp = _ensure_staff_defaults(_space(prog))
        space_rev = int(sp.get('total_space_revenue') or 0)
        sat = int(sp.get('sat_count') or 0)
        space_staff_n = _hired_count(sp)
        space_payroll = estimate_weekly_payroll(sp)
        space_payroll_paid = int(sp.get('total_payroll_paid') or 0)
    except Exception:
        pass
    return {
        'week': week_key(),
        'title': '주간 CEO 리포트',
        'airline_gross': preview.get('gross', 0),
        'airline_net': preview.get('net', 0),
        'airline_gross_f': format_krw(preview.get('gross', 0)),
        'airline_net_f': format_krw(preview.get('net', 0)),
        'space_lifetime_rev': space_rev,
        'space_lifetime_rev_f': format_krw(space_rev),
        'satellites': sat,
        'space_staff': space_staff_n,
        'space_payroll': space_payroll,
        'space_payroll_f': format_krw(space_payroll),
        'space_payroll_paid_f': format_krw(space_payroll_paid),
        'company_value': val.get('valuation', 0),
        'company_value_f': val.get('valuation_formatted'),
        'per': val.get('multiple'),
        'my_pct': round(100 * int(inv.get('my_shares') or 0) / max(1, int(inv.get('total_shares') or 1)), 1),
        'kid': '항공 이익 + 우주 수입·인원·인건비 + 시총. CEO처럼 전체를 봐요!',
    }


FINANCE_GLOSSARY = [
    {'word': 'PER', 'meaning': '주가수익비율. 이익에 몇 배를 곱해 회사 값을 볼지 정하는 배수', 'category': '밸류'},
    {'word': '시총', 'meaning': '시가총액. 주가 × 총 주식 수 = 시장이 매긴 회사 값', 'category': '밸류'},
    {'word': '증자', 'meaning': '주식을 더 찍어 회사 파이를 키우는 것(추가 발행)', 'category': '발행'},
    {'word': '희석', 'meaning': '주식이 늘며 한 주·지분 비율의 무게가 달라질 수 있는 현상', 'category': '발행'},
    {'word': '프리미엄', 'meaning': '내재가치보다 비싸게 팔리는 부분(성장 기대 등)', 'category': '매매'},
    {'word': '할인', 'meaning': '시세보다 싸게 사는 것(매입 협상 등)', 'category': '매매'},
    {'word': '배당', 'meaning': '이익 일부를 주주에게 나눠 주는 것', 'category': '배당'},
    {'word': '성장주', 'meaning': '지금 배당보다 회사 키우기에 돈을 쓰는 스타일 → PER 높은 편', 'category': '배당'},
    {'word': '고배당', 'meaning': '이익을 지금 많이 나눠 줌 → 성장 투자 여력↓, PER 낮아질 수 있음', 'category': '배당'},
    {'word': '공시', 'meaning': '회사 실적·소식을 알리는 공식 발표', 'category': '공시'},
    {'word': '오버밸류', 'meaning': '비싸 보임. 비슷한 것과 비교해 가격이 높음', 'category': '퀴즈'},
    {'word': '언더밸류', 'meaning': '싸 보임. 비교 대상보다 가격이 낮음', 'category': '퀴즈'},
    {'word': '자사주 매입', 'meaning': '시장/투자자 주식을 다시 사들여 내 지분을 늘리는 것', 'category': '매매'},
]


def _reset_daily_actions(inv):
    today = today_str()
    if inv.get('actions_date') != today:
        inv['actions_date'] = today
        inv['actions_today'] = 0


def market_trade(prog, firm_id, action):
    """action: buy | sell — 하루 7회, 산 주 매도 불가"""
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
    """내 회사 지분 배당(운영이익·밸류 연동) + 친구 시장 소액 배당 — 주 1회"""
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '항공사 창업이 필요해요!', 0
    ops, _save = _ops_mod(prog)
    inv = ensure_invest(ops)
    # 예전 매각대금 누락 보전 (한 번)
    backfill = _backfill_npc_sale_proceeds(prog, ops, inv)
    wk = week_key()
    if inv.get('dividend_week') == wk:
        if backfill > 0:
            _save(prog, ops)
            db.session.commit()
            return True, f'지분 매각 대금 보전 +{format_krw(backfill)}! (이번 주 배당은 이미 받았어요)', backfill
        return False, '이번 주 배당은 이미 받았어요!', 0
    total = 0
    parts = []
    if backfill > 0:
        total += backfill
        parts.append(f'매각대금 보전 {format_krw(backfill)}')
    # 내 회사: 내 지분 비율 × (운영 이익 연동 풀)
    if inv.get('shares_issued'):
        my_pct = inv.get('my_shares', 0) / max(1, inv.get('total_shares', TOTAL_SHARES))
        pool, _, _ = _estimate_weekly_company_dividend_pool(prog, ops, inv)
        mine = int(pool * my_pct)
        if mine > 0:
            award_money(prog, mine, f'내 회사 배당 ({wk})', 'dividend')
            total += mine
            parts.append(f'내 회사 지분 {format_krw(mine)}')
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
                try:
                    from app.services.airline_treasury import credit_capital_from_external
                    credit_capital_from_external(ops, move, f'이사회 저축 ({wk})')
                except Exception:
                    pass
                msg += f' · 금고(가수금) +{format_krw(move)}'
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
    # 매각대금 누락 보전 (패널 열 때 한 번)
    backfill = _backfill_npc_sale_proceeds(prog, ops, inv)
    if backfill > 0:
        from app.services.airline_ops import _save_ops
        _save_ops(prog, ops)
        db.session.commit()
    level = int(ops.get('level', 1) or 1)
    issued = bool(inv.get('shares_issued'))
    my = int(inv.get('my_shares', 0) or 0)
    total = int(inv.get('total_shares', TOTAL_SHARES) or TOTAL_SHARES)
    my_pct = round(my / max(1, total) * 100, 1)
    val = estimate_company_valuation(prog, ops, inv)
    my_stake_value = int(val['valuation'] * my / max(1, total))
    div_pool, _, _ = _estimate_weekly_company_dividend_pool(prog, ops, inv)
    my_div_est = int(div_pool * my / max(1, total)) if issued else 0
    prem = _sale_premium_mult(ops)
    can_more_issue = issued and total < MAX_TOTAL_SHARES and can_issue_shares(ops)

    npcs_data = load_json('airline_npc_investors.json') or []
    npc_rows = []
    for n in npcs_data:
        taken = inv.get('npc', {}).get(n['id'])
        declined = inv.get('npc_declined', {}).get(n['id'])
        n_shares = int(n.get('shares', 5) or 5)
        offer_intrinsic = _sale_proceeds_for_shares(val['valuation'], n_shares, total, premium=1.0)
        offer_proceeds = _sale_proceeds_for_shares(val['valuation'], n_shares, total, premium=prem)
        buyback_cost = _sale_proceeds_for_shares(val['valuation'], int(taken or 0), total, premium=BUYBACK_DISCOUNT) if taken else 0
        sale_rec = (inv.get('npc_sale_proceeds') or {}).get(n['id']) or {}
        npc_rows.append({
            **n,
            'joined': bool(taken),
            'held_shares': taken or 0,
            'declined': bool(declined),
            'eligible': level >= int(n.get('min_level', 2)),
            'available': issued and not taken and not declined and level >= int(n.get('min_level', 2)),
            'offer_proceeds': offer_proceeds,
            'offer_proceeds_formatted': format_krw(offer_proceeds),
            'offer_intrinsic_formatted': format_krw(offer_intrinsic),
            'premium_pct': int(round((prem - 1) * 100)),
            'buyback_cost': buyback_cost,
            'buyback_cost_formatted': format_krw(buyback_cost),
            'can_buyback': bool(taken) and not (
                inv.get('buyback_date') == today_str()
                and int(inv.get('buybacks_today') or 0) >= BUYBACK_DAILY_LIMIT
            ),
            'paid_proceeds': int(sale_rec.get('proceeds', 0) or 0),
            'paid_proceeds_formatted': format_krw(int(sale_rec.get('proceeds', 0) or 0)),
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
            'can_issue': ((not issued) and can_issue_shares(ops)) or can_more_issue,
            'is_additional_issue': can_more_issue,
            'my_shares': my,
            'total': total,
            'my_pct': my_pct,
            'max_total': MAX_TOTAL_SHARES,
            'issue_batch': ISSUE_BATCH,
            'issue_hint': (
                f'추가 발행 +{ISSUE_BATCH}개 가능 (최대 {MAX_TOTAL_SHARES})'
                if can_more_issue else
                f'Lv.{ISSUE_MIN_LEVEL}+ 또는 노선 1개 이상이면 조각 발행 가능'
            ),
            'kid': '회사 조각=주식. 추가 발행(증자)·매각 프리미엄·매입으로 금융을 배워요.',
            'my_stake_value': my_stake_value,
            'my_stake_value_formatted': format_krw(my_stake_value),
        },
        'valuation': {
            **val,
            'my_stake_value': my_stake_value,
            'my_stake_value_formatted': format_krw(my_stake_value),
            'sale_premium_pct': int(round((prem - 1) * 100)),
            'buyback_discount_pct': int(round((1 - BUYBACK_DISCOUNT) * 100)),
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
            'pool_estimate': div_pool if issued else 0,
            'pool_estimate_formatted': format_krw(div_pool) if issued else format_krw(0),
            'my_estimate': my_div_est,
            'my_estimate_formatted': format_krw(my_div_est),
            'policy': int(inv.get('dividend_policy') or 1),
            'policy_labels': {
                '0': '성장 (배당↓ PER↑)',
                '1': '균형',
                '2': '고배당 (배당↑ PER↓)',
            },
            'kid': '배당 정책에 따라 배당 크기와 PER 배수가 반대로 움직여요!',
        },
        'board': board_ui,
        'disclosure': build_disclosure_card(prog, ops, inv, val) if issued else None,
        'dilution': inv.get('last_dilution'),
        'ceo_report': build_ceo_report(prog, ops, inv, val),
        'value_quiz': {
            'done': inv.get('value_quiz_week') == week_key() and inv.get('value_quiz_done'),
            'last': inv.get('value_quiz_last'),
            'choices': [
                {'id': 'over', 'label': '고평가(비싸 보임)'},
                {'id': 'fair', 'label': '적정'},
                {'id': 'under', 'label': '저평가(싸 보임)'},
            ],
            'kid': '내 회사 주가 vs 친구 시장 평균 가격을 비교해 봐요.',
        },
        'buyback_limits': {
            'daily_limit': BUYBACK_DAILY_LIMIT,
            'cash_ratio_pct': int(BUYBACK_MAX_CASH_RATIO * 100),
            'used_today': int(inv.get('buybacks_today') or 0) if inv.get('buyback_date') == today_str() else 0,
        },
        'glossary': _load_glossary(),
        'glossary_count': len(_load_glossary()),
        'finance_glossary': FINANCE_GLOSSARY,
        'sale_backfill': backfill,
        'sale_backfill_message': (
            f'지분 매각 대금 보전 +{format_krw(backfill)}이 지갑에 들어왔어요!'
            if backfill > 0 else ''
        ),
        'kid_summary': (
            'PER·시총·증자·희석·배당 vs 성장을 배워요. '
            '매일 시세가 조금 바뀌고, 공시 카드로 소식을 읽어요!'
        ),
    }


def _load_glossary():
    """쉬운 단어장 + 금융 용어"""
    g = load_json('airline_invest_glossary.json')
    base = g if isinstance(g, list) and g else [
        {'word': '회사 조각', 'meaning': '주식처럼 회사를 나누는 몫', 'category': '기초'},
        {'word': '배당', 'meaning': '회사가 잘되면 돌아오는 용돈', 'category': '기초'},
        {'word': '투자', 'meaning': '나중에 도움이 되게 지금 넣는 돈', 'category': '기초'},
        {'word': '지분', 'meaning': '회사 중 내가 가진 비율', 'category': '기초'},
    ]
    # merge finance terms without duplicate words
    words = {x.get('word') for x in base}
    for t in FINANCE_GLOSSARY:
        if t['word'] not in words:
            base.append(t)
            words.add(t['word'])
    return base


def get_glossary_public():
    g = _load_glossary()
    return {'glossary': g, 'glossary_count': len(g)}
