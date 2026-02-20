"""User and staff models for authentication and authorization."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(db.Model, UserMixin):
    """Platform user (restaurant owner or super admin)."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='owner')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    restaurants = db.relationship(
        'Restaurant', backref='owner', lazy='dynamic'
    )

    def get_id(self):
        """Return prefixed ID to avoid conflicts with StaffUser."""
        return f'user_{self.id}'

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)


class StaffUser(db.Model, UserMixin):
    """Staff member scoped to a single restaurant."""

    __tablename__ = 'staff_users'
    __table_args__ = (
        db.UniqueConstraint('restaurant_id', 'username', name='uq_staff_restaurant_username'),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True
    )
    username = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def get_id(self):
        """Return prefixed ID to avoid conflicts with User."""
        return f'staff_{self.id}'

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)
