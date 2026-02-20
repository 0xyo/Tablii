"""Customer-facing blueprint — menu, cart, checkout, orders, reviews."""
import json

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    session, url_for,
)

from app import csrf, db
from app.models.menu import Category, MenuItem
from app.models.order import Order, WaiterCall
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.models.table import Table, TableSession
from app.services.order_service import create_order
from app.services.upload_service import save_uploaded_file
from app.utils.helpers import generate_random_token

customer_bp = Blueprint('customer', __name__, url_prefix='')


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_restaurant_and_table(slug, table_id):
    """Fetch restaurant + table or 404."""
    restaurant = Restaurant.query.filter_by(slug=slug, is_active=True).first_or_404()
    table = Table.query.filter_by(id=table_id, restaurant_id=restaurant.id).first_or_404()
    return restaurant, table


def _ensure_session(table, restaurant):
    """Get or create an active TableSession and store token in browser session."""
    table_session = TableSession.query.filter_by(
        table_id=table.id, is_active=True
    ).first()

    if not table_session:
        table_session = TableSession(
            table_id=table.id,
            restaurant_id=restaurant.id,
            session_token=generate_random_token(),
        )
        db.session.add(table_session)
        table.status = 'occupied'
        db.session.commit()

    session['session_token'] = table_session.session_token
    return table_session


# ──────────────────────────────────────────────
# Route 1: Menu
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>')
def menu(slug, table_id):
    """Display the restaurant menu for a table."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    table_session = _ensure_session(table, restaurant)

    # Query categories with active items
    categories_query = Category.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).order_by(Category.sort_order)

    if restaurant.ramadan_mode:
        categories_query = categories_query.filter(
            Category.ramadan_type.isnot(None)
        )

    categories = categories_query.all()

    # Eager-load available items per category
    for cat in categories:
        cat.active_items = MenuItem.query.filter_by(
            category_id=cat.id,
            restaurant_id=restaurant.id,
            is_available=True,
        ).filter(MenuItem.deleted_at.is_(None)).order_by(MenuItem.sort_order).all()

        # Eager-load customizations and options for each item
        for item in cat.active_items:
            item.active_customizations = item.customizations.all()
            for cust in item.active_customizations:
                cust.active_options = cust.options.all()

    return render_template(
        'customer/menu.html',
        restaurant=restaurant,
        table=table,
        categories=categories,
        session_token=table_session.session_token,
    )


# ──────────────────────────────────────────────
# Route 2: Cart
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/cart')
def cart(slug, table_id):
    """Display the cart page (data managed client-side)."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    return render_template(
        'customer/cart.html',
        restaurant=restaurant,
        table=table,
        session_token=session.get('session_token'),
    )


# ──────────────────────────────────────────────
# Route 3: Checkout
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/checkout')
def checkout(slug, table_id):
    """Display the checkout page."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    return render_template(
        'customer/checkout.html',
        restaurant=restaurant,
        table=table,
        session_token=session.get('session_token'),
    )


# ──────────────────────────────────────────────
# Route 4: Place Order (POST JSON)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/order', methods=['POST'])
@csrf.exempt  # JSON API — CSRF token sent in header by JS
def place_order(slug, table_id):
    """Create a new order from cart data."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)

    # Validate session
    stored_token = session.get('session_token')
    if not stored_token:
        return jsonify(success=False, error='Invalid session.'), 403

    table_session = TableSession.query.filter_by(
        session_token=stored_token, is_active=True
    ).first()
    if not table_session:
        return jsonify(success=False, error='Session expired.'), 403

    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    payment_method = data.get('payment_method', 'cash')
    special_notes = data.get('special_notes', '')

    try:
        order = create_order(
            session_id=table_session.id,
            items=items,
            payment_method=payment_method,
            special_notes=special_notes,
            restaurant=restaurant,
        )
        return jsonify(
            success=True,
            order_id=order.id,
            order_number=order.order_number,
            total_amount=order.total_amount,
        )
    except ValueError as e:
        return jsonify(success=False, error=str(e)), 400
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='An error occurred.'), 500


