# Phase 04 — Authentication & Authorization System

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS (Flask). This is **Phase 4 of 12**. Phases 1–3 are complete: the project has models, migrations, utilities, and base services.

**In this phase you will**: implement the authentication system (login, register, logout) for both restaurant owners and staff users, register blueprints, and create auth templates.

---

## Prerequisites (already done)

- `User` and `StaffUser` models with `set_password()` / `check_password()`.
- `login_manager` initialized with `login_view='auth.login'`.
- `@role_required`, `@restaurant_required` decorators available.
- CSRF protection via Flask-WTF.

---

## Exact Deliverables

```
app/
├── routes/
│   ├── __init__.py           # Blueprint registration helper
│   └── auth.py               # Auth blueprint
│
└── templates/
    ├── base.html              # Master template
    └── auth/
        ├── login.html
        └── register.html
```

Also **update** `app/__init__.py` to register the auth blueprint.

---

## File-by-File Specifications

### 1. `routes/__init__.py`

```python
"""Blueprint registration utility."""


def register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Future blueprints will be registered here in later phases
```

---

### 2. `routes/auth.py`

Create a blueprint named `auth` with `url_prefix=''` (no prefix — auth routes are top-level).

```python
auth_bp = Blueprint('auth', __name__)
```

#### Routes to implement:

##### `GET /login`

- If user is already authenticated → redirect to `/dashboard`.
- Render `auth/login.html` with a `login_type` query parameter (default `'owner'`).
- The template must show two tabs: "Owner Login" and "Staff Login".

##### `POST /login`

- Accept form fields: `login_type`, `email` (for owner) or `username` + `restaurant_slug` (for staff), `password`.
- **Owner login flow**:
  1. Query `User.query.filter_by(email=email).first()`.
  2. If not found or `check_password` fails → flash error "Invalid email or password", redirect to login.
  3. If `not user.is_active` → flash error "Account is deactivated".
  4. On success → `login_user(user)` → redirect to `/dashboard`.
- **Staff login flow**:
  1. Query restaurant by slug.
  2. Query `StaffUser.query.filter_by(restaurant_id=restaurant.id, username=username).first()`.
  3. Validate password.
  4. If `not staff.is_active` → flash error.
  5. On success → `login_user(staff)` → redirect based on role:
     - `'cashier'` → `/cashier/orders`
     - `'kitchen'` → `/kitchen`
     - `'waiter'` → `/waiter/tables`

**Security requirements:**

- Rate limit: track failed attempts in session. After 5 failures within 15 minutes → flash "Too many login attempts. Please wait." and reject.
- Always use `check_password_hash` — never compare plaintext.
- Use `flash()` with category `'error'` for failures, `'success'` for success.

##### `GET /register`

- If user is already authenticated → redirect to `/dashboard`.
- Render `auth/register.html`.

##### `POST /register`

- Accept form fields: `name`, `email`, `phone`, `password`, `confirm_password`, `restaurant_name`.
- **Validation steps** (in order):
  1. All required fields present and non-empty.
  2. `validate_email(email)` passes.
  3. `validate_phone(phone)` passes (if provided).
  4. Password length ≥ 8 characters.
  5. `password == confirm_password`.
  6. Email not already registered: `User.query.filter_by(email=email).first() is None`.
- **On validation success**:
  1. Create `User` with `role='owner'`.
  2. Call `user.set_password(password)`.
  3. Create `Restaurant` with `owner_id=user.id`, `slug=generate_slug(restaurant_name)`.
  4. Create default `Subscription(restaurant_id=restaurant.id, plan='free')`.
  5. Create default `OperatingHours` for all 7 days (Mon–Sun, open 09:00–23:00, `is_closed=False`).
  6. `db.session.add_all(...)`, `db.session.commit()`.
  7. `login_user(user)`.
  8. Redirect to `/dashboard`.
- **On failure**: flash each error, re-render form with submitted values preserved.

##### `GET /logout`

- Call `logout_user()`.
- Flash "You have been logged out." with category `'info'`.
- Redirect to `/login`.

---

### 3. Update `app/__init__.py`

Inside `create_app()`, add after extension initialization:

```python
from app.routes import register_blueprints
register_blueprints(app)
```

**Also** configure the login manager to handle both user types:

```python
@login_manager.user_loader
def load_user(user_id):
    # Try User first, then StaffUser
    user = User.query.get(int(user_id))
    if user:
        return user
    return StaffUser.query.get(int(user_id))
```

> **Important:** Remove the `@login_manager.user_loader` from `models/user.py` since it is now in `__init__.py`. The loader must handle both `User` and `StaffUser`.

**Problem with conflicting IDs:** Since `User` and `StaffUser` are in separate tables, their IDs can overlap (both could have id=1). Solve this by storing a prefixed session ID:

```python
# In User model, add:
def get_id(self):
    return f"user_{self.id}"

# In StaffUser model, add:
def get_id(self):
    return f"staff_{self.id}"

# User loader:
@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('user_'):
        return User.query.get(int(user_id.split('_')[1]))
    elif user_id.startswith('staff_'):
        return StaffUser.query.get(int(user_id.split('_')[1]))
    return None
```

---

### 4. `templates/base.html`

This is the **master template** used by all pages.

