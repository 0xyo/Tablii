"""
Configuration module for Tablii.

Defines development and production configurations.
All secrets are loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration with shared defaults."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'app/static/images/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


class DevelopmentConfig(Config):
    """Development configuration for local use."""

    DEBUG = True
    SOCKETIO_CORS_ORIGINS = '*'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///dev.db'
    )


class ProductionConfig(Config):
    """Production configuration — requires all env vars to be set."""

    DEBUG = False
    _socketio_cors_origins_raw = os.environ['SOCKETIO_CORS_ORIGINS']
    SOCKETIO_CORS_ORIGINS = [
        origin.strip()
        for origin in _socketio_cors_origins_raw.split(',')
        if origin.strip()
    ]
    if not SOCKETIO_CORS_ORIGINS:
        raise ValueError(
            'SOCKETIO_CORS_ORIGINS must contain at least one origin in production.'
        )
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    # Fix Render's postgres:// scheme — SQLAlchemy 2.x requires postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgres://', 'postgresql://', 1
        )
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    """Testing configuration — uses in-memory SQLite, disables CSRF."""

    TESTING = True
    SOCKETIO_CORS_ORIGINS = '*'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
