from flask import Blueprint, render_template

bp = Blueprint('career', __name__, url_prefix='/korea-career')

@bp.route('/')
def index():
    return render_template('korea_career.html')