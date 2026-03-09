"""JSON API blueprint — CSRF-exempt endpoints for external/mobile access."""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.menu import Category, CustomOption, Customization, MenuItem
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.services import upload_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# GET /api/restaurant/<slug>/menu
# ---------------------------------------------------------------------------

@api_bp.route('/restaurant/<slug>/menu', methods=['GET'])
def restaurant_menu(slug):
    """Return the full menu for a restaurant as JSON.

    Returns:
        JSON object with restaurant info, categories, items and customizations.
        404 if the restaurant is not found or inactive.
    """
    restaurant = Restaurant.query.filter_by(slug=slug, is_active=True).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    categories_data = []
    categories = (
        Category.query
        .filter_by(restaurant_id=restaurant.id, is_active=True)
        .order_by(Category.sort_order.asc())
        .all()
    )

    for cat in categories:
        items_data = []
        items = (
            MenuItem.query
            .filter_by(
                category_id=cat.id,
                restaurant_id=restaurant.id,
                is_available=True,
            )
            .filter(MenuItem.deleted_at.is_(None))
            .order_by(MenuItem.sort_order.asc())
            .all()
        )

        for item in items:
            customizations_data = []
            customizations = (
                Customization.query
                .filter_by(menu_item_id=item.id)
                .all()
            )

            for cust in customizations:
                options_data = [
                    {
                        'id': opt.id,
                        'name': opt.name_fr,
                        'extra_price': opt.extra_price,
                        'is_default': opt.is_default,
                    }
                    for opt in cust.options.all()
                ]
                customizations_data.append({
                    'id': cust.id,
                    'group_name': cust.group_name_fr,
                    'type': cust.selection_type,
                    'required': cust.is_required,
                    'options': options_data,
                })

            items_data.append({
                'id': item.id,
                'name': item.name_fr,
                'price': item.price,
                'image_url': item.image_url,
                'is_available': item.is_available,
                'is_popular': item.is_popular,
                'prep_time': item.prep_time,
                'customizations': customizations_data,
            })

        categories_data.append({
            'id': cat.id,
            'name': cat.name_fr,
            'icon': cat.icon,
            'items': items_data,
        })

    return jsonify({
        'restaurant': {
            'name': restaurant.name,
            'slug': restaurant.slug,
            'currency': restaurant.currency,
            'description': restaurant.description,
        },
        'categories': categories_data,
    })


# ---------------------------------------------------------------------------
# GET /api/menu-item/<int:id>
# ---------------------------------------------------------------------------

@api_bp.route('/menu-item/<int:item_id>', methods=['GET'])
def menu_item_detail(item_id):
    """Return a single menu item with its customizations.

    Query param:
        restaurant_id (int, optional): Scope the lookup to a specific restaurant.

    Returns:
        JSON representation of the item or 404.
    """
    query = MenuItem.query.filter_by(id=item_id).filter(MenuItem.deleted_at.is_(None))

    restaurant_id = request.args.get('restaurant_id', type=int)
    if restaurant_id is not None:
        query = query.filter_by(restaurant_id=restaurant_id)

    item = query.first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    customizations_data = []
    for cust in item.customizations.all():
        options_data = [
            {
                'id': opt.id,
                'name': opt.name_fr,
                'extra_price': opt.extra_price,
                'is_default': opt.is_default,
            }
            for opt in cust.options.all()
        ]
        customizations_data.append({
            'id': cust.id,
            'group_name': cust.group_name_fr,
            'type': cust.selection_type,
            'required': cust.is_required,
            'options': options_data,
        })

    return jsonify({
        'id': item.id,
        'name': item.name_fr,
        'price': item.price,
        'description': item.description_fr,
        'image_url': item.image_url,
        'is_available': item.is_available,
        'is_popular': item.is_popular,
        'restaurant_id': item.restaurant_id,
        'customizations': customizations_data,
    })


# ---------------------------------------------------------------------------
# GET /api/order/<int:id>/status
# ---------------------------------------------------------------------------

@api_bp.route('/order/<int:order_id>/status', methods=['GET'])
def order_status(order_id):
    """Return the status and timestamps of an order.

    Returns:
        JSON with order_id, status, and all relevant timestamps.
        404 if the order does not exist.
    """
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    def _fmt(dt):
        return dt.isoformat() if dt else None

    return jsonify({
        'order_id': order.id,
        'order_number': order.order_number,
        'status': order.status,
        'payment_status': order.payment_status,
        'timestamps': {
            'created_at': _fmt(order.created_at),
            'accepted_at': _fmt(order.accepted_at),
            'preparing_at': _fmt(order.preparing_at),
            'ready_at': _fmt(order.ready_at),
            'served_at': _fmt(order.served_at),
            'completed_at': _fmt(order.completed_at),
        },
    })


# ---------------------------------------------------------------------------
# POST /api/upload-image
# ---------------------------------------------------------------------------

@api_bp.route('/upload-image', methods=['POST'])
@login_required
def upload_image():
    """Upload an image file and return its public URL.

    Requires authentication. Accepts multipart/form-data with a 'file' field.

    Returns:
        JSON with ``url`` key on success, or ``error`` on failure.
    """
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    url = upload_service.save_uploaded_file(file, subfolder='api')
    if url is None:
        return jsonify({'error': 'Invalid or unsupported file'}), 400

    return jsonify({'url': url}), 201
