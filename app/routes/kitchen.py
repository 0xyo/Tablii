"""Kitchen blueprint — kitchen display screen."""
from flask import Blueprint, g, jsonify, render_template
from flask_login import login_required

from app.services.order_service import get_active_orders, update_order_status
from app.utils.decorators import restaurant_required, role_required

kitchen_bp = Blueprint('kitchen', __name__, url_prefix='/kitchen')


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
