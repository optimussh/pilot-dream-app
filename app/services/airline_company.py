"""항공사 2층: 손익(P&L) 보드 · 주간 이익 배치 · 회사 금고

아이에게 '주식회사 전신' 개념을 놀이로 익히게 함.
- 매출 = 들어온 돈
- 비용 = 나간 돈(주급 등)
- 이익 = 남은 돈
- 배치 = 이익을 어디에 쓸지 정하기 (금고 / 재투자 / 직원 보너스)
"""
from app.models import db
from app.services.gamification import week_key
from app.services.economy import award_money, spend_money, format_krw
from app.services.pilot_features import get_airline_info

# 이익 배치 선택지 (초등 친화 라벨)
ALLOC_CHOICES = {
    'vault': {
        'id': 'vault',
        'emoji': '🏦',
        'label': '금고에 보관',
        'kid': '안전하게 모아둬요. 나중에 큰 비행기를 살 때 써요!',
        'concept': '저축 · 자본 비축',
        'color': '#0A84FF',
    },
    'reinvest': {
        'id': 'reinvest',
        'emoji': '📈',
        'label': '성장에 재투자',
        'kid': '노선·비행기를 키워요. 이번 주 남은 날 매출이 조금 올라요!',
        'concept': '재투자 · 성장',
        'color': '#33ff33',
    },
    'staff_bonus': {
        'id': 'staff_bonus',
        'emoji': '🎁',
        'label': '직원 보너스',
        'kid': '동료에게 용돈을 나눠줘요. 회사 평판이 올라요!',
        'concept': '인재 투자 · 평판',
        'color': '#ffaa00',
    },
}

REINVEST_BOOST_PCT = 6
STAFF_BONUS_COST_RATIO = 0.35  # 배치 금액의 35%를 지갑에서 씀
MIN_ALLOC = 50_000


def _ops_save(prog):
    from app.services.airline_ops import _ops, _save_ops
    return _ops(prog), _save_ops


def ensure_company_fields(ops):
    ops.setdefault('company_vault', 0)
    ops.setdefault('allocation_week', '')
    ops.setdefault('last_allocation', None)
    ops.setdefault('reinvest_boost_week', '')
    ops.setdefault('reinvest_boost_pct', 0)
    ops.setdefault('staff_bonus_week', '')
    ops.setdefault('allocable_pool', 0)  # 이번 주 배치 가능 이익 누적
    return ops


def note_profit_for_allocation(ops, daily_net):
    """일일 정산에서 순이익이 나면 배치 풀에 적립 (주간 1회 배치용)."""
    ensure_company_fields(ops)
    wk = week_key()
    if ops.get('allocation_week') == wk:
        return
    if daily_net and daily_net > 0:
        ops['allocable_pool'] = int(ops.get('allocable_pool', 0) or 0) + int(daily_net)


def get_reinvest_mult(ops):
    ensure_company_fields(ops)
    if ops.get('reinvest_boost_week') == week_key() and ops.get('reinvest_boost_pct', 0) > 0:
        return 1.0 + ops['reinvest_boost_pct'] / 100.0
    return 1.0


def get_staff_bonus_active(ops):
    ensure_company_fields(ops)
    return ops.get('staff_bonus_week') == week_key()


