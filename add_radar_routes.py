with open("app/routes/main.py", "r", encoding="utf-8") as f:
    content = f.read()

new_routes = """

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
    """새로운 사용자 항공편 추가"""
    data = request.get_json()
    
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
"""

if "Radar User Flights API" not in content:
    content = content.rstrip() + new_routes
    with open("app/routes/main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Radar flight routes added successfully.")
else:
    print("Routes already exist.")
