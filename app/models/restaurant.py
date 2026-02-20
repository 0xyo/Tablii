"""Restaurant, subscription, and operating hours models."""
from datetime import datetime, timezone

from app import db


class Restaurant(db.Model):
    """A restaurant (tenant) on the platform."""

    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False
    )
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(300), nullable=True)
    cover_url = db.Column(db.String(300), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    currency = db.Column(db.String(10), default='TND')
    tax_rate = db.Column(db.Float, default=0.0)
    service_charge = db.Column(db.Float, default=0.0)
    auto_accept = db.Column(db.Boolean, default=False)
    online_payment = db.Column(db.Boolean, default=False)
    ramadan_mode = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    categories = db.relationship('Category', backref='restaurant', lazy='dynamic')
    tables = db.relationship('Table', backref='restaurant', lazy='dynamic')
    staff_users = db.relationship('StaffUser', backref='restaurant', lazy='dynamic')
    orders = db.relationship('Order', backref='restaurant', lazy='dynamic')
    subscription = db.relationship(
        'Subscription', backref='restaurant', uselist=False
    )
    operating_hours = db.relationship(
        'OperatingHours', backref='restaurant', lazy='dynamic'
    )


class Subscription(db.Model):
    """Subscription plan tied to a restaurant."""

    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        unique=True, nullable=False
    )
    plan = db.Column(db.String(30), default='free')
    max_tables = db.Column(db.Integer, default=5)
    max_items = db.Column(db.Integer, default=20)
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class OperatingHours(db.Model):
    """Weekly operating schedule for a restaurant."""

    __tablename__ = 'operating_hours'
    __table_args__ = (
        db.UniqueConstraint(
            'restaurant_id', 'day_of_week',
            name='uq_restaurant_day'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'), nullable=False
    )
    day_of_week = db.Column(db.Integer, nullable=False)
    open_time = db.Column(db.Time, nullable=True)
    close_time = db.Column(db.Time, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
