"""Order, order-item, payment, and waiter-call models."""
from datetime import datetime, timezone

from app import db


class Order(db.Model):
    """A customer order placed at a table."""

    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey('table_sessions.id'), nullable=True
    )
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    table_id = db.Column(
        db.Integer, db.ForeignKey('tables_.id'), nullable=True
    )
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customers.id'), nullable=True
    )
    order_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='new')
    payment_method = db.Column(db.String(20), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    subtotal = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    special_notes = db.Column(db.Text, nullable=True)
    is_gift = db.Column(db.Boolean, default=False)
    gift_from_table = db.Column(db.Integer, nullable=True)
    gift_message = db.Column(db.String(300), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    accepted_at = db.Column(db.DateTime, nullable=True)
    preparing_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    served_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    table = db.relationship('Table', backref='orders')
    payment = db.relationship(
        'PaymentTransaction', backref='order', uselist=False
    )
    review = db.relationship('Review', backref='order', uselist=False)


class OrderItem(db.Model):
    """Individual line item within an order."""

    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('orders.id'),
        nullable=False, index=True
    )
    menu_item_id = db.Column(
        db.Integer, db.ForeignKey('menu_items.id'), nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    selected_options = db.Column(db.Text, nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    menu_item = db.relationship('MenuItem')


class PaymentTransaction(db.Model):
    """Record of an online payment attempt."""

    __tablename__ = 'payment_transactions'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('orders.id'),
        unique=True, nullable=False
    )
    gateway = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    gateway_transaction_id = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='pending')
    raw_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )


class WaiterCall(db.Model):
    """Request from a customer to call a waiter."""

    __tablename__ = 'waiter_calls'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    table_id = db.Column(
        db.Integer, db.ForeignKey('tables_.id'), nullable=False
    )
    call_type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(
        db.Integer, db.ForeignKey('staff_users.id'), nullable=True
    )
