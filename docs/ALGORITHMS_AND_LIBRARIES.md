# Algorithms And Libraries

This document explains the main backend algorithms, the libraries used by the project, and why each one is used.

## Backend Algorithm Map

| Area | Algorithm or pattern | Main files |
| --- | --- | --- |
| App startup | Factory initialization | `app/__init__.py` |
| Routing | Blueprint dispatch | `app/routes/` |
| Authentication | Session user loading with prefixed IDs | `app/models/user.py`, `app/__init__.py` |
| Authorization | Decorator-based role checks | `app/utils/decorators.py` |
| Multi-location | Active restaurant resolution | `app/services/subscription_service.py` |
| Subscriptions | Plan-limit lookup and creation blocking | `app/services/subscription_service.py` |
| Ordering | Server-side validation and total calculation | `app/services/order_service.py` |
| Order status | Finite state machine | `app/services/order_service.py` |
| Table sessions | Session token and table release logic | `app/routes/customer.py`, `app/services/order_service.py` |
| Realtime | Room-based event broadcasting | `app/events/` |
| Analytics | Aggregate queries and grouped metrics | `app/services/analytics_service.py` |
| Payments | Provider request/verify flow | `app/services/payment_service.py` |
| Uploads | Validate, rename, and save files | `app/services/upload_service.py` |
| QR codes | URL encoding into PNG QR images | `app/services/qr_service.py` |
| Localization | Field suffix fallback | `app/utils/helpers.py` |
| Loyalty | Earn/redeem point calculation | `app/services/loyalty_service.py` |

## 1. App Factory Algorithm

Purpose: create a configured Flask app.

Algorithm:

```text
1. Choose config: explicit config_name -> FLASK_ENV -> development.
2. Create Flask app.
3. Load config object.
4. Initialize extensions.
5. Register Socket.IO event handlers.
6. Configure Flask-Login user loader.
7. Register all blueprints.
8. Register Jinja helpers.
9. Return app.
```

Why use this?

The factory pattern makes the backend easier to test, configure, and deploy. Tests can create an isolated app, while production can use different database and secret settings.

## 2. Authentication Loading Algorithm

Purpose: support owners/admins and staff in one login system.

Algorithm:

```text
1. Store owner/admin sessions as user_<id>.
2. Store staff sessions as staff_<id>.
3. On each authenticated request, inspect the prefix.
4. Load from User for user_.
5. Load from StaffUser for staff_.
6. Return None for unknown prefixes.
```

Why use this?

`User` and `StaffUser` are separate tables with different responsibilities. Prefixes allow Flask-Login to use one session cookie while still loading the correct model.

## 3. Authorization Algorithm

Purpose: protect route access.

Algorithm:

```text
1. Check the current user is authenticated.
2. If User is super_admin, allow role-protected routes.
3. If User role matches the allowed roles, allow.
4. If StaffUser role matches the allowed roles, allow.
5. Otherwise abort with 403.
```

Why use this?

Role checks are security rules. Keeping them in decorators makes route permissions visible and prevents copying fragile checks into every route.

## 4. Active Restaurant Resolution Algorithm

Purpose: choose which location an owner is currently managing.

Algorithm:

```text
1. Load all active restaurants owned by the manager.
2. Read session['active_restaurant_id'].
3. If the session ID belongs to one of the active restaurants, use it.
4. If not, fall back to the first active owned restaurant.
5. Store that fallback ID back into the session.
6. If the owner has no active locations, clear the session value.
```

Why use this?

Managers can own multiple locations. A central resolver prevents stale sessions and keeps every dashboard page scoped to one active restaurant.

## 5. Subscription Limit Algorithm

Purpose: enforce free/pro/enterprise limits.

Algorithm:

