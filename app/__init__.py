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

    # Dual user loader (User and StaffUser share session via prefixed IDs)
    from app.models.user import User, StaffUser

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('user_'):
            return User.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('staff_'):
            return StaffUser.query.get(int(user_id.split('_')[1]))
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
