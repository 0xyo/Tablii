"""Waiter call and table status WebSocket emitters."""
import logging

logger = logging.getLogger(__name__)

_socketio = None


def register_waiter_events(socketio):
    """Store socketio reference.

    Args:
        socketio: Flask-SocketIO instance.
    """
    global _socketio
    _socketio = socketio


def notify_waiter_call(call):
    """Broadcast a waiter call to the restaurant room and the assigned waiter.

    Args:
        call: WaiterCall model instance with ``table`` relationship loaded.
    """
    if _socketio is None:
        return
    try:
        data = {
            'call_id': call.id,
            'table_id': call.table_id,
            'table_number': call.table.table_number if call.table else None,
            'call_type': call.call_type,
            'message': call.message or '',
            'created_at': call.created_at.isoformat(),
        }
        # Broadcast to all staff in the restaurant
        _socketio.emit('waiter_call', data, room=f'restaurant_{call.restaurant_id}')
        # Also notify the specific assigned waiter directly
        if call.table and call.table.assigned_waiter_id:
            _socketio.emit('waiter_call', data, room=f'waiter_{call.table.assigned_waiter_id}')
    except Exception:
        logger.exception('notify_waiter_call failed for call %s', call.id)


def notify_table_occupied(table):
    """Broadcast a table occupied event to all restaurant staff."""
    notify_table_status_change(table)


def notify_table_status_change(table):
    """Broadcast any table status change (occupied, free, etc.) to all staff.

    Args:
        table: Table model instance with updated status.
    """
    if _socketio is None:
        return
    try:
        _socketio.emit(
            'table_status_change',
            {
                'table_id': table.id,
                'table_number': table.table_number,
                'status': table.status,
            },
            room=f'restaurant_{table.restaurant_id}',
        )
    except Exception:
        logger.exception('notify_table_status_change failed for table %s', table.id)
