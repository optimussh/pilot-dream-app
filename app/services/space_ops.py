"""우주 사업부 — SpaceX 스타일 후반 챕터"""
from app.models import db
from app.services.gamification import load_json, today_str
from app.services.economy import award_money, format_krw
from app.services.pilot_features import get_meta, save_meta, get_airline_info


def _space(prog):
    meta = get_meta(prog)
    default = {
        'unlocked': False,
        'founded': False,
        'rockets_owned': [],
        'missions_done': [],
        'launches': 0,
        'last_launch_date': '',
    }
    sp = meta.setdefault('space_ops', {})
    for k, v in default.items():
        sp.setdefault(k, v if not isinstance(v, list) else list(v))
    return sp


def _save(prog, sp):
    meta = get_meta(prog)
    meta['space_ops'] = sp
    save_meta(prog, meta)


def check_space_unlock(prog):
    cfg = load_json('player_stats_config.json') or {}
    req = cfg.get('space_unlock', {})
    sp = _space(prog)
    if sp.get('unlocked'):
        return True
    from app.services.player_stats import get_player_stats
    from app.services.airline_ops import _ops
    stats = get_player_stats(prog)
    airline = get_airline_info(prog)
    ops = _ops(prog)
    if not airline.get('founded'):
        return False
    if ops.get('level', 1) < req.get('airline_level', 5):
        return False
    imagination = next((s['value'] for s in stats.get('stats', []) if s['id'] == 'imagination'), 0)
    if imagination < req.get('imagination', 30):
        return False
    if stats.get('stat_sum', 0) < req.get('total_stat_sum', 80):
        return False
    sp['unlocked'] = True
    _save(prog, sp)
    db.session.commit()
    return True


def get_space_status(prog):
    catalog = load_json('space_catalog.json') or {}
    sp = _space(prog)
    unlocked = check_space_unlock(prog) or sp.get('unlocked')
    cfg = load_json('player_stats_config.json') or {}
    req = cfg.get('space_unlock', {})
    from app.services.player_stats import get_player_stats
    from app.services.airline_ops import _ops
    stats = get_player_stats(prog)
    ops = _ops(prog)
    imagination = next((s['value'] for s in stats.get('stats', []) if s['id'] == 'imagination'), 0)
    progress = {
        'airline_level': ops.get('level', 0),
        'need_level': req.get('airline_level', 5),
        'imagination': imagination,
        'need_imagination': req.get('imagination', 30),
        'stat_sum': stats.get('stat_sum', 0),
        'need_stat_sum': req.get('total_stat_sum', 80),
    }
    rockets = []
    for r in catalog.get('rockets', []):
        rockets.append({**r, 'owned': r['id'] in sp.get('rockets_owned', [])})
    missions = []
    for m in catalog.get('missions', []):
        missions.append({
            **m,
            'done': m['id'] in sp.get('missions_done', []),
            'can_launch': m['id'] not in sp.get('missions_done', []) and m.get('rocket') in sp.get('rockets_owned', []),
        })
    return {
        'unlocked': unlocked,
        'founded': sp.get('founded', False),
        'rockets': rockets,
        'missions': missions,
        'launches': sp.get('launches', 0),
        'unlock_progress': progress,
        'kid_hint': '항공사 Lv.5 + 상상력 30 + 능력 합 80이면 우주가 열려요!' if not unlocked else '로켓을 사고 미션을 띄워보세요!',
    }


def found_space_division(prog, name='드림 스페이스'):
    if not check_space_unlock(prog):
        return False, '아직 우주 사업 조건이 안 됐어요!'
    sp = _space(prog)
    if sp.get('founded'):
        return True, '이미 우주 사업부가 있어요!'
    sp['founded'] = True
    _save(prog, sp)
    award_money(prog, 3_000_000, '우주 사업부 설립')
    db.session.commit()
    return True, f'🚀 {name} 우주 사업부 설립!'


def buy_rocket(prog, rocket_id):
    if not check_space_unlock(prog):
        return False, '우주 챕터가 아직 잠겨 있어요!'
    catalog = {r['id']: r for r in load_json('space_catalog.json').get('rockets', [])}
    rocket = catalog.get(rocket_id)
    if not rocket:
        return False, '로켓을 찾을 수 없어요.'
    sp = _space(prog)
    owned = sp.get('rockets_owned', [])
    if rocket_id in owned:
        return False, '이미 보유한 로켓이에요!'
    from app.services.economy import spend_money
    ok, msg = spend_money(prog, rocket['price'], f"로켓 구매: {rocket['name']}")
    if not ok:
        return False, msg
    owned.append(rocket_id)
    sp['rockets_owned'] = owned
    _save(prog, sp)
    db.session.commit()
    return True, f'{rocket["emoji"]} {rocket["name"]} 구매 완료!'


def launch_mission(prog, mission_id):
    if not check_space_unlock(prog):
        return False, '우주 챕터 잠김'
    catalog = {m['id']: m for m in load_json('space_catalog.json').get('missions', [])}
    mission = catalog.get(mission_id)
    if not mission:
        return False, '미션을 찾을 수 없어요.'
    sp = _space(prog)
    if mission_id in sp.get('missions_done', []):
        return False, '이미 완료한 미션이에요!'
    if mission.get('rocket') not in sp.get('rockets_owned', []):
        return False, '필요한 로켓을 먼저 구매하세요!'
    today = today_str()
    if sp.get('last_launch_date') == today:
        return False, '로켓은 하루에 1번만 발사할 수 있어요!'
    done = sp.get('missions_done', [])
    done.append(mission_id)
    sp['missions_done'] = done
    sp['launches'] = sp.get('launches', 0) + 1
    sp['last_launch_date'] = today
    _save(prog, sp)
    award_money(prog, mission.get('reward_money', 0), f"우주 미션: {mission['name']}")
    try:
        from app.services.player_stats import add_stat_xp
        add_stat_xp(prog, 'imagination', mission.get('reward_imagination', 20), 'space')
        apply_activity_stats = None
        from app.services.player_stats import apply_activity_stats as aas
        aas(prog, 'space_launch')
    except Exception:
        pass
    db.session.commit()
    return True, f'{mission["emoji"]} {mission["name"]} 성공! {format_krw(mission.get("reward_money", 0))}'