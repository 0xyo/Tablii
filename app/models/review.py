"""Customer, review, loyalty, and notification models."""
from datetime import datetime, timezone

from app import db


class Customer(db.Model):
    """End customer who places orders (identified by phone)."""

    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Review(db.Model):
    """Post-order review with ratings."""

    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('orders.id'), nullable=False
    )
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    rating = db.Column(db.Integer, nullable=False)
    food_rating = db.Column(db.Integer, nullable=True)
    service_rating = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )


class LoyaltyPoints(db.Model):
    """Loyalty points balance per customer per restaurant."""

    __tablename__ = 'loyalty_points'
    __table_args__ = (
        db.UniqueConstraint(
            'customer_id', 'restaurant_id',
            name='uq_customer_restaurant_loyalty'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customers.id'), nullable=False
    )
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'), nullable=False
    )
    points = db.Column(db.Integer, default=0)
    total_earned = db.Column(db.Integer, default=0)
    total_redeemed = db.Column(db.Integer, default=0)


class Notification(db.Model):
    """In-app notification for staff and owners."""

    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    target_role = db.Column(db.String(20), nullable=True)
    target_user_id = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
