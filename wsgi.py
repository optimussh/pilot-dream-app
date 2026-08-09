"""WSGI entry for gunicorn (avoids clash between app.py and the app/ package)."""
from app import create_app

app = create_app()
