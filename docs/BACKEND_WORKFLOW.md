# Backend Workflow And Logic

This document explains the backend as a sequence of workflows. Each step includes the logic and a "Why use this?" note so the reason behind the architecture stays clear.

## 1. Application Startup

```text
python run.py
  -> create_app()
  -> load config
  -> initialize extensions
  -> register Socket.IO events
  -> register login loader
  -> register blueprints
  -> register Jinja helpers
```

### Step 1: Create the Flask app

Logic:

```python
app = Flask(__name__)
```

Why use this?

Flask needs one application object to hold configuration, routes, extensions, sessions, and request handling. Creating it inside `create_app()` keeps the app testable and configurable.

### Step 2: Load configuration

Logic:

```python
app.config.from_object(config_by_name[config_name])
```

Why use this?

Development, testing, and production need different settings. A config layer prevents hardcoding database URLs, secrets, upload limits, and Socket.IO settings inside route files.

### Step 3: Initialize shared extensions

Logic:

```python
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
socketio.init_app(app, ...)
csrf.init_app(app)
```

Why use this?

Extensions are declared once in `app/__init__.py` and imported everywhere else. This avoids circular setup code and lets models, services, and routes share the same database, login, Socket.IO, and CSRF objects.

### Step 4: Register realtime events

Logic:

```python
register_events(socketio)
```

Why use this?

Orders, kitchen updates, waiter calls, and customer tracking need live updates. Registering events during startup ensures every Socket.IO room and emitter uses the same server instance.

### Step 5: Configure login loading

Logic:

```text
user_1  -> User(id=1)
staff_4 -> StaffUser(id=4)
```

Why use this?

Owners/admins and staff use different database tables but share Flask-Login. Prefixing IDs lets one session system safely load both account types.

### Step 6: Register blueprints

Logic:

```text
landing    -> /
auth       -> /auth
onboarding -> /onboarding
customer   -> /r/<slug>/table/<id>
dashboard  -> /dashboard
cashier    -> /cashier
kitchen    -> /kitchen
waiter     -> /waiter
api        -> /api
admin      -> /admin
```

Why use this?

Each user area has different permissions and workflows. Blueprints keep owner, customer, staff, API, and admin code separated instead of putting every route in one large file.

## 2. Request Routing Workflow

```text
Browser/API request
  -> Flask route match
  -> login/role decorators
  -> active restaurant resolution
  -> route handler
  -> service layer
  -> database
  -> template/JSON/redirect response
```

### Step 1: Match the route

Logic:

Flask finds the route based on URL and HTTP method.

Why use this?

Route matching keeps each feature explicit. For example, `POST /dashboard/tables/add` is clearly different from `GET /dashboard/tables`.

### Step 2: Run decorators

Logic:

```python
@login_required
@role_required('owner')
@restaurant_required
```

Why use this?

Access control should run before business logic. Decorators make security rules visible at the top of the route and reduce repeated permission checks inside handlers.

### Step 3: Resolve active restaurant

Logic:

Owners use `session['active_restaurant_id']`. Staff use their assigned `restaurant_id`.

Why use this?

The app is multi-location. Owners can switch locations, but staff must stay locked to one restaurant. Central resolution prevents accidental cross-location data leaks.

### Step 4: Delegate business logic to services

Logic:

Routes call services such as `create_order()`, `update_order_status()`, or `can_create_location()`.

Why use this?

Routes should coordinate HTTP input/output. Services hold reusable business rules and are easier to test without rendering templates or simulating browsers.

## 3. Owner Multi-Location Workflow

```text
Owner logs in
  -> restaurant_required
  -> resolve_active_restaurant(owner)
  -> g.restaurant is set
  -> dashboard queries use g.restaurant.id
```

### Step 1: Owner logs in

Logic:

The owner authenticates through `/auth/login` and Flask-Login stores a `user_<id>` session.

Why use this?

The manager identity must be stable across all dashboard pages, subscriptions, and location switching.

