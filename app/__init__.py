"""
Tablii application factory.

Creates and configures the Flask application using the factory pattern.
Extensions are declared at module level for import by other modules.
"""
import os
import importlib

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

# --- Extensions (module-level for shared imports) ---
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO()
csrf = CSRFProtect()


def _truthy_env(name):
    """Return True when an environment variable is set to a truthy value."""
    return (os.environ.get(name, '').strip().lower() in {'1', 'true', 'yes', 'on'})


def _demo_bootstrap_requested():
    """Return True when deploy-time demo account bootstrapping should run."""
    return (
        _truthy_env('TABLII_AUTO_SEED')
        or bool((os.environ.get('TABLII_SUPERADMIN_EMAIL') or '').strip())
        or bool((os.environ.get('TABLII_SUPERADMIN_PASSWORD') or '').strip())
        or bool((os.environ.get('TABLII_OWNER_EMAIL') or '').strip())
        or bool((os.environ.get('TABLII_OWNER_PASSWORD') or '').strip())
    )


def _ensure_super_admin_from_env(app):
    """Create/update super admin from env vars when provided."""
    if app.config.get('TESTING'):
        return

    email = (os.environ.get('TABLII_SUPERADMIN_EMAIL') or '').strip().lower()
    password = (os.environ.get('TABLII_SUPERADMIN_PASSWORD') or '').strip()

    if not email or not password:
        return

    from app.models.user import User

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                name='Super Admin',
                email=email,
                role='super_admin',
                is_active=True,
            )
            db.session.add(user)

        user.role = 'super_admin'
        user.is_active = True
        user.set_password(password)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to bootstrap super admin from environment.')


def _ensure_owner_from_env(app):
    """Create/update owner demo account and its restaurant when enabled."""
    if app.config.get('TESTING') or not _demo_bootstrap_requested():
        return

    email = (os.environ.get('TABLII_OWNER_EMAIL') or 'owner@tablii.com').strip().lower()
    password = (os.environ.get('TABLII_OWNER_PASSWORD') or 'owner1234').strip()
    name = (os.environ.get('TABLII_OWNER_NAME') or 'Ahmed Ben Ali').strip()
    restaurant_name = (os.environ.get('TABLII_RESTAURANT_NAME') or 'Chez Ahmed').strip()
    restaurant_slug = (os.environ.get('TABLII_RESTAURANT_SLUG') or 'chez-ahmed').strip()
    restaurant_city = (os.environ.get('TABLII_RESTAURANT_CITY') or 'Tunis').strip()
    restaurant_address = (os.environ.get('TABLII_RESTAURANT_ADDRESS') or '15 Rue de la Kasbah, Tunis').strip()
    restaurant_phone = (os.environ.get('TABLII_RESTAURANT_PHONE') or '+21671000001').strip()

    if not email or not password:
        return

    from app.models.user import User
    from app.models.restaurant import Restaurant, Subscription

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                name=name,
                email=email,
                role='owner',
                is_active=True,
            )
            db.session.add(user)

        user.name = name
        user.role = 'owner'
        user.is_active = True
        user.set_password(password)
        db.session.flush()

        restaurant = Restaurant.query.filter_by(slug=restaurant_slug).first()
        if not restaurant:
            restaurant = Restaurant(
                owner_id=user.id,
                name=restaurant_name,
                slug=restaurant_slug,
                description='Cuisine tunisienne authentique -- saveurs du terroir',
                city=restaurant_city or None,
                address=restaurant_address or None,
                phone=restaurant_phone or None,
                currency='TND',
                tax_rate=7.0,
                auto_accept=False,
                is_active=True,
                is_open=True,
            )
            db.session.add(restaurant)
            db.session.flush()
        else:
            restaurant.owner_id = user.id
            restaurant.name = restaurant_name or restaurant.name
            restaurant.city = restaurant_city or restaurant.city
            restaurant.address = restaurant_address or restaurant.address
            restaurant.phone = restaurant_phone or restaurant.phone
            restaurant.is_active = True
            restaurant.is_open = True

        if not restaurant.subscription:
            db.session.add(Subscription(
                restaurant_id=restaurant.id,
                plan='pro',
                max_tables=20,
                max_items=100,
                is_active=True,
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to bootstrap owner from environment.')


def _maybe_seed_demo_data(app):
    """Seed demo data when explicitly enabled for hosted demo environments."""
    if app.config.get('TESTING'):
        return

    if not _demo_bootstrap_requested():
        return

    try:
        from seed import seed_current_app
        seed_current_app(os.environ.get('FLASK_ENV', 'development'))
    except Exception:
        app.logger.exception('Failed to auto-seed demo data.')


def create_app(config_name=None):
    """
    Application factory.

    Args:
        config_name: Configuration key ('development' or 'production').
                     Falls back to FLASK_ENV env var, then 'development'.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load configuration
    from config import config_by_name
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio_cors_origins = app.config.get('SOCKETIO_CORS_ORIGINS', '*')
    # Flask 3.x compatibility: avoid Flask-SocketIO trying to assign ctx.session.
    socketio.init_app(
        app,
        cors_allowed_origins=socketio_cors_origins,
        async_mode='threading',
        manage_session=False,
    )
    csrf.init_app(app)

    # Register WebSocket event handlers
    from app.events import register_events
    register_events(socketio)

    # Configure Flask-Login
    setattr(login_manager, 'login_view', 'auth.login')
    login_manager.login_message_category = 'warning'

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register models for Alembic detection
    importlib.import_module('app.models')

    with app.app_context():
        _maybe_seed_demo_data(app)
        _ensure_owner_from_env(app)
        _ensure_super_admin_from_env(app)

    # Dual user loader (User and StaffUser share session via prefixed IDs)
    from app.models.user import User, StaffUser

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('user_'):
            return db.session.get(User, int(user_id.split('_')[1]))
        elif user_id.startswith('staff_'):
            return db.session.get(StaffUser, int(user_id.split('_')[1]))
        return None

    # Register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Register Jinja helpers
    from app.utils.helpers import localized
    from app.utils.translations import t as translate_fn
    app.jinja_env.filters['localized'] = localized
    app.jinja_env.globals['localized'] = localized
    app.jinja_env.globals['t'] = translate_fn

    return app
