# Phase 02 — Database Models & Migrations

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS. This is **Phase 2 of 12**. Phase 1 (project foundation) is complete. You now have a working Flask app factory with SQLAlchemy, Migrate, Login, SocketIO, and CSRF extensions initialized.

**In this phase you will**: define all SQLAlchemy models and set up Flask-Migrate.

---

## Prerequisites (already done)

- `app/__init__.py` exports `db`, `migrate`, `login_manager`.
- `config.py` provides `SQLALCHEMY_DATABASE_URI`.
- `run.py` boots the app via `socketio.run()`.

---

## Exact Deliverables

```
app/
└── models/
    ├── __init__.py          # Import all models so Alembic detects them
    ├── user.py              # User, StaffUser
    ├── restaurant.py        # Restaurant, Subscription, OperatingHours
    ├── menu.py              # Category, MenuItem, Customization, CustomOption
    ├── table.py             # Table, TableSession
    ├── order.py             # Order, OrderItem, PaymentTransaction, WaiterCall
    └── review.py            # Customer, Review, LoyaltyPoints, Notification
```

After creating models, run `flask db init` and `flask db migrate -m "initial"` to generate the first migration.

---

## Model Specifications

### 1. `models/user.py` — Platform Users

```python
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
```

#### `User(db.Model, UserMixin)`

| Column          | Type          | Constraints                                                              |
| --------------- | ------------- | ------------------------------------------------------------------------ |
| `id`            | `Integer`     | PK, autoincrement                                                        |
| `email`         | `String(120)` | `unique=True`, `nullable=False`, `index=True`                            |
| `password_hash` | `String(256)` | `nullable=False`                                                         |
| `name`          | `String(100)` | `nullable=False`                                                         |
| `phone`         | `String(20)`  | `nullable=True`                                                          |
| `role`          | `String(20)`  | `nullable=False`, default `'owner'`. Allowed: `'owner'`, `'super_admin'` |
| `is_active`     | `Boolean`     | default `True`                                                           |
| `created_at`    | `DateTime`    | default `datetime.now(timezone.utc)`                                     |

**Methods:**

- `set_password(password)` → stores `generate_password_hash(password)`.
- `check_password(password)` → returns `check_password_hash(self.password_hash, password)`.

**Relationships:**

- `restaurants` → one-to-many with `Restaurant`, `backref='owner'`, `lazy='dynamic'`.

**Flask-Login loader:**

```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

#### `StaffUser(db.Model)`

| Column          | Type          | Constraints                                                     |
| --------------- | ------------- | --------------------------------------------------------------- |
| `id`            | `Integer`     | PK                                                              |
| `restaurant_id` | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`           |
| `username`      | `String(50)`  | `nullable=False`                                                |
| `password_hash` | `String(256)` | `nullable=False`                                                |
| `name`          | `String(100)` | `nullable=False`                                                |
| `role`          | `String(20)`  | `nullable=False`. Allowed: `'cashier'`, `'kitchen'`, `'waiter'` |
| `is_active`     | `Boolean`     | default `True`                                                  |
| `created_at`    | `DateTime`    | default `datetime.now(timezone.utc)`                            |

**Unique constraint:** `(restaurant_id, username)` — usernames are unique per restaurant.

**Methods:** Same `set_password` / `check_password` as `User`.

---

### 2. `models/restaurant.py`

#### `Restaurant(db.Model)`

| Column           | Type          | Constraints                                   |
| ---------------- | ------------- | --------------------------------------------- |
| `id`             | `Integer`     | PK                                            |
| `owner_id`       | `Integer`     | FK → `users.id`, `nullable=False`             |
| `name`           | `String(150)` | `nullable=False`                              |
| `slug`           | `String(100)` | `unique=True`, `nullable=False`, `index=True` |
| `description`    | `Text`        | `nullable=True`                               |
| `logo_url`       | `String(300)` | `nullable=True`                               |
| `cover_url`      | `String(300)` | `nullable=True`                               |
| `address`        | `String(300)` | `nullable=True`                               |
| `phone`          | `String(20)`  | `nullable=True`                               |
| `city`           | `String(100)` | `nullable=True`                               |
| `currency`       | `String(10)`  | default `'TND'`                               |
| `tax_rate`       | `Float`       | default `0.0` (percentage, e.g. 7.0 = 7%)     |
| `service_charge` | `Float`       | default `0.0`                                 |
| `auto_accept`    | `Boolean`     | default `False`                               |
| `online_payment` | `Boolean`     | default `False`                               |
| `ramadan_mode`   | `Boolean`     | default `False`                               |
| `is_active`      | `Boolean`     | default `True`                                |
| `is_open`        | `Boolean`     | default `True`                                |
| `created_at`     | `DateTime`    | default `datetime.now(timezone.utc)`          |

