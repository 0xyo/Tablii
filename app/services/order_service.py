"""Order creation and calculation service."""
import json
import logging
from datetime import datetime, timezone

from app import db
from app.models.menu import CustomOption, MenuItem
from app.models.order import Order, OrderItem
from app.utils.helpers import generate_order_number

logger = logging.getLogger(__name__)


def create_order(session_id, items, payment_method, special_notes, restaurant):
    """Create an order with validated items and server-side price calculation.

    Args:
        session_id: Active TableSession ID.
        items: List of dicts with keys: menu_item_id, quantity, selected_options, notes.
        payment_method: Payment method string (e.g. 'cash', 'online').
        special_notes: Optional order-level notes.
        restaurant: Restaurant model instance.

    Returns:
        Order object on success.

    Raises:
        ValueError: If validation fails.
    """
    if not items:
        raise ValueError('Order must contain at least one item.')

    order_items = []
    subtotal = 0.0

    for item_data in items:
        menu_item_id = item_data.get('menu_item_id')
        quantity = item_data.get('quantity', 1)
        selected_options = item_data.get('selected_options', [])
        notes = item_data.get('notes', '')

        # Validate quantity
        if not isinstance(quantity, int) or quantity < 1 or quantity > 20:
            raise ValueError(f'Invalid quantity for item {menu_item_id}.')

        # Validate menu item belongs to restaurant
        menu_item = MenuItem.query.filter_by(
            id=menu_item_id,
            restaurant_id=restaurant.id,
            is_available=True,
        ).first()

        if not menu_item or menu_item.deleted_at is not None:
            raise ValueError(f'Menu item {menu_item_id} not found or unavailable.')

        # Calculate price: base + selected option extras
        unit_price = menu_item.price

        if selected_options:
            for opt_id in selected_options:
                option = CustomOption.query.get(opt_id)
                if option:
                    unit_price += option.extra_price

        total_price = unit_price * quantity
        subtotal += total_price

        order_items.append(OrderItem(
            menu_item_id=menu_item.id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            selected_options=json.dumps(selected_options) if selected_options else None,
            notes=notes or None,
        ))

    # Calculate tax and total
    tax_amount = subtotal * (restaurant.tax_rate / 100)
    total_amount = subtotal + tax_amount

    # Determine initial status
    now = datetime.now(timezone.utc)
    status = 'new'
    accepted_at = None
    if restaurant.auto_accept:
        status = 'accepted'
        accepted_at = now

    order = Order(
        session_id=session_id,
        restaurant_id=restaurant.id,
        order_number=generate_order_number(),
        status=status,
        payment_method=payment_method,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        special_notes=special_notes or None,
        accepted_at=accepted_at,
    )
    db.session.add(order)
    db.session.flush()  # Get order.id

    for oi in order_items:
        oi.order_id = order.id
        db.session.add(oi)

    db.session.commit()

    # Real-time notification
    try:
        from app.events.order_events import notify_new_order
        notify_new_order(order)
    except Exception:
        logger.exception('notify_new_order failed silently')

    return order


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

VALID_TRANSITIONS = {
    'new': ['accepted', 'cancelled'],
    'accepted': ['preparing', 'cancelled'],
    'preparing': ['ready'],
    'ready': ['served'],
    'served': ['completed'],
}

STATUS_TIMESTAMP = {
    'accepted': 'accepted_at',
    'preparing': 'preparing_at',
    'ready': 'ready_at',
    'served': 'served_at',
    'completed': 'completed_at',
}


def update_order_status(
    order_id: int, new_status: str, restaurant_id: int
) -> tuple[bool, str]:
    """Advance an order through the status state machine.

    Args:
        order_id: Primary key of the order.
        new_status: Target status string.
        restaurant_id: Used to enforce multi-tenant isolation.

    Returns:
        ``(True, 'OK')`` on success or ``(False, error_message)`` on failure.
    """
    from app.models.order import Order  # local import avoids circular deps

    order = Order.query.filter_by(
        id=order_id, restaurant_id=restaurant_id
    ).first()

    if not order:
        return (False, 'Order not found.')

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        return (
            False,
            f'Cannot transition from \'{order.status}\' to \'{new_status}\'.',
        )

    now = datetime.now(timezone.utc)
    order.status = new_status
    ts_field = STATUS_TIMESTAMP.get(new_status)
    if ts_field:
        setattr(order, ts_field, now)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Failed to update order %s to %s', order_id, new_status)
        return (False, 'Database error.')

    # Real-time notifications
    try:
        from app.events.order_events import notify_order_status_change
        notify_order_status_change(order, new_status)

        if new_status == 'accepted':
            from app.events.kitchen_events import notify_kitchen_new_order
            notify_kitchen_new_order(order)
        elif new_status == 'ready':
            from app.events.kitchen_events import notify_order_ready
            notify_order_ready(order)
    except Exception:
        logger.exception('Status change notification failed silently')

    return (True, 'OK')


def get_active_orders(restaurant_id: int) -> dict:
    """Return non-terminal orders grouped by status.

    Args:
        restaurant_id: Filter by restaurant.

    Returns:
        Dict mapping each active status to a list of Order objects.
    """
    from app.models.order import Order  # local import avoids circular deps

    terminal = ('completed', 'cancelled')
    orders = (
        Order.query
        .filter(
            Order.restaurant_id == restaurant_id,
            ~Order.status.in_(terminal),
        )
        .order_by(Order.created_at.asc())
        .all()
    )

    grouped: dict[str, list] = {
        'new': [], 'accepted': [], 'preparing': [], 'ready': [], 'served': []
    }
    for order in orders:
        if order.status in grouped:
            grouped[order.status].append(order)

    return grouped
