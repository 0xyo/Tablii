# Phase 01 — Project Foundation & Configuration

## Context

You are building **Tablii**, a multi-tenant restaurant management SaaS platform using **Python / Flask**. This is Phase 1 of 12. You are setting up the project skeleton, configuration, entry point, and dependency manifest. **No models, routes, or templates yet** — only the foundational scaffolding.

---

## Exact Deliverables

Create the following files with the exact content described below. Do **not** create any files outside this list.

```
tablii/
├── app/
│   └── __init__.py
├── config.py
├── run.py
├── requirements.txt
├── .env
├── .gitignore
├── tailwind.config.js
├── package.json
└── README.md
```

---

## File-by-File Specifications

### 1. `config.py`

Create a configuration module with **three** classes:

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()
```

| Class                       | Purpose         | Key Attributes                                                                                                                                                                                                |
| --------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Config` (base)             | Shared defaults | `SECRET_KEY` from env, `SQLALCHEMY_TRACK_MODIFICATIONS = False`, `UPLOAD_FOLDER = 'app/static/images/uploads'`, `MAX_CONTENT_LENGTH = 5 * 1024 * 1024`, `ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}` |
| `DevelopmentConfig(Config)` | Local dev       | `DEBUG = True`, `SQLALCHEMY_DATABASE_URI` from env defaulting to `sqlite:///dev.db`                                                                                                                           |
| `ProductionConfig(Config)`  | Production      | `DEBUG = False`, `SQLALCHEMY_DATABASE_URI` from env (no default — must be set), `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`                           |

Add a dictionary at module level:

```python
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
```

**Constraints:**

- Every secret **must** come from `os.environ.get()` or `os.environ[]`. Never hardcode secrets.
- Use `os.environ.get('SECRET_KEY', 'dev-fallback-change-me')` only in the base `Config`.

---

### 2. `app/__init__.py` — Application Factory

Implement the **factory pattern**. The function signature must be:

```python
def create_app(config_name=None):
```

**Steps inside `create_app`:**

1. Determine `config_name` from the argument, falling back to `os.environ.get('FLASK_ENV', 'development')`.
2. Create a `Flask(__name__)` instance.
3. Load configuration from `config_by_name[config_name]`.
4. Initialize extensions (only declare them — do **not** import models yet):
   - `db = SQLAlchemy()`
   - `migrate = Migrate()`
   - `login_manager = LoginManager()`
   - `socketio = SocketIO()`
   - `csrf = CSRFProtect()`
5. Call `db.init_app(app)`, `migrate.init_app(app, db)`, `login_manager.init_app(app)`, `socketio.init_app(app, cors_allowed_origins="*")`, `csrf.init_app(app)`.
6. Set `login_manager.login_view = 'auth.login'` and `login_manager.login_message_category = 'warning'`.
7. Ensure the upload folder exists: `os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)`.
8. Return `app`.

**Constraints:**

- Declare extensions (`db`, `migrate`, `login_manager`, `socketio`, `csrf`) at **module level** so other modules can import them via `from app import db`.
- Do **not** register any blueprints in this phase. Leave a clearly marked comment: `# === Register Blueprints (Phase 4+) ===`.
- Do **not** import any model files. Leave a comment: `# === Import models here after Phase 2 ===`.

---

### 3. `run.py` — Entry Point

```python
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

**Constraints:**

- Use `socketio.run()`, not `app.run()`, to enable WebSocket support.
- Do not add any extra logic here.

---

### 4. `requirements.txt`

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-Login==0.6.3
Flask-SocketIO==5.3.6
Flask-WTF==1.2.1
python-dotenv==1.0.0
Werkzeug==3.0.1
SQLAlchemy==2.0.23
alembic==1.13.0
eventlet==0.35.1
Pillow==10.1.0
qrcode==7.4.2
gunicorn==21.2.0
psycopg2-binary==2.9.9
email-validator==2.1.0
```

**Constraints:**

- Pin **every** dependency to an exact version.
- Include `psycopg2-binary` for PostgreSQL and `eventlet` for SocketIO async support.

---

### 5. `.env` (Template)

```env
# === Tablii Environment Variables ===
SECRET_KEY=change-me-to-a-random-string
DATABASE_URL=sqlite:///dev.db
FLASK_ENV=development

# Payment gateway (Phase 9)
FLOUCI_APP_TOKEN=
FLOUCI_APP_SECRET=

# Upload limits
MAX_CONTENT_LENGTH=5242880
```

**Constraints:**

- This file must be listed in `.gitignore`.
- Never commit real secrets.

---

### 6. `.gitignore`

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
venv/
.venv/

# Environment
.env

# Flask
instance/

# Uploads
app/static/images/uploads/

# Node / Tailwind
node_modules/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Database
*.db
```

---

### 7. `tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        arabic: ["Cairo", "sans-serif"],
      },
    },
  },
  plugins: [],
};
```

---

### 8. `package.json`

```json
{
  "name": "tablii",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build:css": "npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --minify",
    "watch:css": "npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --watch"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0"
  }
}
```

---

### 9. `README.md`

Write a concise README containing:

- **Project name**: Tablii
- **One-line description**: Multi-tenant restaurant ordering & management platform.
- **Tech stack bullet list**: Flask, SQLAlchemy, PostgreSQL, Flask-SocketIO, Tailwind CSS, Jinja2.
- **Quick start** section with commands: `pip install -r requirements.txt`, `flask db upgrade`, `python run.py`.
- **Environment variables** reference table pointing to `.env`.

---

## Validation Checklist

Before considering this phase complete, verify:

- [ ] `python run.py` starts without import errors (the app may 404 on all routes — that is expected).
- [ ] `from app import db, socketio, login_manager` works from a Python shell inside the project directory.
- [ ] `config.py` does not contain any hardcoded secrets.
- [ ] `.gitignore` excludes `.env`, `__pycache__/`, `node_modules/`, and upload directories.
- [ ] `requirements.txt` has exact version pins for every dependency.

---

## Strict Rules

1. **Do not** create any database models, routes, templates, or static files in this phase.
2. **Do not** install or use any dependency not listed in `requirements.txt`.
3. **Do not** use Flask's built-in server — always use `socketio.run()`.
4. **Do not** hardcode any secret, API key, or database URL.
5. Follow **PEP 8** formatting strictly.
6. Every file must have a module-level docstring describing its purpose.
