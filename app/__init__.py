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


def _maybe_seed_demo_data(app):
    """Seed demo data when explicitly enabled for hosted demo environments."""
    if app.config.get('TESTING'):
        return

    auto_seed_enabled = (
        os.environ.get('TABLII_AUTO_SEED', '').strip().lower()
        in {'1', 'true', 'yes', 'on'}
    )
    if not auto_seed_enabled:
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
