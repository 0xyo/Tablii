"""Authentication blueprint — login, register, logout."""
from datetime import datetime, time, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.models.restaurant import OperatingHours, Restaurant, Subscription
from app.models.user import StaffUser, User
from app.utils.helpers import generate_slug
from app.utils.validators import validate_email, validate_phone

auth_bp = Blueprint('auth', __name__)

# --- Rate-limiting constants ---
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes


def _is_rate_limited() -> bool:
    """Check if the current session has exceeded login attempt limits."""
    attempts = session.get('login_attempts', 0)
    last_attempt = session.get('last_failed_at')
    if attempts >= MAX_FAILED_ATTEMPTS and last_attempt:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_attempt)).total_seconds()
        if elapsed < LOCKOUT_SECONDS:
            return True
        # Reset after lockout period
        session.pop('login_attempts', None)
        session.pop('last_failed_at', None)
    return False


def _record_failed_attempt():
    """Increment failed login attempts in session."""
    session['login_attempts'] = session.get('login_attempts', 0) + 1
    session['last_failed_at'] = datetime.now(timezone.utc).isoformat()


def _clear_attempts():
    """Clear failed login tracking on success."""
    session.pop('login_attempts', None)
    session.pop('last_failed_at', None)


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET'])
def login():
    """Render the login page."""
    if current_user.is_authenticated:
        return redirect('/dashboard')
    login_type = request.args.get('login_type', 'owner')
    return render_template('auth/login.html', login_type=login_type)


@auth_bp.route('/login', methods=['POST'])
def login_post():
    """Handle login form submission for owners and staff."""
    if current_user.is_authenticated:
        return redirect('/dashboard')

    login_type = request.form.get('login_type', 'owner')

    if _is_rate_limited():
        flash('Too many login attempts. Please wait 15 minutes.', 'error')
        return redirect(url_for('auth.login', login_type=login_type))

    if login_type == 'owner':
        return _handle_owner_login()
    else:
        return _handle_staff_login()


def _handle_owner_login():
    """Process owner login."""
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        _record_failed_attempt()
        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login', login_type='owner'))

    if not user.is_active:
        flash('Account is deactivated.', 'error')
        return redirect(url_for('auth.login', login_type='owner'))

    _clear_attempts()
    login_user(user)
    flash('Welcome back!', 'success')
    return redirect('/dashboard')


def _handle_staff_login():
    """Process staff login."""
    restaurant_slug = request.form.get('restaurant_slug', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    restaurant = Restaurant.query.filter_by(slug=restaurant_slug).first()
    if not restaurant:
        _record_failed_attempt()
        flash('Restaurant not found.', 'error')
        return redirect(url_for('auth.login', login_type='staff'))

    staff = StaffUser.query.filter_by(
        restaurant_id=restaurant.id, username=username
    ).first()

    if not staff or not staff.check_password(password):
        _record_failed_attempt()
        flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login', login_type='staff'))

    if not staff.is_active:
        flash('Account is deactivated.', 'error')
        return redirect(url_for('auth.login', login_type='staff'))

    _clear_attempts()
    login_user(staff)
    flash('Welcome back!', 'success')

    # Redirect based on staff role
    role_redirects = {
        'cashier': '/cashier/orders',
        'kitchen': '/kitchen',
        'waiter': '/waiter/tables',
    }
    return redirect(role_redirects.get(staff.role, '/dashboard'))


# ──────────────────────────────────────────────
# Register
# ──────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET'])
def register():
    """Render the registration page."""
    if current_user.is_authenticated:
        return redirect('/dashboard')
    return render_template('auth/register.html')


@auth_bp.route('/register', methods=['POST'])
def register_post():
    """Handle registration form submission."""
    if current_user.is_authenticated:
        return redirect('/dashboard')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    restaurant_name = request.form.get('restaurant_name', '').strip()

    # Validation
    errors = []

    if not all([name, email, password, confirm_password, restaurant_name]):
        errors.append('All required fields must be filled.')

    email_valid, email_err = validate_email(email)
    if not email_valid:
        errors.append(email_err)

    if phone:
        phone_valid, phone_err = validate_phone(phone)
        if not phone_valid:
            errors.append(phone_err)

    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')

    if password != confirm_password:
        errors.append('Passwords do not match.')

    if not errors and User.query.filter_by(email=email).first():
        errors.append('An account with this email already exists.')

    if errors:
        for err in errors:
            flash(err, 'error')
        return render_template('auth/register.html')

    # Create user, restaurant, subscription, and operating hours
    try:
        user = User(name=name, email=email, phone=phone or None, role='owner')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id

        restaurant = Restaurant(
            owner_id=user.id,
            name=restaurant_name,
            slug=generate_slug(restaurant_name),
        )
        db.session.add(restaurant)
        db.session.flush()  # Get restaurant.id

        subscription = Subscription(restaurant_id=restaurant.id, plan='free')
        db.session.add(subscription)

        # Default operating hours: Mon–Sun, 09:00–23:00
        for day in range(7):
            hours = OperatingHours(
                restaurant_id=restaurant.id,
                day_of_week=day,
                open_time=time(9, 0),
                close_time=time(23, 0),
                is_closed=False,
            )
            db.session.add(hours)

        db.session.commit()

        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect('/dashboard')

    except Exception:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')
        return render_template('auth/register.html')


# ──────────────────────────────────────────────
# Logout
# ──────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
