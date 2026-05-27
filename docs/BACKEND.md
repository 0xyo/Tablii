# Backend Guide

This document explains how the Tablii backend is organized, how requests move through the app, and where to make changes safely.

## Stack

| Concern | Technology |
| --- | --- |
| Web framework | Flask |
| Database ORM | Flask-SQLAlchemy / SQLAlchemy |
| Migrations | Flask-Migrate / Alembic |
| Authentication | Flask-Login |
| Forms and CSRF | Flask-WTF |
| Realtime events | Flask-SocketIO |
| Templates | Jinja2 |
| Payments | Flouci |
| Uploads | Pillow-backed upload service |
| Development database | SQLite |
| Production database | PostgreSQL-ready through `DATABASE_URL` |

## Application Layout

```text
app/
  __init__.py              Flask app factory, extensions, blueprint registration
  config.py                Environment-based configuration
  events/                  Socket.IO room joins and realtime notifications
  models/                  SQLAlchemy models
  routes/                  Flask blueprints for HTML pages and JSON APIs
  services/                Business logic used by routes
  static/                  CSS, JavaScript, uploaded assets, generated QR codes
  templates/               Jinja templates
  utils/                   Decorators, formatting helpers, slug/token helpers
migrations/                Alembic migration history
tests/                     Pytest test suite
run.py                     Local app entrypoint
seed.py                    Demo data bootstrap
```

The app uses a factory pattern in `app/__init__.py`. The factory creates the Flask app, initializes extensions, registers blueprints, installs Socket.IO handlers, and wires template helpers.

## Core Concepts

### Tenancy

`Restaurant` is the tenant boundary. A restaurant row represents one physical location, such as `El Weed La Marsa` or `El Weed Centre Ville`.

Most owner dashboard, staff, customer, order, menu, table, analytics, and notification queries must include `restaurant_id`. This keeps each location independent even when one owner manages multiple locations.

### Manager Locations

Owners can manage several active restaurant locations. The selected location is stored in:

```python
session['active_restaurant_id']
```

`restaurant_required` resolves the active location for owners. If the session is missing or invalid, it falls back to the first active location owned by that user. Staff users do not use the session location switcher; they stay scoped to their assigned `restaurant_id`.

Location helpers live in:

```text
app/services/subscription_service.py
```

Important helpers:

| Helper | Purpose |
| --- | --- |
| `resolve_active_restaurant(owner)` | Returns the owner's active location and repairs invalid session state |
| `active_locations_for_owner(owner)` | Lists active locations for the manager |
| `can_create_location(owner, subscription)` | Checks the `max_locations` subscription limit |
| `ensure_owner_subscription(owner, restaurant)` | Creates or upgrades an owner-level subscription |
| `apply_plan_limits(subscription, plan)` | Applies plan defaults to a subscription |

### Subscription Model

Subscriptions are manager-level, not location-level. `Subscription.owner_id` is the canonical owner. `Subscription.restaurant_id` remains for legacy compatibility and usually points to the first location.

Plan defaults:

| Plan | Locations | Tables per location | Menu items per location |
| --- | ---: | ---: | ---: |
| `free` | 1 | 5 | 20 |
| `pro` | 3 | 25 | 100 |
| `enterprise` | 999 | 999 | 999 |

`Restaurant.subscription` is a compatibility property that returns the owner's subscription when available. Existing code can continue to read `restaurant.subscription`, but new billing logic should prefer owner-level helpers.

Enforcement rules:

- New location creation is blocked when active locations are greater than or equal to `subscription.max_locations`.
- Existing locations remain accessible after a downgrade.
- Table and menu item limits are enforced per active location.
- Expired or unpaid subscriptions block the same flows they blocked before, now at manager level.

## Authentication And Access Control

There are two login model types:

| Model | Use |
| --- | --- |
| `User` | Platform users: owner and super admin |
| `StaffUser` | Restaurant staff: cashier, kitchen, waiter |

