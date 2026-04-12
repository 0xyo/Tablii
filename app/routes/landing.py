"""Landing page blueprint — public marketing page for Tablii."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from app.models.user import User

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """Marketing landing page. Logged-in users go to dashboard."""
    if current_user.is_authenticated:
        if isinstance(current_user, User) and current_user.role == 'super_admin':
            return redirect(url_for('admin.restaurants'))
        return redirect('/dashboard')
    return render_template('landing.html')
