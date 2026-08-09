"""항공사 자금관리 (B + 가드레일)

회사 운용 현금(company_vault)과 개인 포지션을 분리:
- capital (가수금): 이자 0, 1:1 회수
- loan_to_company (대여금): 회사가 내게 빌림 → 주간 이자 → 지갑
- loan_from_company (차입): 내가 회사에서 빌림 → 주간 이자 → 회사

이자는 week_key 기준 주 1회. 투자 탭(지분·배당)과 개념 분리.
"""
from __future__ import annotations

from datetime import datetime

from app.models import db
from app.services.economy import award_money, spend_money, format_krw
from app.services.gamification import week_key
from app.services.pilot_features import get_airline_info

# ── 가드레일 ──
MIN_TX = 10_000
LEND_WEEKLY_RATE = 0.005  # 대여 주이율 0.5%
BORROW_WEEKLY_RATE = 0.0075  # 차입 주이율 0.75% (대여보다 비쌈)
BORROW_MAX_OF_FREE = 0.50  # 여유 현금의 50%까지 차입
MAX_LOG = 20

ACTION_LABELS = {
    'capital_in': '가수금 납입',
    'capital_out': '가수금 회수',
    'lend_in': '대여금 실행',
    'lend_out': '대여금 회수',
    'borrow_in': '회사 차입',
    'borrow_repay': '차입 상환',
    'interest_lend': '대여 이자 수령',
    'interest_borrow': '차입 이자 납부',
    'interest_borrow_cap': '차입 이자 원금 가산',
}


def ensure_treasury(ops: dict) -> dict:
    ops.setdefault('company_vault', 0)
    t = ops.setdefault('treasury', {})
    if not isinstance(t, dict):
        t = {}
        ops['treasury'] = t
    t.setdefault('capital', 0)
    t.setdefault('loan_to_company', 0)
    t.setdefault('loan_from_company', 0)
    t.setdefault('interest_week', '')
    t.setdefault('log', [])
    if not isinstance(t['log'], list):
        t['log'] = []
    # 정수 정규화
    for k in ('capital', 'loan_to_company', 'loan_from_company'):
        t[k] = max(0, int(t.get(k, 0) or 0))
    ops['company_vault'] = max(0, int(ops.get('company_vault', 0) or 0))
    return t


def free_cash(ops: dict) -> int:
    """차입 가능 여유 현금 = 금고 − 가수금 − 대여채권 (하한 0)."""
    ensure_treasury(ops)
    t = ops['treasury']
    reserved = int(t['capital']) + int(t['loan_to_company'])
    return max(0, int(ops.get('company_vault', 0) or 0) - reserved)


def _append_log(t: dict, action: str, amount: int, note: str = '') -> None:
    entry = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'week': week_key(),
        'action': action,
        'label': ACTION_LABELS.get(action, action),
        'amount': int(amount),
        'note': note or '',
    }
    log = t.setdefault('log', [])
    log.append(entry)
    if len(log) > MAX_LOG:
        t['log'] = log[-MAX_LOG:]


def _ok_founded(prog):
    info = get_airline_info(prog)
    if not info.get('founded'):
        return False, None, '먼저 항공사를 창업해주세요!'
    return True, info, ''


def _parse_amount(amount) -> int:
    try:
        return int(amount)
    except (TypeError, ValueError):
        return 0


# ── 입출금 액션 ──

def deposit_capital(prog, amount) -> tuple[bool, str]:
    """지갑 → 가수금 + 회사 금고 (이자 없음)."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    amt = _parse_amount(amount)
    if amt < MIN_TX:
        return False, f'최소 {format_krw(MIN_TX)}부터 넣을 수 있어요.'
    ops = _ops(prog)
    t = ensure_treasury(ops)
    ok_pay, err = spend_money(prog, amt, f'회사 가수금 납입', 'treasury')
    if not ok_pay:
        return False, err
    ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + amt
    t['capital'] = int(t['capital']) + amt
    _append_log(t, 'capital_in', amt)
    _save_ops(prog, ops)
    db.session.commit()
    return True, f'📥 가수금 {format_krw(amt)} 납입! (가수금 잔액 {format_krw(t["capital"])})'


def deposit_loan(prog, amount) -> tuple[bool, str]:
    """지갑 → 대여금 (회사가 빌림) + 회사 금고. 주간 이자 수령."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    amt = _parse_amount(amount)
    if amt < MIN_TX:
        return False, f'최소 {format_krw(MIN_TX)}부터 빌려줄 수 있어요.'
    ops = _ops(prog)
    t = ensure_treasury(ops)
    ok_pay, err = spend_money(prog, amt, f'회사에 대여금', 'treasury')
    if not ok_pay:
        return False, err
    ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + amt
    t['loan_to_company'] = int(t['loan_to_company']) + amt
    _append_log(t, 'lend_in', amt, f'주이율 {LEND_WEEKLY_RATE*100:.2f}%')
    _save_ops(prog, ops)
    db.session.commit()
    return True, (
        f'🤝 대여금 {format_krw(amt)} 실행! '
        f'(채권 {format_krw(t["loan_to_company"])} · 주 {LEND_WEEKLY_RATE*100:.2f}% 이자)'
    )


