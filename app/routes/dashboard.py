"""Dashboard blueprint — restaurant owner admin panel."""
import os
from datetime import date, datetime, timezone

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, send_file, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models.menu import Category, CustomOption, Customization, MenuItem
from app.models.order import Order
from app.models.restaurant import OperatingHours, Restaurant
from app.models.table import Table, TableSession
from app.models.user import StaffUser
from app.services.qr_service import generate_table_qr as _generate_table_qr
from app.services.upload_service import save_uploaded_file
from app.utils.decorators import restaurant_required, role_required
from app.utils.validators import validate_price

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


# ──────────────────────────────────────────────
# 1. Overview
# ──────────────────────────────────────────────

@dashboard_bp.route('')
@login_required
@restaurant_required
def overview():
    """Dashboard home — today's stats and recent orders."""
    restaurant = g.restaurant

    today_orders = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        func.date(Order.created_at) == date.today(),
    ).all()

    orders_today = len(today_orders)
    revenue_today = sum(
        o.total_amount for o in today_orders if o.payment_status == 'paid'
    )
    tables_occupied = Table.query.filter_by(
        restaurant_id=restaurant.id, status='occupied'
    ).count()
    active_staff = StaffUser.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).count()

    recent_orders = Order.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(Order.created_at.desc()).limit(10).all()

    return render_template(
        'dashboard/overview.html',
        restaurant=restaurant,
        orders_today=orders_today,
        revenue_today=revenue_today,
        tables_occupied=tables_occupied,
        active_staff=active_staff,
        recent_orders=recent_orders,
    )


# ──────────────────────────────────────────────
# 2. Categories
# ──────────────────────────────────────────────

@dashboard_bp.route('/menu/categories')
@login_required
@restaurant_required
def categories():
    """List all menu categories."""
    restaurant = g.restaurant
    cats = Category.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(Category.sort_order).all()

    for cat in cats:
        cat.item_count = MenuItem.query.filter(
            MenuItem.category_id == cat.id,
            MenuItem.deleted_at.is_(None),
        ).count()

    return render_template('dashboard/menu/categories.html',
                           restaurant=restaurant, categories=cats)


@dashboard_bp.route('/menu/categories/add', methods=['POST'])
@login_required
@restaurant_required
def category_add():
    """Create a new category."""
    restaurant = g.restaurant
    name_fr = request.form.get('name_fr', '').strip()
    if not name_fr:
        flash('French name is required.', 'error')
        return redirect(url_for('dashboard.categories'))

    max_order = db.session.query(func.max(Category.sort_order)).filter_by(
        restaurant_id=restaurant.id
    ).scalar() or 0

    cat = Category(
        restaurant_id=restaurant.id,
        name_fr=name_fr,
        name_ar=request.form.get('name_ar', '').strip() or None,
        name_en=request.form.get('name_en', '').strip() or None,
        icon=request.form.get('icon', '').strip() or None,
        ramadan_type=request.form.get('ramadan_type') or None,
        sort_order=max_order + 1,
    )
    db.session.add(cat)
    db.session.commit()
    flash('Category created.', 'success')
    return redirect(url_for('dashboard.categories'))


@dashboard_bp.route('/menu/categories/<int:id>/update', methods=['POST'])
@login_required
@restaurant_required
def category_update(id):
    """Update an existing category."""
    restaurant = g.restaurant
    cat = Category.query.filter_by(id=id, restaurant_id=restaurant.id).first_or_404()

    cat.name_fr = request.form.get('name_fr', '').strip() or cat.name_fr
    cat.name_ar = request.form.get('name_ar', '').strip() or None
    cat.name_en = request.form.get('name_en', '').strip() or None
    cat.icon = request.form.get('icon', '').strip() or None
    cat.ramadan_type = request.form.get('ramadan_type') or None
    cat.is_active = 'is_active' in request.form

    db.session.commit()
    flash('Category updated.', 'success')
    return redirect(url_for('dashboard.categories'))


