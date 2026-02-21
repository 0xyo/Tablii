"""Register all WebSocket event handlers."""


def register_events(socketio):
    """Import and register all event handler modules.

    Args:
        socketio: The Flask-SocketIO instance from ``app``.
    """
    from app.events.order_events import register_order_events
    from app.events.kitchen_events import register_kitchen_events
    from app.events.waiter_events import register_waiter_events

    register_order_events(socketio)
    register_kitchen_events(socketio)
    register_waiter_events(socketio)
