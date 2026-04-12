"""Landing page blueprint — public marketing page for Tablii."""
from flask import Blueprint, redirect, render_template
from flask_login import current_user

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """Marketing landing page. Logged-in users go to dashboard."""
    if current_user.is_authenticated:
        return redirect('/dashboard')
    return render_template('landing.html')