`User.get_id()` prefixes IDs with `user_`. `StaffUser.get_id()` prefixes IDs with `staff_`. The Flask-Login loader uses this prefix to load the correct model.

Access decorators live in `app/utils/decorators.py`:

| Decorator | Purpose |
| --- | --- |
| `role_required(*roles)` | Restricts a view to owner/staff roles; super admin bypasses role checks |
| `restaurant_required` | Resolves and stores `g.restaurant`; also adds subscription state |
| `payment_required` | Redirects unpaid owners to onboarding |
| `super_admin_required` | Restricts routes to super admins |

Common globals set by `restaurant_required`:

| Global | Value |
| --- | --- |
| `g.restaurant` | Active restaurant/location for the current request |
| `g.owner_locations` | Active locations owned by the manager |
| `g.owner_subscription` | Owner-level subscription |
| `g.subscription_expired` | Whether the subscription is expired |
| `g.subscription_days_left` | Days until expiry when expiry is close |

## Blueprints

| Blueprint | URL prefix | Responsibility |
| --- | --- | --- |
| `landing` | `/` | Public landing page |
| `auth` | `/auth` | Login, registration, logout |
| `onboarding` | `/onboarding` | Plan selection and subscription payment setup |
| `dashboard` | `/dashboard` | Owner manager dashboard |
| `customer` | none | QR table customer experience under `/r/<slug>/table/<id>` |
| `cashier` | `/cashier` | Cashier order board and manual orders |
| `kitchen` | `/kitchen` | Kitchen display and order preparation flow |
| `waiter` | `/waiter` | Waiter tables, calls, payment confirmation |
| `api` | `/api` | JSON API endpoints |
| `admin` | `/admin` | Super admin management pages |

The `api` blueprint is CSRF-exempt. Some customer JSON routes are also CSRF-exempt because the table-side app submits JSON from the QR menu flow.

## Data Model Overview

Primary models:

| Model | Description |
| --- | --- |
| `User` | Owner and super admin accounts |
| `StaffUser` | Cashier, kitchen, and waiter accounts scoped to one restaurant |
| `Restaurant` | One restaurant location and its settings |
| `Subscription` | Owner-level billing limits and payment state |
| `OperatingHours` | Weekly open/closed schedule per restaurant |
| `Category` | Menu category |
| `MenuItem` | Menu item with localized names/descriptions |
| `Customization` | Option group for a menu item |
| `CustomOption` | Single selectable customization option |
| `Table` | Physical table in a restaurant |
| `TableSession` | Active customer session for an occupied table |
| `Order` | Customer or cashier order |
| `OrderItem` | Line item within an order |
| `PaymentTransaction` | Flouci payment tracking |
| `WaiterCall` | Customer call for water, bill, help, or custom request |
| `Customer` | Lightweight customer profile for loyalty |
| `Review` | Customer review for an order |
| `LoyaltyPoints` | Loyalty balance per customer and restaurant |
| `Notification` | In-app owner/staff notification |

## Services

Business logic should live in `app/services/`, not directly in templates or route handlers.

| Service | Responsibility |
| --- | --- |
| `order_service.py` | Order creation, server-side price calculation, status transitions, table release |
| `subscription_service.py` | Plan defaults, owner subscriptions, location switching, location limits |
| `analytics_service.py` | Revenue, popular items, peak hours, service-time metrics |
| `payment_service.py` | Flouci payment initiation and verification |
| `upload_service.py` | Safe image upload validation and storage |
| `qr_service.py` | Table QR code generation |
| `loyalty_service.py` | Loyalty points earning and balance lookup |
| `notification_service.py` | In-app notification creation |

## Order Lifecycle

Orders follow this state machine:

```text
new -> accepted -> preparing -> ready -> served -> completed
  \       \
   \       -> cancelled
    -> cancelled
```

Valid transitions are defined in `app/services/order_service.py`:

| Current status | Allowed next statuses |
| --- | --- |
| `new` | `accepted`, `cancelled` |
| `accepted` | `preparing`, `cancelled` |
| `preparing` | `ready` |
| `ready` | `served` |
| `served` | `completed` |