**Relationships:**

- `categories` → one-to-many with `Category`
- `tables` → one-to-many with `Table`
- `staff_users` → one-to-many with `StaffUser`
- `orders` → one-to-many with `Order`
- `subscription` → one-to-one with `Subscription`, `uselist=False`
- `operating_hours` → one-to-many with `OperatingHours`

#### `Subscription(db.Model)`

| Column          | Type         | Constraints                                                 |
| --------------- | ------------ | ----------------------------------------------------------- |
| `id`            | `Integer`    | PK                                                          |
| `restaurant_id` | `Integer`    | FK → `restaurants.id`, `unique=True`, `nullable=False`      |
| `plan`          | `String(30)` | default `'free'`. Allowed: `'free'`, `'basic'`, `'premium'` |
| `max_tables`    | `Integer`    | default `5`                                                 |
| `max_items`     | `Integer`    | default `20`                                                |
| `started_at`    | `DateTime`   | default `datetime.now(timezone.utc)`                        |
| `expires_at`    | `DateTime`   | `nullable=True`                                             |
| `is_active`     | `Boolean`    | default `True`                                              |

#### `OperatingHours(db.Model)`

| Column          | Type      | Constraints                             |
| --------------- | --------- | --------------------------------------- |
| `id`            | `Integer` | PK                                      |
| `restaurant_id` | `Integer` | FK → `restaurants.id`, `nullable=False` |
| `day_of_week`   | `Integer` | `nullable=False`. 0=Monday … 6=Sunday   |
| `open_time`     | `Time`    | `nullable=True`                         |
| `close_time`    | `Time`    | `nullable=True`                         |
| `is_closed`     | `Boolean` | default `False`                         |

**Unique constraint:** `(restaurant_id, day_of_week)`.

---

### 3. `models/menu.py`

#### `Category(db.Model)`

| Column            | Type          | Constraints                                            |
| ----------------- | ------------- | ------------------------------------------------------ |
| `id`              | `Integer`     | PK                                                     |
| `restaurant_id`   | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`  |
| `name_ar`         | `String(100)` | `nullable=True`                                        |
| `name_fr`         | `String(100)` | `nullable=False`                                       |
| `name_en`         | `String(100)` | `nullable=True`                                        |
| `icon`            | `String(10)`  | `nullable=True` (emoji)                                |
| `sort_order`      | `Integer`     | default `0`                                            |
| `is_active`       | `Boolean`     | default `True`                                         |
| `available_from`  | `Time`        | `nullable=True`                                        |
| `available_until` | `Time`        | `nullable=True`                                        |
| `ramadan_type`    | `String(20)`  | `nullable=True`. Values: `'iftar'`, `'suhoor'`, `None` |

**Relationships:**

- `items` → one-to-many with `MenuItem`

#### `MenuItem(db.Model)`

| Column           | Type          | Constraints                                           |
| ---------------- | ------------- | ----------------------------------------------------- |
| `id`             | `Integer`     | PK                                                    |
| `category_id`    | `Integer`     | FK → `categories.id`, `nullable=False`, `index=True`  |
| `restaurant_id`  | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True` |
| `name_ar`        | `String(150)` | `nullable=True`                                       |
| `name_fr`        | `String(150)` | `nullable=False`                                      |
| `name_en`        | `String(150)` | `nullable=True`                                       |
| `description_ar` | `Text`        | `nullable=True`                                       |
| `description_fr` | `Text`        | `nullable=True`                                       |
| `description_en` | `Text`        | `nullable=True`                                       |
| `price`          | `Float`       | `nullable=False`                                      |
| `image_url`      | `String(300)` | `nullable=True`                                       |
| `is_available`   | `Boolean`     | default `True`                                        |
| `sort_order`     | `Integer`     | default `0`                                           |
| `prep_time`      | `Integer`     | `nullable=True` (minutes)                             |
| `calories`       | `Integer`     | `nullable=True`                                       |
| `allergens`      | `String(300)` | `nullable=True` (comma-separated)                     |
| `is_popular`     | `Boolean`     | default `False`                                       |
| `deleted_at`     | `DateTime`    | `nullable=True` (soft delete)                         |

