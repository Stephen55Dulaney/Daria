#!/usr/bin/env python
# Script to run the DARIA Interview Tool without LangChain dependencies

import os
import sys
import logging
import json
import uuid
import datetime
import traceback
import re
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import openai
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from werkzeug.local import LocalProxy
from flask import g

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('daria.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)
logger.info("CORS enabled for all origins with extended header support")

# Configure secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'daria-interview-tool-secure-key')

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*")

# Add Flask-Login to handle the current_user variable in templates
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Create an anonymous user to handle the current_user variable in templates
def _get_user():
    user = User('anonymous')
    if hasattr(g, 'user'):
        user = g.user
    return user

app.jinja_env.globals['current_user'] = LocalProxy(_get_user)

# Set up current_user.is_authenticated property
@app.context_processor
def inject_user():
    user = _get_user()
    is_authenticated = False  # Always set to false in this simplified version
    return {
        'current_user': user,
        'current_user.is_authenticated': is_authenticated
    }

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'interviews')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'interviews', 'processed')
SESSIONS_DIR = os.path.join(BASE_DIR, 'data', 'interviews', 'sessions')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Configure app
app.config['INTERVIEW_DATA_DIR'] = DATA_DIR
app.config['INTERVIEW_PROCESSED_DIR'] = PROCESSED_DIR
app.config['INTERVIEW_SESSIONS_DIR'] = SESSIONS_DIR
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload size

# Configure OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Dummy placeholder for disabled LangChain services
discussion_service = None
observer_service = None


# Helper functions
def save_interview(session_id, interview_data):
    """Save interview data to JSON file."""
    try:
        # Make sure session_id is in the data structure for compatibility
        if 'session_id' not in interview_data and 'id' in interview_data:
            interview_data['session_id'] = interview_data['id']
        
        file_path = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f"{session_id}.json")
        with open(file_path, 'w') as f:
            json.dump(interview_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
        return False


def load_interview(session_id):
    """Load interview data from JSON file."""
    try:
        file_path = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f"{session_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading interview: {str(e)}")
        return None


def load_all_interviews():
    """Load all interviews from disk."""
    interviews = []
    if os.path.exists(app.config['INTERVIEW_SESSIONS_DIR']):
        for filename in os.listdir(app.config['INTERVIEW_SESSIONS_DIR']):
            if filename.endswith('.json'):
                session_id = filename.split('.')[0]
                interview = load_interview(session_id)
                if interview:
                    interviews.append(interview)
    return interviews


def load_guide_sessions(guide_id):
    """Load all sessions associated with a specific discussion guide."""
    guide_sessions = []
    if os.path.exists(app.config['INTERVIEW_SESSIONS_DIR']):
        for filename in os.listdir(app.config['INTERVIEW_SESSIONS_DIR']):
            if filename.endswith('.json'):
                session_id = filename.split('.')[0]
                session = load_interview(session_id)
                if session and session.get('guide_id') == guide_id:
                    guide_sessions.append(session)
    return guide_sessions


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Load all available prompts for the health check
    prompts = []
    try:
        # Check for prompt files in the prompts directory
        prompts_dir = os.path.join(BASE_DIR, 'prompts')
        if os.path.exists(prompts_dir):
            for filename in os.listdir(prompts_dir):
                if filename.endswith('.json'):
                    prompt_name = filename.split('.')[0]
                    prompts.append(prompt_name)
    except Exception as e:
        logger.error(f"Error loading prompts for health check: {str(e)}")
    
    # Return status with prompts list and langchain flag
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'available_prompts': prompts,
        'langchain_enabled': False  # Always false in this version
    })


