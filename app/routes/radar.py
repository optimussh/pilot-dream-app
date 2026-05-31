from flask import Blueprint, render_template

bp = Blueprint('radar', __name__, url_prefix='/radar')

@bp.route('/')
def index():
    return render_template('radar.html')