@dashboard_bp.route('/menu/categories/<int:id>/delete', methods=['POST'])
@login_required
@restaurant_required
def category_delete(id):
    """Delete a category (only if no active items)."""
    restaurant = g.restaurant
    cat = Category.query.filter_by(id=id, restaurant_id=restaurant.id).first_or_404()

    active_items = MenuItem.query.filter(
        MenuItem.category_id == cat.id,
        MenuItem.deleted_at.is_(None),
    ).count()
    if active_items > 0:
        flash('Cannot delete category with active menu items.', 'error')
        return redirect(url_for('dashboard.categories'))

    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('dashboard.categories'))


@dashboard_bp.route('/menu/categories/reorder', methods=['POST'])
@login_required
@restaurant_required
def category_reorder():
    """Accept JSON order update for drag-and-drop category sorting."""
    restaurant = g.restaurant
    data = request.get_json(silent=True) or {}
    order = data.get('order', [])

    for entry in order:
        cat = Category.query.filter_by(
            id=entry['id'], restaurant_id=restaurant.id
        ).first()
        if cat:
            cat.sort_order = entry['sort_order']

    db.session.commit()
    return jsonify(success=True)


# ──────────────────────────────────────────────
# 3. Menu Items
# ──────────────────────────────────────────────

@dashboard_bp.route('/menu/items')
@login_required
@restaurant_required
def menu_items():
    """List menu items with optional category filter."""
    restaurant = g.restaurant
    category_id = request.args.get('category_id', type=int)

    query = MenuItem.query.filter(
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    )
    if category_id:
        query = query.filter_by(category_id=category_id)

    items = query.order_by(MenuItem.category_id, MenuItem.sort_order).all()
    categories = Category.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(Category.sort_order).all()

    return render_template('dashboard/menu/items.html',
                           restaurant=restaurant, items=items,
                           categories=categories,
                           selected_category=category_id)


@dashboard_bp.route('/menu/item/new', methods=['GET', 'POST'])
@login_required
@restaurant_required
def menu_item_new():
    """Create a new menu item."""
    restaurant = g.restaurant
    categories = Category.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).order_by(Category.sort_order).all()

    if request.method == 'GET':
        return render_template('dashboard/menu/item_form.html',
                               restaurant=restaurant, categories=categories,
                               item=None, mode='create')

    # POST
    name_fr = request.form.get('name_fr', '').strip()
    price_str = request.form.get('price', '')
    category_id = request.form.get('category_id', type=int)

    errors = []
    if not name_fr:
        errors.append('French name is required.')

    valid_price, price_err = validate_price(price_str)
    if not valid_price:
        errors.append(price_err)
    else:
        price = float(price_str)

    cat = Category.query.filter_by(
        id=category_id, restaurant_id=restaurant.id
    ).first()
    if not cat:
        errors.append('Invalid category.')

    # Subscription limit
    current_count = MenuItem.query.filter(
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).count()
    if restaurant.subscription and current_count >= restaurant.subscription.max_items:
        errors.append(
            f'Subscription limit reached ({restaurant.subscription.max_items} items).'
        )

    if errors:
        for e in errors:
            flash(e, 'error')
        return render_template('dashboard/menu/item_form.html',
                               restaurant=restaurant, categories=categories,
                               item=None, mode='create', form=request.form)

    image_url = None
    if 'image' in request.files:
        f = request.files['image']
        if f and f.filename:
            image_url = save_uploaded_file(f, 'menu_items')

    item = MenuItem(
        restaurant_id=restaurant.id,
        category_id=category_id,
        name_fr=name_fr,
        name_ar=request.form.get('name_ar', '').strip() or None,
        name_en=request.form.get('name_en', '').strip() or None,
        description_fr=request.form.get('description_fr', '').strip() or None,
        description_ar=request.form.get('description_ar', '').strip() or None,
        description_en=request.form.get('description_en', '').strip() or None,
        price=price,
        prep_time=request.form.get('prep_time', type=int),
        calories=request.form.get('calories', type=int),
        allergens=request.form.get('allergens', '').strip() or None,
        is_popular='is_popular' in request.form,
        image_url=image_url,
    )
    db.session.add(item)
    db.session.commit()
    flash('Menu item created.', 'success')
    return redirect(url_for('dashboard.menu_items'))