# Upload Transcript Routes
@app.route('/api/upload_transcript', methods=['POST'])
def api_upload_transcript():
    """Handle transcript upload and conversion to interview format."""
    try:
        # Log the request
        logger.info(f"Received transcript upload request: Files: {list(request.files.keys())}, Form: {list(request.form.keys())}")
        
        # Ensure files were uploaded
        if 'transcript_file' not in request.files:
            logger.error("No transcript_file in request.files")
            return jsonify({'success': False, 'error': 'No transcript file provided'}), 400
        
        transcript_file = request.files['transcript_file']
        if transcript_file.filename == '':
            logger.error("Empty filename provided")
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get metadata from form
        title = request.form.get('title', 'Untitled Interview')
        project = request.form.get('project', '')
        interview_type = request.form.get('interview_type', 'custom_interview')
        researcher_name = request.form.get('researcher_name', '')
        researcher_email = request.form.get('researcher_email', '')
        participant_name = request.form.get('participant_name', 'Anonymous')
        participant_role = request.form.get('participant_role', '')
        participant_email = request.form.get('participant_email', '')
        guide_id = request.form.get('guide_id', '')
        
        logger.info(f"Processing transcript upload for guide_id: {guide_id}")
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Read and process the transcript content
        try:
            transcript_content = transcript_file.read().decode('utf-8')
        except UnicodeDecodeError:
            # Try another common encoding if utf-8 fails
            transcript_file.seek(0)
            transcript_content = transcript_file.read().decode('latin-1')
            
        # Debug: Log the first 10 lines to understand format
        preview_lines = transcript_content.strip().split('\n')[:10]
        logger.info(f"Transcript preview (first 10 lines):\n{''.join([line + '\n' for line in preview_lines])}")
        
        # Process transcript into conversation chunks
        lines = transcript_content.strip().split('\n')
        transcript_chunks = []
        current_speaker = None
        current_timestamp = None
        current_content = []
        
        # Detect format patterns
        zoom_bracket_pattern = r'^\s*\[(.*?)\]\s*(\d{1,2}:\d{1,2}:\d{1,2})'  # [Name] 00:00:00
        simple_bracket_pattern = r'^\s*\[(.*?)\]'  # [Name]
        colon_pattern = r'^([^:]+):\s*(.*)'  # Name: text
        time_pattern = r'^(\d{1,2}:\d{1,2}:\d{1,2})\s+(.+)'  # 00:00:00 text
        
        format_type = None
        
        # Check first few lines to determine format
        for line in [l for l in lines[:15] if l.strip()][:5]:
            if re.match(zoom_bracket_pattern, line):
                format_type = "zoom_bracket"
                break
            elif re.match(simple_bracket_pattern, line):
                format_type = "simple_bracket"
                break
            elif re.match(colon_pattern, line):
                format_type = "colon"
                break
            elif re.match(time_pattern, line):
                format_type = "time_prefixed"
                break
        
        logger.info(f"Detected transcript format: {format_type or 'unknown'}")
        
        # Process transcript based on detected format
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if format_type == "zoom_bracket":
                # Try to match [Speaker] 00:00:00 pattern (Zoom format)
                match = re.match(zoom_bracket_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker and timestamp
                    current_speaker = match.group(1).strip()
                    current_timestamp = match.group(2)
                    
                    # Get content after timestamp
                    timestamp_start = line.find(current_timestamp)
                    if timestamp_start > 0:
                        content_start = timestamp_start + len(current_timestamp)
                        content = line[content_start:].strip()
                        if content:
                            current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "simple_bracket":
                # Try to match [Speaker] pattern (without timestamp)
                match = re.match(simple_bracket_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker
                    current_speaker = match.group(1).strip()
                    
                    # Get content after bracket
                    bracket_end = line.find(']')
                    if bracket_end > 0:
                        content = line[bracket_end+1:].strip()
                        if content:
                            current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "colon":
                # Try to match Name: Content pattern
                match = re.match(colon_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker and content
                    current_speaker = match.group(1).strip()
                    content = match.group(2).strip()
                    if content:
                        current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "time_prefixed":
                # Try to match 00:00:00 Content pattern
                match = re.match(time_pattern, line)
                if match:
                    timestamp = match.group(1)
                    remaining_text = match.group(2).strip()
                    
                    # Check if remaining text has speaker designation
                    speaker_match = re.match(colon_pattern, remaining_text)
                    if speaker_match:
                        # This is a new speaker entry
                        if current_speaker and current_content:
                            transcript_chunks.append({
                                'speaker': current_speaker,
                                'speaker_name': current_speaker,
                                'content': ' '.join(current_content),
                                'timestamp': current_timestamp or ''
                            })
                            current_content = []
                        
                        current_speaker = speaker_match.group(1).strip()
                        current_timestamp = timestamp
                        content = speaker_match.group(2).strip()
                        if content:
                            current_content.append(content)
                    else:
                        # No speaker designation, continue with current speaker
                        current_timestamp = timestamp
                        if current_speaker:
                            current_content.append(remaining_text)
                        else:
                            # No current speaker, create a generic one
                            current_speaker = "Speaker"
                            current_content.append(remaining_text)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            else:
                # Fallback processing for unknown formats
                # Try simple pattern matching
                if not current_speaker:
                    current_speaker = "Speaker 1"
                
                # Check if this line might be a new speaker
                if re.match(r'^[A-Za-z\s]+:', line):
                    match = re.match(r'^([A-Za-z\s]+):\s*(.*)', line)
                    if match:
                        # Save previous content
                        if current_content:
                            transcript_chunks.append({
                                'speaker': current_speaker,
                                'speaker_name': current_speaker,
                                'content': ' '.join(current_content),
                                'timestamp': current_timestamp or ''
                            })
                            current_content = []
                        
                        # New speaker
                        current_speaker = match.group(1).strip()
                        content = match.group(2).strip()
                        if content:
                            current_content.append(content)
                    else:
                        # Just add to current content
                        current_content.append(line)
                else:
                    # Just add to current content
                    current_content.append(line)
        
        # Add the last speaker's content if exists
        if current_speaker and current_content:
            transcript_chunks.append({
                'speaker': current_speaker,
                'speaker_name': current_speaker,
                'content': ' '.join(current_content),
                'timestamp': current_timestamp or ''
            })
        
        # Detect unique speakers 
        unique_speakers = sorted(list(set([chunk['speaker'] for chunk in transcript_chunks])))
        logger.info(f"Detected speakers: {unique_speakers}")
        
        # Try to identify who is the interviewer/researcher and who is the participant
        assistant_speaker = None
        user_speaker = None
        
        # Check common interviewer/researcher identifiers
        researcher_keywords = ['interviewer', 'researcher', 'moderator', 'facilitator', 'dulaney', 'steven', 'steve']
        participant_keywords = ['participant', 'interviewee', 'subject', 'respondent']
        
        for speaker in unique_speakers:
            speaker_lower = speaker.lower()
            # Check common interviewer identifiers
            if any(keyword in speaker_lower for keyword in researcher_keywords):
                assistant_speaker = speaker
                logger.info(f"Identified researcher speaker: {speaker}")
            # Check common participant identifiers
            elif any(keyword in speaker_lower for keyword in participant_keywords):
                user_speaker = speaker
                logger.info(f"Identified participant speaker: {speaker}")
        
        # Track identified speakers
        identified_researcher_speakers = [s for s in unique_speakers if assistant_speaker and s == assistant_speaker]
        identified_participant_speakers = [s for s in unique_speakers if user_speaker and s == user_speaker]
        logger.info(f"Identified researcher speakers: {identified_researcher_speakers}")
        logger.info(f"Identified participant speakers: {identified_participant_speakers}")
        
        # If we couldn't clearly identify, make an educated guess using frequencies
        if not (assistant_speaker and user_speaker) and len(unique_speakers) >= 2:
            # Count mentions by speaker
            speaker_counts = {}
            for chunk in transcript_chunks:
                speaker = chunk['speaker']
                speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
            
            # Sort by frequency (less frequent might be the interviewer, more frequent the participant)
            sorted_speakers = sorted(speaker_counts.items(), key=lambda x: x[1])
            if len(sorted_speakers) >= 2:
                if not assistant_speaker:
                    assistant_speaker = sorted_speakers[0][0]  # Less frequent speaker is likely interviewer
                if not user_speaker:
                    user_speaker = sorted_speakers[-1][0]  # Most frequent speaker is likely participant
        
        # If still not identified, just use the first two speakers
        if not (assistant_speaker and user_speaker) and len(unique_speakers) >= 2:
            if not assistant_speaker:
                assistant_speaker = unique_speakers[0]
            if not user_speaker:
                user_speaker = unique_speakers[1]
        elif not assistant_speaker and len(unique_speakers) == 1:
            # If there's only one speaker, assume they're the participant
            user_speaker = unique_speakers[0]
            assistant_speaker = "Interviewer"
        elif not user_speaker and len(unique_speakers) == 1:
            # If we only identified an assistant but there's only one speaker
            user_speaker = "Participant"
        elif len(unique_speakers) == 0:
            # Fallback if no speakers detected
            assistant_speaker = "Interviewer"
            user_speaker = "Participant"
            
        # Map speaker names to roles for message conversion
        speaker_roles = {}
        for speaker in unique_speakers:
            if speaker == assistant_speaker:
                speaker_roles[speaker] = 'assistant'
            elif speaker == user_speaker:
                speaker_roles[speaker] = 'user'
            else:
                # If we have more than two speakers, additional ones as 'user'
                speaker_roles[speaker] = 'user'
        
        # Convert each chunk to a message
        messages = []
        conversation_history = []
        timestamp_format = "%Y-%m-%dT%H:%M:%S.%f"
        now = datetime.datetime.now()
        for i, chunk in enumerate(transcript_chunks):
            # Create a timestamp with increasing seconds to maintain chronological order
            msg_time = now + datetime.timedelta(seconds=i)
            
            # Get the role for this speaker
            role = speaker_roles.get(chunk['speaker'], 'user')  # Default to user if not mapped
            
            msg = {
                'id': str(uuid.uuid4()),
                'content': chunk['content'],
                'role': role,
                'timestamp': msg_time.strftime(timestamp_format)
            }
            messages.append(msg)
            
            # Also create message in the format that interview sessions expect
            conversation_history.append({
                'role': role,
                'content': chunk['content'],
                'timestamp': chunk['timestamp'] or f"{msg_time.hour}:{msg_time.minute}:{msg_time.second}"
            })
        
        # Check if guide_id exists
        guide_exists = False
        if guide_id:
            guide_file = os.path.join(DATA_DIR, f"{guide_id}.json")
            guide_exists = os.path.exists(guide_file)
            if not guide_exists:
                logger.warning(f"Guide ID {guide_id} specified but file not found at {guide_file}")
        
        # Load information from guide if exists
        guide_info = {}
        if guide_exists:
            try:
                with open(guide_file, 'r') as f:
                    guide_data = json.load(f)
                    guide_info = {
                        'title': guide_data.get('title', 'Untitled Interview'),
                        'project': guide_data.get('project', ''),
                        'interview_type': guide_data.get('interview_type', 'custom_interview'),
                        'topic': guide_data.get('topic', ''),
                        'context': guide_data.get('context', ''),
                        'goals': guide_data.get('goals', ''),
                        'character': guide_data.get('character_select', 'interviewer'),
                        'character_select': guide_data.get('character_select', 'interviewer'),
                        'voice_id': guide_data.get('voice_id', '')
                    }
            except Exception as e:
                logger.error(f"Error loading guide data: {str(e)}")
        
        # Calculate the word count of the transcript
        transcript_text = "\n\n" + "\n\n".join([f"{chunk['speaker']}: {chunk['content']}" for chunk in transcript_chunks])
        word_count = len(transcript_text.split())
        
        # Create the session object
        session_data = {
            'id': session_id,
            'session_id': session_id,  # Add this for compatibility
            'guide_id': guide_id,  # Link to the discussion guide
            'participant': {
                'name': participant_name,
                'email': participant_email,
                'role': participant_role
            },
            'status': 'completed',  # Mark as completed since it's an uploaded transcript
            'messages': messages,
            'conversation_history': conversation_history,  # Add this for compatibility with older format
            'transcript': transcript_text,
            'transcript_length': f"{word_count} characters",
            'messages': 0,  # Will be updated below
            'created_at': datetime.datetime.now().isoformat(),
            'creation_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'last_updated': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat(),
            'expiration_date': (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat(),
            'duration': "N/A"  # Unknown duration for uploaded transcripts
        }
        
        # Update message count
        session_data['messages'] = len(conversation_history)
        
        # Add information from guide if exists
        if guide_info:
            for key, value in guide_info.items():
                if key not in session_data:
                    session_data[key] = value
        else:
            # Use form data if guide not found
            session_data.update({
                'title': title,
                'project': project,
                'interview_type': interview_type,
                'character': 'interviewer',
                'character_select': 'interviewer'
            })
        
        # Save session to file
        session_file = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f"{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Update the discussion guide file to include this session ID
        if guide_id and guide_exists:
            try:
                # Read the current guide data
                with open(guide_file, 'r') as f:
                    guide_data = json.load(f)
                
                # Add the session ID to the guide's sessions list
                if "sessions" not in guide_data:
                    guide_data["sessions"] = []
                
                # Only add it if it's not already in the list
                if session_id not in guide_data["sessions"]:
                    guide_data["sessions"].append(session_id)
                    guide_data["updated_at"] = datetime.datetime.now().isoformat()
                    
                    # Save the updated guide data
                    with open(guide_file, 'w') as f:
                        json.dump(guide_data, f, indent=2)
                    
                    logger.info(f"Updated guide {guide_id} with new session {session_id}")
            except Exception as e:
                logger.error(f"Error updating guide {guide_id} with session {session_id}: {str(e)}")
                # Continue processing even if guide update fails
        
        # Determine redirect URL
        redirect_url = f"/discussion_guide/{guide_id}" if guide_id else f"/session/{session_id}"
        
        logger.info(f"Transcript uploaded and converted to session: {session_id}")
        return jsonify({
            'success': True, 
            'message': 'Transcript uploaded and processed successfully!',
            'session_id': session_id,
            'redirect_url': redirect_url
        })
    
    except Exception as e:
        logger.error(f"Error processing transcript upload: {str(e)}")
        logger.exception(e)
        return jsonify({'success': False, 'error': f'Error processing transcript: {str(e)}'}), 500


@app.route('/')
def home():
    """Render the home page."""
    return render_template('langchain/dashboard.html')


@app.route('/discussion_guide/<guide_id>', methods=['GET'])
def discussion_guide_details(guide_id):
    """Show the discussion guide details page."""
    try:
        # Load the guide data
        guide = {'title': 'Discussion Guide', 'project': 'Project'}
        
        # Load sessions for this guide
        sessions = load_guide_sessions(guide_id)
        logger.info(f"Found {len(sessions)} sessions for guide {guide_id}")
        
        return render_template('langchain/discussion_guide_details.html', 
                              guide=guide, 
                              sessions=sessions, 
                              guide_id=guide_id)
    except Exception as e:
        logger.error(f"Error loading discussion guide page: {str(e)}")
        return render_template('langchain/error.html', error=str(e))


@app.route('/upload_transcript', methods=['GET'])
def upload_transcript_page():
    """Render the upload transcript page."""
    return render_template('langchain/upload_transcript.html', title="Upload Transcript")


@app.route('/session/<session_id>', methods=['GET'])
def session_details(session_id):
    """Show the session details page with transcript and analysis."""
    try:
        # Load the session data
        session = load_interview(session_id)
        if not session:
            return render_template('langchain/error.html', error=f"Session not found: {session_id}")
        
        # Format data for template
        participant_info = {
            'name': session.get('participant', {}).get('name', 'Unknown Participant')
        }
        if 'participant' not in session and 'interviewee' in session:
            participant_info['name'] = session['interviewee'].get('name', 'Unknown Participant')
        
        # Get guide info if available
        guide_id = session.get('guide_id')
        guide = None
        if guide_id:
            guide_file = os.path.join(DATA_DIR, f"{guide_id}.json")
            if os.path.exists(guide_file):
                try:
                    with open(guide_file, 'r') as f:
                        guide = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading guide: {str(e)}")
        
        # Ensure required fields exist for template rendering
        session_view = {
            'id': session.get('id', session.get('session_id', session_id)),
            'title': session.get('title', 'Untitled Session'),
            'project': session.get('project', 'Unknown Project'),
            'type': session.get('interview_type', 'Unknown Type'),
            'status': session.get('status', 'completed'),
            'date': session.get('creation_date', session.get('created_at', 'Unknown Date')),
            'participant': participant_info,
            'character': session.get('character', session.get('character_select', 'Interviewer')),
            'transcript': session.get('transcript', ''),
            'conversation_history': session.get('conversation_history', []),
            'messages': session.get('messages', len(session.get('conversation_history', []))),
            'duration': session.get('duration', 'N/A'),
        }
        
        return render_template('langchain/session_details.html', 
                              session=session_view,
                              guide=guide,
                              session_id=session_id)
    except Exception as e:
        logger.error(f"Error loading session details: {str(e)}")
        logger.exception(e)
        return render_template('langchain/error.html', error=str(e))


# Add route for generating analysis
@app.route('/api/generate_analysis', methods=['POST'])
def generate_analysis():
    """Generate analysis for a session."""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        # Load the session
        session = load_interview(session_id)
        if not session:
            return jsonify({'success': False, 'error': f'Session not found: {session_id}'}), 404
        
        # Create a simple analysis (would normally be AI-generated)
        analysis = {
            'summary': 'This is an automatically generated summary for the interview transcript.',
            'key_points': [
                'Main discussion topic: ' + session.get('title', 'Unknown'),
                'Duration: ' + session.get('duration', 'N/A'),
                'Status: ' + session.get('status', 'Unknown'),
                f"Number of messages: {len(session.get('conversation_history', []))}"
            ],
            'insights': [
                'The transcript appears to contain an interview discussion.',
                'The participant provided several detailed responses.',
                'Multiple topics were covered throughout the discussion.'
            ],
            'recommendations': [
                'Consider following up on specific points mentioned by the participant.',
                'Review responses for additional insights into user needs.',
                'Use this transcript as reference for future research initiatives.'
            ]
        }
        
        # Update the session with the analysis
        session['analysis'] = analysis
        session['has_analysis'] = True
        session['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save the updated session
        save_interview(session_id, session)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error generating analysis: {str(e)}")
        logger.exception(e)
        return jsonify({'success': False, 'error': f'Error generating analysis: {str(e)}'}), 500


# Start the app
if __name__ == '__main__':
    debug_mode = False
    if '--debug' in sys.argv:
        debug_mode = True
    
    # Check if a custom port is specified
    port = 5026  # Changed from 5025 to avoid conflicts
    port_index = -1
    if '--port' in sys.argv:
        port_index = sys.argv.index('--port')
        if port_index >= 0 and port_index + 1 < len(sys.argv):
            port = int(sys.argv[port_index + 1])
            
    print(f"Starting DARIA Interview API on port {port} (WITHOUT LangChain)")
    print(f"Health check endpoint: http://127.0.0.1:{port}/api/health")
    print(f"Discussion Guide page: http://127.0.0.1:{port}/discussion_guide/81222255-a805-4693-9e5c-129270288908")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode, allow_unsafe_werkzeug=True) 