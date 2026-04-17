# Phase 05 — Customer-Facing Interface

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS (Flask). This is **Phase 5 of 12**. Phases 1–4 are complete: the project has models, utilities, services, authentication, and the base template.

**In this phase you will**: build the entire customer-facing experience — the pages a restaurant patron sees after scanning a QR code on their table.

---

## Prerequisites (already done)

- All models: `Restaurant`, `Category`, `MenuItem`, `Table`, `TableSession`, `Order`, `OrderItem`, `Customer`, `Review`, `WaiterCall`.
- `generate_random_token()`, `generate_order_number()`, `format_currency()` helpers.
- `base.html` master template with Tailwind CSS and flash messages.

---

## Exact Deliverables

```
app/
├── routes/
│   └── customer.py              # Customer blueprint
│
├── services/
│   └── order_service.py         # Order creation & calculation (partial — status updates in Phase 7)
│
├── templates/
│   └── customer/
│       ├── base_customer.html   # Customer layout
│       ├── menu.html            # Menu page
│       ├── cart.html            # Cart page
│       ├── checkout.html        # Checkout page
│       ├── order_tracking.html  # Order tracking page
│       ├── call_waiter.html     # Call waiter modal/page
│       └── review.html          # Leave a review page
│
└── static/
    └── js/
        ├── cart.js              # Cart management (localStorage)
        └── order_tracking.js    # Order status tracking (WebSocket)
```

Also update `routes/__init__.py` to register the customer blueprint.

---

## Route Specifications

### Blueprint Setup

```python
customer_bp = Blueprint('customer', __name__, url_prefix='')
```

> **No authentication required** for customer routes — customers are anonymous (identified by session token).

---

### Route 1: `GET /r/<slug>/table/<int:table_id>` — Menu Page

**Logic:**

1. Query `Restaurant.query.filter_by(slug=slug, is_active=True).first_or_404()`.
2. Query `Table.query.filter_by(id=table_id, restaurant_id=restaurant.id).first_or_404()`.
3. Check or create a `TableSession`:
   - Look for existing active session for this table: `TableSession.query.filter_by(table_id=table_id, is_active=True).first()`.
   - If none → create a new one with `session_token=generate_random_token()`, set table `status='occupied'`.
4. Store `session_token` in the user's browser session: `session['session_token'] = table_session.session_token`.
5. Query categories and menu items:
   - `categories = Category.query.filter_by(restaurant_id=restaurant.id, is_active=True).order_by(Category.sort_order).all()`
   - For each category, eager-load items where `is_available=True` and `deleted_at is None`.
   - If `restaurant.ramadan_mode` is True, filter categories by `ramadan_type`.
6. Render `customer/menu.html` with `restaurant`, `table`, `categories`, `session_token`.

**Template requirements (`menu.html`):**

- Header: restaurant name, logo, table number badge.
- Search bar at top (client-side filtering via JavaScript).
- Horizontal scrollable category tabs.
- Grid of menu item cards for each category:
  - Item image (or default placeholder).
  - Item name (use `name_fr` as default).
  - Price formatted with `format_currency`.
  - "Add" button.
- Clicking an item opens a **modal** showing:
  - Large image
  - Full description
  - Customization options (if any) — radio buttons for `single`, checkboxes for `multiple`.
  - Quantity selector (−/+).
  - "Add to cart" button.
- Floating bottom bar: cart icon with item count badge + total price.
- **Mobile-first design**: optimized for phone screens.

---

### Route 2: `GET /r/<slug>/table/<int:table_id>/cart` — Cart Page

**Logic:**

- Render `customer/cart.html` with `restaurant`, `table`, `session_token`.
- Cart data is managed entirely in JavaScript (`localStorage`).

**Template requirements (`cart.html`):**

- List of cart items with: image, name, selected options, quantity (+/−), unit price, line total.
- "Remove" button per item.
- Special notes text area.
- Summary: subtotal, tax (calculated from `restaurant.tax_rate`), total.
- "Checkout" button → links to checkout page.
- "Back to menu" link.
- If cart is empty → show message with link back to menu.

