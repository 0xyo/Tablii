"""Landing page blueprint — public marketing page for Tablii."""
from flask import Blueprint, render_template

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """Marketing landing page for all visitors."""
    return render_template('landing.html')
