"""Order lifecycle WebSocket event handlers and emitters."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Module-level reference set by register_order_events
_socketio = None


def register_order_events(socketio):
    """Register connection/join events for orders.

    Args:
        socketio: Flask-SocketIO instance.
    """
    global _socketio
    _socketio = socketio

    @socketio.on('join_restaurant')
    def on_join_restaurant(data):
        """Staff joins the restaurant-wide broadcast room."""
        from flask_socketio import join_room
        restaurant_id = data.get('restaurant_id')
        if restaurant_id:
            join_room(f'restaurant_{restaurant_id}')
            logger.debug('Client joined restaurant_%s', restaurant_id)

    @socketio.on('join_cashier')
    def on_join_cashier(data):
        """Cashier staff joins the cashier-specific room."""
        from flask_socketio import join_room
        restaurant_id = data.get('restaurant_id')
        if restaurant_id:
            join_room(f'cashier_{restaurant_id}')
            join_room(f'restaurant_{restaurant_id}')

    @socketio.on('join_kitchen')
    def on_join_kitchen(data):
        """Kitchen staff joins the kitchen room."""
        from flask_socketio import join_room
        restaurant_id = data.get('restaurant_id')
        if restaurant_id:
            join_room(f'kitchen_{restaurant_id}')
            join_room(f'restaurant_{restaurant_id}')

    @socketio.on('join_waiter')
    def on_join_waiter(data):
        """Waiter joins their personal room + restaurant room."""
        from flask_socketio import join_room
        restaurant_id = data.get('restaurant_id')
        waiter_id = data.get('waiter_id')
        if restaurant_id:
            join_room(f'restaurant_{restaurant_id}')
        if waiter_id:
            join_room(f'waiter_{waiter_id}')

    @socketio.on('join_customer')
    def on_join_customer(data):
        """Customer joins their private session room for order tracking."""
        from flask_socketio import join_room
        session_token = data.get('session_token')
        if session_token:
            join_room(f'customer_{session_token}')

    @socketio.on('disconnect')
    def on_disconnect():
        logger.debug('Client disconnected: %s', socketio)


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------

def notify_new_order(order):
    """Emit new_order event to restaurant + cashier rooms.

    Args:
        order: Committed Order model instance.
    """
    if _socketio is None:
        return
    try:
        items = order.items.all() if hasattr(order.items, 'all') else list(order.items)
        data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'table_id': order.table_id,
            'table_number': order.table.table_number if order.table else None,
            'total_amount': float(order.total_amount),
            'items_count': len(items),
            'items': [
                {
                    'name': oi.menu_item.name_fr if oi.menu_item else '?',
                    'quantity': oi.quantity,
                    'notes': oi.notes or '',
                }
                for oi in items
            ],
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'currency': order.restaurant.currency if hasattr(order, 'restaurant') and order.restaurant else '',
        }
        _socketio.emit('new_order', data, room=f'restaurant_{order.restaurant_id}')
    except Exception:
        logger.exception('notify_new_order failed for order %s', order.id)


def notify_order_status_change(order, new_status):
    """Emit order_status_update to customer session + restaurant room.

    Args:
        order: Order model instance (after status update).
        new_status: The new status string.
    """
    if _socketio is None:
        return
    try:
        data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'status': new_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        # Notify the customer's tracking page
        if order.session:
            _socketio.emit(
                'order_status_update', data,
                room=f'customer_{order.session.session_token}',
            )
        # Notify all staff
        _socketio.emit('order_status_update', data, room=f'restaurant_{order.restaurant_id}')
    except Exception:
        logger.exception('notify_order_status_change failed for order %s', order.id)
