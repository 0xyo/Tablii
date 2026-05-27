# Tablii

Tablii is a restaurant ordering and management platform built with Flask. It lets customers order from QR menus, while restaurant staff handle orders, kitchen workflow, payments, tables, and analytics in real time.

## Features

- QR code menu for customer ordering
- Real-time order updates with Socket.IO
- Owner dashboard for menu, staff, tables, orders, settings, and analytics
- Staff interfaces for cashier, kitchen, and waiter roles
- Super-admin area for restaurants and subscriptions
- Multilingual menu support
- Flouci payment integration
- PWA assets and service worker support

## Tech Stack

- Python 3.11
- Flask, SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF
- Flask-SocketIO with eventlet
- Jinja templates
- Tailwind CSS
- SQLite for local development
- PostgreSQL for production
- Render deployment with `render.yaml`

## Project Structure

```text
app/                 Flask application code
app/models/          Database models
app/routes/          Web and API routes
app/services/        Business logic
app/templates/       Jinja templates
app/static/          CSS, JavaScript, images, icons, and sounds
migrations/          Alembic database migrations
tests/               Pytest test suite
docs/                API, backend, frontend, and screenshot documentation
run.py               Local application entry point
seed.py              Demo data seeding script
```

## Local Setup

Use PowerShell from the project root.

```powershell
git clone git@github.com:0xyo/Tablii.git
cd Tablii

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
npm install

Copy-Item .env.example .env
npm run build:css

flask db upgrade
python seed.py
python run.py
```

Open `http://127.0.0.1:5000`.

If PowerShell blocks the virtual environment activation, run this once in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Environment

Copy `.env.example` to `.env` and fill in the values you need.

```env
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///dev.db
FLOUCI_APP_TOKEN=
FLOUCI_APP_SECRET=
```

## Demo Accounts

After running `python seed.py`, use these local accounts:

| Role | Login |
| --- | --- |
| Super admin | `superadmin@tablii.com` / `admin1234` |
| Owner | `owner@tablii.com` / `owner1234` |
| Cashier | `caisse1` / `staff1234` |
| Waiter | `serveur1` / `staff1234` |
| Kitchen | `cuisine1` / `staff1234` |

Staff users belong to the restaurant slug `chez-ahmed`.

## Useful Commands

```powershell
npm run build:css
npm run watch:css
pytest tests/
flask db upgrade
python seed.py
python run.py
```

## Documentation

- [Backend overview](./docs/BACKEND.md)
- [API reference](./docs/API.md)
- [Frontend report](./docs/FRONTEND_REPORT.md)
- [Screenshots](./docs/screenshots)

## Deployment

This project includes `render.yaml` for Render.

1. Push the repository to GitHub.
2. Create a new Render Blueprint from the repository.
3. Add `FLOUCI_APP_TOKEN` and `FLOUCI_APP_SECRET`.
4. Deploy.
