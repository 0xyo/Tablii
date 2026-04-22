"""Customer-facing blueprint — menu, cart, checkout, orders, reviews."""
import json
from datetime import datetime

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    session, url_for,
)

from app import csrf, db
from app.models.menu import Category, MenuItem
from app.models.order import Order, WaiterCall
from app.models.restaurant import DEFAULT_RAMADAN_IFTAR_TIME, Restaurant
from app.models.review import Customer, Review
from app.models.table import Table, TableSession
from app.services.order_service import create_order
from app.services.upload_service import save_uploaded_file
from app.utils.helpers import generate_random_token, resolve_language

customer_bp = Blueprint('customer', __name__, url_prefix='')


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_restaurant_and_table(slug, table_id):
    """Fetch restaurant + table or 404."""
    restaurant = Restaurant.query.filter_by(slug=slug, is_active=True).first_or_404()
    table = Table.query.filter_by(id=table_id, restaurant_id=restaurant.id).first_or_404()
    return restaurant, table


def _get_loyalty_points(table_session, restaurant):
    """Return current loyalty points if loyalty is enabled and customer is linked."""
    if not restaurant.loyalty_enabled or not table_session.customer_id:
        return 0
    from app.services.loyalty_service import get_balance
    return get_balance(table_session.customer_id, restaurant.id)


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

        # Real-time: notify staff that a table is now occupied
        try:
            from app.events.waiter_events import notify_table_occupied
            notify_table_occupied(table)
        except Exception:
            pass

    session['session_token'] = table_session.session_token
    return table_session


# ──────────────────────────────────────────────
# Route 0: Customer Identification (optional)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/identify', methods=['POST'])
@csrf.exempt
def identify_customer(slug, table_id):
    """Optionally link a customer profile to the current session."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)

    stored_token = session.get('session_token')
    if not stored_token:
        return jsonify(success=False, error='No active session.'), 403

    table_session = TableSession.query.filter_by(
        session_token=stored_token, is_active=True
    ).first()
    if not table_session:
        return jsonify(success=False, error='Session expired.'), 403

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:100]
    phone = (data.get('phone') or '').strip()[:20]

    if not name:
        return jsonify(success=False, error='Name is required.'), 400

    # Save guest name on the session
    table_session.guest_name = name

    # If phone provided, find or create a lightweight Customer record
    if phone:
        customer = Customer.query.filter_by(phone=phone).first()
        if not customer:
            customer = Customer(phone=phone, name=name)
            db.session.add(customer)
            db.session.flush()
        elif not customer.name and name:
            customer.name = name
        table_session.customer_id = customer.id
        session['customer_name'] = customer.name or name
    else:
        session['customer_name'] = name

    db.session.commit()
    return jsonify(success=True, name=name)


# ──────────────────────────────────────────────
# Route 1: Menu
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>')
def menu(slug, table_id):
    """Display the restaurant menu for a table."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    table_session = _ensure_session(table, restaurant)
    now_time = datetime.now().time()
    ramadan_service = restaurant.get_current_ramadan_service(now_time)
    ramadan_iftar_time = (
        restaurant.get_effective_ramadan_iftar_time()
        if restaurant.ramadan_mode
        else DEFAULT_RAMADAN_IFTAR_TIME
    )

    # Query categories with active items
    categories_query = Category.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).order_by(Category.sort_order)

    if ramadan_service:
        categories_query = categories_query.filter(
            Category.ramadan_type == ramadan_service
        )

    categories = categories_query.all()

    # Filter categories by time-based availability
    for cat in categories:
        cat.is_time_available = True
        if cat.available_from and cat.available_until:
            if cat.available_from <= cat.available_until:
                cat.is_time_available = cat.available_from <= now_time <= cat.available_until
            else:  # overnight range (e.g., 22:00 - 06:00)
                cat.is_time_available = now_time >= cat.available_from or now_time <= cat.available_until

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
        guest_name=table_session.guest_name or session.get('customer_name', ''),
        loyalty_points=_get_loyalty_points(table_session, restaurant),
        ramadan_service=ramadan_service,
        ramadan_iftar_time=ramadan_iftar_time,
        lang=resolve_language(restaurant),
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
        lang=resolve_language(restaurant),
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
        lang=resolve_language(restaurant),
    )


