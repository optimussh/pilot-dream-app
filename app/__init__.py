from flask import Flask
import os
from app.models import db

def create_app():
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static',
        instance_relative_config=True
    )
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pilot-dream-dev-key')
    app.config['DEBUG'] = os.environ.get('FLASK_ENV') != 'production'
    
    # Database 설정 (Supabase PostgreSQL 우선, 없으면 로컬 SQLite)
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Supabase / PostgreSQL 사용
        # Supabase가 가끔 'postgres://'로 주는데 SQLAlchemy는 'postgresql://'을 선호
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # 로컬 개발용 SQLite
        os.makedirs(app.instance_path, exist_ok=True)
        db_path = os.path.join(app.instance_path, 'pilot_dream.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if inspector.has_table('user_progress'):
                cols = {c['name'] for c in inspector.get_columns('user_progress')}
                migrations = [
                    ('daily_learning', "TEXT DEFAULT '{}'"),
                    ('wallet_balance', 'INTEGER DEFAULT 0'),
                    ('salary_milestones_paid', 'INTEGER DEFAULT 0'),
                    ('hour_boosts', 'REAL DEFAULT 0.0'),
                    ('inventory', "TEXT DEFAULT '[]'"),
                    ('equipped_avatar', "TEXT DEFAULT '{}'"),
                    ('owned_aircraft', 'TEXT DEFAULT \'["b737","a320"]\''),
                    ('active_aircraft', "VARCHAR(30) DEFAULT 'b737'"),
                    ('aircraft_loadouts', "TEXT DEFAULT '{}'"),
                    ('transaction_log', "TEXT DEFAULT '[]'"),
                    ('salary_bonuses_paid', "TEXT DEFAULT '[]'"),
                    ('pilot_meta', "TEXT DEFAULT '{}'"),
                ]
                with db.engine.connect() as conn:
                    for col_name, col_def in migrations:
                        if col_name not in cols:
                            conn.execute(text(
                                f'ALTER TABLE user_progress ADD COLUMN {col_name} {col_def}'
                            ))
                    conn.commit()
        except Exception:
            pass
        try:
            from app.services.content_bank import ensure_all_banks
            ensure_all_banks()
        except Exception:
            pass

    # Register all blueprints
    from app.routes import (
        main,
        radar,
        aircraft,
        planner,
        logbook,
        badges,
        atc,
        career,
        learn,
        shop,
        extras,
        airline,
        guide,
    )  # noqa: airline, guide registered below

    app.register_blueprint(main.bp)
    app.register_blueprint(radar.bp)
    app.register_blueprint(aircraft.bp)
    app.register_blueprint(planner.bp)
    app.register_blueprint(logbook.bp)
    app.register_blueprint(badges.bp)
    app.register_blueprint(atc.bp)
    app.register_blueprint(career.bp)
    app.register_blueprint(learn.bp)
    app.register_blueprint(shop.bp)
    app.register_blueprint(extras.bp)
    app.register_blueprint(airline.bp)
    app.register_blueprint(guide.bp)

    from app.services.game_bridge import GAMES_ENABLED
    if GAMES_ENABLED:
        from app.routes import games
        app.register_blueprint(games.bp)

    return app