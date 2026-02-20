"""Table and table-session models."""
from datetime import datetime, timezone

from app import db


class Table(db.Model):
    """Physical table in a restaurant."""

    __tablename__ = 'tables_'
    __table_args__ = (
        db.UniqueConstraint(
            'restaurant_id', 'table_number',
            name='uq_restaurant_table_number'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    table_number = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default='free')
    qr_code_url = db.Column(db.String(300), nullable=True)
    position_x = db.Column(db.Float, nullable=True)
    position_y = db.Column(db.Float, nullable=True)
    assigned_waiter_id = db.Column(
        db.Integer, db.ForeignKey('staff_users.id'), nullable=True
    )

    # Relationships
    sessions = db.relationship('TableSession', backref='table', lazy='dynamic')
    assigned_waiter = db.relationship('StaffUser', backref='assigned_tables')


class TableSession(db.Model):
    """Active dining session at a table."""

    __tablename__ = 'table_sessions'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(
        db.Integer, db.ForeignKey('tables_.id'),
        nullable=False, index=True
    )
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'), nullable=False
    )
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customers.id'), nullable=True
    )
    session_token = db.Column(db.String(64), unique=True, nullable=False)
    guest_name = db.Column(db.String(100), nullable=True)
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ended_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    orders = db.relationship('Order', backref='session', lazy='dynamic')