**Relationships:**

- `customizations` → one-to-many with `Customization`

#### `Customization(db.Model)`

| Column           | Type          | Constraints                                        |
| ---------------- | ------------- | -------------------------------------------------- |
| `id`             | `Integer`     | PK                                                 |
| `menu_item_id`   | `Integer`     | FK → `menu_items.id`, `nullable=False`             |
| `group_name_ar`  | `String(100)` | `nullable=True`                                    |
| `group_name_fr`  | `String(100)` | `nullable=False`                                   |
| `group_name_en`  | `String(100)` | `nullable=True`                                    |
| `selection_type` | `String(20)`  | `nullable=False`. Values: `'single'`, `'multiple'` |
| `is_required`    | `Boolean`     | default `False`                                    |
| `max_selections` | `Integer`     | `nullable=True`                                    |

**Relationships:**

- `options` → one-to-many with `CustomOption`

#### `CustomOption(db.Model)`

| Column             | Type          | Constraints                                |
| ------------------ | ------------- | ------------------------------------------ |
| `id`               | `Integer`     | PK                                         |
| `customization_id` | `Integer`     | FK → `customizations.id`, `nullable=False` |
| `name_ar`          | `String(100)` | `nullable=True`                            |
| `name_fr`          | `String(100)` | `nullable=False`                           |
| `name_en`          | `String(100)` | `nullable=True`                            |
| `extra_price`      | `Float`       | default `0.0`                              |
| `is_default`       | `Boolean`     | default `False`                            |

---

### 4. `models/table.py`

#### `Table(db.Model)`

Use the table name `tables_` to avoid SQL keyword conflict.

| Column               | Type          | Constraints                                                    |
| -------------------- | ------------- | -------------------------------------------------------------- |
| `id`                 | `Integer`     | PK                                                             |
| `restaurant_id`      | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`          |
| `table_number`       | `Integer`     | `nullable=False`                                               |
| `capacity`           | `Integer`     | default `4`                                                    |
| `status`             | `String(20)`  | default `'free'`. Values: `'free'`, `'occupied'`, `'reserved'` |
| `qr_code_url`        | `String(300)` | `nullable=True`                                                |
| `position_x`         | `Float`       | `nullable=True` (for floor map)                                |
| `position_y`         | `Float`       | `nullable=True`                                                |
| `assigned_waiter_id` | `Integer`     | FK → `staff_users.id`, `nullable=True`                         |

**Unique constraint:** `(restaurant_id, table_number)`.

**Relationships:**

- `sessions` → one-to-many with `TableSession`
- `assigned_waiter` → many-to-one with `StaffUser`

#### `TableSession(db.Model)`

| Column          | Type          | Constraints                                       |
| --------------- | ------------- | ------------------------------------------------- |
| `id`            | `Integer`     | PK                                                |
| `table_id`      | `Integer`     | FK → `tables_.id`, `nullable=False`, `index=True` |
| `restaurant_id` | `Integer`     | FK → `restaurants.id`, `nullable=False`           |
| `customer_id`   | `Integer`     | FK → `customers.id`, `nullable=True`              |
| `session_token` | `String(64)`  | `unique=True`, `nullable=False`                   |
| `guest_name`    | `String(100)` | `nullable=True`                                   |
| `started_at`    | `DateTime`    | default `datetime.now(timezone.utc)`              |
| `ended_at`      | `DateTime`    | `nullable=True`                                   |
| `is_active`     | `Boolean`     | default `True`                                    |

**Relationships:**

- `orders` → one-to-many with `Order`

---

### 5. `models/order.py`

#### `Order(db.Model)`

| Column            | Type          | Constraints                                                                                                        |
| ----------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| `id`              | `Integer`     | PK                                                                                                                 |
| `session_id`      | `Integer`     | FK → `table_sessions.id`, `nullable=True`                                                                          |
| `restaurant_id`   | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`                                                              |
| `table_id`        | `Integer`     | FK → `tables_.id`, `nullable=True`                                                                                 |
| `customer_id`     | `Integer`     | FK → `customers.id`, `nullable=True`                                                                               |
| `order_number`    | `String(10)`  | `nullable=False` (e.g. `'#A7K2'`)                                                                                  |
| `status`          | `String(20)`  | default `'new'`. Values: `'new'`, `'accepted'`, `'preparing'`, `'ready'`, `'served'`, `'completed'`, `'cancelled'` |
| `payment_method`  | `String(20)`  | `nullable=True`. Values: `'cash'`, `'online'`                                                                      |
| `payment_status`  | `String(20)`  | default `'pending'`. Values: `'pending'`, `'paid'`, `'failed'`, `'refunded'`                                       |
| `subtotal`        | `Float`       | default `0.0`                                                                                                      |
| `tax_amount`      | `Float`       | default `0.0`                                                                                                      |
| `total_amount`    | `Float`       | default `0.0`                                                                                                      |
| `special_notes`   | `Text`        | `nullable=True`                                                                                                    |
| `is_gift`         | `Boolean`     | default `False`                                                                                                    |
| `gift_from_table` | `Integer`     | `nullable=True`                                                                                                    |
| `gift_message`    | `String(300)` | `nullable=True`                                                                                                    |
| `created_at`      | `DateTime`    | default `datetime.now(timezone.utc)`                                                                               |
| `accepted_at`     | `DateTime`    | `nullable=True`                                                                                                    |
| `preparing_at`    | `DateTime`    | `nullable=True`                                                                                                    |
| `ready_at`        | `DateTime`    | `nullable=True`                                                                                                    |
| `served_at`       | `DateTime`    | `nullable=True`                                                                                                    |
| `completed_at`    | `DateTime`    | `nullable=True`                                                                                                    |

