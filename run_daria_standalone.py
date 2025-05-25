#!/usr/bin/env python3
"""
Standalone DARIA Interview API
This is a self-contained version that doesn't rely on the original run_interview_api.py
"""

import os
import sys
import json
import uuid
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room

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

def save_interview(session_id: str, interview_data: Dict[str, Any]) -> bool:
    """Save interview data to file."""
    try:
        file_path = DATA_DIR / f"{session_id}.json"
        with open(file_path, 'w') as f:
            json.dump(interview_data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
        return False

def load_interview(session_id: str) -> Optional[Dict[str, Any]]:
    """Load interview data from file."""
    try:
        file_path = DATA_DIR / f"{session_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading interview: {str(e)}")
        return None

def get_all_interviews() -> List[Dict[str, Any]]:
    """Get list of all interviews."""
    interviews = []
    try:
        for file_path in DATA_DIR.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    interviews.append(data)
            except Exception as e:
                logger.error(f"Error loading interview {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing interviews: {str(e)}")
    return interviews

# Routes
@app.route('/')
def home():
    """Home page."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page."""
    interviews = get_all_interviews()
    return render_template('dashboard.html', interviews=interviews)

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/sessions')
def get_sessions():
    """Get all interview sessions."""
    interviews = get_all_interviews()
    return jsonify(interviews)

@app.route('/api/interview/start', methods=['POST'])
def start_interview():
    """Start a new interview session."""
    try:
        data = request.json or {}
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Create new interview data
        interview_data = {
            'session_id': session_id,
            'title': data.get('title', 'Untitled Interview'),
            'status': 'active',
            'created_at': datetime.datetime.now().isoformat(),
            'conversation_history': []
        }
        
        # Save interview data
        if save_interview(session_id, interview_data):
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': "Hello! How can I help you today?"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Failed to save interview data"
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/interview/<session_id>/message', methods=['POST'])
def add_message(session_id):
    """Add a message to the interview."""
    try:
        data = request.json or {}
        message = data.get('message', '')
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({
                'success': False,
                'error': "Interview not found"
            }), 404
            
        # Add message to history
        if 'conversation_history' not in interview_data:
            interview_data['conversation_history'] = []
            
        interview_data['conversation_history'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Save updated interview data
        if save_interview(session_id, interview_data):
            return jsonify({
                'success': True,
                'message': "Message added successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Failed to save message"
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

@socketio.on('join')
def handle_join(data):
    """Handle client joining a room."""
    room = data.get('room')
    if room:
        join_room(room)
        logger.info(f"Client joined room: {room}")

@socketio.on('leave')
def handle_leave(data):
    """Handle client leaving a room."""
    room = data.get('room')
    if room:
        leave_room(room)
        logger.info(f"Client left room: {room}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DARIA Interview API')
    parser.add_argument('--port', type=int, default=5025, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    print(f"Starting DARIA Interview API on port {args.port}")
    print(f"Health check endpoint: http://127.0.0.1:{args.port}/api/health")
    print(f"Dashboard: http://127.0.0.1:{args.port}/dashboard")
    print(f"API docs: http://127.0.0.1:{args.port}/static/api_docs.html")
    
    socketio.run(app, host='0.0.0.0', port=args.port, debug=args.debug) 