# ──────────────────────────────────────────────
# Route 4: Place Order (POST JSON)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/order', methods=['POST'])
@csrf.exempt  # JSON API — CSRF token sent in header by JS
def place_order(slug, table_id):
    """Create a new order from cart data."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)

    if not restaurant.is_currently_open():
        return jsonify(success=False, error='Restaurant is currently closed. Please come back during opening hours.'), 403

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
    is_gift = bool(data.get('is_gift', False))
    gift_message = data.get('gift_message', '') if is_gift else ''

    # Validate gift target table
    gift_from_table = None
    if is_gift:
        target_table_id = data.get('gift_to_table')
        if not target_table_id:
            return jsonify(success=False, error='Please select a table to send the gift to.'), 400
        target_table = Table.query.filter_by(
            id=target_table_id, restaurant_id=restaurant.id
        ).first()
        if not target_table or target_table.status != 'occupied':
            return jsonify(success=False, error='Selected table is not occupied.'), 400
        if target_table.id == table.id:
            return jsonify(success=False, error='Cannot send a gift to your own table.'), 400
        gift_from_table = table.table_number

    try:
        order = create_order(
            session_id=table_session.id,
            items=items,
            payment_method=payment_method,
            special_notes=special_notes,
            restaurant=restaurant,
            table_id=target_table.id if is_gift else table.id,
            is_gift=is_gift,
            gift_from_table=gift_from_table,
            gift_message=gift_message[:300] if gift_message else None,
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
# Route 4b: Occupied Tables (for gift ordering)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/occupied-tables')
def occupied_tables(slug, table_id):
    """Return list of occupied tables (excluding current) for gift ordering."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)
    tables = Table.query.filter(
        Table.restaurant_id == restaurant.id,
        Table.status == 'occupied',
        Table.id != table.id,
    ).order_by(Table.table_number).all()
    return jsonify(tables=[
        {'id': t.id, 'table_number': t.table_number} for t in tables
    ])


# ──────────────────────────────────────────────
# Route 5: Order Tracking
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/track/<int:order_id>')
def track_order(slug, table_id, order_id):
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
        lang=resolve_language(restaurant),
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
        lang=resolve_language(restaurant),
    )


@customer_bp.route('/r/<slug>/table/<int:table_id>/call-waiter', methods=['POST'])
@csrf.exempt  # JSON API
def call_waiter(slug, table_id):
    """Create a waiter call request."""
    restaurant, table = _get_restaurant_and_table(slug, table_id)

    data = request.get_json(silent=True) or {}
    call_type = data.get('call_type', '')
    message = data.get('message', '').strip()

    valid_types = {'water', 'bill', 'help', 'custom'}
    if call_type not in valid_types:
        return jsonify(success=False, error='Invalid call type.'), 400
    if call_type == 'custom' and not message:
        return jsonify(success=False, error='Message is required for custom calls.'), 400

    try:
        waiter_call = WaiterCall(
            restaurant_id=restaurant.id,
            table_id=table.id,
            call_type=call_type,
            message=message or None,
        )
        db.session.add(waiter_call)
        db.session.commit()

        # Real-time: push waiter call to staff
        try:
            from app.events.waiter_events import notify_waiter_call
            notify_waiter_call(waiter_call)
        except Exception:
            pass

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
        lang=resolve_language(restaurant),
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
            lang=resolve_language(restaurant),
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
            lang=resolve_language(restaurant),
        )


# ──────────────────────────────────────────────
# Route 8: Online Payment (Flouci)
# ──────────────────────────────────────────────

@customer_bp.route('/r/<slug>/table/<int:table_id>/order/<int:order_id>/pay')
def payment_initiate(slug, table_id, order_id):
    """Redirect customer to Flouci online payment page."""
    from flask import current_app
    from app.services.payment_service import initiate_flouci_payment

    restaurant, table = _get_restaurant_and_table(slug, table_id)
    order = Order.query.filter_by(
        id=order_id, restaurant_id=restaurant.id
    ).first_or_404()

    if order.payment_status != 'pending':
        flash('This order has already been paid.', 'info')
        return redirect(url_for('customer.track_order',
                                slug=slug, table_id=table_id, order_id=order_id))

    success_url = url_for('customer.payment_callback', _external=True,
                          slug=slug, table_id=table_id, order_id=order_id)
    fail_url = url_for('customer.payment_callback', _external=True,
                       slug=slug, table_id=table_id, order_id=order_id, failed='1')

    result = initiate_flouci_payment(order_id, order.total_amount, success_url, fail_url)

    if result is None:
        flash('Payment service is unavailable. Please pay at the counter.', 'error')
        return redirect(url_for('customer.track_order',
                                slug=slug, table_id=table_id, order_id=order_id))

    return redirect(result['payment_url'])


@customer_bp.route('/r/<slug>/table/<int:table_id>/order/<int:order_id>/payment/callback')
def payment_callback(slug, table_id, order_id):
    """Verify Flouci payment and update order status."""
    from app.services.payment_service import verify_flouci_payment

    restaurant, table = _get_restaurant_and_table(slug, table_id)
    payment_id = request.args.get('payment_id', '')

    if request.args.get('failed'):
        flash('Payment was not completed. Please try again or pay at the counter.', 'error')
    elif payment_id and verify_flouci_payment(payment_id):
        flash('Payment successful! Your order is confirmed.', 'success')
    else:
        flash('Payment could not be verified. Please contact staff.', 'warning')

    return redirect(url_for('customer.track_order',
                            slug=slug, table_id=table_id, order_id=order_id))