An order cannot move to `completed` unless `payment_status` is `paid`.

When all orders in a table session are terminal (`completed` or `cancelled`), the table session can be closed and the table returns to `free`.

## Realtime Events

Socket.IO rooms are restaurant-scoped:

| Room | Joined by |
| --- | --- |
| `restaurant_<restaurant_id>` | Dashboard, cashier, waiter, shared restaurant listeners |
| `cashier_<restaurant_id>` | Cashier board |
| `kitchen_<restaurant_id>` | Kitchen display |
| `waiter_<staff_user_id>` | Individual waiter |
| `customer_<session_token>` | Customer order tracking page |

Client join events:

| Event | Payload |
| --- | --- |
| `join_restaurant` | `{ "restaurant_id": 1 }` |
| `join_cashier` | `{ "restaurant_id": 1 }` |
| `join_kitchen` | `{ "restaurant_id": 1 }` |
| `join_waiter` | `{ "restaurant_id": 1, "waiter_id": 4 }` |
| `join_customer` | `{ "session_token": "..." }` |

Server emitted events:

| Event | Typical room | Purpose |
| --- | --- | --- |
| `new_order` | `restaurant_<id>` | A new order was created |
| `new_notification` | `restaurant_<id>` | A lightweight notification marker |
| `kitchen_new_order` | `kitchen_<id>` | Kitchen should start tracking an accepted order |
| `order_status_update` | `restaurant_<id>`, `customer_<token>` | Order moved to a new status |
| `order_ready` | `restaurant_<id>` | Kitchen marked an order ready |
| `waiter_call` | `restaurant_<id>`, `waiter_<id>` | Customer requested waiter help |
| `table_status_change` | `restaurant_<id>` | Table changed status |

## Payments

Flouci integration lives in `app/services/payment_service.py`.

Customer flow:

1. Customer opens `/r/<slug>/table/<table_id>/order/<order_id>/pay`.
2. Backend creates a Flouci payment and redirects the customer to the payment page.
3. Flouci redirects back to `/payment/callback`.
4. Backend verifies the payment and updates payment state.

Required environment variables:

```env
FLOUCI_APP_TOKEN=
FLOUCI_APP_SECRET=
```

When payment service is unavailable, the app falls back to cash-at-counter messaging.

## Uploads

Uploads are handled by `app/services/upload_service.py`.

Current upload flows include:

- Menu/item/dashboard image uploads
- API image upload at `POST /api/upload-image`
- Review photo upload

The configured upload limit is controlled by:

```env
MAX_CONTENT_LENGTH=5242880
```

## Local Development

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build:css
flask db upgrade
python seed.py
python run.py
```

Default local URL:

```text
http://127.0.0.1:5000
```

## Database Migrations

Use Alembic through Flask-Migrate:

```powershell
flask db migrate -m "Describe the schema change"
flask db upgrade
```

Migration rules:

- Add a migration for every database schema change.
- Keep migrations backward-aware when existing production data may exist.
- For multi-location changes, preserve existing `Restaurant`, `Subscription`, and owner rows.
- Prefer data migrations that copy or fill values instead of deleting old data.

## Testing

Run the full test suite:

```powershell
pytest tests/
```

Useful focused checks:

```powershell
python -m compileall app
pytest tests/test_subscription_locations.py
```

For backend changes, add tests around:

- Authorization boundaries
- Restaurant/location scoping
- Subscription limit enforcement
- Order status transitions
- Payment and upload failure paths
- JSON API response shape

## Backend Change Checklist

Before shipping backend work:

- Queries are scoped by `restaurant_id` or owner where appropriate.
- Staff users cannot access another restaurant.
- Owner dashboard routes use the active location from `g.restaurant`.
- Subscription limits use `subscription_service.py`.
- Route handlers delegate business logic to services when logic is non-trivial.
- Schema changes include an Alembic migration.
- User-facing errors are clear and safe.
- Tests cover the success path and the main failure path.
