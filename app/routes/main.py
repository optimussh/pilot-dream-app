from flask import Blueprint, render_template, jsonify, request
from app.models import db, LogbookEntry, UserBadge, UserRadarFlight
from datetime import datetime
import json
import os

bp = Blueprint('main', __name__)

def load_json_data(filename):
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@bp.route('/')
def dashboard():
    entries = LogbookEntry.query.all()
    total_hours = sum(e.hours for e in entries)
    aircraft_set = {e.aircraft for e in entries if e.aircraft}
    
    return render_template(
        'dashboard.html', 
        total_hours=round(total_hours, 1),
        aircraft_types=len(aircraft_set),
        flight_count=len(entries)
    )

@bp.route('/api/logbook/add', methods=['POST'])
def add_logbook_entry():
    data = request.get_json()
    
    entry = LogbookEntry(
        date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
        flight_number=data.get("flight_number"),
        aircraft=data.get("aircraft"),
        route=data.get("route"),
        hours=float(data.get("hours", 0)),
        notes=data.get("notes", "")
    )
    db.session.add(entry)
    db.session.commit()
    
    # Auto badge check - 강화된 버전
    try:
        from app.routes.badges import ALL_BADGES, UserBadge
        from collections import defaultdict
        
        entries = LogbookEntry.query.all()
        total_hours = sum(e.hours for e in entries)
        flight_count = len(entries)
        
        # 기종별 시간 집계
        aircraft_hours = defaultdict(float)
        for e in entries:
            if e.aircraft:
                aircraft_hours[e.aircraft] += e.hours
        
        unlocked = {b.badge_id for b in UserBadge.query.all()}
        
        for badge in ALL_BADGES:
            if badge['id'] in unlocked:
                continue
                
            req = badge.get('requirement', {})
            req_type = req.get('type')
            unlocked_new = False
            
            if req_type == 'total_hours' and total_hours >= req.get('value', 0):
                unlocked_new = True
            elif req_type == 'flight_count' and flight_count >= req.get('value', 0):
                unlocked_new = True
            elif req_type == 'aircraft_hours':
                ac_name = req.get('aircraft')
                if ac_name and aircraft_hours.get(ac_name, 0) >= req.get('value', 0):
                    unlocked_new = True
            
            if unlocked_new:
                new_badge = UserBadge(badge_id=badge['id'])
                db.session.add(new_badge)
                db.session.commit()
                
    except Exception as e:
        pass  # fail silently for now
    
    return jsonify({"status": "success"})

@bp.route('/api/logbook')
def get_logbook():
    entries = LogbookEntry.query.order_by(LogbookEntry.date.desc()).all()
    return jsonify([{
        "date": e.date,
        "flight_number": e.flight_number,
        "aircraft": e.aircraft,
        "route": e.route,
        "hours": e.hours,
        "notes": e.notes
    } for e in entries])

@bp.route('/api/logbook/reset', methods=['POST'])
def reset_logbook():
    """전체 비행 기록 + 뱃지 + 사용자 레이더 항공편 초기화 (완전 리셋)"""
    try:
        LogbookEntry.query.delete()
        UserBadge.query.delete()
        UserRadarFlight.query.delete()
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": "모든 비행 기록, 획득 뱃지, 사용자 레이더 항공편이 초기화되었습니다."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@bp.route('/api/airports')
def get_airports():
    airports = load_json_data('airports.json')
    return jsonify(airports)

@bp.route('/api/aircraft')
def get_aircraft():
    aircraft = load_json_data('aircraft.json')
    return jsonify(aircraft)

@bp.route('/api/flights')
def get_flights():
    flights = load_json_data('flights_db.json')
    return jsonify(flights)


@bp.route('/api/atc')
def get_atc():
    atc = load_json_data('atc_phrases.json')
    return jsonify(atc)


# ==================== Radar User Flights API ====================

@bp.route("/api/radar/flights")
def get_user_radar_flights():
    """사용자가 추가한 레이더 항공편 조회"""
    flights = UserRadarFlight.query.order_by(UserRadarFlight.created_at.desc()).all()
    return jsonify([{
        "id": f.id,
        "callsign": f.callsign,
        "org_id": f.org_id,
        "dest_id": f.dest_id,
        "ac_name": f.ac_name,
        "is_korea": f.is_korea
    } for f in flights])


@bp.route("/api/radar/flights", methods=["POST"])
def add_user_radar_flight():
    """새로운 사용자 항공편 추가 (최대 20개 제한)"""
    data = request.get_json()
    
    # 최대 20개 제한
    current_count = UserRadarFlight.query.count()
    if current_count >= 20:
        return jsonify({
            "status": "error",
            "message": "사용자 항공편은 최대 20개까지만 추가할 수 있습니다."
        }), 400
    
    flight = UserRadarFlight(
        callsign=data.get("callsign", "CUSTOM001"),
        org_id=data["org_id"],
        dest_id=data["dest_id"],
        ac_name=data.get("ac_name", "B737-800"),
        is_korea=data.get("is_korea", False)
    )
    db.session.add(flight)
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "flight": {
            "id": flight.id,
            "callsign": flight.callsign,
            "org_id": flight.org_id,
            "dest_id": flight.dest_id
        }
    })


@bp.route("/api/radar/flights/<int:flight_id>", methods=["DELETE"])
def delete_user_radar_flight(flight_id):
    """사용자 항공편 삭제"""
    flight = UserRadarFlight.query.get(flight_id)
    if not flight:
        return jsonify({"status": "error", "message": "Flight not found"}), 404
    
    db.session.delete(flight)
    db.session.commit()
    
    return jsonify({"status": "success"})
