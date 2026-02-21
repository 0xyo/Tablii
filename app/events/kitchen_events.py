"""Kitchen-specific WebSocket emitters."""
import logging

logger = logging.getLogger(__name__)

_socketio = None


def register_kitchen_events(socketio):
    """Store socketio reference (no additional event handlers needed here).

    Args:
        socketio: Flask-SocketIO instance.
    """
    global _socketio
    _socketio = socketio


def notify_kitchen_new_order(order):
    """Send full order details to the kitchen room when an order is accepted.

    Args:
        order: Order model instance (status == 'accepted').
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
            'items': [
                {
                    'name': oi.menu_item.name_fr if oi.menu_item else '?',
                    'quantity': oi.quantity,
                    'options': oi.selected_options or '',
                    'notes': oi.notes or '',
                }
                for oi in items
            ],
            'special_notes': order.special_notes or '',
            'accepted_at': order.accepted_at.isoformat() if order.accepted_at else None,
            'created_at': order.created_at.isoformat(),
        }
        _socketio.emit('kitchen_new_order', data, room=f'kitchen_{order.restaurant_id}')
    except Exception:
        logger.exception('notify_kitchen_new_order failed for order %s', order.id)


def notify_order_ready(order):
    """Notify all staff when an order is ready for serving.

    Args:
        order: Order model instance (status == 'ready').
    """
    if _socketio is None:
        return
    try:
        _socketio.emit(
            'order_ready',
            {
                'order_id': order.id,
                'order_number': order.order_number,
                'table_id': order.table_id,
                'table_number': order.table.table_number if order.table else None,
            },
            room=f'restaurant_{order.restaurant_id}',
        )
    except Exception:
        logger.exception('notify_order_ready failed for order %s', order.id)
