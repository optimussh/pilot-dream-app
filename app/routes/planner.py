from flask import Blueprint, render_template

bp = Blueprint('planner', __name__, url_prefix='/flight-planner')

@bp.route('/')
def index():
    return render_template('flight_planner.html')