def _allocable_amount(ops, preview=None):
    ensure_company_fields(ops)
    wk = week_key()
    if ops.get('allocation_week') == wk:
        return 0
    pool = int(ops.get('allocable_pool', 0) or 0)
    if pool <= 0 and preview:
        # 폴백: 이번 주 예상 순이익의 1/7 (하루분) 이상이면 최소 배치 가능
        net = int((preview or {}).get('net', 0) or 0)
        if net > 0:
            pool = max(MIN_ALLOC, net // 7)
    return max(0, pool)


def build_company_board(prog, ops=None, preview=None):
    """개요 탭용 손익 보드 + 배치 UI 데이터"""
    from app.services.airline_ops import _ops, estimate_weekly_revenue
    info = get_airline_info(prog)
    if not info.get('founded'):
        return None
    ops = ops or _ops(prog)
    ensure_company_fields(ops)
    preview = preview or estimate_weekly_revenue(prog, ops)
    side = preview.get('side_income') or {}
    route_g = int(preview.get('route_gross', 0) or 0)
    side_t = int(preview.get('side_income_total', 0) or 0)
    log_b = int(preview.get('log_bonus', 0) or 0)
    gross = int(preview.get('gross', 0) or 0)
    payroll = int(preview.get('payroll', 0) or 0)
    net = int(preview.get('net', 0) or 0)
    vault = int(ops.get('company_vault', 0) or 0)
    alloc_amt = _allocable_amount(ops, preview)
    done = ops.get('allocation_week') == week_key()
    last = ops.get('last_allocation')

    story = [
        {
            'id': 'sales',
            'emoji': '✈️',
            'label': '매출',
            'kid': '손님·화물·부가서비스에서 들어온 돈',
            'amount': gross,
            'formatted': format_krw(gross),
            'detail': f'노선 {format_krw(route_g)} + 부가 {format_krw(side_t)} + 로그북 {format_krw(log_b)}',
        },
        {
            'id': 'cost',
            'emoji': '👥',
            'label': '비용',
            'kid': '직원 주급 등 회사가 쓰는 돈',
            'amount': -payroll,
            'formatted': format_krw(payroll),
            'detail': '주급은 매주 1번 나가요',
        },
        {
            'id': 'profit',
            'emoji': '💎',
            'label': '이익',
            'kid': '매출에서 비용을 뺀 나머지 (잘 남으면 회사 성장!)',
            'amount': net,
            'formatted': format_krw(net),
            'detail': '이익이 플러스면 CEO 배치를 할 수 있어요',
        },
    ]

    terms = [
        {'word': '매출', 'meaning': '회사로 들어온 돈 (비행·서비스)'},
        {'word': '비용', 'meaning': '회사가 쓴 돈 (주급·정비 등)'},
        {'word': '이익', 'meaning': '들어온 돈 − 쓴 돈. 남는 몫!'},
        {'word': '재투자', 'meaning': '이익을 다시 회사에 넣어 키우기'},
        {'word': '금고', 'meaning': '나중에 쓰려고 모아 둔 회사 돈'},
        {'word': '평판', 'meaning': '사람들이 회사를 얼마나 믿는지'},
    ]

    choices = []
    for key, meta in ALLOC_CHOICES.items():
        item = dict(meta)
        if key == 'vault':
            item['effect'] = f'회사 금고 +{format_krw(alloc_amt)} (지갑에서 이동)'
        elif key == 'reinvest':
            item['effect'] = f'매출 +{REINVEST_BOOST_PCT}% (이번 주) · 경영 XP'
        else:
            cost = max(MIN_ALLOC // 2, int(alloc_amt * STAFF_BONUS_COST_RATIO))
            item['effect'] = f'지갑 −{format_krw(cost)} · 평판 +3'
            item['cost'] = cost
        choices.append(item)

    boosts = []
    if get_reinvest_mult(ops) > 1.0:
        boosts.append(f'📈 재투자 보너스 적용 중 (+{ops.get("reinvest_boost_pct", REINVEST_BOOST_PCT)}% 매출)')
    if get_staff_bonus_active(ops):
        boosts.append('🎁 직원 보너스 주간 — 동료 사기 UP')

    return {
        'founded': True,
        'company_name': info.get('name', '내 항공사'),
        'level': ops.get('level', 1),
        'reputation': ops.get('reputation', 50),
        'story': story,
        'terms': terms,
        'vault': vault,
        'vault_formatted': format_krw(vault),
        'gross': gross,
        'payroll': payroll,
        'net': net,
        'formatted_gross': format_krw(gross),
        'formatted_payroll': format_krw(payroll),
        'formatted_net': format_krw(net),
        'allocation': {
            'available': alloc_amt > 0 and not done,
            'done': done,
            'amount': alloc_amt,
            'amount_formatted': format_krw(alloc_amt),
            'choices': choices,
            'last': last,
            'week': week_key(),
        },
        'boosts': boosts,
        'kid_summary': (
            f'이번 주 예상 이익은 {format_krw(net)}예요. '
            + ('이익을 어디에 쓸지 CEO 회의에서 정해 보세요!' if alloc_amt > 0 and not done
               else ('이번 주 배치는 끝났어요. 잘했어요!' if done
                     else '노선을 돌리면 이익이 생겨요.'))
        ),
    }


def allocate_weekly_profit(prog, choice_id):
    """주 1회 이익 배치"""
    from app.services.airline_ops import _ops, _save_ops, estimate_weekly_revenue
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    if choice_id not in ALLOC_CHOICES:
        return False, '금고 / 재투자 / 직원 보너스 중 골라주세요.'

    ops = _ops(prog)
    ensure_company_fields(ops)
    wk = week_key()
    if ops.get('allocation_week') == wk:
        return False, '이번 주 이익 배치는 이미 끝났어요! 다음 주에 다시 만나요.'

    preview = estimate_weekly_revenue(prog, ops)
    amount = _allocable_amount(ops, preview)
    if amount < MIN_ALLOC:
        # 최소 금액 미만이면 예상 순이익 기반 소액 허용
        if int(preview.get('net', 0) or 0) <= 0 and amount <= 0:
            return False, '배치할 이익이 아직 없어요. 노선 수익을 먼저 받아보세요!'
        amount = max(amount, MIN_ALLOC) if preview.get('net', 0) > 0 else amount
    if amount <= 0:
        return False, '배치할 이익이 아직 없어요. 노선 수익을 먼저 받아보세요!'

    meta = ALLOC_CHOICES[choice_id]
    msg = ''

    if choice_id == 'vault':
        bal = prog.wallet_balance or 0
        move = min(amount, bal)
        if move <= 0:
            return False, '지갑에 옮길 돈이 부족해요. 수익을 받은 뒤 다시 시도하세요!'
        ok, err = spend_money(prog, move, f'회사 금고 적립 ({wk})', 'company_vault')
        if not ok:
            return False, err
        ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + move
        msg = f'🏦 회사 금고에 {format_krw(move)}를 모았어요! (총 {format_krw(ops["company_vault"])})'

    elif choice_id == 'reinvest':
        ops['reinvest_boost_week'] = wk
        ops['reinvest_boost_pct'] = REINVEST_BOOST_PCT
        ops['xp'] = ops.get('xp', 0) + 8
        ops['reputation'] = min(100, ops.get('reputation', 50) + 1)
        # 레벨업 체크
        while ops['xp'] >= ops.get('level', 1) * 80:
            ops['xp'] -= ops.get('level', 1) * 80
            ops['level'] = ops.get('level', 1) + 1
        msg = f'📈 성장 재투자! 이번 주 노선 매출 +{REINVEST_BOOST_PCT}% · 회사 경험치 UP'

    else:  # staff_bonus
        cost = max(MIN_ALLOC // 2, int(amount * STAFF_BONUS_COST_RATIO))
        bal = prog.wallet_balance or 0
        if bal < cost:
            return False, f'직원 보너스에 {format_krw(cost)}이 필요해요. (지갑: {format_krw(bal)})'
        ok, err = spend_money(prog, cost, f'직원 보너스 ({wk})', 'salary')
        if not ok:
            return False, err
        ops['staff_bonus_week'] = wk
        ops['reputation'] = min(100, ops.get('reputation', 50) + 3)
        msg = f'🎁 직원 보너스 {format_krw(cost)} 지급! 평판 +3 · 동료 사기 UP'

    ops['allocation_week'] = wk
    ops['allocable_pool'] = 0
    ops['last_allocation'] = {
        'week': wk,
        'choice': choice_id,
        'label': meta['label'],
        'emoji': meta['emoji'],
        'amount': amount,
        'message': msg,
    }
    _save_ops(prog, ops)
    try:
        from app.services.player_stats import apply_activity_stats
        apply_activity_stats(prog, 'airline_settle')
    except Exception:
        pass
    db.session.commit()
    return True, msg


def withdraw_company_vault(prog, amount=None):
    """금고 → 지갑 (전액 또는 일부)"""
    from app.services.airline_ops import _ops, _save_ops
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, '먼저 항공사를 창업해주세요!'
    ops = _ops(prog)
    ensure_company_fields(ops)
    vault = int(ops.get('company_vault', 0) or 0)
    if vault <= 0:
        return False, '금고가 비어 있어요.'
    take = vault if amount is None else min(vault, max(0, int(amount)))
    if take <= 0:
        return False, '꺼낼 금액을 확인해주세요.'
    ops['company_vault'] = vault - take
    award_money(prog, take, f'회사 금고 인출', 'company_vault')
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'🏦 금고에서 {format_krw(take)}를 지갑으로 옮겼어요! (남은 금고 {format_krw(ops["company_vault"])})'
