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
    
    # Ensure instance folder exists (important for SQLite)
    os.makedirs(app.instance_path, exist_ok=True)
    
    # SQLite database (persistent via Docker volume)
    db_path = os.path.join(app.instance_path, 'pilot_dream.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Register all blueprints
    from app.routes import (
        main,
        radar,
        aircraft,
        planner,
        logbook,
        badges,
        atc,
        career
    )

    app.register_blueprint(main.bp)
    app.register_blueprint(radar.bp)
    app.register_blueprint(aircraft.bp)
    app.register_blueprint(planner.bp)
    app.register_blueprint(logbook.bp)
    app.register_blueprint(badges.bp)
    app.register_blueprint(atc.bp)
    app.register_blueprint(career.bp)

    return app