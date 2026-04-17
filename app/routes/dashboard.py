"""Dashboard blueprint — restaurant owner admin panel."""
import os
from datetime import date, datetime, timedelta, time as _time, timezone

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, send_file, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models.menu import Category, CustomOption, Customization, MenuItem
from app.models.order import Order
from app.models.restaurant import (
    DEFAULT_RAMADAN_IFTAR_TIME,
    OperatingHours,
    Restaurant,
    Subscription,
)
from app.models.review import Review
from app.models.table import Table, TableSession
from app.models.user import StaffUser, User
from app.services.notification_service import (
    get_unread_notifications, mark_all_read, mark_notification_read,
)
from app.services.qr_service import generate_table_qr as _generate_table_qr
from app.services.upload_service import delete_file, save_uploaded_file, validate_image
from app.utils.decorators import restaurant_required, role_required
from app.utils.validators import validate_email, validate_price

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

    icon_url = None
    if 'icon_image' in request.files:
        f = request.files['icon_image']
        if f and f.filename:
            icon_url = save_uploaded_file(f, 'category_icons')

    cat = Category(
        restaurant_id=restaurant.id,
        name_fr=name_fr,
        name_ar=request.form.get('name_ar', '').strip() or None,
        name_en=request.form.get('name_en', '').strip() or None,
        icon=request.form.get('icon', '').strip() or None,
        icon_url=icon_url,
        ramadan_type=request.form.get('ramadan_type') or None,
        sort_order=max_order + 1,
    )

    # Time-based availability
    avail_from = request.form.get('available_from', '').strip()
    avail_until = request.form.get('available_until', '').strip()
    if avail_from:
        try:
            cat.available_from = _time.fromisoformat(avail_from)
        except ValueError:
            pass
    if avail_until:
        try:
            cat.available_until = _time.fromisoformat(avail_until)
        except ValueError:
            pass

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
    cat.ramadan_type = request.form.get('ramadan_type') or None
    cat.is_active = 'is_active' in request.form

    # Time-based availability
    avail_from = request.form.get('available_from', '').strip()
    avail_until = request.form.get('available_until', '').strip()
    if avail_from:
        try:
            cat.available_from = _time.fromisoformat(avail_from)
        except ValueError:
            pass
    else:
        cat.available_from = None
    if avail_until:
        try:
            cat.available_until = _time.fromisoformat(avail_until)
        except ValueError:
            pass
    else:
        cat.available_until = None

    # Handle icon removal
    if request.form.get('remove_icon') == '1':
        if cat.icon_url:
            delete_file(cat.icon_url)
        cat.icon = None
        cat.icon_url = None

    # Handle icon image upload
    if 'icon_image' in request.files:
        f = request.files['icon_image']
        if f and f.filename:
            if cat.icon_url:
                delete_file(cat.icon_url)
            cat.icon_url = save_uploaded_file(f, 'category_icons')
            cat.icon = None  # clear emoji when custom image is uploaded

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
    if item.image_url:
        delete_file(item.image_url)
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
    floor_data = [
        {
            'id': t.id,
            'table_number': t.table_number,
            'status': t.status,
            'pos_x': t.position_x,
            'pos_y': t.position_y,
        }
        for t in all_tables
    ]
    return render_template('dashboard/tables/list.html',
                           restaurant=restaurant, tables=all_tables,
                           waiters=waiters, floor_data=floor_data)


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


@dashboard_bp.route('/tables/layout', methods=['POST'])
@login_required
@restaurant_required
def table_layout():
    """Save floor plan positions for tables."""
    restaurant = g.restaurant
    data = request.get_json(silent=True) or {}
    positions = data.get('positions', [])

    table_ids = {t.id for t in Table.query.filter_by(restaurant_id=restaurant.id).all()}
    for pos in positions:
        tid = pos.get('id')
        if tid not in table_ids:
            continue
        table = db.session.get(Table, tid)
        table.position_x = float(pos.get('pos_x', 0))
        table.position_y = float(pos.get('pos_y', 0))

    db.session.commit()
    return jsonify(success=True)


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

    # Build expected file path
    filename = f'table_{restaurant.slug}_{table.table_number}.png'
    qr_dir = os.path.join(current_app.root_path, 'static', 'images', 'uploads', 'qrcodes')
    qr_path = os.path.join(qr_dir, filename)

    # Regenerate if file doesn't exist on disk
    if not os.path.exists(qr_path):
        qr_url = _generate_table_qr(restaurant.slug, table.id, table.table_number)
        if qr_url:
            table.qr_code_url = qr_url
            db.session.commit()
        else:
            flash('Failed to generate QR code. Please try again.', 'error')
            return redirect(url_for('dashboard.tables'))

    if os.path.exists(qr_path):
        return send_file(qr_path, as_attachment=True,
                         download_name=f'table_{table.table_number}_qr.png')

    flash('QR code file not found. Please try again.', 'error')
    return redirect(url_for('dashboard.tables'))


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


