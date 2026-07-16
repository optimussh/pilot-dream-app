"""Full-app smoke: pages, APIs, captain-life quizzes, airline revenue, learn."""
import traceback
from app import create_app

app = create_app()
c = app.test_client()
errors = []
ok_n = 0


def check(cond, msg):
    global ok_n
    if cond:
        ok_n += 1
        print(f'  OK: {msg}')
    else:
        errors.append(msg)
        print(f'FAIL: {msg}')


print('=== GET pages & APIs ===')
routes = [
    '/', '/learn', '/quiz', '/flashcards', '/scenarios',
    '/captain-life', '/airline', '/shop', '/hangar', '/radar/', '/logbook/',
    '/guide', '/world', '/api/gamification/status',
    '/api/gamification/quiz', '/api/gamification/flashcard/daily',
    '/api/gamification/scenarios', '/api/extras/summary',
    '/api/airline/dashboard', '/api/airline/revenue',
    '/api/extras/fuel-quiz', '/api/extras/codex',
    '/api/player/stats', '/api/guide/sections',
    '/api/economy/wallet', '/api/shop/items',
]
for path in routes:
    try:
        r = c.get(path, follow_redirects=True)
        check(r.status_code == 200, f'GET {path} -> {r.status_code}')
        if r.status_code != 200:
            try:
                print('   body:', (r.get_data(as_text=True) or '')[:200])
            except Exception:
                pass
    except Exception as e:
        errors.append(f'GET {path} EXC {e}')
        print(f'EXC: GET {path}: {e}')

