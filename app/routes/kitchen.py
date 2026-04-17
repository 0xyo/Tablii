"""Kitchen blueprint — kitchen display screen."""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.user import StaffUser, User
from app.services.order_service import get_active_orders, update_order_status
from app.services.upload_service import delete_file, save_uploaded_file, validate_image
from app.utils.decorators import restaurant_required, role_required
from app.utils.validators import validate_email

kitchen_bp = Blueprint('kitchen', __name__, url_prefix='/kitchen')


@kitchen_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@restaurant_required
@role_required('kitchen', 'owner')
def profile():
    """Kitchen staff profile page (self-service)."""
    restaurant = g.restaurant
    user = current_user

    if request.method == 'GET':
        return render_template('kitchen/profile.html', restaurant=restaurant, user=user)

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
            'kitchen/profile.html',
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
                'kitchen/profile.html',
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
    return redirect(url_for('kitchen.profile'))


@kitchen_bp.route('')
@login_required
@restaurant_required
@role_required('kitchen', 'owner')
def display():
    """Kitchen display: accepted and preparing orders."""
    restaurant = g.restaurant
    grouped = get_active_orders(restaurant.id)
    return render_template(
        'kitchen/display.html',
        restaurant=restaurant,
        accepted=grouped.get('accepted', []),
        preparing=grouped.get('preparing', []),
    )


@kitchen_bp.route('/orders/<int:id>/preparing', methods=['POST'])
@login_required
@restaurant_required
@role_required('kitchen', 'owner')
def set_preparing(id):
    """Advance order to 'preparing'. Returns JSON."""
    ok, msg = update_order_status(id, 'preparing', g.restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400
    return jsonify(success=True, order_id=id, new_status='preparing')


@kitchen_bp.route('/orders/<int:id>/ready', methods=['POST'])
@login_required
@restaurant_required
@role_required('kitchen', 'owner')
def set_ready(id):
    """Advance order to 'ready'. Returns JSON."""
    ok, msg = update_order_status(id, 'ready', g.restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400
    return jsonify(success=True, order_id=id, new_status='ready')
