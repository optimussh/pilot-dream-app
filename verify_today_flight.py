"""Today's flight: favorite route, more-menu ranking, duty APIs."""
from types import SimpleNamespace
from app.services.today_flight import pick_route_from_entries, rank_more_items, MORE_CATALOG


class FakeProg:
    def __init__(self, meta=None, log=None):
        import json
        self._store = {
            'pilot_meta': json.dumps(meta or {}, ensure_ascii=False),
            'activity_log': json.dumps(log or [], ensure_ascii=False),
        }

    def _json(self, field, default):
        import json
        try:
            return json.loads(self._store.get(field) or json.dumps(default))
        except (json.JSONDecodeError, TypeError):
            return default

    def set_json(self, field, value):
        import json
        self._store[field] = json.dumps(value, ensure_ascii=False)


def test_pick_fallback():
    f = pick_route_from_entries([])
    assert f['route'] == 'ICN-CJU', f
    assert f['dest'] == 'CJU'


def test_pick_favorite_longhaul():
    rows = [
        SimpleNamespace(route='TPE-JFK', flight_number='BR001', aircraft='Boeing 777-300ER', hours=14),
        SimpleNamespace(route='TPE-JFK', flight_number='BR001', aircraft='Boeing 777-300ER', hours=14),
        SimpleNamespace(route='ICN-CJU', flight_number='7C101', aircraft='B737-800', hours=1.2),
    ]
    f = pick_route_from_entries(rows)
    assert f['route'] == 'TPE-JFK', f
    assert f['flight_number'] == 'BR001'
    assert f['dest'] == 'JFK'
    assert f['hours'] == 14


def test_more_menu_arcade_rises():
    prog = FakeProg(
        meta={'minigames': {'refuel': {'played': 35}, 'landing': {'played': 15}}},
        log=[{'type': 'pricing_lab'}] * 5,
    )
    ranked = rank_more_items(prog)
    ids = [x['id'] for x in ranked]
    assert ids[0] == 'arcade', ids
    assert 'world' in ids[:4]
    assert [x['id'] for x in ranked if x['id'] == 'guide']
    assert len(ranked) == len(MORE_CATALOG)


if __name__ == '__main__':
    test_pick_fallback()
    print('  OK: fallback ICN-CJU')
    test_pick_favorite_longhaul()
    print('  OK: favorite TPE-JFK')
    test_more_menu_arcade_rises()
    print('  OK: more menu ranks arcade first')

    from app import create_app
    app = create_app()
    c = app.test_client()
    r = c.get('/api/duty/today')
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    d = r.get_json()
    assert d.get('flight', {}).get('route'), d
    assert len(d.get('steps') or []) == 5, d
    print(f"  OK: GET /api/duty/today route={d['flight']['route']} next={d.get('next_step')}")

    r = c.get('/api/nav/more')
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    items = (r.get_json() or {}).get('items') or []
    assert len(items) >= 8, items
    print(f"  OK: GET /api/nav/more first={items[0].get('id')} n={len(items)}")

    r = c.post('/api/duty/skip', json={'step_id': 'airport'})
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    print('  OK: POST skip airport')

    r = c.get('/captain-day')
    assert r.status_code == 200
    print('  OK: GET /captain-day')
    print('All today-flight checks passed!')
