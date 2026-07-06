from flask import Blueprint, render_template, jsonify, request
from app.models import db, LogbookEntry, UserBadge, UserRadarFlight, UserProgress, FutureLetter
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
    data = request.get_json() or {}

    date = (data.get("date") or "").strip()
    flight_number = (data.get("flight_number") or "").strip()
    aircraft = (data.get("aircraft") or "").strip()
    route = (data.get("route") or "").strip()
    notes = (data.get("notes") or "").strip()

    try:
        hours = float(data.get("hours", 0))
    except (TypeError, ValueError):
        hours = 0

    missing = []
    if not date:
        missing.append("날짜")
    if not flight_number:
        missing.append("편명")
    if not route:
        missing.append("노선")
    if not aircraft:
        missing.append("기종")
    if hours <= 0:
        missing.append("비행시간")

    if missing:
        return jsonify({
            "status": "error",
            "message": f"필수 항목을 확인해주세요: {', '.join(missing)}"
        }), 400

    if len(flight_number) > 20:
        return jsonify({
            "status": "error",
            "message": "편명이 너무 깁니다. 20자 이하로 입력해주세요."
        }), 400

    entry = LogbookEntry(
        date=date,
        flight_number=flight_number,
        aircraft=aircraft,
        route=route,
        hours=hours,
        notes=notes
    )
    db.session.add(entry)
    db.session.commit()

    salary_result = None
    try:
        from app.services.gamification import get_or_create_progress, log_activity
        from app.services.economy import process_salary
        prog = get_or_create_progress()
        log_activity(prog, 'logbook', data.get('flight_number', ''))
        salary_result = process_salary(prog)
    except Exception:
        pass
    
    # Auto badge check - 강화된 버전
    try:
        from app.routes.badges import get_all_badges, UserBadge
        from collections import defaultdict
        
        entries = LogbookEntry.query.all()
        prog = UserProgress.query.first()
        virtual = (prog.virtual_hours or 0) if prog else 0
        total_hours = sum(e.hours for e in entries) + virtual
        flight_count = len(entries)
        
        # 기종별 시간 집계
        aircraft_hours = defaultdict(float)
        for e in entries:
            if e.aircraft:
                aircraft_hours[e.aircraft] += e.hours
        
        unlocked = {b.badge_id for b in UserBadge.query.all()}
        
        for badge in get_all_badges():
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
    
    resp = {"status": "success"}
    if salary_result:
        resp["salary"] = salary_result
        prog = UserProgress.query.first()
        resp["wallet_balance"] = (prog.wallet_balance or 0) if prog else 0
    return jsonify(resp)

@bp.route('/api/logbook')
def get_logbook():
    entries = LogbookEntry.query.order_by(LogbookEntry.date.desc(), LogbookEntry.id.desc()).all()
    return jsonify([{
        "id": e.id,
        "date": e.date,
        "flight_number": e.flight_number,
        "aircraft": e.aircraft,
        "route": e.route,
        "hours": e.hours,
        "notes": e.notes
    } for e in entries])


@bp.route('/api/logbook/<int:entry_id>', methods=['DELETE'])
def delete_logbook_entry(entry_id):
    entry = LogbookEntry.query.get(entry_id)
    if not entry:
        return jsonify({
            "status": "error",
            "message": "해당 비행 기록을 찾을 수 없습니다."
        }), 404

    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "success", "message": "비행 기록이 삭제되었습니다."})


@bp.route('/api/logbook/reset', methods=['POST'])
def reset_logbook():
    """전체 비행 기록 + 뱃지 + 사용자 레이더 항공편 초기화 (완전 리셋)"""
    try:
        LogbookEntry.query.delete()
        UserBadge.query.delete()
        UserRadarFlight.query.delete()
        UserProgress.query.delete()
        FutureLetter.query.delete()
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": "모든 비행 기록, 뱃지, 학습 진행, 편지, 레이더 항공편이 초기화되었습니다."
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
    try:
        from app.services.gamification import get_or_create_progress
        from app.services.economy import aircraft_unlock_status
        prog = get_or_create_progress()
        enriched = []
        for ac in aircraft:
            st = aircraft_unlock_status(prog, ac['id'])
            enriched.append({**ac, **{k: st[k] for k in (
                'owned', 'unlocked', 'progress_pct', 'hours_remaining',
                'discounted_price', 'effective_hours'
            ) if k in st}})
        return jsonify(enriched)
    except Exception:
        return jsonify(aircraft)

@bp.route('/api/flights')
def get_flights():
    flights = load_json_data('flights_db.json')
    return jsonify(flights)


@bp.route('/api/airlines')
def get_airlines():
    airlines = load_json_data('airlines.json')
    return jsonify(airlines)


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
    try:
        data = request.get_json(silent=True) or {}

        callsign = (data.get("callsign") or "MY-001").strip()[:20]
        org_id = (data.get("org_id") or "").strip()[:10]
        dest_id = (data.get("dest_id") or "").strip()[:10]
        ac_name = (data.get("ac_name") or "B737-800").strip()[:50]

        if not org_id or not dest_id:
            return jsonify({
                "status": "error",
                "message": "출발·도착 공항을 선택해주세요."
            }), 400

        if org_id == dest_id:
            return jsonify({
                "status": "error",
                "message": "출발과 도착 공항이 같을 수 없습니다."
            }), 400

        is_korea = data.get("is_korea", False)
        if isinstance(is_korea, str):
            is_korea = is_korea.lower() in ("true", "1", "yes")

        current_count = UserRadarFlight.query.count()
        if current_count >= 20:
            return jsonify({
                "status": "error",
                "message": "사용자 항공편은 최대 20개까지만 추가할 수 있습니다."
            }), 400

        flight = UserRadarFlight(
            callsign=callsign,
            org_id=org_id,
            dest_id=dest_id,
            ac_name=ac_name,
            is_korea=bool(is_korea)
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
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"항공편 저장 중 오류가 발생했습니다: {str(e)}"
        }), 500


@bp.route("/api/radar/flights/<int:flight_id>", methods=["DELETE"])
def delete_user_radar_flight(flight_id):
    """사용자 항공편 삭제"""
    flight = UserRadarFlight.query.get(flight_id)
    if not flight:
        return jsonify({"status": "error", "message": "Flight not found"}), 404
    
    db.session.delete(flight)
    db.session.commit()
    
    return jsonify({"status": "success"})
