from app import create_app
from app.extensions import socketio

# Create the Flask app
app = create_app()

# Export for Gunicorn
application = app

if __name__ == "__main__":
    socketio.run(app, debug=False, host="0.0.0.0", port=5000)
