from flask import Blueprint, render_template

bp = Blueprint('logbook', __name__, url_prefix='/logbook')

@bp.route('/')
def index():
    return render_template('logbook.html')