import os
from flask import Flask
import uuid

# Force skip eventlet
os.environ['SKIP_EVENTLET'] = '1'

# Import the app after setting environment variables
from app import app

try:
    # Try to import Flask-Session
    from flask_session import Session
    
    # Configure server-side sessions
    app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in files instead of cookies
    app.config['SESSION_FILE_DIR'] = 'flask_sessions'  # Directory for session files
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', str(uuid.uuid4()))  # Ensure secret key is set
    
    # Create sessions directory if it doesn't exist
    os.makedirs('flask_sessions', exist_ok=True)
    
    # Initialize the session extension
    Session(app)
    print("Using server-side session storage")
except ImportError:
    print("Warning: Flask-Session not installed. Using cookie-based sessions with limited size.")
    # Set a larger cookie size limit as a fallback
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

if __name__ == '__main__':
    print("Starting minimal Flask server on port 5003...")
    app.run(host='127.0.0.1', port=5003, debug=True) 