def recover_capital(prog, amount=None) -> tuple[bool, str]:
    """가수금 회수: 금고 → 지갑 (이자 0). amount None = 전액."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    ops = _ops(prog)
    t = ensure_treasury(ops)
    cap = int(t['capital'])
    vault = int(ops.get('company_vault', 0) or 0)
    max_take = min(cap, vault)
    if max_take <= 0:
        return False, '회수할 가수금이 없어요. (금고 잔액도 확인!)'
    if amount is None:
        take = max_take
    else:
        take = _parse_amount(amount)
        if take < MIN_TX and take != max_take:
            return False, f'최소 {format_krw(MIN_TX)} 또는 전액만 가능해요.'
        take = min(take, max_take)
    if take <= 0:
        return False, '금액을 확인해주세요.'
    ops['company_vault'] = vault - take
    t['capital'] = cap - take
    award_money(prog, take, '가수금 회수', 'treasury')
    _append_log(t, 'capital_out', take)
    _save_ops(prog, ops)
    db.session.commit()
    return True, (
        f'📤 가수금 {format_krw(take)} 회수! '
        f'(남은 가수금 {format_krw(t["capital"])} · 금고 {format_krw(ops["company_vault"])})'
    )


def recover_loan(prog, amount=None) -> tuple[bool, str]:
    """대여 원금 회수: 회사가 갚음 (금고 → 지갑)."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    ops = _ops(prog)
    t = ensure_treasury(ops)
    loan = int(t['loan_to_company'])
    vault = int(ops.get('company_vault', 0) or 0)
    max_take = min(loan, vault)
    if max_take <= 0:
        return False, '회수할 대여금이 없거나 회사 현금이 부족해요.'
    if amount is None:
        take = max_take
    else:
        take = _parse_amount(amount)
        if take < MIN_TX and take != max_take:
            return False, f'최소 {format_krw(MIN_TX)} 또는 전액만 가능해요.'
        take = min(take, max_take)
    if take <= 0:
        return False, '금액을 확인해주세요.'
    ops['company_vault'] = vault - take
    t['loan_to_company'] = loan - take
    award_money(prog, take, '대여금 원금 회수', 'treasury')
    _append_log(t, 'lend_out', take)
    _save_ops(prog, ops)
    db.session.commit()
    return True, (
        f'💵 대여 원금 {format_krw(take)} 회수! '
        f'(남은 채권 {format_krw(t["loan_to_company"])})'
    )


