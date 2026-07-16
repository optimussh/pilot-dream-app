"""플레이어 RPG 능력치 — 6스탯 + 레벨"""
from app.models import db
from app.services.gamification import load_json


def _cfg():
    return load_json('player_stats_config.json') or {}


def _meta(prog):
    pm = prog._json('pilot_meta', {})
    default = {
        'stats': {s['id']: 0 for s in _cfg().get('stats', [])},
        'stat_xp': {s['id']: 0 for s in _cfg().get('stats', [])},
        'stat_points': 0,
        'player_level': 1,
        'total_xp': 0,
    }
    ps = pm.setdefault('player_stats', {})
    for k, v in default.items():
        if k == 'stats' or k == 'stat_xp':
            ps.setdefault(k, {})
            for sid in default['stats']:
                ps[k].setdefault(sid, 0)
        else:
            ps.setdefault(k, v if not isinstance(v, dict) else dict(v))
    return ps


def _save(prog, ps):
    pm = prog._json('pilot_meta', {})
    pm['player_stats'] = ps
    prog.set_json('pilot_meta', pm)


def add_stat_xp(prog, stat_id, amount, reason=''):
    if amount <= 0:
        return None
    cfg = _cfg()
    valid = {s['id'] for s in cfg.get('stats', [])}
    if stat_id not in valid:
        return None
    ps = _meta(prog)
    xp_per = cfg.get('xp_per_level', 100)
    ps['stat_xp'][stat_id] = ps['stat_xp'].get(stat_id, 0) + amount
    ps['total_xp'] = ps.get('total_xp', 0) + amount
    leveled = []
    while ps['stat_xp'][stat_id] >= xp_per:
        ps['stat_xp'][stat_id] -= xp_per
        ps['stats'][stat_id] = ps['stats'].get(stat_id, 0) + 1
        ps['stat_points'] = ps.get('stat_points', 0) + 1
        leveled.append(stat_id)
    old_lvl = ps.get('player_level', 1)
    stat_sum = sum(ps['stats'].values())
    ps['player_level'] = max(1, 1 + stat_sum // 6)
    if ps['player_level'] > old_lvl:
        ps['stat_points'] = ps.get('stat_points', 0) + 2
    _save(prog, ps)
    db.session.commit()
    return {'stat': stat_id, 'amount': amount, 'leveled': leveled, 'reason': reason}


def allocate_stat_point(prog, stat_id):
    cfg = _cfg()
    valid = {s['id'] for s in cfg.get('stats', [])}
    if stat_id not in valid:
        return False, '능력을 찾을 수 없어요.'
    ps = _meta(prog)
    if ps.get('stat_points', 0) < 1:
        return False, '능력 포인트가 없어요! 더 활동해보세요.'
    ps['stat_points'] -= 1
    ps['stats'][stat_id] = ps['stats'].get(stat_id, 0) + 1
    stat_sum = sum(ps['stats'].values())
    ps['player_level'] = max(1, 1 + stat_sum // 6)
    _save(prog, ps)
    db.session.commit()
    return True, ''


def get_player_stats(prog):
    ps = _meta(prog)
    cfg = _cfg()
    stat_defs = {s['id']: s for s in cfg.get('stats', [])}
    xp_per = cfg.get('xp_per_level', 100)
    result = []
    level_cap = max(12, cfg.get('bar_level_cap', 12))
    band = 100 / level_cap
    for sid, sdef in stat_defs.items():
        val = ps['stats'].get(sid, 0)
        xp = ps['stat_xp'].get(sid, 0)
        xp_ratio = (xp / xp_per) if xp_per else 0
        # 레벨(메인) + 다음 레벨까지 XP(세부) — 레벨이 오르면 바도 함께 오름
        pct = min(100, int(val * band + xp_ratio * band * 0.9))
        result.append({
            **sdef,
            'value': val,
            'xp': xp,
            'xp_need': xp_per,
            'pct': pct,
        })
    return {
        'stats': result,
        'stat_points': ps.get('stat_points', 0),
        'player_level': ps.get('player_level', 1),
        'total_xp': ps.get('total_xp', 0),
        'stat_sum': sum(ps['stats'].values()),
        'space_unlock_hint': cfg.get('space_unlock', {}),
    }


def apply_activity_stats(prog, activity_type, extra=None):
    """활동 유형별 스탯 XP 부여"""
    mapping = {
        'logbook': ('flying', 25),
        'quiz': ('knowledge', 20),
        'quiz_high': ('knowledge', 35),
        'flashcard': ('knowledge', 10),
        'mission': ('knowledge', 15),
        'airport_quiz': ('navigation', 12),
        'route_challenge': ('navigation', 20),
        'planner': ('navigation', 15),
        'crew_unlock': ('leadership', 18),
        'airline_settle': ('business', 30),
        'airline_hire': ('leadership', 15),
        'shop_buy': ('business', 8),
        'season': ('imagination', 25),
        'space_launch': ('imagination', 50),
        'captain_duty': ('leadership', 12),
    }
    pair = mapping.get(activity_type)
    if not pair:
        return None
    stat, amt = pair
    if extra and isinstance(extra, (int, float)):
        amt = int(amt * extra)
    return add_stat_xp(prog, stat, amt, activity_type)