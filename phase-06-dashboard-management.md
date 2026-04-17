# Phase 06 — Dashboard & Menu Management

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS (Flask). This is **Phase 6 of 12**. Phases 1–5 are complete: authentication, customer interface, and order creation work.

**In this phase you will**: build the restaurant owner's dashboard — the admin panel for managing the restaurant, menu, tables, staff, and settings.

---

## Prerequisites (already done)

- Owner authentication with `@login_required`.
- `@role_required('owner')` and `@restaurant_required` decorators.
- All models for `Restaurant`, `Category`, `MenuItem`, `Customization`, `CustomOption`, `Table`, `StaffUser`, `Subscription`, `OperatingHours`.
- `upload_service` for image uploads, `qr_service` for QR codes.

---

## Exact Deliverables

```
app/
├── routes/
│   └── dashboard.py                  # Dashboard blueprint
│
└── templates/
    └── dashboard/
        ├── base_dashboard.html       # Dashboard layout with sidebar
        ├── overview.html             # Overview / home
        ├── menu/
        │   ├── categories.html       # List & manage categories
        │   ├── items.html            # List menu items
        │   ├── item_form.html        # Create / edit menu item
        │   └── customizations.html   # Manage customization options
        ├── tables/
        │   ├── list.html             # List & manage tables
        │   └── qr_codes.html         # View & print QR codes
        ├── staff/
        │   ├── list.html             # List staff members
        │   └── form.html             # Add / edit staff member
        ├── orders/
        │   └── history.html          # Order history with filters
        └── settings.html             # Restaurant settings
```

Also update `routes/__init__.py` to register `dashboard_bp`.

---

## Blueprint Setup

```python
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
```

**Every route** in this blueprint must have:

```python
@dashboard_bp.route(...)
@login_required
@restaurant_required
def route_function():
    restaurant = g.restaurant
    ...
```

---

## Route Specifications

### 1. `GET /dashboard` — Overview

**Logic:**

1. Query today's orders: `Order.query.filter(Order.restaurant_id == restaurant.id, func.date(Order.created_at) == date.today()).all()`.
2. Calculate: `orders_today` (count), `revenue_today` (sum of `total_amount` where `payment_status == 'paid'`), `tables_occupied` (count of tables with status `'occupied'`).
3. Query last 10 orders for the "Recent Orders" table.
4. Render `dashboard/overview.html`.

**Template (`overview.html`):**

- **Stat cards row** (4 cards): Orders Today, Revenue Today, Tables Occupied, Active Staff.
- Each card: icon, label, value, colored background.
- **Recent Orders table**: order number, table, items count, total, status badge, time.
- Status badges use color coding: `new` → blue, `preparing` → yellow, `ready` → green, `served` → gray.

---

### 2. Menu Management — Categories

#### `GET /dashboard/menu/categories`

- Query all categories for the restaurant, ordered by `sort_order`.
- Render with category list table: name (FR/AR/EN), icon, sort order, active status, item count, action buttons (edit, toggle active, delete).

#### `POST /dashboard/menu/categories/add`

- Accept form: `name_fr` (required), `name_ar`, `name_en`, `icon`, `ramadan_type`.
- Validate `name_fr` is not empty.
- Create `Category`, set `sort_order` to max existing + 1.
- Redirect back with flash success.

#### `POST /dashboard/menu/categories/<int:id>/update`

- Update name fields, icon, active status, ramadan_type.
- Redirect back.

#### `POST /dashboard/menu/categories/<int:id>/delete`

- Only allow if category has no active menu items. If it has items → flash error.
- Delete the category.
- Redirect back.

#### `POST /dashboard/menu/categories/reorder`

- Accept JSON: `{order: [{id: 1, sort_order: 0}, {id: 2, sort_order: 1}, ...]}`.
- Validate all IDs belong to the restaurant.
- Update `sort_order` for each.
- Return JSON `{success: true}`.

---

### 3. Menu Management — Items