def borrow_from_company(prog, amount) -> tuple[bool, str]:
    """회사에서 빌리기: 금고 → 지갑, 차입 잔액↑ (이자 부담)."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    amt = _parse_amount(amount)
    if amt < MIN_TX:
        return False, f'최소 {format_krw(MIN_TX)}부터 빌릴 수 있어요.'
    ops = _ops(prog)
    t = ensure_treasury(ops)
    free = free_cash(ops)
    max_borrow = int(free * BORROW_MAX_OF_FREE)
    if max_borrow < MIN_TX:
        return False, (
            f'여유 현금이 부족해요. (여유 {format_krw(free)}, '
            f'차입 한도 {int(BORROW_MAX_OF_FREE*100)}% = {format_krw(max_borrow)})'
        )
    if amt > max_borrow:
        return False, f'차입 한도는 {format_krw(max_borrow)}예요. (여유 현금의 {int(BORROW_MAX_OF_FREE*100)}%)'
    vault = int(ops.get('company_vault', 0) or 0)
    if amt > vault:
        return False, '회사 금고 잔액이 부족해요.'
    ops['company_vault'] = vault - amt
    t['loan_from_company'] = int(t['loan_from_company']) + amt
    award_money(prog, amt, '회사 자금 차입', 'treasury')
    _append_log(t, 'borrow_in', amt, f'주이율 {BORROW_WEEKLY_RATE*100:.2f}%')
    _save_ops(prog, ops)
    db.session.commit()
    return True, (
        f'🏦 회사 차입 {format_krw(amt)}! '
        f'(빚 {format_krw(t["loan_from_company"])} · 주 {BORROW_WEEKLY_RATE*100:.2f}% 이자)'
    )


def repay_borrow(prog, amount=None) -> tuple[bool, str]:
    """차입 상환: 지갑 → 금고."""
    from app.services.airline_ops import _ops, _save_ops

    ok, _, err = _ok_founded(prog)
    if not ok:
        return False, err
    ops = _ops(prog)
    t = ensure_treasury(ops)
    debt = int(t['loan_from_company'])
    if debt <= 0:
        return False, '갚을 회사 차입이 없어요.'
    if amount is None:
        take = debt
    else:
        take = _parse_amount(amount)
        if take < MIN_TX and take != debt:
            return False, f'최소 {format_krw(MIN_TX)} 또는 전액만 가능해요.'
        take = min(take, debt)
    if take <= 0:
        return False, '금액을 확인해주세요.'
    ok_pay, err = spend_money(prog, take, '회사 차입 상환', 'treasury')
    if not ok_pay:
        return False, err
    ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + take
    t['loan_from_company'] = debt - take
    _append_log(t, 'borrow_repay', take)
    _save_ops(prog, ops)
    db.session.commit()
    return True, (
        f'✅ 차입 {format_krw(take)} 상환! '
        f'(남은 빚 {format_krw(t["loan_from_company"])})'
    )


# ── 주간 이자 ──

def settle_treasury_interest(prog, ops=None, force: bool = False) -> dict | None:
    """주 1회 이자 정산. 대여→지갑, 차입→회사(부족 시 원금 가산)."""
    from app.services.airline_ops import _ops, _save_ops

    if not get_airline_info(prog).get('founded'):
        return None
    ops = ops if ops is not None else _ops(prog)
    t = ensure_treasury(ops)
    wk = week_key()
    if not force and t.get('interest_week') == wk:
        return None

    lend_principal = int(t['loan_to_company'])
    borrow_principal = int(t['loan_from_company'])
    if lend_principal <= 0 and borrow_principal <= 0:
        t['interest_week'] = wk
        if ops is not None:
            _save_ops(prog, ops)
        return {
            'week': wk,
            'lend_interest': 0,
            'borrow_interest': 0,
            'borrow_capitalized': 0,
            'message': '정산할 이자 포지션이 없어요.',
        }

    lend_interest = int(lend_principal * LEND_WEEKLY_RATE) if lend_principal > 0 else 0
    if lend_principal > 0 and lend_interest < 1 and LEND_WEEKLY_RATE > 0:
        lend_interest = 1 if lend_principal >= MIN_TX else 0

    borrow_interest = int(borrow_principal * BORROW_WEEKLY_RATE) if borrow_principal > 0 else 0
    if borrow_principal > 0 and borrow_interest < 1 and BORROW_WEEKLY_RATE > 0:
        borrow_interest = 1 if borrow_principal >= MIN_TX else 0

    paid_lend = 0
    if lend_interest > 0:
        vault = int(ops.get('company_vault', 0) or 0)
        paid_lend = min(lend_interest, vault)
        if paid_lend > 0:
            ops['company_vault'] = vault - paid_lend
            award_money(prog, paid_lend, f'대여 이자 ({wk})', 'treasury_interest')
            _append_log(t, 'interest_lend', paid_lend, f'원금 {format_krw(lend_principal)}')
        # 회사 현금 부족 분은 미지급 — 다음 주 재시도(원금 가산 없음)

    paid_borrow = 0
    capitalized = 0
    if borrow_interest > 0:
        bal = prog.wallet_balance or 0
        if bal >= borrow_interest:
            ok_pay, _ = spend_money(
                prog, borrow_interest, f'차입 이자 ({wk})', 'treasury_interest'
            )
            if ok_pay:
                paid_borrow = borrow_interest
                ops['company_vault'] = int(ops.get('company_vault', 0) or 0) + paid_borrow
                _append_log(t, 'interest_borrow', paid_borrow, f'빚 {format_krw(borrow_principal)}')
        else:
            # 지갑 부족 → 원금에 가산 (복리 압력)
            capitalized = borrow_interest
            t['loan_from_company'] = borrow_principal + capitalized
            _append_log(
                t, 'interest_borrow_cap', capitalized,
                '지갑 부족으로 이자 원금 가산',
            )

    t['interest_week'] = wk
    _save_ops(prog, ops)

    parts = []
    if paid_lend:
        parts.append(f'대여 이자 +{format_krw(paid_lend)}')
    elif lend_interest and not paid_lend:
        parts.append('대여 이자: 회사 현금 부족으로 미지급')
    if paid_borrow:
        parts.append(f'차입 이자 −{format_krw(paid_borrow)}')
    if capitalized:
        parts.append(f'차입 이자 원금 가산 {format_krw(capitalized)}')
    msg = ' · '.join(parts) if parts else '이자 변동 없음'

    return {
        'week': wk,
        'lend_interest': paid_lend,
        'lend_interest_due': lend_interest,
        'borrow_interest': paid_borrow,
        'borrow_interest_due': borrow_interest,
        'borrow_capitalized': capitalized,
        'message': msg,
    }


def credit_capital_from_external(ops: dict, amount: int, note: str = '') -> None:
    """CEO 배치·이사회 등 외부에서 금고 적립 시 가수금으로 장부 반영."""
    if amount <= 0:
        return
    t = ensure_treasury(ops)
    t['capital'] = int(t['capital']) + int(amount)
    _append_log(t, 'capital_in', int(amount), note or '외부 적립')


# ── 패널 / 요약 ──

def build_treasury_panel(prog) -> dict | None:
    from app.services.airline_ops import _ops, _save_ops

    if not get_airline_info(prog).get('founded'):
        return None
    ops = _ops(prog)
    # 패널 열 때 주간 이자 시도
    interest = settle_treasury_interest(prog, ops)
    if interest is not None:
        db.session.commit()
    else:
        ensure_treasury(ops)

    t = ops['treasury']
    vault = int(ops.get('company_vault', 0) or 0)
    capital = int(t['capital'])
    lend = int(t['loan_to_company'])
    debt = int(t['loan_from_company'])
    free = free_cash(ops)
    max_borrow = int(free * BORROW_MAX_OF_FREE)
    wallet = prog.wallet_balance or 0

    lend_due = int(lend * LEND_WEEKLY_RATE) if lend > 0 else 0
    if lend > 0 and lend_due < 1:
        lend_due = 1 if lend >= MIN_TX else 0
    borrow_due = int(debt * BORROW_WEEKLY_RATE) if debt > 0 else 0
    if debt > 0 and borrow_due < 1:
        borrow_due = 1 if debt >= MIN_TX else 0

    wk = week_key()
    interest_done = t.get('interest_week') == wk

    log = list(reversed(t.get('log') or []))
    for e in log:
        e['amount_formatted'] = format_krw(abs(int(e.get('amount', 0) or 0)))

    return {
        'wallet': wallet,
        'wallet_formatted': format_krw(wallet),
        'company_cash': vault,
        'company_cash_formatted': format_krw(vault),
        'capital': capital,
        'capital_formatted': format_krw(capital),
        'loan_to_company': lend,
        'loan_to_company_formatted': format_krw(lend),
        'loan_from_company': debt,
        'loan_from_company_formatted': format_krw(debt),
        'free_cash': free,
        'free_cash_formatted': format_krw(free),
        'max_borrow': max_borrow,
        'max_borrow_formatted': format_krw(max_borrow),
        'min_tx': MIN_TX,
        'min_tx_formatted': format_krw(MIN_TX),
        'rates': {
            'lend_weekly_pct': round(LEND_WEEKLY_RATE * 100, 2),
            'borrow_weekly_pct': round(BORROW_WEEKLY_RATE * 100, 2),
            'borrow_max_pct': int(BORROW_MAX_OF_FREE * 100),
        },
        'expected': {
            'lend_interest': lend_due,
            'lend_interest_formatted': format_krw(lend_due),
            'borrow_interest': borrow_due,
            'borrow_interest_formatted': format_krw(borrow_due),
            'net_interest': lend_due - borrow_due,
            'net_interest_formatted': format_krw(lend_due - borrow_due),
        },
        'interest_week': t.get('interest_week') or '',
        'interest_done_this_week': interest_done,
        'last_interest': interest,
        'log': log[:20],
        'terms': [
            {'word': '가수금', 'meaning': '내 돈을 회사에 보탠 출자성 예치. 이자 없음, 회수 가능'},
            {'word': '대여금', 'meaning': '회사에 빌려준 돈. 매주 이자 받음'},
            {'word': '차입', 'meaning': '회사 돈을 내가 빌려 씀. 매주 이자 냄'},
            {'word': '여유 현금', 'meaning': '금고 − 가수금 − 대여채권. 차입 한도 기준'},
            {'word': '주간 이자', 'meaning': '매주 한 번 대여·차입 이자를 정산해요'},
        ],
        'kid_summary': (
            f'회사 금고 {format_krw(vault)} · 가수금 {format_krw(capital)} · '
            f'대여채권 {format_krw(lend)} · 내 빚 {format_krw(debt)}. '
            f'이자는 주 1회 정산해요.'
        ),
    }


def get_treasury_summary(ops: dict) -> dict:
    """대시보드/개요용 짧은 요약."""
    t = ensure_treasury(ops)
    vault = int(ops.get('company_vault', 0) or 0)
    return {
        'company_cash': vault,
        'company_cash_formatted': format_krw(vault),
        'capital': int(t['capital']),
        'loan_to_company': int(t['loan_to_company']),
        'loan_from_company': int(t['loan_from_company']),
        'free_cash': free_cash(ops),
    }
