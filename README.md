# 🍽️ Tablii

> Multi-tenant restaurant ordering & management platform.

## Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy 2.0, Flask-Migrate
- **Auth**: Flask-Login (dual owner/staff login)
- **Real-time**: Flask-SocketIO with eventlet
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Jinja2 templates, Tailwind CSS 3.4
- **Payments**: Flouci (Tunisian gateway)
- **Deployment**: Render.com

## Quick Start

```bash
# 1. Clone the repo
git clone git@github.com:0xyo/Tablii.git
cd Tablii

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Tailwind CSS
npm install

# 5. Build CSS
npm run build:css

# 6. Set up environment variables
cp .env.example .env  # Edit with your values

# 7. Initialize database
flask db upgrade

# 8. Run the app
python run.py
```

The app will be available at `http://localhost:5000`.

## Environment Variables

| Variable             | Description                                | Default                  |
| -------------------- | ------------------------------------------ | ------------------------ |
| `SECRET_KEY`         | Flask secret key                           | `dev-fallback-change-me` |
| `DATABASE_URL`       | Database connection URI                    | `sqlite:///dev.db`       |
| `FLASK_ENV`          | Environment (`development` / `production`) | `development`            |
| `FLOUCI_APP_TOKEN`   | Flouci payment token                       | —                        |
| `FLOUCI_APP_SECRET`  | Flouci payment secret                      | —                        |
| `MAX_CONTENT_LENGTH` | Max upload size (bytes)                    | `5242880`                |

## License

MIT