---

### Route 3: `GET /r/<slug>/table/<int:table_id>/checkout` — Checkout Page

**Logic:**

- Render `customer/checkout.html`.

**Template requirements (`checkout.html`):**

- Order summary (items, quantities, options, prices).
- Payment method selection:
  - "Pay at counter (Cash)" — always available.
  - "Pay online" — only if `restaurant.online_payment` is True.
- "Confirm Order" button.
- CSRF token embedded.

---

### Route 4: `POST /r/<slug>/table/<int:table_id>/order` — Place Order

**Logic:**

1. Parse JSON body: `items` (array of `{menu_item_id, quantity, selected_options, notes}`), `payment_method`, `special_notes`.
2. Validate session token from browser session.
3. Call `order_service.create_order(session_id, items, payment_method, special_notes, restaurant)`.
4. Return JSON: `{success: true, order_id, order_number, total_amount}`.

**The `order_service.create_order()` function must:**

1. Validate every `menu_item_id` exists and belongs to `restaurant_id`.
2. Validate `quantity >= 1` and `quantity <= 20`.
3. Calculate `unit_price` = item base price + sum of selected option extra prices.
4. Calculate `total_price` = `unit_price * quantity`.
5. Calculate `subtotal` = sum of all `total_price` values.
6. Calculate `tax_amount` = `subtotal * (restaurant.tax_rate / 100)`.
7. Calculate `total_amount` = `subtotal + tax_amount`.
8. Generate `order_number` via `generate_order_number()`.
9. Create `Order` and all `OrderItem` records.
10. If `restaurant.auto_accept` is True → set `status='accepted'` and `accepted_at=now`.
11. Commit to database.
12. Return the created `Order` object.

**Error handling:** If any item is invalid → rollback and return `{success: false, error: "..."}` with status 400.

---

### Route 5: `GET /r/<slug>/table/<int:table_id>/track/<int:order_id>` — Order Tracking

**Logic:**

1. Query the order: `Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first_or_404()`.
2. Render `customer/order_tracking.html`.

**Template requirements (`order_tracking.html`):**

- Order number displayed prominently.
- Visual status timeline with steps: New → Accepted → Preparing → Ready → Served.
- Current step highlighted with animation (pulsing dot).
- Timestamps for each completed step.
- Item list (read-only).
- Total amount.
- JavaScript WebSocket listener to update status in real-time (details in Phase 8).

---

### Route 6: `POST /r/<slug>/table/<int:table_id>/call-waiter` — Call Waiter

**Logic:**

1. Parse JSON body: `call_type` (required), `message` (optional).
2. Validate `call_type` is one of: `'water'`, `'bill'`, `'help'`, `'custom'`.
3. Create `WaiterCall` record.
4. Return JSON `{success: true}`.
5. _(WebSocket notification will be added in Phase 8.)_

**Template requirements (`call_waiter.html`):**

- Grid of quick-action buttons with icons: 💧 Water, 🧾 Bill, 🆘 Help.
- Text input for custom message.
- Submit button.

---

### Route 7: `GET /r/<slug>/table/<int:table_id>/review/<int:order_id>` — Leave Review

**Logic:**

1. Query the order (must belong to restaurant and have `status='served'` or `'completed'`).
2. If review already exists for this order → show "Already reviewed" message.
3. Render `customer/review.html`.

#### `POST /r/<slug>/table/<int:table_id>/review/<int:order_id>`

1. Parse form: `rating` (1–5, required), `food_rating` (1–5, optional), `service_rating` (1–5, optional), `comment` (optional), `photo` (optional file).
2. Validate rating range.
3. If photo uploaded → save via `upload_service.save_uploaded_file(file, 'reviews')`.
4. Create `Review` record.
5. Flash success, redirect to menu or a "Thank you" message.

**Template requirements (`review.html`):**

- Star rating input (clickable stars using CSS/JS — no library needed).
- Optional sub-ratings for food and service.
- Comment textarea.
- Photo upload with preview.
- Submit button.