**Relationships:**

- `items` → one-to-many with `OrderItem`
- `payment` → one-to-one with `PaymentTransaction`, `uselist=False`
- `review` → one-to-one with `Review`, `uselist=False`

#### `OrderItem(db.Model)`

| Column             | Type          | Constraints                                                     |
| ------------------ | ------------- | --------------------------------------------------------------- |
| `id`               | `Integer`     | PK                                                              |
| `order_id`         | `Integer`     | FK → `orders.id`, `nullable=False`, `index=True`                |
| `menu_item_id`     | `Integer`     | FK → `menu_items.id`, `nullable=False`                          |
| `quantity`         | `Integer`     | `nullable=False`, default `1`                                   |
| `unit_price`       | `Float`       | `nullable=False`                                                |
| `total_price`      | `Float`       | `nullable=False`                                                |
| `selected_options` | `Text`        | `nullable=True` (JSON string of selected customization options) |
| `notes`            | `String(300)` | `nullable=True`                                                 |

#### `PaymentTransaction(db.Model)`

| Column                   | Type          | Constraints                                                         |
| ------------------------ | ------------- | ------------------------------------------------------------------- |
| `id`                     | `Integer`     | PK                                                                  |
| `order_id`               | `Integer`     | FK → `orders.id`, `unique=True`, `nullable=False`                   |
| `gateway`                | `String(30)`  | `nullable=False`. Values: `'flouci'`, `'konnect'`                   |
| `amount`                 | `Float`       | `nullable=False`                                                    |
| `gateway_transaction_id` | `String(200)` | `nullable=True`                                                     |
| `status`                 | `String(20)`  | default `'pending'`. Values: `'pending'`, `'completed'`, `'failed'` |
| `raw_response`           | `Text`        | `nullable=True` (JSON)                                              |
| `created_at`             | `DateTime`    | default `datetime.now(timezone.utc)`                                |

#### `WaiterCall(db.Model)`

