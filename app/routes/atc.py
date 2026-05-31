from flask import Blueprint, render_template

bp = Blueprint('atc', __name__, url_prefix='/atc-english')

@bp.route('/')
def index():
    return render_template('atc_english.html')