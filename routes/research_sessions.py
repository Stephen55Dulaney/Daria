from flask import Blueprint, render_template, jsonify
from pathlib import Path
import json
import logging
import sys
import os

# Import SESSIONS_DIR and INTERVIEWS_DIR from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_daria_simplified import SESSIONS_DIR, INTERVIEWS_DIR

logger = logging.getLogger(__name__)

research_sessions_bp = Blueprint('research_sessions', __name__)

@research_sessions_bp.route('/sessions')
def research_sessions():
    """Render the research sessions page with all sessions."""
    try:
        # Get all sessions from the database
        sessions = []
        for file_path in Path(SESSIONS_DIR).glob("*.json"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            
            with open(file_path, 'r') as f:
                session_data = json.load(f)
                # Add a preview of the first message if available
                if session_data.get('messages'):
                    first_message = session_data['messages'][0]
                    session_data['preview'] = first_message.get('content', '')[:150] + '...'
                sessions.append(session_data)
        
        # Get all guides for the new session modal
        guides = []
        for file_path in Path(INTERVIEWS_DIR).glob("*.json"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            
            with open(file_path, 'r') as f:
                guide_data = json.load(f)
                guides.append(guide_data)
        
        return render_template('langchain/research_sessions.html', 
                             sessions=sessions,
                             guides=guides)
    except Exception as e:
        logger.error(f"Error loading research sessions: {str(e)}")
        return render_template('langchain/error.html', 
                             error="Failed to load research sessions. Please try again later."), 500 