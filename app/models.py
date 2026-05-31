from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class LogbookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    flight_number = db.Column(db.String(20), nullable=False)
    aircraft = db.Column(db.String(50))
    route = db.Column(db.String(50))
    hours = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    badge_id = db.Column(db.String(50), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('badge_id', name='_badge_uc'),)


class UserRadarFlight(db.Model):
    """사용자가 직접 추가한 레이더 항공편 (개인화된 비행)"""
    id = db.Column(db.Integer, primary_key=True)
    callsign = db.Column(db.String(20), nullable=False)
    org_id = db.Column(db.String(10), nullable=False)
    dest_id = db.Column(db.String(10), nullable=False)
    ac_name = db.Column(db.String(50))
    is_korea = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