| Column          | Type          | Constraints                                                         |
| --------------- | ------------- | ------------------------------------------------------------------- |
| `id`            | `Integer`     | PK                                                                  |
| `restaurant_id` | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`               |
| `table_id`      | `Integer`     | FK → `tables_.id`, `nullable=False`                                 |
| `call_type`     | `String(30)`  | `nullable=False`. Values: `'water'`, `'bill'`, `'help'`, `'custom'` |
| `message`       | `String(300)` | `nullable=True`                                                     |
| `status`        | `String(20)`  | default `'pending'`. Values: `'pending'`, `'resolved'`              |
| `created_at`    | `DateTime`    | default `datetime.now(timezone.utc)`                                |
| `resolved_at`   | `DateTime`    | `nullable=True`                                                     |
| `resolved_by`   | `Integer`     | FK → `staff_users.id`, `nullable=True`                              |

---

### 6. `models/review.py`

#### `Customer(db.Model)`

| Column          | Type          | Constraints                          |
| --------------- | ------------- | ------------------------------------ |
| `id`            | `Integer`     | PK                                   |
| `phone`         | `String(20)`  | `unique=True`, `nullable=False`      |
| `name`          | `String(100)` | `nullable=True`                      |
| `email`         | `String(120)` | `nullable=True`                      |
| `password_hash` | `String(256)` | `nullable=True`                      |
| `created_at`    | `DateTime`    | default `datetime.now(timezone.utc)` |

#### `Review(db.Model)`

| Column           | Type          | Constraints                                           |
| ---------------- | ------------- | ----------------------------------------------------- |
| `id`             | `Integer`     | PK                                                    |
| `order_id`       | `Integer`     | FK → `orders.id`, `nullable=False`                    |
| `restaurant_id`  | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True` |
| `rating`         | `Integer`     | `nullable=False`. Range: 1–5                          |
| `food_rating`    | `Integer`     | `nullable=True`. Range: 1–5                           |
| `service_rating` | `Integer`     | `nullable=True`. Range: 1–5                           |
| `comment`        | `Text`        | `nullable=True`                                       |
| `photo_url`      | `String(300)` | `nullable=True`                                       |
| `created_at`     | `DateTime`    | default `datetime.now(timezone.utc)`                  |

#### `LoyaltyPoints(db.Model)`

| Column           | Type      | Constraints                             |
| ---------------- | --------- | --------------------------------------- |
| `id`             | `Integer` | PK                                      |
| `customer_id`    | `Integer` | FK → `customers.id`, `nullable=False`   |
| `restaurant_id`  | `Integer` | FK → `restaurants.id`, `nullable=False` |
| `points`         | `Integer` | default `0`                             |
| `total_earned`   | `Integer` | default `0`                             |
| `total_redeemed` | `Integer` | default `0`                             |

**Unique constraint:** `(customer_id, restaurant_id)`.

#### `Notification(db.Model)`

| Column           | Type          | Constraints                                                                                     |
| ---------------- | ------------- | ----------------------------------------------------------------------------------------------- |
| `id`             | `Integer`     | PK                                                                                              |
| `restaurant_id`  | `Integer`     | FK → `restaurants.id`, `nullable=False`, `index=True`                                           |
| `target_role`    | `String(20)`  | `nullable=True`. Values: `'cashier'`, `'kitchen'`, `'waiter'`, `'owner'`                        |
| `target_user_id` | `Integer`     | `nullable=True`                                                                                 |
| `type`           | `String(30)`  | `nullable=False`. Values: `'new_order'`, `'order_ready'`, `'call_waiter'`, `'payment_received'` |
| `title`          | `String(200)` | `nullable=False`                                                                                |
| `body`           | `Text`        | `nullable=True`                                                                                 |
| `is_read`        | `Boolean`     | default `False`                                                                                 |
| `created_at`     | `DateTime`    | default `datetime.now(timezone.utc)`                                                            |

---

### 7. `models/__init__.py`

Import **every** model class so Alembic auto-detects them:

```python
"""Import all models so Alembic migrations can detect them."""
from app.models.user import User, StaffUser
from app.models.restaurant import Restaurant, Subscription, OperatingHours
from app.models.menu import Category, MenuItem, Customization, CustomOption
from app.models.table import Table, TableSession
from app.models.order import Order, OrderItem, PaymentTransaction, WaiterCall
from app.models.review import Customer, Review, LoyaltyPoints, Notification
```

---

## Update `app/__init__.py`

Add the following line **inside** `create_app()`, after extension initialization and before the return:

```python
from app import models  # noqa: F401 — ensure models are registered
```

---

## Migration Commands

After all model files are created, run:

```bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

---

## Validation Checklist

- [ ] All model files import `db` from `app` and use `db.Model`.
- [ ] All foreign keys point to correct table names (watch for `tables_` not `tables`).
- [ ] All `DateTime` defaults use `datetime.now(timezone.utc)` (not the deprecated `utcnow()`).
- [ ] All unique constraints are declared.
- [ ] `flask db migrate` generates a migration file without errors.
- [ ] `flask db upgrade` applies the migration successfully.
- [ ] All relationships have matching FKs.

---

## Strict Rules

1. **Do not** create any routes, templates, services, or static files.
2. **Do not** use `db.create_all()` — use Flask-Migrate exclusively.
3. Every model class must have `__tablename__` explicitly set.
4. Use `db.relationship()` with explicit `backref` or `back_populates`.
5. All string column lengths must match the table above exactly.
6. Follow **PEP 8** and add a docstring to every model class.