print('\n=== Captain life quizzes ===')
with app.app_context():
    from app.services.gamification import get_or_create_progress, today_str
    from app.services.pilot_extras import (
        _meta, _save_meta, _airport_fact_for_today, _prepare_airport_quiz,
        submit_daily_airport_quiz, get_fuel_quiz, submit_fuel_quiz,
        _prepare_fuel_quiz, get_extras_summary,
    )
    from app.services.airline_revenue import (
        fetch_revenue_dashboard, accept_cargo, complete_cargo, answer_briefing,
        set_mro_desk, claim_seasonal,
    )
    from app.services.airline_ops import (
        get_airline_dashboard, estimate_weekly_revenue, set_ancillary,
    )
    from app.models import db
    from app.services.content_bank import shuffle_quiz_choices

    prog = get_or_create_progress()

    # Airport: reset + correct answer
    try:
        ex = _meta(prog)
        ex['daily_airport'] = {}
        _save_meta(prog, ex)
        db.session.commit()
        ap = _airport_fact_for_today(today_str())
        prep = _prepare_airport_quiz(ap['id'], ap['quiz'], today_str())
        ok, result = submit_daily_airport_quiz(prog, prep['answer'])
        check(ok and result.get('correct') is True, f'airport correct: {result}')
    except Exception as e:
        errors.append(f'airport correct: {e}')
        traceback.print_exc()

    # Airport: reset + wrong answer still works
    try:
        ex = _meta(prog)
        ex['daily_airport'] = {}
        _save_meta(prog, ex)
        db.session.commit()
        ap = _airport_fact_for_today(today_str())
        prep = _prepare_airport_quiz(ap['id'], ap['quiz'], today_str())
        wrong = (prep['answer'] + 1) % max(len(prep['choices']), 1)
        ok, result = submit_daily_airport_quiz(prog, wrong)
        check(ok and result.get('correct') is False, f'airport wrong: {result}')
    except Exception as e:
        errors.append(f'airport wrong: {e}')
        traceback.print_exc()

    # Fuel quiz correct
    try:
        ex = _meta(prog)
        ex['fuel_quiz_today'] = 0
        ex['fuel_quiz_date'] = today_str()
        _save_meta(prog, ex)
        db.session.commit()
        q, err = get_fuel_quiz(prog)
        check(q is not None and not err, f'fuel get: {err}')
        if q:
            prep = _prepare_fuel_quiz(q['id'], today_str(), 0)
            ok, result = submit_fuel_quiz(prog, q['id'], prep['answer'])
            check(ok and result.get('correct') is True, f'fuel correct: {result}')
    except Exception as e:
        errors.append(f'fuel correct: {e}')
        traceback.print_exc()

    # Shuffle integrity: answer text preserved
    try:
        bad = 0
        for i, fq in enumerate([
            {'id': 't1', 'choices': ['A', 'B', 'C', 'D'], 'answer': 0},
            {'id': 't2', 'choices': ['A', 'B', 'C', 'D'], 'answer': 2},
            {'id': 't3', 'choices': ['A', 'B', 'C', 'D'], 'answer': 3},
        ]):
            for seed in [f's{i}', f's{i}x', f'y{i}']:
                p = shuffle_quiz_choices(fq, seed=seed)
                if p['choices'][p['answer']] != fq['choices'][fq['answer']]:
                    bad += 1
        check(bad == 0, f'shuffle integrity (bad={bad})')
    except Exception as e:
        errors.append(f'shuffle: {e}')
        traceback.print_exc()

    print('\n=== Airline revenue ===')
    try:
        dash = get_airline_dashboard(prog)
        founded = bool(dash.get('airline', {}).get('founded'))
        check(True, f'airline founded={founded}')
        if founded:
            rp = dash.get('ops', {}).get('revenue_panel')
            check(rp is not None, 'dashboard has revenue_panel')
            rd = fetch_revenue_dashboard(prog)
            panel = rd.get('revenue_panel') or {}
            check(len(panel.get('cargo_offers', [])) == 3, 'cargo offers=3')
            check(len(panel.get('briefings', [])) == 5, 'briefings=5')
            est = estimate_weekly_revenue(prog)
            check('gross' in est and 'side_income' in est, f'estimate gross={est.get("gross")}')

            brief = panel['briefings'][0]
            # may already be done
            ok, msg, fee = answer_briefing(prog, brief['idx'], brief['answer'])
            check(ok or '이미' in str(msg), f'briefing: {msg}')

            opens = [o for o in panel.get('cargo_offers', []) if o.get('status') == 'open']
            if opens:
                o = opens[0]
                ok, msg = accept_cargo(prog, o['id'])
                check(ok or '이미' in str(msg), f'cargo accept: {msg}')
                ans = (o.get('quiz') or {}).get('answer', 0)
                ok, msg, pay = complete_cargo(prog, o['id'], ans)
                check(ok or '이미' in str(msg) or '먼저' in str(msg), f'cargo complete: {msg}')

            ok, msg = set_ancillary(prog, 'basic')
            check(ok, f'ancillary: {msg}')
        else:
            check(True, 'skip revenue actions (airline not founded)')
    except Exception as e:
        errors.append(f'revenue: {e}')
        traceback.print_exc()

    print('\n=== Learn APIs ===')
    try:
        r = c.get('/api/gamification/quiz')
        d = r.get_json() or {}
        qs = d.get('questions') or []
        check(len(qs) > 0 or d.get('daily_done'), f'quiz qs={len(qs)} done={d.get("daily_done")}')
        for q in qs[:3]:
            check('answer' not in q, f'quiz public no answer ({q.get("id")})')

        r = c.get('/api/gamification/flashcard/daily')
        d = r.get_json() or {}
        cards = d.get('cards') or []
        check(len(cards) == 5 or d.get('daily_done') or d.get('extra_done') or d.get('mode') == 'extra',
              f'flashcards n={len(cards)} mode={d.get("mode")}')

        r = c.get('/api/gamification/scenarios')
        d = r.get_json() or {}
        sc = d.get('scenarios') or d.get('items') or []
        check(len(sc) > 0 or d.get('daily_done') or d.get('extra_done'),
              f'scenarios n={len(sc)} done={d.get("daily_done")}')

        # quiz submit with string answer indices (regression: TypeError)
        from app.services.gamification import get_daily_learning, save_daily_learning, today_str
        from app.services.content_bank import get_quiz_bank, prepare_quiz_questions, lookup_by_ids
        from app.models import db as _db
        dl = get_daily_learning(prog)
        for k in list(dl.keys()):
            if 'quiz' in k:
                dl.pop(k, None)
        save_daily_learning(prog, dl)
        _db.session.commit()
        r = c.get('/api/gamification/quiz')
        d = r.get_json() or {}
        if not d.get('daily_done'):
            dl = get_daily_learning(prog)
            qd = dl.get('quiz', {})
            ids = qd.get('ids') or []
            prepared = qd.get('prepared')
            if not prepared and ids:
                prepared = prepare_quiz_questions(lookup_by_ids(get_quiz_bank(), ids), today_str())
            if prepared:
                answers_str = {q['id']: str(q['answer']) for q in prepared}
                r = c.post('/api/gamification/quiz/submit',
                           json={'answers': answers_str, 'question_ids': ids})
                j = r.get_json() or {}
                check(r.status_code == 200 and j.get('score') == 100,
                      f'quiz string answers score={j.get("score")} err={j.get("error")}')
    except Exception as e:
        errors.append(f'learn: {e}')
        traceback.print_exc()

    print('\n=== Extras summary integrity ===')
    try:
        s = get_extras_summary(prog)
        for key in ('captain_duty', 'daily_airport', 'crew_cards', 'schedule', 'on_time'):
            check(key in s, f'summary has {key}')
        ap = s.get('daily_airport') or {}
        q = ap.get('quiz') or {}
        check('answer' not in q, 'airport quiz hides answer')
    except Exception as e:
        errors.append(f'summary: {e}')
        traceback.print_exc()

print(f'\n=== Results: {ok_n} passed, {len(errors)} failed ===')
for e in errors:
    print(f'  - {e}')
if errors:
    raise SystemExit(1)
print('\nAll full-smoke checks passed!')
