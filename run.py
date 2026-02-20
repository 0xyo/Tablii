"""
Tablii entry point.

Starts the Flask application with SocketIO support.
"""
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