### Step 2: Load active locations

Logic:

```python
active_locations_for_owner(current_user)
```

Why use this?

Only active restaurants should appear in the location switcher. Archived locations keep their data but should not behave like normal working locations.

### Step 3: Resolve selected location

Logic:

```python
resolve_active_restaurant(current_user)
```

If the session location is missing or invalid, the first active owned location becomes active.

Why use this?

The dashboard should never break because a browser has stale session data. Fallback behavior keeps the manager productive and avoids invalid location access.

### Step 4: Scope dashboard data

Logic:

Dashboard routes query with:

```python
restaurant_id = g.restaurant.id
```

Why use this?

Menus, tables, staff, orders, settings, analytics, and notifications must stay separate per location. This is the most important multi-tenant rule in the app.

### Step 5: Add a location

Logic:

```python
can_create_location(owner, subscription)
```

If allowed, create a new `Restaurant` row and default operating hours.

Why use this?

Location creation is controlled by the manager subscription. The limit is enforced at creation time, while existing over-limit locations remain accessible after downgrade.

## 4. Subscription Workflow

```text
Owner account
  -> one Subscription(owner_id)
  -> plan limits
  -> max locations
  -> max tables/items per active location
```

### Step 1: Find owner subscription

Logic:

```python
get_owner_subscription(owner)
```

Why use this?

Billing belongs to the manager, not to one restaurant location. This supports one owner managing several branches under one plan.

### Step 2: Apply plan limits

Logic:

```python
apply_plan_limits(subscription, 'pro')
```

Why use this?

Plan defaults stay centralized. When free/pro/enterprise limits change, one helper updates max locations, tables, and menu items consistently.

### Step 3: Enforce limits at creation

Logic:

```text
new location -> compare active location count with max_locations
new table    -> compare table count in active restaurant with max_tables
new item     -> compare item count in active restaurant with max_items
```

Why use this?

Blocking creation protects subscription rules without hiding existing data. This is safer for downgrades and avoids deleting business-critical restaurant records.

### Step 4: Check payment state

Logic:

```python
@payment_required
```

Why use this?

Unpaid owners should finish onboarding before using paid dashboard flows. Keeping this as a decorator makes payment gating consistent.

## 5. Customer QR Ordering Workflow

```text
Customer scans QR
  -> GET /r/<slug>/table/<table_id>
  -> table session created/reused
  -> customer builds cart in browser
  -> POST order JSON
  -> server validates prices/items/session
  -> order saved
  -> realtime notifications emitted
```

### Step 1: Scan table QR

Logic:

The URL contains restaurant slug and table ID:

```text
/r/chez-ahmed/table/5
```

Why use this?

The QR code identifies both the restaurant and the physical table. Customers do not need to log in or install an app.

### Step 2: Create or reuse table session

Logic:

```python
_ensure_session(table, restaurant)
```

Why use this?

A table session groups orders, guest identity, loyalty, and payment state for one sitting. It also lets the table become `occupied`.

### Step 3: Submit order JSON

Logic:

```http
POST /r/<slug>/table/<table_id>/order
```

Why use this?

Ordering is an action from the customer app, so JSON is simpler and faster than a full form reload. The browser can keep cart state and submit only when ready.

### Step 4: Validate order on the server

Logic:

`create_order()` checks session, restaurant, item availability, quantities, customizations, taxes, service charge, and subscription expiry.

Why use this?

Never trust client-side cart totals. Server-side validation prevents wrong prices, deleted items, unavailable items, and cross-restaurant item injection.

### Step 5: Save order and notify staff

Logic:

After commit, the backend emits `new_order` and creates an in-app notification.

Why use this?

The database is the source of truth. Realtime events should happen after the order exists, so staff screens never receive an order that cannot be loaded.

## 6. Staff Order Workflow

```text
Cashier accepts order
  -> kitchen receives it
  -> kitchen marks preparing
  -> kitchen marks ready
  -> waiter serves
  -> cashier/waiter confirms payment
  -> order completes
  -> table can close
```

