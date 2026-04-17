# Phase 08 — Real-Time WebSocket System

## Context

**Tablii** — Phase 8 of 12. Implement Flask-SocketIO real-time communication for orders, kitchen, and waiter calls.

---

## Deliverables

```
app/events/
├── __init__.py            # Register all event handlers
├── order_events.py        # Order lifecycle events
├── kitchen_events.py      # Kitchen notifications
└── waiter_events.py       # Waiter call notifications

app/static/js/socket.js    # Client-side socket configuration
```

Update `app/__init__.py` to import events inside `create_app()`.

---

## Architecture — Rooms

| Room Name          | Who Joins                    | Purpose                               |
| ------------------ | ---------------------------- | ------------------------------------- |
| `restaurant_{id}`  | All staff of that restaurant | Broadcast all events                  |
| `kitchen_{id}`     | Kitchen staff                | Kitchen-specific orders               |
| `cashier_{id}`     | Cashier staff                | New orders, status changes            |
| `waiter_{id}`      | Individual waiter            | Calls + ready orders for their tables |
| `customer_{token}` | Single customer session      | Order status updates                  |

---

## `events/__init__.py`

```python
"""Register all WebSocket event handlers."""

def register_events(socketio):
    from app.events.order_events import register_order_events
    from app.events.kitchen_events import register_kitchen_events
    from app.events.waiter_events import register_waiter_events
    register_order_events(socketio)
    register_kitchen_events(socketio)
    register_waiter_events(socketio)
```

In `app/__init__.py`, after `socketio.init_app(app)`:

```python
from app.events import register_events
register_events(socketio)
```

---

## `events/order_events.py`

### Connection Events

```python
def register_order_events(socketio):
    @socketio.on('join_restaurant')
    # data: {restaurant_id}
    # Join room f"restaurant_{data['restaurant_id']}"

    @socketio.on('join_customer')
    # data: {session_token}
    # Join room f"customer_{data['session_token']}"

    @socketio.on('join_kitchen')
    # data: {restaurant_id}
    # Join room f"kitchen_{data['restaurant_id']}"
```

### Emit Functions (called from services/routes)

```python
def notify_new_order(order):
    """Emit to restaurant room + kitchen room when new order is created."""
    data = {
        'order_id': order.id,
        'order_number': order.order_number,
        'table_number': order.table.table_number if order.table else None,
        'total_amount': order.total_amount,
        'items_count': len(order.items.all()),
        'status': order.status,
        'created_at': order.created_at.isoformat(),
    }
    socketio.emit('new_order', data, room=f'restaurant_{order.restaurant_id}')
    socketio.emit('kitchen_new_order', data, room=f'kitchen_{order.restaurant_id}')

def notify_order_status_change(order, new_status):
    """Emit to customer + restaurant rooms when order status changes."""
    data = {
        'order_id': order.id,
        'order_number': order.order_number,
        'status': new_status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    # Notify customer
    if order.session:
        socketio.emit('order_status_update', data, room=f'customer_{order.session.session_token}')
    # Notify all staff
    socketio.emit('order_status_update', data, room=f'restaurant_{order.restaurant_id}')
```

---

## `events/kitchen_events.py`

```python
def notify_kitchen_new_order(order):
    """Send full order details to kitchen when order is accepted."""
    items = [{
        'name': item.menu_item.name_fr,
        'quantity': item.quantity,
        'options': item.selected_options,
        'notes': item.notes,
    } for item in order.items]
    data = {
        'order_id': order.id,
        'order_number': order.order_number,
        'table_number': order.table.table_number if order.table else None,
        'items': items,
        'special_notes': order.special_notes,
        'accepted_at': order.accepted_at.isoformat() if order.accepted_at else None,
    }
    socketio.emit('kitchen_new_order', data, room=f'kitchen_{order.restaurant_id}')

def notify_order_ready(order):
    """Notify when order is ready for serving."""
    socketio.emit('order_ready', {
        'order_id': order.id,
        'order_number': order.order_number,
        'table_number': order.table.table_number if order.table else None,
    }, room=f'restaurant_{order.restaurant_id}')
```

---

## `events/waiter_events.py`

```python
def notify_waiter_call(call):
    """Notify waiters when customer calls."""
    data = {
        'call_id': call.id,
        'table_number': call.table.table_number,
        'call_type': call.call_type,
        'message': call.message,
        'created_at': call.created_at.isoformat(),
    }
    socketio.emit('waiter_call', data, room=f'restaurant_{call.restaurant_id}')
    # Also emit to specific waiter if table has assigned waiter
    if call.table.assigned_waiter_id:
        socketio.emit('waiter_call', data, room=f'waiter_{call.table.assigned_waiter_id}')

def notify_table_occupied(table):
    socketio.emit('table_status_change', {
        'table_id': table.id,
        'table_number': table.table_number,
        'status': table.status,
    }, room=f'restaurant_{table.restaurant_id}')
```

---

## Integration Points

Update these existing files to emit events:

1. **`order_service.create_order()`** → call `notify_new_order(order)` after commit.
2. **`order_service.update_order_status()`** → call `notify_order_status_change(order, new_status)`. If `new_status == 'accepted'` → also call `notify_kitchen_new_order(order)`. If `new_status == 'ready'` → call `notify_order_ready(order)`.
3. **`customer.call_waiter` route** → call `notify_waiter_call(call)` after commit.
4. **`customer.menu` route** (table session creation) → call `notify_table_occupied(table)`.

---

## `static/js/socket.js`

```javascript
const socket = io();

function connectAsStaff(restaurantId) {
  socket.emit("join_restaurant", { restaurant_id: restaurantId });
}
function connectAsKitchen(restaurantId) {
  socket.emit("join_kitchen", { restaurant_id: restaurantId });
}
function connectAsCustomer(sessionToken) {
  socket.emit("join_customer", { session_token: sessionToken });
}

// Sound utilities
const sounds = {
  new_order: new Audio("/static/sounds/new_order.mp3"),
  order_ready: new Audio("/static/sounds/order_ready.mp3"),
  call_waiter: new Audio("/static/sounds/call_waiter.mp3"),
};
function playSound(type) {
  if (sounds[type]) {
    sounds[type].play().catch(() => {});
  }
}
```

---

## Validation

- [ ] New order triggers real-time update on cashier board.
- [ ] Status change reaches customer tracking page instantly.
- [ ] Kitchen gets notified when order is accepted.
- [ ] Waiter gets call notification in real-time.
- [ ] Sounds play on new events.
- [ ] Multiple restaurants' events don't leak between rooms.

## Strict Rules

1. Never emit to a room without the restaurant ID prefix.
2. Always import `socketio` from `app` — never create a new instance.
3. Validate room membership on connection.
4. All emit data must be JSON-serializable.
5. Handle disconnection gracefully.
