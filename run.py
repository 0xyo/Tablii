"""
Tablii entry point.

Starts the Flask application with SocketIO support.
Uses threading mode which is reliable on Windows.
"""
from app import create_app, db, socketio

app = create_app()

# Ensure all database tables exist before serving (safe for first run)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(
        app,
        debug=True,
        host='127.0.0.1',
        port=5000,
        use_reloader=False,       # avoids the double-bind issue on Windows
        allow_unsafe_werkzeug=True,
    )