# ──────────────────────────────────────────────
# Route 5: Order Tracking
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/track/<int:order_id>')
def track_order(slug, table_id):
    """Display order tracking page."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    order = Order.query.filter_by(
        id=order_id, restaurant_id=restaurant.id
    ).first_or_404()

    return render_template(
        'customer/order_tracking.html',
        restaurant=restaurant,
        table=table,
        order=order,
    )


# ──────────────────────────────────────────────
# Route 6: Call Waiter (POST JSON)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/call-waiter', methods=['GET'])
def call_waiter_page(slug, table_id):
    """Display the call waiter page."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    return render_template(
        'customer/call_waiter.html',
        restaurant=restaurant,
        table=table,
    )


@customer_bp.route('/r/<slug>/table/<int:table_id>/call-waiter', methods=['POST'])
@csrf.exempt  # JSON API
def call_waiter(slug, table_id):
    """Create a waiter call request."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)

    data = request.get_json(silent=True) or {}
    call_type = data.get('call_type', '')
    message = data.get('message', '')

    valid_types = {'water', 'bill', 'help', 'custom'}
    if call_type not in valid_types:
        return jsonify(success=False, error='Invalid call type.'), 400

    try:
        waiter_call = WaiterCall(
            restaurant_id=restaurant.id,
            table_id=table.id,
            call_type=call_type,
            message=message or None,
        )
        db.session.add(waiter_call)
        db.session.commit()
        return jsonify(success=True)
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='An error occurred.'), 500


# ──────────────────────────────────────────────
# Route 7: Review
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/review/<int:order_id>', methods=['GET'])
def review_page(slug, table_id, order_id):
    """Display the review page."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    order = Order.query.filter_by(
        id=order_id, restaurant_id=restaurant.id
    ).first_or_404()

    if order.status not in ('served', 'completed'):
        flash('You can only review completed orders.', 'warning')
        return redirect(url_for('customer.menu', slug=slug, table_id=table_id))

    existing_review = Review.query.filter_by(order_id=order.id).first()
    if existing_review:
        flash('You have already reviewed this order.', 'info')
        return redirect(url_for('customer.menu', slug=slug, table_id=table_id))

    return render_template(
        'customer/review.html',
        restaurant=restaurant,
        table=table,
        order=order,
    )


@customer_bp.route('/r/<slug>/table/<int:table_id>/review/<int:order_id>', methods=['POST'])
def review_submit(slug, table_id, order_id):
    """Submit a review for a completed order."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    order = Order.query.filter_by(
        id=order_id, restaurant_id=restaurant.id
    ).first_or_404()

    if order.status not in ('served', 'completed'):
        flash('You can only review completed orders.', 'warning')
        return redirect(url_for('customer.menu', slug=slug, table_id=table_id))

    existing_review = Review.query.filter_by(order_id=order.id).first()
    if existing_review:
        flash('You have already reviewed this order.', 'info')
        return redirect(url_for('customer.menu', slug=slug, table_id=table_id))

    rating = request.form.get('rating', type=int)
    food_rating = request.form.get('food_rating', type=int)
    service_rating = request.form.get('service_rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or not (1 <= rating <= 5):
        flash('Please provide a rating between 1 and 5.', 'error')
        return render_template(
            'customer/review.html',
            restaurant=restaurant, table=table, order=order,
        )

    photo_url = None
    photo = request.files.get('photo')
    if photo and photo.filename:
        photo_url = save_uploaded_file(photo, 'reviews')

    try:
        review = Review(
            order_id=order.id,
            restaurant_id=restaurant.id,
            rating=rating,
            food_rating=food_rating if food_rating and 1 <= food_rating <= 5 else None,
            service_rating=service_rating if service_rating and 1 <= service_rating <= 5 else None,
            comment=comment or None,
            photo_url=photo_url,
        )
        db.session.add(review)
        db.session.commit()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('customer.menu', slug=slug, table_id=table_id))
    except Exception:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')
        return render_template(
            'customer/review.html',
            restaurant=restaurant, table=table, order=order,
        )
