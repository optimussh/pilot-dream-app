from flask import Blueprint, render_template, jsonify, request
from app.models import db, UserBadge, LogbookEntry
import json
import os
from collections import defaultdict

bp = Blueprint('badges', __name__, url_prefix='/badges')

def load_badges():
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'badges.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

ALL_BADGES = load_badges()

def get_unlocked_badge_ids():
    return [b.badge_id for b in UserBadge.query.all()]

def compute_user_progress():
    """Compute current user stats from logbook"""
    entries = LogbookEntry.query.all()
    
    total_hours = sum(e.hours for e in entries)
    flight_count = len(entries)
    
    # Per aircraft hours
    aircraft_hours = defaultdict(float)
    for e in entries:
        if e.aircraft:
            aircraft_hours[e.aircraft] += e.hours
    
    # Simple ATC proxy (can be improved later with actual learning tracking)
    atc_phrases = min(flight_count * 3, 250)
    
    return {
        "total_hours": round(total_hours, 1),
        "flight_count": flight_count,
        "aircraft_hours": dict(aircraft_hours),
        "atc_phrases": atc_phrases
    }

def get_badge_progress(badge, progress):
    """Calculate progress percentage for a badge"""
    req = badge.get("requirement", {})
    req_type = req.get("type")
    
    if req_type == "total_hours":
        current = progress["total_hours"]
        target = req.get("value", 1)
        return min(100, int((current / target) * 100)), current, target
    
    elif req_type == "flight_count":
        current = progress["flight_count"]
        target = req.get("value", 1)
        return min(100, int((current / target) * 100)), current, target
    
    elif req_type == "aircraft_hours":
        ac = req.get("aircraft")
        current = progress["aircraft_hours"].get(ac, 0)
        target = req.get("value", 1)
        return min(100, int((current / target) * 100)), current, target
    
    elif req_type == "atc_phrases":
        current = progress["atc_phrases"]
        target = req.get("value", 1)
        return min(100, int((current / target) * 100)), current, target
    
    else:
        # Special / manual badges
        return 0, 0, 1

@bp.route('/')
def index():
    unlocked_ids = set(get_unlocked_badge_ids())
    progress = compute_user_progress()
    
    unlocked = []
    locked = []
    
    for badge in ALL_BADGES:
        pct, current, target = get_badge_progress(badge, progress)
        badge_copy = badge.copy()
        badge_copy["progress"] = pct
        badge_copy["current"] = current
        badge_copy["target"] = target
        
        if badge["id"] in unlocked_ids:
            unlocked.append(badge_copy)
        else:
            locked.append(badge_copy)
    
    # Group by category for better display
    from collections import defaultdict
    locked_by_category = defaultdict(list)
    for b in locked:
        locked_by_category[b["category"]].append(b)
    
    return render_template(
        'badges.html', 
        unlocked=unlocked, 
        locked=locked, 
        locked_by_category=dict(locked_by_category),
        progress=progress,
        all_badges=ALL_BADGES
    )

@bp.route('/api/progress')
def api_progress():
    """API for dashboard and other pages"""
    progress = compute_user_progress()
    unlocked_ids = set(get_unlocked_badge_ids())
    
    # Find next most achievable badge
    next_badge = None
    best_progress = -1
    
    for badge in ALL_BADGES:
        if badge["id"] in unlocked_ids:
            continue
        pct, current, target = get_badge_progress(badge, progress)
        if pct > best_progress:
            best_progress = pct
            next_badge = badge
            next_badge["progress"] = pct
            next_badge["current"] = current
            next_badge["target"] = target
    
    return jsonify({
        "progress": progress,
        "unlocked_count": len(unlocked_ids),
        "total_badges": len(ALL_BADGES),
        "next_badge": next_badge
    })

@bp.route('/unlock', methods=['POST'])
def unlock_badge():
    data = request.get_json()
    badge_id = data.get('badge_id')
    
    unlocked_ids = get_unlocked_badge_ids()
    
    valid_ids = [b['id'] for b in ALL_BADGES]
    
    if badge_id in valid_ids and badge_id not in unlocked_ids:
        new_badge = UserBadge(badge_id=badge_id)
        db.session.add(new_badge)
        db.session.commit()
        return jsonify({"success": True, "badge_id": badge_id})
    
    return jsonify({"success": False})