#!/usr/bin/env python3
"""
DARIA Interview API Wrapper
This script provides a patched version of the interview API that works with Python 3.13
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Define paths
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data" / "interviews"
SESSIONS_DIR = DATA_DIR / 'sessions'
PROMPT_DIR = BASE_DIR / "tools" / "prompt_manager" / "prompts"

# Create necessary directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
PROMPT_DIR.mkdir(parents=True, exist_ok=True)

# Configure app paths
app.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)
app.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)

# Import and run the main application
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DARIA Interview API')
    parser.add_argument('--port', type=int, default=5025, help='Port to run the server on')
    parser.add_argument('--use-langchain', action='store_true', help='Use LangChain for interviews')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--no-langchain', action='store_true', help='Disable LangChain features')
    args = parser.parse_args()
    
    try:
        # Import the main application code
        from run_interview_api import setup_routes, initialize_services
        
        # Initialize services
        initialize_services(use_langchain=args.use_langchain)
        
        # Set up routes
        setup_routes(app)
        
        # Start the server
        print(f"Starting DARIA Interview API on port {args.port}")
        print(f"Health check endpoint: http://127.0.0.1:{args.port}/api/health")
        print(f"API docs: http://127.0.0.1:{args.port}/static/api_docs.html")
        
        socketio.run(app, host='0.0.0.0', port=args.port, debug=args.debug)
        
    except Exception as e:
        logger.error(f"Failed to start DARIA: {str(e)}")
        sys.exit(1) 