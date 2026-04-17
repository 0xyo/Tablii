# Phase 07 — Order Workflow & Staff Interfaces

## Context

**Tablii** — Phase 7 of 12. Build cashier, kitchen, and waiter interfaces + order status workflow.

---

## Deliverables

```
app/routes/cashier.py, kitchen.py, waiter.py
app/services/order_service.py (extend)
app/templates/cashier/base_cashier.html, orders.html, manual_order.html
app/templates/kitchen/display.html
app/templates/waiter/tables.html
app/templates/components/order_card.html
app/static/js/cashier_board.js, kitchen_display.js
```

Register all three blueprints in `routes/__init__.py`.

---

## Order Status State Machine

```
[new] → [accepted] → [preparing] → [ready] → [served] → [completed]
  ↓         ↓
[cancelled]  [cancelled]
```

Only forward transitions allowed. Each sets its timestamp (`accepted_at`, etc.).

---

## `order_service.py` — Add Functions

### `update_order_status(order_id, new_status, restaurant_id) → (bool, str)`

1. Query by `id` AND `restaurant_id`. 2. Validate via transition map:

```python
VALID_TRANSITIONS = {
    'new': ['accepted', 'cancelled'],
    'accepted': ['preparing', 'cancelled'],
    'preparing': ['ready'],
    'ready': ['served'],
    'served': ['completed'],
}
```

3. Update status + timestamp. Commit. Return `(True, "OK")` or `(False, "Invalid transition")`.

### `get_active_orders(restaurant_id) → dict`

Query orders NOT in `[completed, cancelled]`, group by status into dict.

---

## Cashier Blueprint (`/cashier`)

Require `@role_required('cashier', 'owner')`.

### `GET /cashier/orders` — Kanban Board

Render 4 columns: New, Accepted, Preparing, Ready. Each order as a card: order number, table, item count, total, timer, action button. Audio alert on new orders.

### `POST /cashier/orders/<id>/status`

Accept JSON `{new_status}`. Call `update_order_status()`. Return JSON.

### `GET /cashier/manual-order` & `POST /cashier/manual-order`

Form to create orders manually: select table, select items, choose payment. Creates TableSession if needed.

---

## Kitchen Blueprint (`/kitchen`)

Require `@role_required('kitchen', 'owner')`.

### `GET /kitchen` — Kitchen Display

Show `accepted` and `preparing` orders. Large text for visibility. Timer with color-coded urgency (>10min yellow, >20min red). Full item details with options and notes.

### `POST /kitchen/orders/<id>/preparing` and `POST /kitchen/orders/<id>/ready`

Update status. Return JSON.

---

## Waiter Blueprint (`/waiter`)

Require `@role_required('waiter', 'owner')`.

### `GET /waiter/tables`

Show tables assigned to current waiter. Card per table: number, status (free/occupied/ready), call badges.

### `GET /waiter/calls`

Return pending `WaiterCall` records as JSON.

### `POST /waiter/calls/<id>/resolve`

Set `status='resolved'`, `resolved_at`, `resolved_by`. Return JSON.

### `POST /waiter/orders/<id>/served`

Call `update_order_status(id, 'served')`. Return JSON.

---

## JavaScript

### `cashier_board.js`

- `addOrderToBoard(data)` — create card DOM, append to column.
- `moveOrderCard(id, status)` — animate card to new column.
- `changeOrderStatus(id, status)` — POST via fetch, move card on success.
- `playNewOrderSound()` — play `new_order.mp3`.

### `kitchen_display.js`

- `addToKitchenBoard(data)` — create kitchen card with item details.
- `startTimer(id, startTime)` — update every second, color by urgency.
- `markAsPreparing(id)` / `markAsReady(id)` — POST, remove card on ready.

---

## Strict Rules

1. State machine transitions are enforced — no skipping.
2. All queries filter by `restaurant_id`.
3. Kitchen display: large text, tablet-optimized.
4. All status endpoints return JSON.
5. Audio only on new events, not page reload.
6. PEP 8 for Python, async/await for JS fetch calls.
