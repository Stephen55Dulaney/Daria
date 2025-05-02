import os
import uuid
import tempfile
import sys
from pathlib import Path
from flask import Flask
from flask_session import Session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Force skip eventlet
os.environ['SKIP_EVENTLET'] = '1'

# Create necessary directories for prompt management
prompt_dir = Path('daria_interview_tool/prompts')
prompt_history_dir = Path('daria_interview_tool/prompt_history')

prompt_dir.mkdir(exist_ok=True)
prompt_history_dir.mkdir(exist_ok=True)

# Import the app after setting environment variables
from daria_interview_tool import create_app

# Create the app instance
app = create_app()

# Configure server-side session storage
app.config.update(
    # Use filesystem session storage
    SESSION_TYPE='filesystem',
    # Store sessions in temp directory to avoid permission issues
    SESSION_FILE_DIR=tempfile.gettempdir(),
    # Don't use permanent sessions
    SESSION_PERMANENT=False,
    # Set session lifetime
    PERMANENT_SESSION_LIFETIME=3600,
    # Force the use of server-side sessions
    SESSION_USE_SIGNER=True,
    # Set a random secret key
    SECRET_KEY=os.environ.get('SECRET_KEY', str(uuid.uuid4())),
    # Disable browser cookies for sessions
    SESSION_COOKIE_SECURE=False,
    # Make session cookie smaller by only storing session ID
    SESSION_COOKIE_HTTPONLY=True
)

# Initialize the session extension
Session(app)

# Disable reloader to avoid issues with sessions
if __name__ == '__main__':
    port = 5009
    print(f"Starting Flask application with server-side sessions on port {port}...")
    
    # Try to run the app, catch port conflicts and suggest alternatives
    try:
        app.run(host='127.0.0.1', port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} is already in use.")
            print("Try running with a different port:")
            print(f"python {sys.argv[0]} --port 5004")
            
            # Try an alternative port
            alternative_port = port + 1
            try_alternative = input(f"Would you like to try port {alternative_port} instead? (y/n): ")
            if try_alternative.lower() == 'y':
                print(f"Starting on port {alternative_port}...")
                app.run(host='127.0.0.1', port=alternative_port, debug=False)
        else:
            raise 