```text
1. Normalize unknown plan names to free.
2. Look up limits from PLAN_LIMITS.
3. For location creation, compare active location count with max_locations.
4. For table creation, compare active restaurant table count with max_tables.
5. For menu item creation, compare active restaurant item count with max_items.
6. Block only new creation; do not delete existing over-limit data.
```

Why use this?

Subscription limits are business rules. Central plan defaults keep the app consistent, and blocking only creation avoids destructive behavior after downgrades.

## 6. Order Creation Algorithm

Purpose: create a trusted order from customer or cashier input.

Algorithm:

```text
1. Reject empty carts.
2. Check restaurant subscription expiry.
3. For each requested item:
   - Validate quantity is between 1 and 20.
   - Load the menu item by id and restaurant_id.
   - Reject unavailable or deleted items.
   - Start with the menu item base price.
   - Add selected customization option prices.
   - Enforce max selections per customization group.
   - Calculate line total.
4. Calculate subtotal.
5. Calculate tax and service charge.
6. Calculate total amount.
7. Set initial status to new or accepted depending on auto_accept.
8. Save Order and OrderItem rows.
9. Emit realtime notifications.
10. Create in-app notification.
11. Award loyalty points when enabled.
```

Why use this?

The frontend cart cannot be trusted for price, ownership, or availability. The backend recalculates everything so customers cannot change prices or order items from another restaurant.

## 7. Order Status State Machine

Purpose: keep order progress valid.

Algorithm:

```text
new       -> accepted, cancelled
accepted  -> preparing, cancelled
preparing -> ready
ready     -> served
served    -> completed
```

Extra rule:

```text
completed requires payment_status == paid
```

Why use this?

Restaurants need predictable order flow. A finite state machine prevents impossible jumps like `new -> served` and protects reporting data.

## 8. Table Session Algorithm

Purpose: connect a physical table with customer activity.

Algorithm:

```text
1. Customer opens QR menu URL.
2. Find active TableSession for that table.
3. If none exists, create a new TableSession with a random token.
4. Mark table as occupied.
5. Store session_token in the browser session.
6. Group all orders from that sitting under the TableSession.
7. When all non-cancelled orders are paid/completed, close the session and mark table free.
```

Why use this?

Customers do not log in. A table session gives the backend a stable way to group orders, waiter calls, loyalty, and payment state for one table visit.

## 9. Realtime Room Algorithm

Purpose: send events only to the right screens.

Algorithm:

```text
1. Client connects with Socket.IO.
2. Client emits a join event for its role.
3. Server adds the socket to role/location rooms:
   - restaurant_<restaurant_id>
   - cashier_<restaurant_id>
   - kitchen_<restaurant_id>
   - waiter_<staff_id>
   - customer_<session_token>
4. Backend emits events to the smallest useful room.
```

Why use this?

Room-based broadcasting avoids sending every event to every client. It protects restaurant isolation and keeps frontend screens simpler.

## 10. Analytics Algorithms

Purpose: calculate dashboard metrics efficiently.

### Daily Stats

Algorithm:

```text
1. Build UTC day start and day end.
2. Count orders in that range.
3. Sum paid revenue.
4. Count distinct tables used.
5. Group orders by status.
6. Group orders by payment method.
```

Why use this?

Daily snapshots answer owner questions quickly: how many orders, how much paid revenue, which statuses, and how tables were used.

### Revenue By Period

Algorithm:

```text
1. Build start/end datetimes.
2. Group orders by date.
3. Sum total amount per date.
4. Count orders per date.
5. Return ordered rows for charting.
```

Why use this?

Grouping in SQL is faster than loading all orders into Python and calculating totals manually.

### Popular Items

Algorithm:

```text
1. Join MenuItem -> OrderItem -> Order.
2. Filter by restaurant and period.
3. Group by menu item.
4. Sum quantity and revenue.
5. Sort by quantity sold.
6. Limit to top 10.
```

Why use this?

Owners need to know what sells. The algorithm uses database aggregation so it stays efficient as order volume grows.

