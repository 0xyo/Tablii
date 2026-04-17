# Phase 03 — Core Utilities & Service Helpers

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS (Flask / SQLAlchemy). This is **Phase 3 of 12**. Phases 1–2 are complete: the project skeleton exists with all database models and migrations.

**In this phase you will**: create reusable utility functions (decorators, validators, helpers) and two foundational services (QR code generation and file upload).

---

## Prerequisites (already done)

- All models exist in `app/models/`.
- `app/__init__.py` exports `db`, `login_manager`, `socketio`, `csrf`.
- Migrations are applied; the database schema is live.

---

## Exact Deliverables

```
app/
├── utils/
│   ├── __init__.py          # Empty or re-exports
│   ├── decorators.py        # Access-control decorators
│   ├── validators.py        # Input validation functions
│   └── helpers.py           # General-purpose helpers
│
└── services/
    ├── __init__.py           # Empty
    ├── qr_service.py         # QR code generation
    └── upload_service.py     # File upload handling
```

---

## File-by-File Specifications

### 1. `utils/decorators.py`

Implement **three** decorators. Each must be a properly nested function with `functools.wraps`.

#### `@role_required(*roles)`

- **Purpose**: Restrict a route to specific staff roles OR owner.
- **Logic**:
  1. Check `current_user.is_authenticated`. If not → `abort(401)`.
  2. If `current_user` is a `User` instance (owner/super_admin), check `current_user.role in roles` or `current_user.role == 'super_admin'` (super admin bypasses).
  3. If `current_user` is a `StaffUser` instance, check `current_user.role in roles`.
  4. If role check fails → `abort(403)`.
- **Usage example**: `@role_required('cashier', 'owner')`
- **Imports needed**: `from flask_login import current_user`, `from flask import abort`, `from app.models.user import User, StaffUser`.

#### `@restaurant_required`

- **Purpose**: Ensure the logged-in staff/owner is associated with a restaurant and inject `restaurant` into `g`.
- **Logic**:
  1. If `current_user` is a `User` (owner), query the first restaurant owned by them. If none → `abort(404)` with message "No restaurant found".
  2. If `current_user` is a `StaffUser`, load `current_user.restaurant`.
  3. Store the restaurant object in `g.restaurant`.
- **Imports needed**: `from flask import g`.

#### `@super_admin_required`

- **Purpose**: Restrict to super admin only.
- **Logic**: Check `current_user.is_authenticated` and `isinstance(current_user, User)` and `current_user.role == 'super_admin'`. Otherwise `abort(403)`.

---

### 2. `utils/validators.py`

Implement **four** pure functions. Each returns a tuple `(is_valid: bool, error_message: str | None)`.

#### `validate_email(email: str) -> tuple[bool, str | None]`

- Strip whitespace, lowercase.
- Use `email_validator` library: call `validate_email(email)`. If `EmailNotValidError` → return `(False, "Invalid email address")`.
- On success → return `(True, None)`.

#### `validate_phone(phone: str) -> tuple[bool, str | None]`

- Strip whitespace, remove spaces and dashes.
- Must match regex `^\+?[0-9]{8,15}$`.
- Return `(False, "Invalid phone number")` on failure.

#### `validate_price(price) -> tuple[bool, str | None]`

- Attempt conversion to `float`.
- Must be `>= 0` and have at most 2 decimal places (use `round(price, 2) == price` check; accept if `price` is an `int`).
- Return `(False, "Price must be a non-negative number with at most 2 decimal places")` on failure.

#### `sanitize_input(text: str) -> str`

- Strip leading/trailing whitespace.
- Replace multiple consecutive whitespace with single space.
- Use `markupsafe.escape()` to escape HTML entities.
- Return the cleaned string.

---

### 3. `utils/helpers.py`

Implement **four** pure/simple functions.

#### `generate_slug(name: str) -> str`