#### `GET /dashboard/menu/items`

- Query items with optional filter by `category_id` query param.
- Exclude soft-deleted items (`deleted_at is None`).
- Render table: image thumbnail, name, category, price, available toggle, popular badge, actions.

#### `GET /dashboard/menu/item/new`

- Render `item_form.html` in "create" mode.
- Pass all categories for the select dropdown.

#### `POST /dashboard/menu/item/new`

- Accept form: `name_fr` (required), `name_ar`, `name_en`, `description_fr`, `description_ar`, `description_en`, `category_id` (required), `price` (required), `prep_time`, `calories`, `allergens`, `is_popular` (checkbox), `image` (file upload).
- Validate:
  - `name_fr` not empty.
  - `price` is a valid positive number (use `validate_price`).
  - `category_id` exists and belongs to restaurant.
  - Check subscription limit: `MenuItem.query.filter_by(restaurant_id=restaurant.id, deleted_at=None).count() < subscription.max_items`.
- If image uploaded → `upload_service.save_uploaded_file(file, 'menu_items')`.
- Create `MenuItem`.
- Flash success, redirect to items list.

#### `GET /dashboard/menu/item/<int:id>/edit`

- Load item, verify it belongs to restaurant.
- Render `item_form.html` in "edit" mode with existing data.

#### `POST /dashboard/menu/item/<int:id>/edit`

- Same validation as create.
- If new image uploaded → delete old image, save new one.
- Update all fields.
- Flash success, redirect to items list.

#### `POST /dashboard/menu/item/<int:id>/delete`

- **Soft delete**: set `deleted_at = datetime.now(timezone.utc)`.
- Do NOT physically delete — orders may reference this item.
- Flash success.

#### `POST /dashboard/menu/item/<int:id>/toggle`

- Toggle `is_available` boolean.
- Return JSON `{success: true, is_available: <new_value>}`.

---

### 4. Menu Management — Customizations

#### `GET /dashboard/menu/item/<int:item_id>/customizations`

- Load item and its customizations with options.
- Render `customizations.html`.

#### `POST /dashboard/menu/item/<int:item_id>/customizations/add`

- Accept: `group_name_fr`, `group_name_ar`, `group_name_en`, `selection_type`, `is_required`, `max_selections`.
- Create `Customization`.

#### `POST /dashboard/menu/customizations/<int:id>/options/add`

- Accept: `name_fr`, `name_ar`, `name_en`, `extra_price`, `is_default`.
- Validate `extra_price` is valid.
- Create `CustomOption`.

#### `POST /dashboard/menu/customizations/<int:id>/delete`

- Delete customization and all its options (cascade).

---

### 5. Table Management

#### `GET /dashboard/tables`

- Query all tables ordered by `table_number`.
- Render grid: table number, capacity, status indicator (color-coded), assigned waiter, QR code link.

#### `POST /dashboard/tables/add`

- Accept: `table_number`, `capacity`.
- Validate:
  - `table_number` is unique for this restaurant.
  - Check subscription: `Table.query.filter_by(restaurant_id=restaurant.id).count() < subscription.max_tables`.
- Create `Table`.
- Auto-generate QR code via `qr_service.generate_table_qr()`.
- Flash success.

#### `POST /dashboard/tables/<int:id>/delete`

- Only allow if table has no active session. If active → flash error.
- Delete table.

#### `GET /dashboard/tables/<int:id>/qr`

- Regenerate QR code if missing.
- Return the QR code image file as a download (use `send_file`).

#### `POST /dashboard/tables/<int:id>/assign-waiter`

- Accept: `waiter_id` (staff user with role `'waiter'`).
- Validate waiter belongs to restaurant.
- Update `table.assigned_waiter_id`.

---

### 6. Staff Management

#### `GET /dashboard/staff`

- Query all `StaffUser` for the restaurant.
- Render table: name, username, role badge, active status, actions.

#### `GET /dashboard/staff/add`

