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
                if 'daily_learning' not in cols:
                    with db.engine.connect() as conn:
                        conn.execute(text(
                            "ALTER TABLE user_progress ADD COLUMN daily_learning TEXT DEFAULT '{}'"
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
        learn
    )

    app.register_blueprint(main.bp)
    app.register_blueprint(radar.bp)
    app.register_blueprint(aircraft.bp)
    app.register_blueprint(planner.bp)
    app.register_blueprint(logbook.bp)
    app.register_blueprint(badges.bp)
    app.register_blueprint(atc.bp)
    app.register_blueprint(career.bp)
    app.register_blueprint(learn.bp)

    return app