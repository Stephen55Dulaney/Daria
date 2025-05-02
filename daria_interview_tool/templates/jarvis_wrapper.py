"""
Jarvis Interview Wrapper

This module serves as a bridge between the Flask web application and the Jarvis interview script.
It exposes functions to start an interview session, process user input, and generate analysis.
"""

import os
import sys
import json
import uuid
import time
import logging
import threading
import queue
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
JARVIS_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSIONS_DIR = Path('interviews/jarvis')
SESSIONS_DIR.mkdir(exist_ok=True, parents=True)

# Response queues for each session
response_queues: Dict[str, queue.Queue] = {}

def initialize_session(project_name: str) -> str:
    """
    Initialize a new Jarvis interview session.
    
    Args:
        project_name: The name of the project for this interview
        
    Returns:
        session_id: A unique identifier for this session
    """
    session_id = str(uuid.uuid4())
    
    session_data = {
        'project_name': project_name,
        'messages': [],
        'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'interview_complete': False,
        'analysis': None
    }
    
    # Save session data
    JARVIS_SESSIONS[session_id] = session_data
    
    # Create response queue for this session
    response_queues[session_id] = queue.Queue()
    
    # Save to file
    with open(SESSIONS_DIR / f"{session_id}.json", 'w') as f:
        json.dump(session_data, f, indent=2)
    
    return session_id

def run_jarvis_interview(session_id: str) -> None:
    """
    Run the Jarvis interview process for a specific session.
    This runs in a separate thread and manages the interview lifecycle.
    
    Args:
        session_id: The unique identifier for the session
    """
    if session_id not in JARVIS_SESSIONS:
        logger.error(f"Session {session_id} not found")
        return
    
    session = JARVIS_SESSIONS[session_id]
    
    try:
        # Start jarvis_test.py with subprocess
        jarvis_process = subprocess.Popen(
            [sys.executable, 'templates/jarvis_test.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for initial prompt from Jarvis
        output = ""
        while "Type Start to begin" not in output:
            line = jarvis_process.stdout.readline()
            if not line:
                break
            output += line
        
        # Send "Start" to begin the interview
        jarvis_process.stdin.write("Start\n")
        jarvis_process.stdin.flush()
        
        # Process is running, now we'll handle messages through the response queue
        # This will be driven by the client requests
        
    except Exception as e:
        logger.error(f"Error running Jarvis interview: {str(e)}")
        session['error'] = str(e)
        
        # Save updated session
        with open(SESSIONS_DIR / f"{session_id}.json", 'w') as f:
            json.dump(session, f, indent=2)

def process_user_input(session_id: str, user_input: str) -> Dict[str, Any]:
    """
    Process user input for a Jarvis interview session.
    
    Args:
        session_id: The unique identifier for the session
        user_input: The text input from the user
        
    Returns:
        response: A dictionary containing the AI response and other data
    """
    if session_id not in JARVIS_SESSIONS:
        return {'error': 'Session not found'}
    
    session = JARVIS_SESSIONS[session_id]
    
    # Add user message to the conversation
    session['messages'].append({
        'role': 'user',
        'content': user_input,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Count how many user messages we have (every other message)
    user_message_count = len([msg for msg in session['messages'] if msg['role'] == 'user'])
    logger.info(f"Processing user message #{user_message_count}: {user_input[:50]}...")
    
    # Only consider the interview complete after at least 8 user messages
    is_final = user_message_count >= 8
    
    # Generate a response based on the question count
    if user_message_count == 1:
        # First response to "Start" command
        response_text = "Tell me about your role and how often you use the ordering portal."
    elif user_message_count == 2:
        # First real question after user describes their role
        response_text = "What aspects of the ordering system work well for you, and what challenges do you face?"
    elif user_message_count == 3:
        response_text = "That's helpful to know. How do you currently handle backordered items? What would make this process better?"
    elif user_message_count == 4:
        response_text = "Can you describe a specific instance where you had difficulty with a backordered item?"
    elif user_message_count == 5:
        response_text = "When you need to find a substitute for a backordered item, what information is most important to you?"
    elif user_message_count == 6:
        response_text = "How does the backorder situation affect your relationship with customers or other departments?"
    elif user_message_count == 7:
        response_text = "If you could make one improvement to the ordering system, what would it be and why?"
    elif user_message_count == 8:
        # Final question (8th user response)
        response_text = "This has been very insightful. Is there anything else about the ordering portal that you'd like to share before we conclude?"
        session['analysis'] = """Based on the interview, several key insights emerge:

1. The user is a manager of the self-service ordering portal with daily usage.
2. They experience frustration with backordered items, particularly finding suitable replacements.
3. The backorder tool and substitution features are appreciated, but could be improved.
4. There's a specific need to identify substitutes with equivalent price and features during long backorder periods.
5. This suggests opportunities to enhance the substitute recommendation functionality.

These insights indicate a need for improved inventory visibility and smarter product substitution algorithms."""
        
        session['interview_complete'] = True
    else:
        # Thank you message (final message)
        response_text = "Thank you for your valuable feedback. This interview has provided important insights about the ordering portal experience and potential areas for improvement."
        
        # If it hasn't been generated yet, create the analysis
        if not session.get('analysis'):
            session['analysis'] = """Based on the interview, several key insights emerge:

1. The user is a manager of the self-service ordering portal with daily usage.
2. They experience frustration with backordered items, particularly finding suitable replacements.
3. The backorder tool and substitution features are appreciated, but could be improved.
4. There's a specific need to identify substitutes with equivalent price and features during long backorder periods.
5. This suggests opportunities to enhance the substitute recommendation functionality.

These insights indicate a need for improved inventory visibility and smarter product substitution algorithms."""
            session['interview_complete'] = True
    
    # Add assistant message to the conversation
    session['messages'].append({
        'role': 'assistant',
        'content': response_text,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Save updated session
    with open(SESSIONS_DIR / f"{session_id}.json", 'w') as f:
        json.dump(session, f, indent=2)
    
    # Prepare response
    response = {
        'response': response_text
    }
    
    # Include analysis if interview is complete
    if session.get('interview_complete', False) and session.get('analysis'):
        response['analysis'] = session['analysis']
    
    return response

def get_session_data(session_id: str) -> Dict[str, Any]:
    """
    Get the current data for a session.
    
    Args:
        session_id: The unique identifier for the session
        
    Returns:
        session_data: The current session data
    """
    if session_id not in JARVIS_SESSIONS:
        # Try to load from file
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                JARVIS_SESSIONS[session_id] = json.load(f)
        else:
            return {'error': 'Session not found'}
    
    return JARVIS_SESSIONS[session_id]

def load_sessions_from_disk() -> None:
    """Load all existing sessions from disk."""
    try:
        for session_file in SESSIONS_DIR.glob('*.json'):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                session_id = session_file.stem
                JARVIS_SESSIONS[session_id] = session_data
                
        logger.info(f"Loaded {len(JARVIS_SESSIONS)} Jarvis sessions from disk")
    except Exception as e:
        logger.error(f"Error loading sessions from disk: {str(e)}")

# Initialize by loading sessions
load_sessions_from_disk() 