### Peak Hours

Algorithm:

```text
1. Extract hour from order created_at.
2. Count orders per hour.
3. Fill missing hours with zero.
4. Return 24 rows.
```

Why use this?

Charts are easier to render when every hour exists, including quiet hours with zero orders.

### Average Service Time

Algorithm:

```text
1. Load recent orders.
2. For each order, calculate:
   - accepted_at - created_at
   - ready_at - accepted_at
   - served_at - created_at
3. Average each list.
4. Return null when no valid data exists.
```

Why use this?

Service timing helps managers identify slow acceptance, slow kitchen preparation, or slow serving.

## 11. Payment Algorithm

Purpose: create and verify Flouci payments.

Algorithm:

```text
1. Load order.
2. Reject missing order or non-pending payment.
3. Read Flouci credentials from server config.
4. Convert TND amount to millimes: int(amount * 1000).
5. Send payment creation request to Flouci.
6. Save PaymentTransaction with pending status.
7. Redirect customer to payment URL.
8. On callback, verify payment_id with Flouci.
9. If SUCCESS, mark transaction completed and order paid.
10. If order was already served, mark it completed.
11. Try to release the table session.
```

Why use this?

Payment credentials must remain server-side. Verification prevents fake success redirects from marking orders paid.

## 12. Upload Algorithm

Purpose: safely save uploaded images.

Algorithm:

```text
1. Reject missing file.
2. Extract extension.
3. Check extension against allowed list.
4. Measure file size.
5. Reject files over MAX_CONTENT_LENGTH.
6. Sanitize original filename with secure_filename.
7. Prefix filename with a UUID.
8. Save into configured upload subfolder.
9. Return public static URL.
```

Why use this?

Uploads are risky. Extension checks, size checks, safe filenames, and UUID prefixes reduce collisions and unsafe paths.

## 13. QR Code Algorithm

Purpose: create scannable table URLs.

Algorithm:

```text
1. Build public table URL from host, restaurant slug, and table id.
2. Create QRCode object.
3. Add URL data.
4. Fit QR code size automatically.
5. Render black/white PNG.
6. Save to static QR upload folder.
7. Return the public image URL.
```

Why use this?

QR codes let customers open the correct restaurant and table without installing an app or typing a URL.

## 14. Localization Algorithm

Purpose: return the correct translated field.

Algorithm:

```text
1. Resolve language from ?lang query parameter.
2. If missing, use browser session language.
3. If missing, use restaurant default language.
4. If missing or invalid, use fr.
5. Read field_<lang>.
6. If empty, fall back to field_fr.
```

Why use this?

Menus need French, Arabic, and English support. The fallback keeps pages usable even when a translation is incomplete.

## 15. Slug And Token Algorithms

### Slug Generation

Algorithm:

```text
1. Lowercase the name.
2. Replace non-alphanumeric characters with hyphens.
3. Collapse repeated hyphens.
4. Trim leading/trailing hyphens.
5. Append a short random hex suffix.
```

Why use this?

Slugs must be URL-safe and mostly human-readable. The random suffix reduces collisions between restaurants with similar names.

### Session Token Generation

Algorithm:

```text
1. Generate cryptographically secure random bytes.
2. Encode them into a URL-safe token.
3. Store token in browser session and TableSession.
```

Why use this?

Customer table sessions should not be guessable. `secrets` is designed for security-sensitive random values.

## 16. Loyalty Algorithm

Purpose: calculate points and discounts.

Earn algorithm:

```text
points = floor(order_total) * restaurant.loyalty_points_per_unit
```

Redeem algorithm:

```text
discount = points_to_redeem * restaurant.loyalty_redemption_value
```

Why use this?

The formula is simple for managers and customers to understand. It also keeps loyalty scoped per restaurant.

## 17. Validation Algorithms

