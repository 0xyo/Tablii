"""Waiter blueprint — table overview, waiter calls, serve orders."""
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template
from flask_login import current_user, login_required

from app import db
from app.models.order import Order, WaiterCall
from app.models.table import Table
from app.models.user import StaffUser, User
from app.services.order_service import close_table_session, update_order_status
from app.services.upload_service import delete_file, save_uploaded_file, validate_image
from app.utils.decorators import restaurant_required, role_required
from app.utils.validators import validate_email

waiter_bp = Blueprint('waiter', __name__, url_prefix='/waiter')


@waiter_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def profile():
    """Waiter profile page (self-service)."""
    restaurant = g.restaurant
    user = current_user

    if request.method == 'GET':
        return render_template('waiter/profile.html', restaurant=restaurant, user=user)

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
            'waiter/profile.html',
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
                'waiter/profile.html',
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
    return redirect(url_for('waiter.profile'))


@waiter_bp.route('/tables')
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def tables():
    """Show tables assigned to the current waiter."""
    restaurant = g.restaurant

    # Owners see all tables; waiters see only their assigned tables
    if current_user.role == 'owner':
        assigned = Table.query.filter_by(
            restaurant_id=restaurant.id
        ).order_by(Table.table_number).all()
    else:
        assigned = Table.query.filter_by(
            restaurant_id=restaurant.id,
            assigned_waiter_id=current_user.id,
        ).order_by(Table.table_number).all()

    # Pending call count per table
    call_counts: dict[int, int] = {}
    if assigned:
        table_ids = [t.id for t in assigned]
        calls = WaiterCall.query.filter(
            WaiterCall.table_id.in_(table_ids),
            WaiterCall.status == 'pending',
        ).all()
        for c in calls:
            call_counts[c.table_id] = call_counts.get(c.table_id, 0) + 1

    return render_template(
        'waiter/tables.html',
        restaurant=restaurant,
        tables=assigned,
        call_counts=call_counts,
    )


@waiter_bp.route('/calls')
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def calls():
    """Return pending WaiterCall records as JSON."""
    restaurant = g.restaurant
    pending = WaiterCall.query.filter_by(
        restaurant_id=restaurant.id, status='pending'
    ).order_by(WaiterCall.created_at.asc()).all()

    return jsonify(calls=[
        {
            'id': c.id,
            'table_id': c.table_id,
            'call_type': c.call_type,
            'message': c.message,
            'created_at': c.created_at.isoformat(),
        }
        for c in pending
    ])


@waiter_bp.route('/calls/<int:id>/resolve', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def resolve_call(id):
    """Mark a waiter call as resolved. Returns JSON."""
    restaurant = g.restaurant
    call = WaiterCall.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    call.status = 'resolved'
    call.resolved_at = datetime.now(timezone.utc)
    call.resolved_by = current_user.id
    db.session.commit()

    return jsonify(success=True, call_id=id, table_id=call.table_id)


@waiter_bp.route('/orders/<int:id>/served', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def mark_served(id):
    """Advance order to 'served'. Returns JSON."""
    ok, msg = update_order_status(id, 'served', g.restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400
    return jsonify(success=True, order_id=id, new_status='served')


@waiter_bp.route('/tables/<int:table_id>/close', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def close_table(table_id):
    """Close the active session on a table and set it to free."""
    ok, msg = close_table_session(table_id, g.restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400
    return jsonify(success=True, table_id=table_id, new_status='free')


@waiter_bp.route('/orders/<int:id>/confirm-payment', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def confirm_payment(id):
    """Mark a cash/card order as paid (waiter collected money at table)."""
    restaurant = g.restaurant
    order = Order.query.filter_by(id=id, restaurant_id=restaurant.id).first_or_404()
    if order.payment_status == 'paid':
        return jsonify(success=True, message='Already paid.')
    order.payment_status = 'paid'
    db.session.commit()
    return jsonify(success=True, order_id=id)