@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@restaurant_required
@role_required('owner')
def profile():
    """Owner profile page."""
    restaurant = g.restaurant
    user = current_user

    if not isinstance(user, User):
        abort(403)

    if request.method == 'GET':
        return render_template(
            'dashboard/profile.html',
            restaurant=restaurant,
            user=user,
        )

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
        return render_template(
            'dashboard/profile.html',
            restaurant=restaurant,
            user=user,
            form=request.form,
        )

    user.name = name
    user.email = email

    if password:
        user.set_password(password)

    if avatar and avatar.filename:
        new_avatar_url = save_uploaded_file(avatar, 'avatars')
        if not new_avatar_url:
            flash('Avatar upload failed.', 'error')
            return render_template(
                'dashboard/profile.html',
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
    return redirect(url_for('dashboard.profile'))


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

    lang_choice = request.form.get('default_language', 'fr')
    if lang_choice in ('fr', 'ar', 'en'):
        restaurant.default_language = lang_choice

    restaurant.is_open = 'is_open' in request.form
    restaurant.auto_accept = 'auto_accept' in request.form
    restaurant.online_payment = 'online_payment' in request.form
    restaurant.ramadan_mode = 'ramadan_mode' in request.form

    # Ramadan Iftar time
    iftar_str = request.form.get('ramadan_iftar_time', '').strip()
    if iftar_str:
        try:
            iftar_h, iftar_m = map(int, iftar_str.split(':'))
            from datetime import time as _t
            restaurant.ramadan_iftar_time = _t(iftar_h, iftar_m)
        except (ValueError, TypeError):
            restaurant.ramadan_iftar_time = DEFAULT_RAMADAN_IFTAR_TIME
    elif restaurant.ramadan_mode:
        restaurant.ramadan_iftar_time = (
            restaurant.ramadan_iftar_time or DEFAULT_RAMADAN_IFTAR_TIME
        )
    else:
        restaurant.ramadan_iftar_time = None
    restaurant.loyalty_enabled = 'loyalty_enabled' in request.form

    ppu = request.form.get('loyalty_points_per_unit', type=int)
    if ppu and 1 <= ppu <= 100:
        restaurant.loyalty_points_per_unit = ppu

    rdv = request.form.get('loyalty_redemption_value', type=float)
    if rdv and 0.001 <= rdv <= 10:
        restaurant.loyalty_redemption_value = rdv

    # Logo upload
    if 'logo' in request.files:
        f = request.files['logo']
        if f and f.filename:
            if restaurant.logo_url:
                delete_file(restaurant.logo_url)
            restaurant.logo_url = save_uploaded_file(f, 'logos')

    # Cover image upload
    if 'cover' in request.files:
        f = request.files['cover']
        if f and f.filename:
            if restaurant.cover_url:
                delete_file(restaurant.cover_url)
            restaurant.cover_url = save_uploaded_file(f, 'covers')

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


# ──────────────────────────────────────────────
# 9. Analytics
# ──────────────────────────────────────────────

@dashboard_bp.route('/analytics')
@login_required
@restaurant_required
def analytics():
    """Analytics & reporting dashboard."""
    from datetime import timedelta, date as _date

    from app.services.analytics_service import (
        get_daily_stats,
        get_revenue_by_period,
        get_popular_items,
        get_peak_hours,
        get_average_service_time,
        get_waiter_call_stats,
    )

    restaurant = g.restaurant
    period = request.args.get('period', '7d')
    period_map = {'7d': 7, '30d': 30, '90d': 90}
    days = period_map.get(period, 7)

    today = _date.today()
    start = today - timedelta(days=days - 1)

    daily_stats = get_daily_stats(restaurant.id, today)
    revenue_data = get_revenue_by_period(restaurant.id, start, today)
    popular_items = get_popular_items(restaurant.id, period_days=days)
    peak_hours = get_peak_hours(restaurant.id, period_days=days)
    service_time = get_average_service_time(restaurant.id, period_days=days)
    call_stats = get_waiter_call_stats(restaurant.id, period_days=days)

    return render_template(
        'dashboard/analytics/reports.html',
        restaurant=restaurant,
        period=period,
        daily_stats=daily_stats,
        revenue_data=revenue_data,
        popular_items=popular_items,
        peak_hours=peak_hours,
        service_time=service_time,
        call_stats=call_stats,
    )


# ──────────────────────────────────────────────
# 10. Reviews
# ──────────────────────────────────────────────

@dashboard_bp.route('/reviews')
@login_required
@restaurant_required
def reviews():
    """Customer reviews overview."""
    restaurant = g.restaurant
    page = request.args.get('page', 1, type=int)

    query = Review.query.filter_by(restaurant_id=restaurant.id)
    total_reviews = query.count()

    avg_rating = db.session.query(func.avg(Review.rating)).filter(
        Review.restaurant_id == restaurant.id
    ).scalar() or 0
    avg_food = db.session.query(func.avg(Review.food_rating)).filter(
        Review.restaurant_id == restaurant.id,
        Review.food_rating.isnot(None),
    ).scalar() or 0
    avg_service = db.session.query(func.avg(Review.service_rating)).filter(
        Review.restaurant_id == restaurant.id,
        Review.service_rating.isnot(None),
    ).scalar() or 0

    pagination = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template(
        'dashboard/reviews.html',
        restaurant=restaurant,
        reviews=pagination.items,
        pagination=pagination,
        total_reviews=total_reviews,
        avg_rating=round(avg_rating, 1),
        avg_food=round(avg_food, 1),
        avg_service=round(avg_service, 1),
    )


# ──────────────────────────────────────────────
# 11. Notifications API
# ──────────────────────────────────────────────

@dashboard_bp.route('/notifications')
@login_required
@restaurant_required
def notifications_list():
    """Return unread notifications as JSON."""
    restaurant = g.restaurant
    role = None
    if hasattr(current_user, 'role'):
        role = current_user.role
    notifications = get_unread_notifications(restaurant.id, role=role)
    return jsonify(notifications=[
        {
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'body': n.body,
            'created_at': n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ])


@dashboard_bp.route('/notifications/count')
@login_required
@restaurant_required
def notifications_count():
    """Return unread notification count as JSON."""
    restaurant = g.restaurant
    role = None
    if hasattr(current_user, 'role'):
        role = current_user.role
    notifications = get_unread_notifications(restaurant.id, role=role)
    return jsonify(count=len(notifications))


@dashboard_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
@restaurant_required
def notification_read(notification_id):
    """Mark a single notification as read."""
    restaurant = g.restaurant
    success = mark_notification_read(notification_id, restaurant.id)
    return jsonify(success=success)


@dashboard_bp.route('/notifications/read-all', methods=['POST'])
@login_required
@restaurant_required
def notifications_read_all():
    """Mark all notifications as read."""
    restaurant = g.restaurant
    role = None
    if hasattr(current_user, 'role'):
        role = current_user.role
    count = mark_all_read(restaurant.id, role=role)
    return jsonify(success=True, count=count)


# ──────────────────────────────────────────────
# 12. Subscription Management
# ──────────────────────────────────────────────

PLAN_LIMITS = {
    'free':       {'max_tables': 5,   'max_items': 20},
    'pro':        {'max_tables': 25,  'max_items': 100},
    'enterprise': {'max_tables': 999, 'max_items': 999},
}
PLAN_ORDER = ('free', 'pro', 'enterprise')


@dashboard_bp.route('/subscription')
@login_required
@role_required('owner')
@restaurant_required
def subscription():
    """View current subscription and plan options."""
    restaurant = g.restaurant
    sub = restaurant.subscription

    tables_used = Table.query.filter_by(restaurant_id=restaurant.id).count()
    items_used = MenuItem.query.filter(
        MenuItem.restaurant_id == restaurant.id,
        MenuItem.deleted_at.is_(None),
    ).count()

    max_tables = sub.max_tables if sub else 5
    max_items = sub.max_items if sub else 20
    current_plan = sub.plan if sub and sub.plan in PLAN_ORDER else 'free'

    return render_template(
        'dashboard/subscription.html',
        restaurant=restaurant,
        subscription=sub,
        current_plan=current_plan,
        plan_order=PLAN_ORDER,
        tables_used=tables_used,
        items_used=items_used,
        max_tables=max_tables,
        max_items=max_items,
    )


@dashboard_bp.route('/subscription/change', methods=['POST'])
@login_required
@role_required('owner')
@restaurant_required
def subscription_change():
    """Switch the restaurant to a different plan."""
    restaurant = g.restaurant
    plan = request.form.get('plan', '').strip()

    if plan not in PLAN_LIMITS:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('dashboard.subscription'))

    sub = restaurant.subscription
    current_plan = sub.plan if sub and sub.plan in PLAN_ORDER else 'free'
    if sub and sub.plan not in PLAN_ORDER:
        current_app.logger.warning(
            'Unknown current subscription plan for restaurant %s: %s. Falling back to free.',
            restaurant.id,
            sub.plan,
        )

    current_rank = PLAN_ORDER.index(current_plan)
    if plan not in PLAN_ORDER:
        current_app.logger.error(
            'Unknown target subscription plan for restaurant %s: %s',
            restaurant.id,
            plan,
        )
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('dashboard.subscription'))
    target_rank = PLAN_ORDER.index(plan)

    if plan == current_plan:
        flash(f'You are already on the {plan.title()} plan.', 'info')
        return redirect(url_for('dashboard.subscription'))

    if target_rank > current_rank:
        flash(
            'Paid upgrades are not self-serve yet. Contact support to activate a higher plan.',
            'error',
        )
        return redirect(url_for('dashboard.subscription'))

    if not sub:
        sub = Subscription(restaurant_id=restaurant.id)
        db.session.add(sub)

    limits = PLAN_LIMITS[plan]
    now = datetime.now(timezone.utc)
    sub.plan = plan
    sub.max_tables = limits['max_tables']
    sub.max_items = limits['max_items']
    sub.is_active = True
    sub.started_at = now
    if plan == 'free':
        sub.expires_at = None
    elif not sub.expires_at or sub.expires_at <= now:
        sub.expires_at = now + timedelta(days=30)

    db.session.commit()
    flash(f'Plan changed to {plan.title()}.', 'success')
    return redirect(url_for('dashboard.subscription'))
