"""Cashier blueprint — order Kanban board and manual order entry."""

from flask import (
    Blueprint, g, jsonify, redirect, render_template,
    request, url_for, flash,
)
from flask_login import current_user, login_required

from app import db
from app.models.menu import Category, MenuItem
from app.models.order import Order
from app.models.table import Table, TableSession
from app.models.user import StaffUser, User
from app.services.order_service import (
    create_order, get_active_orders, update_order_status,
)
from app.services.upload_service import delete_file, save_uploaded_file, validate_image
from app.utils.decorators import restaurant_required, role_required
from app.utils.helpers import generate_random_token
from app.utils.validators import validate_email

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')


@cashier_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@restaurant_required
@role_required('cashier', 'owner')
def profile():
    """Cashier profile page (self-service)."""
    restaurant = g.restaurant
    user = current_user

    if request.method == 'GET':
        return render_template('cashier/profile.html', restaurant=restaurant, user=user)

    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')

    errors = []
    if not name:
        errors.append('Name is required.')

    if isinstance(user, StaffUser):
        username = request.form.get('username', '').strip()
        if not username:
            errors.append('Username is required.')
        else:
            existing = StaffUser.query.filter(
                StaffUser.restaurant_id == restaurant.id,
                StaffUser.username == username,
                StaffUser.id != user.id,
            ).first()
            if existing:
                errors.append('Username is already taken in this restaurant.')
        if password and len(password) < 6:
            errors.append('Password must be at least 6 characters.')
    elif isinstance(user, User):
        email = request.form.get('email', '').strip().lower()
        email_valid, email_error = validate_email(email)
        if not email_valid:
            errors.append(email_error)
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            errors.append('An account with this email already exists.')
        if password and len(password) < 8:
            errors.append('Password must be at least 8 characters.')
    else:
        errors.append('Unsupported user account.')

    avatar = request.files.get('avatar')
    if avatar and avatar.filename:
        is_valid, upload_error = validate_image(avatar)
        if not is_valid:
            errors.append(upload_error or 'Invalid avatar file.')

    if errors:
        for err in errors:
            flash(err, 'error')
        return render_template(
            'cashier/profile.html',
            restaurant=restaurant,
            user=user,
            form=request.form,
        )

    user.name = name
    if isinstance(user, StaffUser):
        user.username = request.form.get('username', '').strip()
    else:
        user.email = request.form.get('email', '').strip().lower()

    if password:
        user.set_password(password)

    if avatar and avatar.filename:
        new_avatar_url = save_uploaded_file(avatar, 'avatars')
        if not new_avatar_url:
            flash('Avatar upload failed.', 'error')
            return render_template(
                'cashier/profile.html',
                restaurant=restaurant,
                user=user,
                form=request.form,
            )
        old_avatar_url = user.avatar_url
        user.avatar_url = new_avatar_url
        if old_avatar_url:
            delete_file(old_avatar_url)

    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('cashier.profile'))


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


@cashier_bp.route('/orders/<int:id>/confirm-payment', methods=['POST'])
@login_required
@restaurant_required
@role_required('cashier', 'owner')
def confirm_payment(id):
    """Mark a cash/card order as paid."""
    restaurant = g.restaurant
    order = Order.query.filter_by(id=id, restaurant_id=restaurant.id).first_or_404()
    if order.payment_status == 'paid':
        return jsonify(success=True, message='Already paid.')
    order.payment_status = 'paid'
    db.session.commit()
    return jsonify(success=True, order_id=id)
