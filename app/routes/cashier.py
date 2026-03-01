"""Cashier blueprint — order Kanban board and manual order entry."""
import json
from datetime import datetime, timezone

from flask import (
    Blueprint, g, jsonify, redirect, render_template,
    request, url_for, flash,
)
from flask_login import login_required

from app import db
from app.models.menu import Category, MenuItem
from app.models.order import Order
from app.models.table import Table, TableSession
from app.services.order_service import (
    create_order, get_active_orders, update_order_status,
)
from app.utils.decorators import restaurant_required, role_required
from app.utils.helpers import generate_random_token

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')


# ---------------------------------------------------------------------------
# Orders — Kanban board
# ---------------------------------------------------------------------------

@cashier_bp.route('/orders')
@login_required
@restaurant_required
@role_required('cashier', 'owner')
def orders():
    """Kanban board showing active orders in 4 columns."""
    restaurant = g.restaurant
    grouped = get_active_orders(restaurant.id)
    return render_template(
        'cashier/orders.html',
        restaurant=restaurant,
        grouped=grouped,
    )


@cashier_bp.route('/orders/<int:id>/status', methods=['POST'])
@login_required
@restaurant_required
@role_required('cashier', 'owner')
def update_status(id):
    """Advance order status. Accepts JSON {new_status}. Returns JSON."""
    restaurant = g.restaurant
    data = request.get_json(silent=True) or {}
    new_status = data.get('new_status', '').strip()

    if not new_status:
        return jsonify(success=False, error='new_status is required.'), 400

    ok, msg = update_order_status(id, new_status, restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400

    return jsonify(success=True, order_id=id, new_status=new_status)


# ---------------------------------------------------------------------------
# Manual order
# ---------------------------------------------------------------------------

@cashier_bp.route('/manual-order', methods=['GET', 'POST'])
@login_required
@restaurant_required
@role_required('cashier', 'owner')
def manual_order():
    """Staff-created order form."""
    restaurant = g.restaurant
    tables = Table.query.filter_by(restaurant_id=restaurant.id).order_by(
        Table.table_number
    ).all()
    categories = Category.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).order_by(Category.sort_order).all()
    menu_items = MenuItem.query.filter(
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.is_available.is_(True),
        MenuItem.deleted_at.is_(None),
    ).order_by(MenuItem.category_id, MenuItem.name_fr).all()

    if request.method == 'GET':
        return render_template(
            'cashier/manual_order.html',
            restaurant=restaurant,
            tables=tables,
            categories=categories,
            menu_items=menu_items,
        )

    # POST — parse form
    table_id = request.form.get('table_id', type=int)
    payment_method = request.form.get('payment_method', 'cash')
    special_notes = request.form.get('special_notes', '').strip()

    # Build items list from form: item_<id> = quantity
    items = []
    for key, val in request.form.items():
        if key.startswith('item_'):
            try:
                menu_item_id = int(key[5:])
                qty = int(val)
                if qty > 0:
                    items.append({
                        'menu_item_id': menu_item_id,
                        'quantity': qty,
                        'selected_options': [],
                        'notes': request.form.get(f'notes_{menu_item_id}', ''),
                    })
            except (ValueError, TypeError):
                continue

    if not items:
        flash('Select at least one item.', 'error')
        return redirect(url_for('cashier.manual_order'))

    # Resolve or create table session
    session_id = None
    table = None
    if table_id:
        table = Table.query.filter_by(
            id=table_id, restaurant_id=restaurant.id
        ).first()
        if table:
            active_session = TableSession.query.filter_by(
                table_id=table.id, is_active=True
            ).first()
            if not active_session:
                active_session = TableSession(
                    table_id=table.id,
                    restaurant_id=restaurant.id,
                    session_token=generate_random_token(),
                )
                db.session.add(active_session)
                db.session.flush()
                table.status = 'occupied'
            session_id = active_session.id

    try:
        order = create_order(
            session_id,
            items,
            payment_method,
            special_notes,
            restaurant,
            table_id=table_id,
        )
        flash(f'Order #{order.order_number} created.', 'success')
        return redirect(url_for('cashier.orders'))
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('cashier.manual_order'))
