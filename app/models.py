from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

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


class UserProgress(db.Model):
    """게이미피케이션 통합 진행 상태 (단일 사용자)"""
    id = db.Column(db.Integer, primary_key=True)
    virtual_hours = db.Column(db.Float, default=0.0)
    streak_days = db.Column(db.Integer, default=0)
    last_active_date = db.Column(db.String(10))
    flashcard_streak = db.Column(db.Integer, default=0)
    last_flashcard_date = db.Column(db.String(10))
    flashcards_learned = db.Column(db.Text, default='[]')
    first_flight_done = db.Column(db.Boolean, default=False)
    first_flight_step = db.Column(db.Integer, default=0)
    unlocked_content = db.Column(db.Text, default='[]')
    completed_missions = db.Column(db.Text, default='{}')
    completed_weekly = db.Column(db.Text, default='{}')
    quiz_history = db.Column(db.Text, default='[]')
    scenario_progress = db.Column(db.Text, default='{}')
    activity_log = db.Column(db.Text, default='[]')
    daily_mission_streak = db.Column(db.Integer, default=0)
    last_all_missions_date = db.Column(db.String(10))
    daily_learning = db.Column(db.Text, default='{}')
    wallet_balance = db.Column(db.Integer, default=0)
    salary_milestones_paid = db.Column(db.Integer, default=0)
    hour_boosts = db.Column(db.Float, default=0.0)
    inventory = db.Column(db.Text, default='[]')
    equipped_avatar = db.Column(db.Text, default='{}')
    owned_aircraft = db.Column(db.Text, default='["b737","a320"]')
    active_aircraft = db.Column(db.String(30), default='b737')
    aircraft_loadouts = db.Column(db.Text, default='{}')
    transaction_log = db.Column(db.Text, default='[]')
    salary_bonuses_paid = db.Column(db.Text, default='[]')
    pilot_meta = db.Column(db.Text, default='{}')

    def _json(self, field, default):
        try:
            return json.loads(getattr(self, field) or json.dumps(default))
        except (json.JSONDecodeError, TypeError):
            return default

    def set_json(self, field, value):
        setattr(self, field, json.dumps(value, ensure_ascii=False))


class FutureLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    written_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_opened = db.Column(db.Boolean, default=False)
    opened_at = db.Column(db.DateTime)