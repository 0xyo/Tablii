# Phase 09 — Payment Integration & Analytics

## Context

**Tablii** — Phase 9 of 12. Implement payment gateway integration (Flouci/Konnect) and analytics service for restaurant reporting.

---

## Deliverables

```
app/services/
├── payment_service.py       # Payment gateway integration
├── analytics_service.py     # Reporting & statistics
└── notification_service.py  # In-app notification management

app/routes/
└── dashboard.py             # Add analytics route (extend existing)

app/templates/dashboard/
└── analytics/
    └── reports.html         # Analytics dashboard page

app/static/js/
└── analytics_charts.js      # Chart rendering (Chart.js)
```

---

## `services/payment_service.py`

### Flouci Payment Gateway

**Environment variables required:** `FLOUCI_APP_TOKEN`, `FLOUCI_APP_SECRET`.

#### `initiate_flouci_payment(order_id, amount, success_url, fail_url) → dict | None`

1. Query order, verify it exists and `payment_status == 'pending'`.
2. POST to `https://developers.flouci.com/api/generate_payment`:
   ```python
   payload = {
       'app_token': app_token,
       'app_secret': app_secret,
       'amount': int(amount * 1000),  # Flouci uses millimes
       'accept_card': 'true',
       'session_timeout_secs': 1200,
       'success_link': success_url,
       'fail_link': fail_url,
       'developer_tracking_id': str(order_id),
   }
   ```
3. If successful → create `PaymentTransaction(order_id, gateway='flouci', amount, gateway_transaction_id=response['payment_id'])`.
4. Return `{'payment_url': response['link'], 'payment_id': response['payment_id']}`.
5. On error → log, return `None`.

#### `verify_flouci_payment(payment_id) → bool`

1. GET `https://developers.flouci.com/api/verify_payment/{payment_id}`.
2. If `response['result']['status'] == 'SUCCESS'`:
   - Update `PaymentTransaction.status = 'completed'`.
   - Update `Order.payment_status = 'paid'`.
   - Store `raw_response`.
   - Return `True`.
3. Else → return `False`.

#### Payment callback route (add to `routes/customer.py`):

```python
@customer_bp.route('/payment/callback')
def payment_callback():
    payment_id = request.args.get('payment_id')
    if verify_flouci_payment(payment_id):
        flash('Payment successful!', 'success')
    else:
        flash('Payment failed.', 'error')
    # Redirect to order tracking
```

---

## `services/analytics_service.py`

All functions take `restaurant_id` as first param and filter exclusively by it.

### `get_daily_stats(restaurant_id, date) → dict`

```python
return {
    'total_orders': <count>,
    'total_revenue': <sum of paid orders>,
    'average_order_value': <revenue / orders>,
    'tables_used': <distinct table_ids>,
    'orders_by_status': {'completed': N, 'cancelled': N, ...},
    'payment_methods': {'cash': N, 'online': N},
}
```

### `get_revenue_by_period(restaurant_id, start_date, end_date) → list[dict]`

Return daily totals: `[{'date': '2024-01-15', 'revenue': 450.500, 'orders': 23}, ...]`.

### `get_popular_items(restaurant_id, period_days=30) → list[dict]`

Return top 10 items: `[{'name': 'Pizza', 'quantity_sold': 145, 'revenue': 1450.0}, ...]`.

### `get_peak_hours(restaurant_id, period_days=30) → list[dict]`

Return orders per hour: `[{'hour': 12, 'count': 45}, {'hour': 13, 'count': 52}, ...]`.

### `get_average_service_time(restaurant_id, period_days=7) → dict`

```python
return {
    'avg_accept_time': <seconds from new to accepted>,
    'avg_prep_time': <seconds from accepted to ready>,
    'avg_total_time': <seconds from new to served>,
}
```

---

## `services/notification_service.py`

### `create_notification(restaurant_id, type, title, body, target_role=None, target_user_id=None)`

Create a `Notification` record. Return the notification.

### `get_unread_notifications(restaurant_id, role=None, user_id=None) → list`

Query unread notifications filtered by restaurant, optionally by role or user.

### `mark_notification_read(notification_id, restaurant_id) → bool`

Set `is_read = True`. Return success.

### `mark_all_read(restaurant_id, role=None) → int`

Mark all matching unread notifications as read. Return count.

---

## Analytics Dashboard Route

### `GET /dashboard/analytics`

Accept query params: `period` (default `'7d'`), options: `'7d'`, `'30d'`, `'90d'`.

1. Calculate `start_date` from period.
2. Call analytics service functions.
3. Render `dashboard/analytics/reports.html` with data.

**Template (`reports.html`):**

- Period selector tabs (7d / 30d / 90d).
- **Revenue chart** (line chart, daily revenue over period).
- **Stat cards**: Total Revenue, Total Orders, Avg Order Value, Avg Service Time.
- **Top Items** (bar chart, top 10).
- **Peak Hours** (heatmap or bar chart).
- **Order status distribution** (pie/doughnut chart).

---

## `static/js/analytics_charts.js`

Use **Chart.js** (load from CDN in the template).

```javascript
function renderRevenueChart(canvasId, data) { ... }
// Line chart with dates on X-axis, revenue on Y-axis.
// Orange gradient fill.

function renderTopItemsChart(canvasId, data) { ... }
// Horizontal bar chart. Item names + quantity sold.

function renderPeakHoursChart(canvasId, data) { ... }
// Vertical bar chart. Hours on X-axis, order count on Y-axis.

function renderOrderStatusChart(canvasId, data) { ... }
// Doughnut chart with status colors.
```

---

## Validation

- [ ] Flouci payment initiation returns a redirect URL.
- [ ] Payment verification updates order payment status.
- [ ] Analytics show correct data for selected period.
- [ ] Charts render with real data.
- [ ] All analytics queries filter by `restaurant_id`.

## Strict Rules

1. Never expose payment secrets in client-side code or logs.
2. Always verify payments server-side — never trust client callbacks alone.
3. Analytics queries must be optimized (use `func.sum`, `func.count`, `func.date`).
4. All monetary amounts: store as float, display with 3 decimal places (TND).
5. Rate-limit payment initiation (max 1 per order per minute).
