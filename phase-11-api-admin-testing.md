# Phase 11 — API Endpoints, Admin Panel, Testing & Seed Data

## Context

**Tablii** — Phase 11 of 12. Build JSON API endpoints, super admin panel, tests, and seed data script.

---

## Deliverables

```
app/routes/
├── api.py                # JSON API blueprint
└── admin.py              # Super admin blueprint

app/templates/admin/
├── base_admin.html       # Admin layout
├── restaurants.html      # Restaurant management
├── subscriptions.html    # Subscription management
└── platform_analytics.html  # Platform stats

tests/
├── __init__.py
├── conftest.py           # Pytest fixtures
├── test_auth.py
├── test_orders.py
├── test_menu.py
├── test_api.py
└── test_services.py

seed.py                   # Database seeding script
```

Register `api_bp` and `admin_bp` in `routes/__init__.py`.

---

## API Blueprint (`/api`)

```python
api_bp = Blueprint('api', __name__, url_prefix='/api')
```

CSRF exempt this blueprint: `csrf.exempt(api_bp)` (API uses no session forms).

### Routes

#### `GET /api/restaurant/<slug>/menu`

Return full menu as JSON:

```json
{
    "restaurant": {"name": "...", "slug": "...", "currency": "TND"},
    "categories": [
        {
            "id": 1, "name": "...", "icon": "🍕",
            "items": [
                {"id": 1, "name": "...", "price": 12.5, "image_url": "...", "is_available": true,
                 "customizations": [
                     {"id": 1, "group_name": "Size", "type": "single", "required": true,
                      "options": [{"id": 1, "name": "Small", "extra_price": 0}, ...]}
                 ]}
            ]
        }
    ]
}
```

#### `GET /api/menu-item/<int:id>`

Return single item with customizations. Include `restaurant_id` check via query param `?restaurant_id=X`.

#### `GET /api/order/<int:id>/status`

Return `{"order_id": 1, "status": "preparing", "timestamps": {...}}`.

#### `POST /api/upload-image`

Accept multipart image upload. Require authentication (`@login_required`). Save via `upload_service`. Return `{"url": "/static/images/uploads/..."}`.

---

## Admin Blueprint (`/admin`)

```python
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
```

All routes require `@super_admin_required`.

### `GET /admin/restaurants`

List all restaurants with: name, owner email, slug, plan, is_active, created_at, order count. Paginated.

### `POST /admin/restaurants/<int:id>/toggle`

Toggle `restaurant.is_active`. Return JSON.

### `GET /admin/subscriptions`

List all subscriptions with restaurant name, plan, expires_at, is_active. Allow plan changes.

### `POST /admin/subscriptions/<int:id>/update`

Update plan, max_tables, max_items, expires_at.

### `GET /admin/analytics`

Platform-wide stats: total restaurants, total orders, total revenue, new restaurants this month, active subscriptions by plan.

---

## Admin Templates

### `base_admin.html`

Extend `base.html`. Dark sidebar with admin nav: Restaurants, Subscriptions, Analytics, Logout.

### `restaurants.html`

Table with columns: Name, Owner, Slug, Plan, Active (toggle), Created, Actions.

### `subscriptions.html`

Table with edit modals per subscription.

### `platform_analytics.html`

Stat cards + simple tables. No charts required (keep it simple).

---

## Testing (`tests/`)

### `conftest.py`

```python
import pytest
from app import create_app, db as _db

@pytest.fixture(scope='session')
def app():
    app = create_app('testing')  # Add TestingConfig to config.py
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()

@pytest.fixture
def sample_user(db):
    from app.models.user import User
    user = User(email='test@test.com', name='Test Owner', role='owner')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_restaurant(db, sample_user):
    from app.models.restaurant import Restaurant
    r = Restaurant(owner_id=sample_user.id, name='Test Resto', slug='test-resto')
    db.session.add(r)
    db.session.commit()
    return r
```

Add `TestingConfig` to `config.py`:

```python
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
```

### `test_auth.py`

- `test_register_success` — POST valid data, assert redirect + user created.
- `test_register_duplicate_email` — assert error flash.
- `test_login_valid_owner` — assert redirect to dashboard.
- `test_login_invalid_password` — assert stays on login.
- `test_logout` — assert redirect + session cleared.

### `test_orders.py`

- `test_create_order` — create order via service, verify total calculation.
- `test_order_status_transitions` — test valid transitions pass, invalid fail.
- `test_order_number_generated` — verify format `#XXXX`.

### `test_menu.py`

- `test_create_category` — verify category belongs to restaurant.
- `test_create_menu_item` — verify item creation with price.
- `test_soft_delete_item` — verify `deleted_at` is set, item not returned in active queries.

### `test_api.py`

- `test_get_menu_json` — verify JSON structure matches spec.
- `test_get_order_status` — verify response format.

### `test_services.py`

- `test_validate_email_valid` — assert `(True, None)`.
- `test_validate_email_invalid` — assert `(False, ...)`.
- `test_generate_slug` — assert format with hex suffix.
- `test_format_currency` — assert `"12.500 TND"`.

---

## `seed.py`

```python
"""Seed database with test data for development."""
from app import create_app, db
from app.models.user import User, StaffUser
from app.models.restaurant import Restaurant, Subscription, OperatingHours
from app.models.menu import Category, MenuItem
from app.models.table import Table
from datetime import time

def seed():
    app = create_app('development')
    with app.app_context():
        # Create owner
        owner = User(email='owner@tablii.com', name='Ahmed Owner', role='owner')
        owner.set_password('password123')
        db.session.add(owner)
        db.session.flush()

        # Create restaurant
        restaurant = Restaurant(
            owner_id=owner.id, name='Chez Ahmed',
            slug='chez-ahmed', description='Cuisine tunisienne authentique',
            city='Tunis', currency='TND', tax_rate=7.0, auto_accept=False
        )
        db.session.add(restaurant)
        db.session.flush()

        # Subscription, operating hours, staff, categories, items, tables
        # ... (create 3 staff, 4 categories, 15 menu items, 8 tables)

        db.session.commit()
        print('✅ Database seeded successfully!')

if __name__ == '__main__':
    seed()
```

Create realistic Tunisian restaurant data: categories (Entrées, Plats, Desserts, Boissons), items with Arabic/French names, prices in TND.

---

## Validation

- [ ] `pytest tests/` passes all tests.
- [ ] `python seed.py` populates database without errors.
- [ ] `GET /api/restaurant/chez-ahmed/menu` returns valid JSON.
- [ ] Admin panel lists seeded restaurant.
- [ ] API endpoints are CSRF-exempt.
- [ ] TestingConfig uses in-memory SQLite.

## Strict Rules

1. API responses must always return valid JSON with consistent structure.
2. Admin routes must use `@super_admin_required` — never `@role_required('owner')`.
3. Tests must be independent — each test must work in isolation.
4. Seed script must be idempotent — running twice should not crash.
5. Never test with the production database.
6. All test assertions must be specific — no bare `assert response.status_code == 200`.