### Step 1: Move status through state machine

Logic:

```python
update_order_status(order_id, new_status, restaurant_id)
```

Why use this?

Orders must follow a predictable path. A state machine prevents invalid jumps, such as `new -> ready` or `served -> preparing`.

### Step 2: Require payment before completion

Logic:

```text
completed requires payment_status == paid
```

Why use this?

The system should not close an order as complete until money is collected or confirmed.

### Step 3: Auto-release table when possible

Logic:

If all orders in the active table session are terminal, the table session can close and the table returns to `free`.

Why use this?

Staff should not manually clean up every table after the last order is completed. Automatic release keeps table status accurate.

## 7. Realtime Workflow

```text
Client connects
  -> joins role room
  -> backend emits events to scoped rooms
  -> only relevant screens update
```

### Step 1: Join room

Logic:

```javascript
socket.emit("join_kitchen", { restaurant_id: 1 });
```

Why use this?

Rooms keep realtime messages scoped. Kitchen screens do not need waiter-only events, and one restaurant should never receive another restaurant's orders.

### Step 2: Emit role-specific event

Logic:

```python
socketio.emit('kitchen_new_order', data, room=f'kitchen_{restaurant_id}')
```

Why use this?

Targeted emits reduce frontend filtering and protect location boundaries.

### Step 3: Emit customer tracking updates

Logic:

```python
room = f'customer_{session_token}'
```

Why use this?

Customers should only receive updates for their own table session. The session token gives a private tracking channel without customer login.

## 8. Payment Workflow

```text
Customer chooses online payment
  -> backend creates Flouci payment
  -> customer redirects to Flouci
  -> callback verifies payment
  -> order payment_status updates
```

### Step 1: Start payment from backend

Logic:

```python
initiate_flouci_payment(order_id, amount, success_url, fail_url)
```

Why use this?

Payment credentials must stay on the server. The browser should never know Flouci secrets.

### Step 2: Redirect to provider

Logic:

The customer leaves Tablii and pays on Flouci.

Why use this?

Using the provider-hosted payment page reduces sensitive payment handling inside the app.

### Step 3: Verify callback

Logic:

```python
verify_flouci_payment(payment_id)
```

Why use this?

The app should not trust a redirect alone. Verification confirms with the payment provider before marking payment as successful.

## 9. Admin Workflow

```text
Super admin logs in
  -> admin routes
  -> manage restaurants/subscriptions
  -> update platform-level settings
```

### Step 1: Require super admin

Logic:

```python
@super_admin_required
```

Why use this?

Admin pages can affect every tenant. They need a stronger permission boundary than normal owner pages.

### Step 2: Manage subscriptions

Logic:

Admin can update plan, max locations, max tables, max items, expiry, active state, and payment status.

Why use this?

Support and operations need a way to fix billing states, handle custom enterprise limits, and unblock accounts without editing the database manually.

## 10. Backend Design Rules

### Rule 1: Keep tenant boundaries explicit

Logic:

Every query for tenant data should include `restaurant_id` or owner scope.

Why use this?

Tenant leaks are one of the highest-risk bugs in this application.

### Rule 2: Put business rules in services

Logic:

Use route handlers for HTTP and services for business decisions.

Why use this?

Services are reusable from dashboard, staff routes, API routes, seed scripts, and tests.

### Rule 3: Validate server-side

Logic:

Prices, quantities, limits, status transitions, and ownership are checked on the backend.

Why use this?

Frontend checks improve UX, but backend checks protect the database and business rules.

### Rule 4: Emit realtime events after database commits

Logic:

Create/update the database row first, then notify clients.

Why use this?

Clients should only react to data that already exists and can be fetched or displayed reliably.

### Rule 5: Archive instead of deleting important business data

Logic:

Locations are archived with `Restaurant.is_active = False`.

Why use this?

Restaurants, orders, analytics, reviews, and payments are business records. Archiving preserves history while removing the location from daily workflows.
