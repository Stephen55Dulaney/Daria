#!/usr/bin/env python3
"""
DARIA Prompt Manager and LangChain Integration

This script runs a simplified version of the DARIA Interview Tool
focusing on prompt management and evaluation capabilities.
"""

import os
import sys
import json
import time
import uuid
import logging
import datetime
import argparse
from pathlib import Path
from flask import Flask, redirect, render_template, url_for, request, jsonify, Response
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure SKIP_EVENTLET is set for Python 3.13 compatibility
os.environ['SKIP_EVENTLET'] = '1'

# Define paths
PROMPT_DIR = "tools/prompt_manager/prompts"
TEMPLATES_DIR = "tools/prompt_manager/templates"
HISTORY_DIR = os.path.join(PROMPT_DIR, ".history")
INTERVIEWS_DIR = "langchain_features/interviews"

# Create required directories
os.makedirs(PROMPT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(INTERVIEWS_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, 
           template_folder='langchain_features/templates',
           static_folder='langchain_features/static')

# Configure the app
app.secret_key = str(uuid.uuid4())
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['JSON_SORT_KEYS'] = False

# Add the prompt manager templates to Jinja's search path
app.jinja_loader.searchpath.append(
    os.path.abspath(TEMPLATES_DIR)
)

# Import the prompt manager integration
from langchain_features.prompt_integration import configure_prompt_manager
from tools.prompt_manager.prompt_manager import get_prompt_manager

# Initialize prompt manager with custom prefix to avoid conflicts
prompt_manager = configure_prompt_manager(app, 
                                         prompt_dir=PROMPT_DIR, 
                                         name_prefix="langchain")

# ===============================
# Routes and Views
# ===============================

@app.route('/')
def index():
    """Redirect to dashboard."""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard view showing available prompts and interviews."""
    available_agents = prompt_manager.get_available_agents()
    return render_template('langchain/dashboard.html', prompts=available_agents)

@app.route('/interview_test')
def interview_test():
    """Test interface for interviewing with LangChain."""
    return render_template('langchain/interview_test.html')

@app.route('/interview_setup')
def interview_setup():
    """Setup interface for creating a new interview."""
    available_prompts = prompt_manager.get_available_agents()
    return render_template('langchain/interview_setup.html', 
                          available_prompts=available_prompts)

@app.route('/interview_session')
def interview_session():
    """The interview session interface."""
    return render_template('langchain/interview_session.html')

@app.route('/interview_archive')
def interview_archive():
    """View interview archive."""
    interviews = load_all_interviews()
    return render_template('langchain/interview_archive.html', 
                          interviews=interviews)

@app.route('/interview_details/<session_id>')
def interview_details(session_id):
    """View details of a specific interview."""
    interview = load_interview(session_id)
    if not interview:
        return redirect(url_for('interview_archive'))
    return render_template('langchain/interview_details.html', 
                          interview=interview,
                          session_id=session_id)

# ===============================
# API Endpoints
# ===============================

@app.route('/api/interview/start', methods=['POST'])
def api_interview_start():
    """Start a new interview session."""
    data = request.json
    character_name = data.get('prompt_name', 'interviewer')
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    # Create interview data
    now = datetime.datetime.now()
    expiration_date = now + datetime.timedelta(days=7)
    
    interview_data = {
        'session_id': session_id,
        'character': character_name,
        'title': data.get('title', 'Untitled Interview'),
        'description': data.get('description', ''),
        'status': 'active',
        'created_at': now,
        'last_updated': now,
        'expiration_date': expiration_date,
        'conversation_history': []
    }
    
    # Load the character's prompt
    try:
        character_config = prompt_manager.load_prompt(character_name)
        system_prompt = character_config.get('dynamic_prompt_prefix', '')
    except Exception as e:
        logger.error(f"Error loading character prompt: {str(e)}")
        system_prompt = "You are a helpful interview assistant."
    
    # Generate greeting message
    greeting = f"Hello! I'm {character_name}. I'll be conducting this interview today. Let's get started. Could you please introduce yourself?"
    
    # Add greeting to conversation history
    interview_data['conversation_history'] = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": greeting}
    ]
    
    # Save the interview
    save_interview(session_id, interview_data)
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': greeting,
        'prompt': character_config
    })

@app.route('/api/interview/respond', methods=['POST'])
def api_interview_respond():
    """Respond to user input during an interview."""
    data = request.json
    session_id = data.get('session_id')
    user_input = data.get('message', '')
    
    if not session_id or not user_input:
        return jsonify({'success': False, 'error': 'Missing session_id or message'}), 400
    
    # Load interview data
    interview_data = load_interview(session_id)
    if not interview_data:
        return jsonify({'success': False, 'error': f'No interview found for session: {session_id}'}), 404
    
    # Add user message to conversation history
    if 'conversation_history' not in interview_data:
        interview_data['conversation_history'] = []
    
    interview_data['conversation_history'].append({
        "role": "user",
        "content": user_input
    })
    
    # Generate AI response (simplified mock response for now)
    ai_response = "Thank you for sharing that information. Could you elaborate more on your experience?"
    
    # Add AI response to conversation history
    interview_data['conversation_history'].append({
        "role": "assistant",
        "content": ai_response
    })
    
    # Update last_updated timestamp
    interview_data['last_updated'] = datetime.datetime.now()
    
    # Save updated interview data
    save_interview(session_id, interview_data)
    
    return jsonify({
        'success': True,
        'message': ai_response,
        'session_id': session_id
    })

@app.route('/api/interview/end', methods=['POST'])
def api_interview_end():
    """End an interview session."""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'success': False, 'error': 'Missing session_id'}), 400
    
    # Load interview data
    interview_data = load_interview(session_id)
    if not interview_data:
        return jsonify({'success': False, 'error': f'No interview found for session: {session_id}'}), 404
    
    # Update interview status
    interview_data['status'] = 'completed'
    interview_data['last_updated'] = datetime.datetime.now()
    
    # Save updated interview data
    save_interview(session_id, interview_data)
    
    # Generate a simple summary of the conversation
    message_count = len([msg for msg in interview_data.get('conversation_history', []) if msg.get('role') == 'user'])
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'summary': f"Interview completed with {message_count} user messages.",
        'status': 'completed'
    })

@app.route('/api/interviews', methods=['GET'])
def api_get_interviews():
    """Get a list of all interviews."""
    interviews = load_all_interviews()
    return jsonify({
        'success': True,
        'interviews': interviews
    })

@app.route('/api/prompt_performance', methods=['GET'])
def api_prompt_performance():
    """Get performance data for prompts."""
    agent_name = request.args.get('agent')
    if not agent_name:
        return jsonify({'success': False, 'error': 'Missing agent parameter'}), 400
    
    try:
        performance_data = prompt_manager.get_prompt_performance(agent_name)
        return jsonify({
            'success': True,
            'agent': agent_name,
            'performance': performance_data
        })
    except Exception as e:
        logger.error(f"Error getting prompt performance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===============================
# Persistence Functions
# ===============================

def save_interview(session_id, interview_data):
    """Persist interview data to JSON file."""
    try:
        # Convert datetime objects to strings
        serializable_data = {}
        for key, value in interview_data.items():
            if isinstance(value, datetime.datetime):
                serializable_data[key] = value.isoformat()
            else:
                serializable_data[key] = value
                
        # Save to a file named with the session_id
        file_path = os.path.join(INTERVIEWS_DIR, f"{session_id}.json")
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        logger.info(f"Saved interview data for session: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving interview data for session {session_id}: {str(e)}")
        return False

def load_interview(session_id):
    """Load interview data from JSON file."""
    try:
        file_path = os.path.join(INTERVIEWS_DIR, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                interview_data = json.load(f)
                
            # Convert ISO dates back to datetime objects
            for key, value in interview_data.items():
                if key in ['created_at', 'expiration_date', 'last_updated']:
                    try:
                        interview_data[key] = datetime.datetime.fromisoformat(value)
                    except (ValueError, TypeError):
                        pass
                        
            logger.info(f"Loaded interview data for session: {session_id}")
            return interview_data
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            return None
    except Exception as e:
        logger.error(f"Error loading interview data for session {session_id}: {str(e)}")
        return None

def load_all_interviews():
    """Load all interviews from the interviews directory."""
    interviews = {}
    try:
        for filename in os.listdir(INTERVIEWS_DIR):
            if filename.endswith(".json") and not filename.endswith("_transcript.json"):
                session_id = filename.split('.')[0]
                interview_data = load_interview(session_id)
                if interview_data:
                    interviews[session_id] = interview_data
        logger.info(f"Loaded {len(interviews)} interviews from {INTERVIEWS_DIR}")
        return interviews
    except Exception as e:
        logger.error(f"Error loading interviews: {str(e)}")
        return {}

# ===============================
# Main Entry Point
# ===============================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the LangChain Prompt Manager system')
    parser.add_argument('--port', type=int, default=5010, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Set Flask environment
    os.environ['FLASK_ENV'] = 'development' if args.debug else 'production'
    
    print(f"Starting DARIA Prompt Manager on port {args.port}...")
    print(f"Access the application at: http://127.0.0.1:{args.port}")
    print(f"Dashboard: http://127.0.0.1:{args.port}/dashboard")
    print(f"Interview Test: http://127.0.0.1:{args.port}/interview_test")
    print(f"Interview Setup: http://127.0.0.1:{args.port}/interview_setup")
    print(f"Prompt Manager: http://127.0.0.1:{args.port}/prompts/")
    
    app.run(debug=args.debug, host='127.0.0.1', port=args.port) 