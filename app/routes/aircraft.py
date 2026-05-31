from flask import Blueprint, render_template

bp = Blueprint('aircraft', __name__, url_prefix='/aircraft')

@bp.route('/')
def index():
    return render_template('aircraft.html')