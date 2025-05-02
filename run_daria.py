from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set environment variable to skip eventlet
os.environ['SKIP_EVENTLET'] = '1'

# Add error handling
try:
    from app import app

    if __name__ == '__main__':
        # Instead of using socketio.run with eventlet, use the Flask development server
        # This is a temporary fix until eventlet is compatible with Python 3.13
        host = os.environ.get('HOST', '127.0.0.1')
        port = int(os.environ.get('PORT', 5003))
        
        print(f"Starting Flask application on http://{host}:{port}")
        print("Note: WebSocket functionality will be limited without eventlet")
        
        app.run(host=host, port=port, debug=True, use_reloader=True)
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
