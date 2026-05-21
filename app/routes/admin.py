"""Super-admin blueprint — platform management for Tablii admins."""
from datetime import datetime, timezone

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models.order import Order
from app.models.restaurant import Restaurant, Subscription
from app.models.user import User
from app.services.subscription_service import PLAN_LIMITS
from app.services.upload_service import delete_file, save_uploaded_file, validate_image
from app.utils.decorators import super_admin_required
from app.utils.validators import validate_email

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@super_admin_required
def profile():
    """Edit the current super-admin profile."""
    user = current_user

    if not isinstance(user, User):
        return redirect(url_for('admin.restaurants'))

    if request.method == 'GET':
        return render_template('admin/profile.html', user=user)

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    errors = []
    if not name:
        errors.append('Name is required.')

    email_valid, email_error = validate_email(email)
    if not email_valid:
        errors.append(email_error)

    existing = User.query.filter(User.email == email, User.id != user.id).first()
    if existing:
        errors.append('An account with this email already exists.')

    if password and len(password) < 8:
        errors.append('Password must be at least 8 characters.')

    avatar = request.files.get('avatar')
    if avatar and avatar.filename:
        is_valid, upload_error = validate_image(avatar)
        if not is_valid:
            errors.append(upload_error or 'Invalid avatar file.')

    if errors:
        for err in errors:
            flash(err, 'error')
        return render_template('admin/profile.html', user=user, form=request.form)

    user.name = name
    user.email = email

    if password:
        user.set_password(password)

    if avatar and avatar.filename:
        new_avatar_url = save_uploaded_file(avatar, 'avatars')
        if not new_avatar_url:
            flash('Avatar upload failed.', 'error')
            return render_template('admin/profile.html', user=user, form=request.form)
        old_avatar_url = user.avatar_url
        user.avatar_url = new_avatar_url
        if old_avatar_url:
            delete_file(old_avatar_url)

    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('admin.profile'))


# ---------------------------------------------------------------------------
# GET /admin/restaurants
# ---------------------------------------------------------------------------

@admin_bp.route('/restaurants', methods=['GET'])
@login_required
@super_admin_required
def restaurants():
    """List all restaurants with owner info, plan, and order count. Paginated."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = (
        Restaurant.query
        .options(
            joinedload(Restaurant.owner).joinedload(User.subscription),
        )
        .order_by(Restaurant.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    restaurant_ids = [r.id for r in pagination.items]
    order_count_map = {
        rid: cnt
        for rid, cnt in db.session.query(
            Order.restaurant_id,
            func.count(Order.id),
        )
        .filter(Order.restaurant_id.in_(restaurant_ids))
        .group_by(Order.restaurant_id)
        .all()
    } if restaurant_ids else {}

    # Augment each restaurant with order count and owner email
    restaurants_data = []
    for r in pagination.items:
        owner = r.owner
        order_count = order_count_map.get(r.id, 0)
        restaurants_data.append({
            'restaurant': r,
            'owner_email': owner.email if owner else '—',
            'owner_name': owner.name if owner else '—',
            'plan': r.subscription.plan if r.subscription else 'none',
            'order_count': order_count,
        })

    return render_template(
        'admin/restaurants.html',
        restaurants_data=restaurants_data,
        pagination=pagination,
    )


# ---------------------------------------------------------------------------
# POST /admin/restaurants/<int:id>/toggle
# ---------------------------------------------------------------------------

@admin_bp.route('/restaurants/<int:restaurant_id>/toggle', methods=['POST'])
@login_required
@super_admin_required
def toggle_restaurant(restaurant_id):
    """Toggle the is_active flag of a restaurant. Returns JSON."""
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    restaurant.is_active = not restaurant.is_active
    db.session.commit()
    return jsonify({
        'success': True,
        'restaurant_id': restaurant.id,
        'is_active': restaurant.is_active,
    })


# ---------------------------------------------------------------------------
# GET /admin/subscriptions
# ---------------------------------------------------------------------------

@admin_bp.route('/subscriptions', methods=['GET'])
@login_required
@super_admin_required
def subscriptions():
    """List all subscriptions with restaurant name and plan info."""
    subs = (
        Subscription.query
        .options(joinedload(Subscription.owner))
        .options(joinedload(Subscription.restaurant))
        .order_by(Subscription.started_at.desc())
        .all()
    )
    for sub in subs:
        sub.active_location_count = Restaurant.query.filter_by(
            owner_id=sub.owner_id,
            is_active=True,
        ).count()
    return render_template('admin/subscriptions.html', subscriptions=subs)


# ---------------------------------------------------------------------------
# POST /admin/subscriptions/<int:id>/update
# ---------------------------------------------------------------------------

@admin_bp.route('/subscriptions/<int:sub_id>/update', methods=['POST'])
@login_required
@super_admin_required
def update_subscription(sub_id):
    """Update plan, limits, payment status, and expiry for a subscription."""
    sub = Subscription.query.get_or_404(sub_id)

    plan = request.form.get('plan', '').strip()
    max_locations = request.form.get('max_locations', type=int)
    max_tables = request.form.get('max_tables', type=int)
    max_items = request.form.get('max_items', type=int)
    expires_at_str = request.form.get('expires_at', '').strip()

    valid_plans = set(PLAN_LIMITS)
    if plan and plan in valid_plans:
        sub.plan = plan

    if max_locations is not None and max_locations > 0:
        sub.max_locations = max_locations

    if max_tables is not None and max_tables > 0:
        sub.max_tables = max_tables

    if max_items is not None and max_items > 0:
        sub.max_items = max_items

    sub.payment_completed = 'payment_completed' in request.form

    if expires_at_str:
        try:
            sub.expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            flash('Invalid expiry date format.', 'error')
            return redirect(url_for('admin.subscriptions'))

    db.session.commit()
    flash('Subscription updated.', 'success')
    return redirect(url_for('admin.subscriptions'))


# ---------------------------------------------------------------------------
# GET /admin/analytics
# ---------------------------------------------------------------------------

@admin_bp.route('/analytics', methods=['GET'])
@login_required
@super_admin_required
def analytics():
    """Platform-wide stats: total restaurants, orders, revenue, plan distribution."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_restaurants = Restaurant.query.count()
    active_restaurants = Restaurant.query.filter_by(is_active=True).count()
    new_this_month = Restaurant.query.filter(
        Restaurant.created_at >= month_start
    ).count()

    total_orders = Order.query.count()
    total_revenue_row = db.session.query(
        func.coalesce(func.sum(Order.total_amount), 0.0)
    ).scalar()
    total_revenue = float(total_revenue_row)

    # Plan distribution
    plan_counts = (
        db.session.query(Subscription.plan, func.count(Subscription.id))
        .group_by(Subscription.plan)
        .all()
    )

    active_subscriptions = Subscription.query.filter_by(is_active=True).count()

    # Recent 10 restaurants
    recent_restaurants = (
        Restaurant.query
        .order_by(Restaurant.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'admin/platform_analytics.html',
        total_restaurants=total_restaurants,
        active_restaurants=active_restaurants,
        new_this_month=new_this_month,
        total_orders=total_orders,
        total_revenue=total_revenue,
        plan_counts=dict(plan_counts),
        active_subscriptions=active_subscriptions,
        recent_restaurants=recent_restaurants,
    )