@dashboard_bp.route('/menu/item/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@restaurant_required
def menu_item_edit(id):
    """Edit an existing menu item."""
    restaurant = g.restaurant
    item = MenuItem.query.filter(
        MenuItem.id == id,
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).first_or_404()

    categories = Category.query.filter_by(
        restaurant_id=restaurant.id, is_active=True
    ).order_by(Category.sort_order).all()

    if request.method == 'GET':
        return render_template('dashboard/menu/item_form.html',
                               restaurant=restaurant, categories=categories,
                               item=item, mode='edit')

    # POST
    name_fr = request.form.get('name_fr', '').strip()
    price_str = request.form.get('price', '')
    category_id = request.form.get('category_id', type=int)

    errors = []
    if not name_fr:
        errors.append('French name is required.')

    valid_price, price_err = validate_price(price_str)
    if not valid_price:
        errors.append(price_err)
    else:
        price = float(price_str)

    cat = Category.query.filter_by(
        id=category_id, restaurant_id=restaurant.id
    ).first()
    if not cat:
        errors.append('Invalid category.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return render_template('dashboard/menu/item_form.html',
                               restaurant=restaurant, categories=categories,
                               item=item, mode='edit', form=request.form)

    # Handle image upload
    if 'image' in request.files:
        f = request.files['image']
        if f and f.filename:
            image_url = save_uploaded_file(f, 'menu_items')
            item.image_url = image_url

    item.name_fr = name_fr
    item.name_ar = request.form.get('name_ar', '').strip() or None
    item.name_en = request.form.get('name_en', '').strip() or None
    item.description_fr = request.form.get('description_fr', '').strip() or None
    item.description_ar = request.form.get('description_ar', '').strip() or None
    item.description_en = request.form.get('description_en', '').strip() or None
    item.category_id = category_id
    item.price = price
    item.prep_time = request.form.get('prep_time', type=int)
    item.calories = request.form.get('calories', type=int)
    item.allergens = request.form.get('allergens', '').strip() or None
    item.is_popular = 'is_popular' in request.form

    db.session.commit()
    flash('Menu item updated.', 'success')
    return redirect(url_for('dashboard.menu_items'))


@dashboard_bp.route('/menu/item/<int:id>/delete', methods=['POST'])
@login_required
@restaurant_required
def menu_item_delete(id):
    """Soft-delete a menu item."""
    restaurant = g.restaurant
    item = MenuItem.query.filter(
        MenuItem.id == id,
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).first_or_404()

    item.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    flash('Menu item removed.', 'success')
    return redirect(url_for('dashboard.menu_items'))


@dashboard_bp.route('/menu/item/<int:id>/toggle', methods=['POST'])
@login_required
@restaurant_required
def menu_item_toggle(id):
    """Toggle item availability — returns JSON."""
    restaurant = g.restaurant
    item = MenuItem.query.filter(
        MenuItem.id == id,
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).first_or_404()

    item.is_available = not item.is_available
    db.session.commit()
    return jsonify(success=True, is_available=item.is_available)


# ──────────────────────────────────────────────
# 4. Customizations
# ──────────────────────────────────────────────

@dashboard_bp.route('/menu/item/<int:item_id>/customizations')
@login_required
@restaurant_required
def customizations(item_id):
    """List customization groups for a menu item."""
    restaurant = g.restaurant
    item = MenuItem.query.filter(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).first_or_404()

    custs = item.customizations.all()
    for c in custs:
        c.opts = c.options.all()

    return render_template('dashboard/menu/customizations.html',
                           restaurant=restaurant, item=item,
                           customizations=custs)


@dashboard_bp.route('/menu/item/<int:item_id>/customizations/add', methods=['POST'])
@login_required
@restaurant_required
def customization_add(item_id):
    """Add a customization group to a menu item."""
    restaurant = g.restaurant
    item = MenuItem.query.filter(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).first_or_404()

    group_name_fr = request.form.get('group_name_fr', '').strip()
    if not group_name_fr:
        flash('Group name (FR) is required.', 'error')
        return redirect(url_for('dashboard.customizations', item_id=item_id))

    cust = Customization(
        menu_item_id=item.id,
        group_name_fr=group_name_fr,
        group_name_ar=request.form.get('group_name_ar', '').strip() or None,
        group_name_en=request.form.get('group_name_en', '').strip() or None,
        selection_type=request.form.get('selection_type', 'single'),
        is_required='is_required' in request.form,
        max_selections=request.form.get('max_selections', type=int),
    )
    db.session.add(cust)
    db.session.commit()
    flash('Customization group added.', 'success')
    return redirect(url_for('dashboard.customizations', item_id=item_id))


@dashboard_bp.route('/menu/customizations/<int:id>/options/add', methods=['POST'])
@login_required
@restaurant_required
def custom_option_add(id):
    """Add an option to a customization group."""
    restaurant = g.restaurant
    cust = Customization.query.join(MenuItem).filter(
        Customization.id == id,
        MenuItem.restaurant_id == restaurant.id,
    ).first_or_404()

    extra_price_str = request.form.get('extra_price', '0')
    valid, err = validate_price(extra_price_str)
    if not valid:
        flash(f'Extra price: {err}', 'error')
        return redirect(url_for('dashboard.customizations', item_id=cust.menu_item_id))

    option = CustomOption(
        customization_id=cust.id,
        name_fr=request.form.get('name_fr', '').strip(),
        name_ar=request.form.get('name_ar', '').strip() or None,
        name_en=request.form.get('name_en', '').strip() or None,
        extra_price=float(extra_price_str),
        is_default='is_default' in request.form,
    )
    db.session.add(option)
    db.session.commit()
    flash('Option added.', 'success')
    return redirect(url_for('dashboard.customizations', item_id=cust.menu_item_id))


@dashboard_bp.route('/menu/customizations/<int:id>/delete', methods=['POST'])
@login_required
@restaurant_required
def customization_delete(id):
    """Delete a customization group and all its options."""
    restaurant = g.restaurant
    cust = Customization.query.join(MenuItem).filter(
        Customization.id == id,
        MenuItem.restaurant_id == restaurant.id,
    ).first_or_404()

    item_id = cust.menu_item_id
    db.session.delete(cust)
    db.session.commit()
    flash('Customization group deleted.', 'success')
    return redirect(url_for('dashboard.customizations', item_id=item_id))


# ──────────────────────────────────────────────
# 5. Tables
# ──────────────────────────────────────────────

@dashboard_bp.route('/tables')
@login_required
@restaurant_required
def tables():
    """List all tables."""
    restaurant = g.restaurant
    all_tables = Table.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(Table.table_number).all()
    waiters = StaffUser.query.filter_by(
        restaurant_id=restaurant.id, role='waiter', is_active=True
    ).all()
    return render_template('dashboard/tables/list.html',
                           restaurant=restaurant, tables=all_tables,
                           waiters=waiters)


@dashboard_bp.route('/tables/add', methods=['POST'])
@login_required
@restaurant_required
def table_add():
    """Create a new table and generate its QR code."""
    restaurant = g.restaurant
    table_number = request.form.get('table_number', type=int)
    capacity = request.form.get('capacity', 4, type=int)

    if not table_number:
        flash('Table number is required.', 'error')
        return redirect(url_for('dashboard.tables'))

    # Subscription limit
    current_count = Table.query.filter_by(restaurant_id=restaurant.id).count()
    if restaurant.subscription and current_count >= restaurant.subscription.max_tables:
        flash(
            f'Subscription limit reached ({restaurant.subscription.max_tables} tables).',
            'error',
        )
        return redirect(url_for('dashboard.tables'))

    # Uniqueness check
    existing = Table.query.filter_by(
        restaurant_id=restaurant.id, table_number=table_number
    ).first()
    if existing:
        flash(f'Table {table_number} already exists.', 'error')
        return redirect(url_for('dashboard.tables'))

    table = Table(
        restaurant_id=restaurant.id,
        table_number=table_number,
        capacity=capacity,
    )
    db.session.add(table)
    db.session.flush()  # get table.id

    # Auto-generate QR code
    qr_url = _generate_table_qr(restaurant.slug, table.id, table_number)
    table.qr_code_url = qr_url

    db.session.commit()
    flash(f'Table {table_number} created with QR code.', 'success')
    return redirect(url_for('dashboard.tables'))


@dashboard_bp.route('/tables/<int:id>/delete', methods=['POST'])
@login_required
@restaurant_required
def table_delete(id):
    """Delete a table (only if no active session)."""
    restaurant = g.restaurant
    table = Table.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    active_session = TableSession.query.filter_by(
        table_id=table.id, is_active=True
    ).first()
    if active_session:
        flash('Cannot delete table with an active session.', 'error')
        return redirect(url_for('dashboard.tables'))

    db.session.delete(table)
    db.session.commit()
    flash('Table deleted.', 'success')
    return redirect(url_for('dashboard.tables'))


@dashboard_bp.route('/tables/<int:id>/qr')
@login_required
@restaurant_required
def table_qr(id):
    """Download or regenerate the QR code for a table."""
    restaurant = g.restaurant
    table = Table.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    if not table.qr_code_url:
        qr_url = _generate_table_qr(restaurant.slug, table.id, table.table_number)
        table.qr_code_url = qr_url
        db.session.commit()

    # Derive absolute filesystem path from the relative URL stored
    # e.g. "/static/images/uploads/qrcodes/table_slug_1.png"
    relative = (table.qr_code_url or '').lstrip('/')
    qr_path = os.path.join(current_app.root_path, relative.replace('static/', 'static/', 1))

    if os.path.exists(qr_path):
        return send_file(qr_path, as_attachment=True,
                         download_name=f'table_{table.table_number}_qr.png')
    abort(404)


@dashboard_bp.route('/tables/<int:id>/assign-waiter', methods=['POST'])
@login_required
@restaurant_required
def table_assign_waiter(id):
    """Assign a waiter to a table."""
    restaurant = g.restaurant
    table = Table.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    waiter_id = request.form.get('waiter_id', type=int)
    if waiter_id:
        waiter = StaffUser.query.filter_by(
            id=waiter_id, restaurant_id=restaurant.id, role='waiter'
        ).first()
        if not waiter:
            flash('Invalid waiter.', 'error')
            return redirect(url_for('dashboard.tables'))
        table.assigned_waiter_id = waiter_id
    else:
        table.assigned_waiter_id = None

    db.session.commit()
    flash('Waiter assignment updated.', 'success')
    return redirect(url_for('dashboard.tables'))


# ──────────────────────────────────────────────
# 6. Staff Management
# ──────────────────────────────────────────────

@dashboard_bp.route('/staff')
@login_required
@restaurant_required
def staff():
    """List all staff members."""
    restaurant = g.restaurant
    members = StaffUser.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(StaffUser.name).all()
    return render_template('dashboard/staff/list.html',
                           restaurant=restaurant, staff=members)


@dashboard_bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
@restaurant_required
def staff_add():
    """Add a new staff member."""
    restaurant = g.restaurant

    if request.method == 'GET':
        return render_template('dashboard/staff/form.html',
                               restaurant=restaurant, member=None, mode='create')

    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', '')

    errors = []
    if not name:
        errors.append('Name is required.')
    if not username:
        errors.append('Username is required.')
    if len(password) < 6:
        errors.append('Password must be at least 6 characters.')
    if role not in ('cashier', 'kitchen', 'waiter'):
        errors.append('Invalid role.')

    # Username uniqueness within restaurant
    existing = StaffUser.query.filter_by(
        restaurant_id=restaurant.id, username=username
    ).first()
    if existing:
        errors.append(f'Username "{username}" is already taken.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return render_template('dashboard/staff/form.html',
                               restaurant=restaurant, member=None, mode='create',
                               form=request.form)

    member = StaffUser(
        restaurant_id=restaurant.id,
        name=name,
        username=username,
        role=role,
    )
    member.set_password(password)
    db.session.add(member)
    db.session.commit()
    flash(f'Staff member {name} added.', 'success')
    return redirect(url_for('dashboard.staff'))


@dashboard_bp.route('/staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@restaurant_required
def staff_edit(id):
    """Edit a staff member."""
    restaurant = g.restaurant
    member = StaffUser.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    if request.method == 'GET':
        return render_template('dashboard/staff/form.html',
                               restaurant=restaurant, member=member, mode='edit')

    name = request.form.get('name', '').strip()
    role = request.form.get('role', '')
    password = request.form.get('password', '')
    is_active = 'is_active' in request.form

    errors = []
    if not name:
        errors.append('Name is required.')
    if role not in ('cashier', 'kitchen', 'waiter'):
        errors.append('Invalid role.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return render_template('dashboard/staff/form.html',
                               restaurant=restaurant, member=member, mode='edit',
                               form=request.form)

    member.name = name
    member.role = role
    member.is_active = is_active
    if password and len(password) >= 6:
        member.set_password(password)

    db.session.commit()
    flash('Staff member updated.', 'success')
    return redirect(url_for('dashboard.staff'))


@dashboard_bp.route('/staff/<int:id>/delete', methods=['POST'])
@login_required
@restaurant_required
def staff_delete(id):
    """Delete a staff member."""
    restaurant = g.restaurant
    member = StaffUser.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()
    db.session.delete(member)
    db.session.commit()
    flash('Staff member removed.', 'success')
    return redirect(url_for('dashboard.staff'))


# ──────────────────────────────────────────────
# 7. Order History
# ──────────────────────────────────────────────

@dashboard_bp.route('/orders/history')
@login_required
@restaurant_required
def order_history():
    """Paginated, filtered order history."""
    restaurant = g.restaurant
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)

    query = Order.query.filter_by(restaurant_id=restaurant.id)

    if status:
        query = query.filter_by(status=status)
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Order.created_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            from datetime import timedelta
            query = query.filter(Order.created_at < dt + timedelta(days=1))
        except ValueError:
            pass

    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template(
        'dashboard/orders/history.html',
        restaurant=restaurant,
        orders=pagination.items,
        pagination=pagination,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


# ──────────────────────────────────────────────
# 8. Settings
# ──────────────────────────────────────────────

@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@restaurant_required
def settings():
    """Restaurant settings page."""
    restaurant = g.restaurant
    hours = {
        h.day_of_week: h
        for h in OperatingHours.query.filter_by(
            restaurant_id=restaurant.id
        ).all()
    }

    if request.method == 'GET':
        return render_template('dashboard/settings.html',
                               restaurant=restaurant, hours=hours)

    # POST
    restaurant.name = request.form.get('name', '').strip() or restaurant.name
    restaurant.description = request.form.get('description', '').strip() or None
    restaurant.address = request.form.get('address', '').strip() or None
    restaurant.phone = request.form.get('phone', '').strip() or None
    restaurant.city = request.form.get('city', '').strip() or None

    tax_str = request.form.get('tax_rate', '0')
    valid_tax, _ = validate_price(tax_str)
    if valid_tax:
        restaurant.tax_rate = float(tax_str)

    svc_str = request.form.get('service_charge', '0')
    valid_svc, _ = validate_price(svc_str)
    if valid_svc:
        restaurant.service_charge = float(svc_str)

    restaurant.auto_accept = 'auto_accept' in request.form
    restaurant.online_payment = 'online_payment' in request.form
    restaurant.ramadan_mode = 'ramadan_mode' in request.form

    # Logo upload
    if 'logo' in request.files:
        f = request.files['logo']
        if f and f.filename:
            restaurant.logo_url = save_uploaded_file(f, 'logos')

    # Operating hours (7 days, 0=Monday … 6=Sunday)
    for day in range(7):
        open_time_str = request.form.get(f'open_{day}', '')
        close_time_str = request.form.get(f'close_{day}', '')
        is_closed = f'closed_{day}' in request.form

        hour_rec = hours.get(day)
        if not hour_rec:
            hour_rec = OperatingHours(
                restaurant_id=restaurant.id, day_of_week=day
            )
            db.session.add(hour_rec)

        hour_rec.is_closed = is_closed
        if not is_closed and open_time_str and close_time_str:
            try:
                from datetime import time
                open_h, open_m = map(int, open_time_str.split(':'))
                close_h, close_m = map(int, close_time_str.split(':'))
                hour_rec.open_time = time(open_h, open_m)
                hour_rec.close_time = time(close_h, close_m)
            except (ValueError, TypeError):
                pass

    db.session.commit()
    flash('Settings saved.', 'success')
    return redirect(url_for('dashboard.settings'))