- Lowercase the name.
- Replace spaces and non-alphanumeric characters with hyphens.
- Remove consecutive hyphens.
- Strip leading/trailing hyphens.
- Append a 4-character random hex suffix: `f"{base_slug}-{secrets.token_hex(2)}"`.
- Return the result.

#### `format_currency(amount: float, currency: str = 'TND') -> str`

- Return `f"{amount:.3f} {currency}"` (Tunisian Dinar uses 3 decimal places).

#### `generate_random_token(length: int = 32) -> str`

- Return `secrets.token_urlsafe(length)`.

#### `generate_order_number() -> str`

- Generate a 4-character uppercase alphanumeric code: `'#' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))`.
- Example output: `'#A7K2'`.

---

### 4. `services/qr_service.py`

#### `generate_qr_code(data: str, filename: str) -> str`

- **Purpose**: Generate a QR code PNG image and save it.
- **Logic**:
  1. Create QR code using `qrcode` library with `box_size=10`, `border=2`.
  2. Save to `os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', filename)`.
  3. Create the `qrcodes` subdirectory if it does not exist.
  4. Return the relative URL path: `f'/static/images/uploads/qrcodes/{filename}'`.
- **Error handling**: Catch `Exception`, log the error, return `None`.

#### `get_table_url(restaurant_slug: str, table_id: int) -> str`

- **Purpose**: Build the full public URL a customer scans.
- **Logic**: Return `f"{request.host_url}r/{restaurant_slug}/table/{table_id}"`.
- **Import**: `from flask import request`.

#### `generate_table_qr(restaurant_slug: str, table_id: int, table_number: int) -> str | None`

- Combines the two functions above.
- Calls `get_table_url()` to build the URL.
- Calls `generate_qr_code(url, f"table_{restaurant_slug}_{table_number}.png")`.
- Returns the saved QR code URL or `None` on failure.

---

### 5. `services/upload_service.py`

#### `validate_image(file) -> tuple[bool, str | None]`

- Check file is not `None` and `file.filename != ''`.
- Check extension is in `current_app.config['ALLOWED_EXTENSIONS']`.
- Check file size does not exceed `current_app.config['MAX_CONTENT_LENGTH']`.
- Return `(True, None)` or `(False, "error message")`.

#### `save_uploaded_file(file, subfolder: str) -> str | None`

- **Purpose**: Safely save an uploaded file.
- **Logic**:
  1. Call `validate_image(file)`. If invalid → return `None`.
  2. Generate a secure filename: `f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"`.
  3. Save to `os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, filename)`.
  4. Create the subdirectory if needed.
  5. Return the relative URL: `f'/static/images/uploads/{subfolder}/{filename}'`.
- **Import**: `from werkzeug.utils import secure_filename`.

#### `delete_file(file_path: str) -> bool`

- Convert relative URL to absolute filesystem path.
- Check file exists. If yes → `os.remove()` → return `True`.
- If file not found → return `False`.
- Catch `OSError`, log it, return `False`.

---

## Validation Checklist

- [ ] All decorators can be imported: `from app.utils.decorators import role_required, restaurant_required, super_admin_required`.
- [ ] `validate_email("test@example.com")` returns `(True, None)`.
- [ ] `validate_email("not-an-email")` returns `(False, ...)`.
- [ ] `generate_slug("My Restaurant")` returns a lowercase hyphenated string with a hex suffix.
- [ ] `generate_order_number()` returns a string like `'#A7K2'`.
- [ ] `generate_qr_code()` creates a PNG file on disk.
- [ ] `save_uploaded_file()` saves a file and returns a URL path.

---

## Strict Rules

1. **Do not** create any routes, templates, or WebSocket events.
2. **Do not** modify any model files from Phase 2.
3. All functions must have type hints on parameters and return types.
4. All functions must have docstrings.
5. Use `current_app` (not `app`) for accessing config inside services.
6. Never trust user input — always validate/sanitize before processing.
7. Follow **PEP 8** strictly.