---

## JavaScript Specifications

### `static/js/cart.js`

Implement a `Cart` class using the **module pattern** or ES6 class:

```javascript
class Cart {
    constructor(restaurantSlug, tableId) { ... }

    // Storage key: `tablii_cart_${restaurantSlug}_${tableId}`

    addItem(item)        // item = {id, name, price, quantity, options, image_url}
    removeItem(index)    // Remove by index
    updateQuantity(index, quantity)  // Update quantity, remove if 0
    getItems()           // Return array of items
    getSubtotal()        // Sum of (price + options_extra) * quantity
    getTax(taxRate)      // subtotal * (taxRate / 100)
    getTotal(taxRate)    // subtotal + tax
    getItemCount()       // Total item count
    clear()              // Empty cart
    save()               // Save to localStorage
    load()               // Load from localStorage
}
```

**Rules:**

- Auto-save after every mutation (add, remove, update).
- Auto-load on construction.
- Update the floating cart badge count whenever cart changes.

### `static/js/order_tracking.js`

```javascript
/**
 * Listen for order status updates via WebSocket.
 * Placeholder: the actual socket connection will be implemented in Phase 8.
 * For now, implement the UI update functions:
 */

function updateOrderStatus(status) { ... }
// - Highlight the correct step in the timeline.
// - Add a pulsing animation to the active step.
// - Show timestamp for each completed step.

function showStatusNotification(status) { ... }
// - Show a toast notification when status changes.
// - Play a sound if status is 'ready'.
```

---

## Customer Layout Template

### `templates/customer/base_customer.html`

```
{% extends 'base.html' %}

{% block content %}
<div class="max-w-lg mx-auto min-h-screen bg-white">
    <!-- Header -->
    <header class="sticky top-0 z-40 bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
            {% if restaurant.logo_url %}
            <img src="{{ restaurant.logo_url }}" alt="{{ restaurant.name }}" class="w-8 h-8 rounded-full object-cover">
            {% endif %}
            <h1 class="text-lg font-semibold">{{ restaurant.name }}</h1>
        </div>
        <span class="bg-orange-100 text-orange-700 text-xs font-medium px-2 py-1 rounded-full">
            Table {{ table.table_number }}
        </span>
    </header>

    <!-- Page content -->
    <main class="pb-24">
        {% block customer_content %}{% endblock %}
    </main>

    <!-- Bottom bar -->
    <nav class="fixed bottom-0 left-0 right-0 max-w-lg mx-auto bg-white border-t border-gray-100 px-4 py-3 flex items-center justify-between">
        {% block bottom_bar %}{% endblock %}
    </nav>
</div>
{% endblock %}
```

---

## Validation Checklist

- [ ] Scanning a QR code URL (`/r/my-restaurant/table/1`) shows the restaurant menu.
- [ ] Adding items to cart persists in localStorage.
- [ ] Cart page shows correct items, quantities, and calculated totals.
- [ ] Submitting an order creates `Order` and `OrderItem` records in the database.
- [ ] Order tracking page shows the correct status timeline.
- [ ] Call waiter creates a `WaiterCall` record.
- [ ] Review submission creates a `Review` record.
- [ ] All customer routes work **without authentication** (anonymous access).
- [ ] Category tabs filter menu items correctly.
- [ ] Search bar filters items by name (client-side).

---

## Strict Rules

1. **Do not** require login for any customer route — customers are anonymous.
2. **Do not** expose restaurant admin data to customers (e.g., staff info, analytics).
3. **Always** validate that menu items belong to the correct restaurant (multi-tenant isolation).
4. Cart data lives **only** in `localStorage` — never stored server-side before order submission.
5. All prices must be calculated **server-side** when creating orders — never trust client-sent totals.
6. Use semantic HTML: `<main>`, `<header>`, `<nav>`, `<section>`, `<article>`.
7. Mobile-first responsive design — optimize for 375px width.
8. Follow **PEP 8** for Python and use consistent Jinja2 formatting.