- Render `form.html` in create mode.

#### `POST /dashboard/staff/add`

- Accept: `name`, `username`, `password`, `role` (cashier/kitchen/waiter).
- Validate:
  - `username` unique within restaurant.
  - `password` length ≥ 6.
  - `role` is valid enum value.
- Create `StaffUser` with `set_password()`.
- Flash success.

#### `GET /dashboard/staff/<int:id>/edit`

- Render form in edit mode.

#### `POST /dashboard/staff/<int:id>/edit`

- Update name, role. If new password provided → update password.
- Toggle active status if checkbox changed.

#### `POST /dashboard/staff/<int:id>/delete`

- Delete staff user.

---

### 7. Order History

#### `GET /dashboard/orders/history`

- Accept query params: `status`, `date_from`, `date_to`, `page` (default 1).
- Query orders with filters, paginated (20 per page).
- Render: order number, table, items count, total, status, payment status, date/time.
- Include date-range picker and status filter dropdown.

---

### 8. Settings

#### `GET /dashboard/settings`

- Load restaurant data and operating hours.
- Render form with all editable fields.

#### `POST /dashboard/settings`

- Accept: `name`, `description`, `address`, `phone`, `city`, `tax_rate`, `service_charge`, `auto_accept`, `online_payment`, `ramadan_mode`, `logo` (file), operating hours (7 day entries).
- Validate and update restaurant fields.
- Update operating hours for each day.
- If logo uploaded → save and update `logo_url`.
- Flash success.

---

## Dashboard Layout Template

### `templates/dashboard/base_dashboard.html`

Extend `base.html`. Structure:

```
┌────────────────────────────────────────────────────┐
│ Full-width layout                                  │
│ ┌──────────┐ ┌──────────────────────────────────┐  │
│ │ Sidebar  │ │ Main Content Area                │  │
│ │          │ │ ┌─────────────────────────────┐   │  │
│ │ Logo     │ │ │ Top bar: page title, user   │   │  │
│ │ Nav      │ │ └─────────────────────────────┘   │  │
│ │ links    │ │ ┌─────────────────────────────┐   │  │
│ │          │ │ │ {% block dashboard_content %}│   │  │
│ │          │ │ └─────────────────────────────┘   │  │
│ └──────────┘ └──────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

**Sidebar navigation items:**

1. 📊 Overview → `/dashboard`
2. 🍽️ Menu → `/dashboard/menu/categories`
3. 🪑 Tables → `/dashboard/tables`
4. 👥 Staff → `/dashboard/staff`
5. 📋 Orders → `/dashboard/orders/history`
6. ⚙️ Settings → `/dashboard/settings`
7. 🚪 Logout → `/logout`

**Responsive:** Sidebar collapses to hamburger menu on mobile (< 768px).

---

## Validation Checklist

- [ ] `/dashboard` shows today's stats and recent orders.
- [ ] Categories can be created, edited, reordered, and deleted.
- [ ] Menu items can be created with image upload, edited, and soft-deleted.
- [ ] Customization options can be added to menu items.
- [ ] Tables can be added with QR code auto-generation.
- [ ] Staff members can be added with roles.
- [ ] Order history displays with working filters and pagination.
- [ ] Settings page saves all restaurant configuration.
- [ ] Subscription limits are enforced (max tables, max items).
- [ ] All routes verify `restaurant_id` ownership (multi-tenant isolation).

---

## Strict Rules

1. **Every** database query must filter by `restaurant_id` — never query without tenant isolation.
2. **Every** POST route must validate CSRF token.
3. Image uploads must use `upload_service` — never handle files directly in routes.
4. Soft-delete menu items — never use `db.session.delete()` on `MenuItem`.
5. All forms must preserve user input on validation failure.
6. Use `flash()` for all success/error messages.
7. Subscription limits must be checked before creating tables or menu items.
8. Follow **PEP 8** and maintain consistent template formatting.