```html
<!DOCTYPE html>
<html lang="fr" dir="ltr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{% block title %}Tablii{% endblock %}</title>

    <!-- Tailwind CSS (compiled) -->
    <link
      rel="stylesheet"
      href="{{ url_for('static', filename='css/output.css') }}"
    />

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Cairo:wght@400;600;700&display=swap"
      rel="stylesheet"
    />

    <!-- PWA -->
    <link
      rel="manifest"
      href="{{ url_for('static', filename='manifest.json') }}"
    />
    <meta name="theme-color" content="#f97316" />

    {% block head %}{% endblock %}
  </head>
  <body class="font-sans bg-gray-50 text-gray-900 antialiased">
    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %} {% if
    messages %}
    <div id="flash-messages" class="fixed top-4 right-4 z-50 space-y-2">
      {% for category, message in messages %}
      <div
        class="flash-msg px-4 py-3 rounded-lg shadow-lg text-white text-sm
                {% if category == 'error' %}bg-red-500
                {% elif category == 'success' %}bg-green-500
                {% elif category == 'warning' %}bg-yellow-500 text-gray-900
                {% else %}bg-blue-500{% endif %}"
        role="alert"
      >
        {{ message }}
      </div>
      {% endfor %}
    </div>
    {% endif %} {% endwith %} {% block content %}{% endblock %}

    <!-- Socket.IO (loaded on every page, connected only where needed) -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>

    <!-- Global JS utilities -->
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>

    {% block scripts %}{% endblock %}

    <script>
      // Auto-dismiss flash messages after 5 seconds
      setTimeout(() => {
        document.querySelectorAll(".flash-msg").forEach((el) => {
          el.style.transition = "opacity 0.5s";
          el.style.opacity = "0";
          setTimeout(() => el.remove(), 500);
        });
      }, 5000);
    </script>
  </body>
</html>
```

---

### 5. `templates/auth/login.html`

Extend `base.html`. Build a **centered card layout** with:

- Tablii logo/title at the top.
- Two tab buttons: "Owner" and "Staff" that toggle which form is visible.
- **Owner form** fields: `email` (type email, required), `password` (type password, required), submit button.
- **Staff form** fields: `restaurant_slug` (text, required, placeholder "Restaurant ID"), `username` (text, required), `password` (type password, required), submit button.
- Both forms POST to `/login` with a hidden field `login_type` set to `'owner'` or `'staff'`.
- Link to register page: "Don't have an account? Register here".
- All inputs must have `id` attributes and associated `<label>` elements.
- Add CSRF token to both forms: `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.

**Styling requirements:**

- Card with white background, rounded corners, shadow.
- Primary orange color (`#f97316`) for buttons and active tab.
- Responsive: full width on mobile, max-width 400px on desktop.

---

### 6. `templates/auth/register.html`

Extend `base.html`. Build a **centered card layout** with:

- Title: "Create your restaurant".
- Fields: `name` (text), `email` (email), `phone` (tel), `restaurant_name` (text), `password` (password), `confirm_password` (password).
- All fields required except `phone`.
- Submit button: "Create Account".
- Link to login page: "Already have an account? Login here".
- CSRF token included.
- If form was submitted with errors, preserve the submitted values in the input fields using Jinja2 `value="{{ request.form.get('name', '') }}"`.

---

### 7. `static/css/input.css`

Create the Tailwind source file:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    font-family: "Inter", sans-serif;
  }

  [dir="rtl"] body {
    font-family: "Cairo", sans-serif;
  }
}

@layer components {
  .btn-primary {
    @apply bg-orange-500 hover:bg-orange-600 text-white font-medium py-2.5 px-6 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-orange-300;
  }

  .btn-secondary {
    @apply bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2.5 px-6 rounded-lg transition-colors duration-200;
  }

  .btn-danger {
    @apply bg-red-500 hover:bg-red-600 text-white font-medium py-2.5 px-6 rounded-lg transition-colors duration-200;
  }

  .input-field {
    @apply w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-orange-500 transition-colors;
  }

  .card {
    @apply bg-white rounded-xl shadow-sm border border-gray-100 p-6;
  }
}
```

---

### 8. `static/js/app.js`

Create a minimal global utility file:

```javascript
/**
 * Tablii — Global JavaScript Utilities
 */

/**
 * Display a toast notification.
 * @param {string} message - The message to display.
 * @param {string} type - 'success' | 'error' | 'info' | 'warning'
 */
function showToast(message, type = "info") {
  const colors = {
    success: "bg-green-500",
    error: "bg-red-500",
    warning: "bg-yellow-500 text-gray-900",
    info: "bg-blue-500",
  };
  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm ${colors[type] || colors.info}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = "opacity 0.5s";
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}

/**
 * Format a number as Tunisian Dinar currency.
 * @param {number} amount
 * @returns {string}
 */
function formatCurrency(amount) {
  return `${parseFloat(amount).toFixed(3)} TND`;
}

/**
 * Smooth scroll to top of page.
 */
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}
```

---

## Validation Checklist

- [ ] `GET /login` renders the login page without errors.
- [ ] `POST /register` with valid data creates a User, Restaurant, Subscription, and OperatingHours, then redirects to `/dashboard` (which will 404 — that is expected at this phase).
- [ ] `POST /login` with valid owner credentials logs in and redirects.
- [ ] `POST /login` with invalid credentials shows a flash error and stays on login page.
- [ ] `GET /logout` logs out and redirects to `/login`.
- [ ] CSRF token is present in all forms.
- [ ] Flash messages appear and auto-dismiss after 5 seconds.
- [ ] The `User.get_id()` / `StaffUser.get_id()` prefix mechanism works correctly with `load_user()`.

---

## Strict Rules

1. **Do not** create routes for dashboard, customer, cashier, kitchen, waiter, or admin — those are later phases.
2. **Do not** bypass CSRF protection on any POST route.
3. **Never** store passwords in plaintext — always use `generate_password_hash`.
4. All form validation must happen **server-side**. Client-side validation is optional extra.
5. Use `flash()` for all user-facing messages — never render errors inline without also flashing.
6. All database writes must be wrapped in a try/except with `db.session.rollback()` on failure.
7. Follow **PEP 8** for Python and use proper HTML5 semantics in templates.
