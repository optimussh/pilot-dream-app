"""Smoke test for airline treasury (capital / lend / borrow / interest)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, UserProgress
from app.services.airline_ops import _ops, _save_ops
from app.services.airline_treasury import (
    MIN_TX,
    deposit_capital,
    deposit_loan,
    recover_capital,
    recover_loan,
    borrow_from_company,
    repay_borrow,
    settle_treasury_interest,
    build_treasury_panel,
    free_cash,
    ensure_treasury,
)


def main():
    app = create_app()
    ok_all = True
    with app.app_context():
        prog = UserProgress.query.first()
        if not prog:
            print('FAIL: no UserProgress')
            return 1
        prog.wallet_balance = 50_000_000
        ops = _ops(prog)
        ops['company_vault'] = 0
        ops['treasury'] = {
            'capital': 0,
            'loan_to_company': 0,
            'loan_from_company': 0,
            'interest_week': '',
            'log': [],
        }
        # ensure founded flag path
        from app.services.pilot_features import get_airline_info, found_airline
        info = get_airline_info(prog)
        if not info.get('founded'):
            # minimal found
            ok, msg = found_airline(prog, 'Treasury Test Air', '🧪')
            print('found:', ok, msg)
        _save_ops(prog, ops)
        db.session.commit()

        def check(cond, label):
            nonlocal ok_all
            if cond:
                print('OK ', label)
            else:
                print('FAIL', label)
                ok_all = False

        w0 = prog.wallet_balance
        ok, msg = deposit_capital(prog, 100_000)
        check(ok and prog.wallet_balance == w0 - 100_000, f'capital deposit {msg}')
        ops = _ops(prog)
        t = ensure_treasury(ops)
        check(ops['company_vault'] == 100_000 and t['capital'] == 100_000, 'vault/capital after deposit')

        ok, msg = deposit_loan(prog, 200_000)
        check(ok, f'lend {msg}')
        ops = _ops(prog)
        t = ensure_treasury(ops)
        check(t['loan_to_company'] == 200_000 and ops['company_vault'] == 300_000, 'lend balances')

        # free cash = 300k - 100k - 200k = 0 → borrow should fail
        ok, msg = borrow_from_company(prog, MIN_TX)
        check(not ok, f'borrow blocked when free=0 ({msg})')

        # add free cash via vault without capital (simulate)
        ops = _ops(prog)
        ops['company_vault'] = int(ops['company_vault']) + 500_000
        _save_ops(prog, ops)
        db.session.commit()
        free = free_cash(_ops(prog))
        check(free == 500_000, f'free cash {free}')
        max_b = int(free * 0.5)
        ok, msg = borrow_from_company(prog, max_b)
        check(ok, f'borrow {msg}')
        ops = _ops(prog)
        t = ensure_treasury(ops)
        check(t['loan_from_company'] == max_b, 'debt principal')

        # interest
        t['interest_week'] = ''
        _save_ops(prog, ops)
        db.session.commit()
        w_before = prog.wallet_balance
        result = settle_treasury_interest(prog, force=True)
        db.session.commit()
        check(result is not None, f'interest result {result}')
        # 대여 이자 수령 + 차입 이자 납부 → 순액은 음수일 수 있음
        check(
            result.get('lend_interest', 0) == 1000
            and result.get('borrow_interest', 0) == 1875,
            f'interest amounts lend={result.get("lend_interest")} borrow={result.get("borrow_interest")}',
        )
        expected_wallet = w_before + result['lend_interest'] - result['borrow_interest']
        check(prog.wallet_balance == expected_wallet, f'wallet after interest {prog.wallet_balance}=={expected_wallet}')

        ok, msg = recover_loan(prog, 50_000)
        check(ok, f'recover loan {msg}')
        ok, msg = recover_capital(prog, 50_000)
        check(ok, f'recover capital {msg}')
        ok, msg = repay_borrow(prog, 50_000)
        check(ok, f'repay {msg}')

        panel = build_treasury_panel(prog)
        check(panel and 'company_cash' in panel, 'panel builds')
        check(panel['min_tx'] == MIN_TX, 'min_tx')

    print('RESULT', 'PASS' if ok_all else 'FAIL')
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
