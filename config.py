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
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///dev.db'
    )


class ProductionConfig(Config):
    """Production configuration — requires all env vars to be set."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
