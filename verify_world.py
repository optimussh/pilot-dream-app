"""세계 경제 / 꿈 유지 기능 스모크 테스트"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.services.gamification import get_or_create_progress
from app.services import world_economy as we

app = create_app()

def main():
    with app.app_context():
        prog = get_or_create_progress()
        print('1. sky times...')
        st = we.get_sky_times(prog)
        assert st.get('papers'), 'no papers'
        print('   papers', len(st['papers']), 'oil', st.get('oil', {}).get('price'))

        print('2. multipliers...')
        m = we.get_world_multipliers(prog)
        assert m.get('demand_mult')
        print('   demand', m['demand_mult'], 'fuel', m['fuel_cost_mult'])

        print('3. flight story...')
        s = we.get_flight_story('ICN', 'LAX')
        assert s.get('title')
        print('   ', s['emoji'], s['title'])

        print('4. pricing lab...')
        ok, msg, res = we.run_pricing_lab(prog, 'jeju_weekend', 1.0)
        assert ok, msg
        print('   ', res.get('kid_summary'))

        print('5. trade mission step...')
        ok, msg, extra = we.advance_trade(prog, 'trade_chips')
        assert ok, msg
        print('   ', msg[:60])

        print('6. hub mission...')
        hubs = we.get_hub_missions(prog)
        assert hubs
        # may already be done from re-runs
        h = hubs[0]
        if not h.get('done'):
            ok, msg = we.complete_hub_mission(prog, h['id'], h['quiz']['answer'])
            assert ok, msg
            print('   ', msg[:60])
        else:
            print('   already done')

        print('7. economy quiz...')
        q = we.get_economy_quiz(prog)
        assert q and q.get('questions')
        print('   questions', len(q['questions']))

        print('8. night sky...')
        ns = we.get_night_sky_list(prog)
        assert ns
        print('   stories', len(ns))

        print('9. alliance...')
        al = we.get_alliance_map(prog)
        assert al.get('nodes')
        print('   nodes', len(al['nodes']))

        print('10. airport codex...')
        codex = we.get_airport_codex(prog)
        assert codex.get('items')
        print('   airports', codex['total'])

        print('11. ceo report...')
        rep = we.build_ceo_report(prog)
        assert rep.get('title')
        print('   ', rep['title'], rep.get('week'))

        print('12. tourism calendar...')
        cal = we.get_tourism_calendar()
        assert cal.get('year')
        print('   month', cal['month'], cal.get('current', {}).get('theme'))

        print('13. letters...')
        letters = we.get_letter_milestones(prog)
        assert 'milestones' in letters
        print('   milestones', len(letters['milestones']))

        print('14. parent...')
        parent = we.get_parent_summary(prog)
        assert 'talk_prompts' in parent
        print('   prompts', len(parent['talk_prompts']))

        print('15. hub summary...')
        hub = we.get_world_hub_summary(prog)
        assert hub.get('sky_times')
        print('   stats', hub.get('stats'))

        print('16. HTTP routes...')
        client = app.test_client()
        for path in [
            '/world',
            '/api/world/summary',
            '/api/world/sky-times',
            '/api/world/flight-story?org=ICN&dest=CJU',
            '/api/world/pricing',
            '/api/world/trade',
            '/api/world/alliance',
            '/api/world/economy-quiz',
            '/api/world/ceo-report',
            '/api/world/parent',
        ]:
            r = client.get(path)
            assert r.status_code == 200, f'{path} -> {r.status_code}'
            print('   OK', path)

        print('\nALL WORLD FEATURES OK')

if __name__ == '__main__':
    main()