| Validator | Logic | Why use this? |
| --- | --- | --- |
| Email | Use `email-validator`, deliverability disabled | Correct format validation without slow DNS checks |
| Phone | Regex for optional `+` and 8-15 digits | Simple international-friendly phone validation |
| Price | Parse float, require non-negative and max 2 decimals | Prevent invalid menu prices |
| Sanitization | Strip, collapse whitespace, escape HTML | Reduce messy input and protect HTML output |

## Backend Libraries

| Library | Used for | Why use this? |
| --- | --- | --- |
| `Flask` | Web app, routing, request/response handling | Lightweight and flexible for a server-rendered dashboard plus JSON endpoints |
| `Flask-SQLAlchemy` | Database ORM integration | Gives model/query patterns that fit Flask and reduce raw SQL |
| `SQLAlchemy` | ORM, relationships, aggregate queries | Handles database abstraction, joins, filters, and transactions |
| `Flask-Migrate` | Migration commands | Integrates Alembic with Flask CLI |
| `alembic` | Database schema migrations | Tracks schema changes safely across environments |
| `Flask-Login` | Session login management | Handles current user, login/logout, and protected views |
| `Flask-WTF` | Forms and CSRF protection | Protects server-rendered form submissions |
| `Flask-SocketIO` | Realtime WebSocket-style events | Powers live order, kitchen, waiter, and customer tracking updates |
| `eventlet` | Async networking support for Socket.IO deployments | Common production companion for Socket.IO servers |
| `Werkzeug` | Password hashing, secure filenames, WSGI utilities | Flask's underlying toolkit; used directly for security helpers |
| `python-dotenv` | Local environment variable loading | Makes local setup easier with `.env` files |
| `Pillow` | Image support through QR/upload dependencies | Enables image manipulation and saving in Python |
| `qrcode` | QR code generation | Converts table URLs into scannable PNG images |
| `requests` | HTTP requests to Flouci | Simple, reliable API calls to the payment provider |
| `email-validator` | Email format validation | More accurate than a homemade email regex |
| `MarkupSafe` | HTML escaping | Prevents unsafe user input from rendering as HTML |
| `psycopg` / `psycopg2-binary` | PostgreSQL drivers | Allow production PostgreSQL connections |
| `gunicorn` | Production WSGI server | Standard Python web process manager for deployment |

## Frontend Build Library

| Library | Used for | Why use this? |
| --- | --- | --- |
| `tailwindcss` | Compiling utility CSS | Keeps dashboard/customer styling consistent without writing a large custom CSS framework |

## Standard Library Modules Used Heavily

| Module | Used for | Why use this? |
| --- | --- | --- |
| `datetime` | Timestamps, date ranges, service-time calculations | Built-in time handling |
| `timezone` / `zoneinfo` | UTC and restaurant-aware time checks | Reduces ambiguity around business hours and Ramadan service windows |
| `secrets` | Session tokens and slug suffixes | Secure random generation |
| `random` / `string` | Short order number codes | Simple human-friendly order references |
| `re` | Slugs, phone validation, whitespace cleanup | Fast text pattern handling |
| `uuid` | Upload filename uniqueness | Avoids filename collisions |
| `os` | Directory creation and file paths | Cross-platform filesystem operations |
| `json` | Selected options and payment raw responses | Store structured data when no separate table is needed |
| `logging` | Operational errors and warnings | Keeps failures visible without exposing details to users |

## Why These Choices Fit Tablii

Tablii is a multi-tenant restaurant platform with server-rendered dashboards, customer QR menus, realtime staff workflows, and payments. The chosen backend design favors:

- Clear tenant scoping through `restaurant_id`.
- Central business rules in services.
- Simple relational models for menus, tables, orders, staff, and subscriptions.
- Realtime updates for restaurant operations.
- Server-side validation for pricing and payment safety.
- Practical libraries that are common in Flask production apps.

The result is a backend that is easy to explain, test, and extend without adding unnecessary complexity.
