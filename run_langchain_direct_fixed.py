#!/usr/bin/env python3
"""
Fixed LangChain Interview Runner with proper blueprint structure
Simple interview tool with persistent storage and clean architecture
"""

import os
import sys
import json
import time
import uuid
import logging
import datetime
import argparse
import requests
from pathlib import Path
from flask import Flask, redirect, render_template, Blueprint, send_from_directory, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import shutil
import tempfile
from io import BytesIO
import yaml
from werkzeug.middleware.proxy_fix import ProxyFix
from langchain_features.prompt_manager.models import PromptManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run LangChain Interview Prototype')
parser.add_argument('--port', type=int, default=5010, help='Port to run the server on')
args = parser.parse_args()

# Ensure SKIP_EVENTLET is set for Python 3.13 compatibility
os.environ['SKIP_EVENTLET'] = '1'

# Define the directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INTERVIEWS_DIR = os.path.join(DATA_DIR, "interviews")
PROMPT_DIR = "langchain_features/prompt_manager/prompts"
HISTORY_DIR = os.path.join(PROMPT_DIR, ".history")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INTERVIEWS_DIR, exist_ok=True)
os.makedirs(PROMPT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

# Initialize prompt manager with the appropriate directories
# Note: Directly instantiate the PromptManager class
from langchain_features.prompt_manager.models import PromptManager
prompt_mgr = PromptManager(prompt_dir=PROMPT_DIR)
logger.info(f"Initialized PromptManager with prompt_dir={PROMPT_DIR}")

# Initialize Flask app with direct template access
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
app.secret_key = str(uuid.uuid4())
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['JSON_SORT_KEYS'] = False

# Add prompt manager templates to the Jinja search path
app.jinja_loader.searchpath.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools/prompt_manager/templates')
)

# Create Flask blueprints
interview_bp = Blueprint('interview', __name__)
api_bp = Blueprint('api', __name__)
legacy_bp = Blueprint('legacy', __name__)

# ========================
# Database Persistence Functions
# ========================

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

# ========================
# Interview API Routes
# ========================

@api_bp.route('/interview/start', methods=['POST'])
def start_interview():
    """
    Start a new interview session.
    """
    try:
        data = request.json
        character_name = data.get('character', 'interviewer')
        voice_id = data.get('voice', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Create interview data
        now = datetime.datetime.now()
        expiration_date = now + datetime.timedelta(days=7)
        
        interview_data = {
            'session_id': session_id,
            'character': character_name,
            'voice_id': voice_id,
            'title': data.get('title', 'Untitled Interview'),
            'description': data.get('description', ''),
            'status': 'active',
            'created_at': now,
            'last_updated': now,
            'expiration_date': expiration_date,
            'conversation_history': []
        }
        
        # Save interview data
        save_interview(session_id, interview_data)
        
        # Load the character's prompt
        try:
            character_config = prompt_mgr.load_prompt_config(character_name)
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
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': greeting
        })
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/interview/respond', methods=['POST'])
def respond_to_interview():
    """
    Respond to the user's input in an interview session.
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        user_input = data.get('message', '')
        
        if not session_id or not user_input:
            return jsonify({'success': False, 'error': 'Missing session_id or message'}), 400
        
        # Check if user wants to end the interview
        lower_input = user_input.lower()
        if ('end interview' in lower_input or 
            'end the interview' in lower_input or 
            'please end the interview' in lower_input or 
            'please end interview' in lower_input or
            'please finish the interview' in lower_input or
            'please finish interview' in lower_input or
            'finish interview' in lower_input or 
            'finish the interview' in lower_input or 
            'conclude interview' in lower_input or 
            'conclude the interview' in lower_input or
            'could we please end' in lower_input or
            'i would like to end the interview' in lower_input):
            
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
            
            # Add farewell message to conversation history
            farewell_message = "I'll end the interview now. Thank you for your time and valuable insights!"
            interview_data['conversation_history'].append({
                "role": "assistant",
                "content": farewell_message
            })
            
            # Update status to completed
            interview_data['status'] = 'completed'
            interview_data['last_updated'] = datetime.datetime.now()
            
            # Save updated interview data
            save_interview(session_id, interview_data)
            
            # Return a special response indicating the interview should end
            return jsonify({
                'success': True,
                'message': farewell_message,
                'session_id': session_id,
                'end_interview': True
            })
        
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
        
        # Generate AI response based on character
        character_name = interview_data.get('character_select', 'interviewer')
        try:
            ai_response = generate_follow_up_question(user_input, character_name)
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            ai_response = "I'm sorry, I encountered an issue processing your response. Could you provide more details or try rephrasing?"
        
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
    except Exception as e:
        logger.error(f"Error responding to interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/interview/end', methods=['POST'])
def end_interview():
    """
    End an interview session and save the transcript.
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'success': False, 'error': f'No interview found for session: {session_id}'}), 404
        
        # Update status to completed
        interview_data['status'] = 'completed'
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Generate a reward code
        reward_code = f"DARIA-{session_id[:8]}"
        interview_data['reward_code'] = reward_code
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        # Create transcript
        if 'conversation_history' in interview_data:
            transcript = []
            for message in interview_data['conversation_history']:
                if message['role'] != 'system':
                    speaker = 'Interviewer' if message['role'] == 'assistant' else 'Participant'
                    transcript.append({
                        'speaker': speaker,
                        'content': message['content'],
                        'timestamp': interview_data['last_updated'].isoformat()
                    })
            
            # Save transcript
            transcript_path = os.path.join(INTERVIEWS_DIR, f"{session_id}_transcript.json")
            with open(transcript_path, 'w') as f:
                json.dump(transcript, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Interview completed successfully',
            'session_id': session_id,
            'reward_code': reward_code
        })
    except Exception as e:
        logger.error(f"Error ending interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech using a fallback method.
    """
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'Missing text parameter'}), 400
        
        # Use a sample audio file for testing
        test_audio_path = "static/sample_audio.mp3"
        if os.path.exists(test_audio_path):
            return send_file(test_audio_path, mimetype='audio/mpeg')
            
        # If no sample file, create a simple audio response
        return jsonify({
            'success': True,
            'message': 'Text-to-speech would convert this text: ' + text,
            'audio_url': '/static/sample_audio.mp3'
        })
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/text_to_speech_elevenlabs', methods=['POST'])
def text_to_speech_elevenlabs():
    """
    Convert text to speech using ElevenLabs API (forwarded to audio service).
    """
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default voice: Rachel
        session_id = data.get('session_id', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'Missing text parameter'}), 400
        
        # Forward request to ElevenLabs audio service
        try:
            audio_service_url = "http://127.0.0.1:5007/text_to_speech"
            response = requests.post(
                audio_service_url,
                json={
                    'text': text,
                    'voice_id': voice_id
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # Return the audio directly
                return Response(
                    response.content,
                    mimetype='audio/mpeg'
                )
            else:
                logger.error(f"Error from audio service: {response.text}")
                return jsonify({'success': False, 'error': 'Error from audio service'}), 500
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to audio service: {str(e)}")
            
            # Fallback to standard text-to-speech
            return jsonify({
                'success': False,
                'error': 'Could not connect to ElevenLabs service',
                'fallback': True
            }), 503
            
    except Exception as e:
        logger.error(f"Error in ElevenLabs text-to-speech: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/speech_to_text', methods=['POST'])
def direct_speech_to_text():
    """
    Direct endpoint for speech-to-text conversion (no /api prefix)
    """
    return speech_to_text()

# Original endpoint stays for backward compatibility
@api_bp.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """
    Convert speech to text (forwarded to audio service).
    """
    try:
        audio_file = request.files.get('audio')
        
        if not audio_file:
            return jsonify({'success': False, 'error': 'No audio file received'}), 400
        
        # Forward to audio service
        try:
            audio_service_url = "http://127.0.0.1:5007/speech_to_text"
            
            files = {
                'audio': (audio_file.filename, audio_file.read(), audio_file.content_type)
            }
            
            response = requests.post(
                audio_service_url,
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error from speech-to-text service: {response.text}")
                return jsonify({
                    'success': False, 
                    'error': 'Error from speech-to-text service',
                    'text': 'Failed to transcribe audio'
                }), 500
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to speech-to-text service: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Could not connect to speech-to-text service',
                'text': 'Speech-to-text service is unavailable'
            }), 503
            
    except Exception as e:
        logger.error(f"Error in speech-to-text: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'text': 'An error occurred during transcription'
        }), 500

@api_bp.route('/interviews', methods=['GET'])
def get_interviews():
    """
    Get a list of all interviews.
    """
    try:
        interviews = load_all_interviews()
        
        # Convert to a list for the response
        interview_list = []
        for session_id, interview in interviews.items():
            # Convert datetime objects to strings for JSON serialization
            serializable_interview = {}
            for key, value in interview.items():
                if isinstance(value, datetime.datetime):
                    serializable_interview[key] = value.isoformat()
                elif key == 'conversation_history':
                    # Only include a summary of the conversation history
                    if value:
                        serializable_interview['message_count'] = len([m for m in value if m['role'] != 'system'])
                    else:
                        serializable_interview['message_count'] = 0
                else:
                    serializable_interview[key] = value
            
            interview_list.append(serializable_interview)
        
        return jsonify({
            'success': True,
            'interviews': interview_list
        })
    except Exception as e:
        logger.error(f"Error getting interviews: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/check_services', methods=['GET'])
def check_services():
    """
    Check if all required services are running.
    """
    services = {
        'main_app': {
            'status': 'running',
            'endpoint': '/'
        },
        'audio_service': {
            'status': 'unknown',
            'endpoint': 'http://127.0.0.1:5007/'
        }
    }
    
    # Check audio service
    try:
        response = requests.get(services['audio_service']['endpoint'], timeout=2)
        if response.status_code == 200:
            services['audio_service']['status'] = 'running'
        else:
            services['audio_service']['status'] = 'error'
    except:
        services['audio_service']['status'] = 'not_running'
    
    return jsonify({
        'success': True,
        'services': services
    })

@api_bp.route('/character/<character_name>', methods=['GET'])
def get_character(character_name):
    """Get a character's prompt data."""
    try:
        print(f"DEBUG: Character API called for: {character_name}")
        print(f"DEBUG: prompt_mgr type: {type(prompt_mgr)}")
        print(f"DEBUG: prompt_mgr.__class__.__name__: {prompt_mgr.__class__.__name__}")
        print(f"DEBUG: Has list_agents method: {'list_agents' in dir(prompt_mgr)}")
        print(f"DEBUG: Has load_prompt_config method: {'load_prompt_config' in dir(prompt_mgr)}")
        print(f"DEBUG: prompt_dir path: {prompt_mgr.prompt_dir}")
        print(f"DEBUG: prompt_dir exists: {os.path.exists(prompt_mgr.prompt_dir)}")
        print(f"DEBUG: prompt_dir contents: {os.listdir(prompt_mgr.prompt_dir) if os.path.exists(prompt_mgr.prompt_dir) else 'Not found'}")
        
        config = prompt_mgr.load_prompt_config(character_name)
        if config:
            # Debug the analysis_prompt value
            analysis_prompt = getattr(config, 'analysis_prompt', '')
            print(f"DEBUG: Analysis prompt for {character_name}: {analysis_prompt[:100]}...")
            
            logger.info(f"Retrieved character data for {character_name}: {config.role}")
            return jsonify({
                'success': True,
                'name': config.agent_name,
                'role': config.role,
                'description': config.description,
                'dynamic_prompt_prefix': config.dynamic_prompt_prefix,
                'analysis_prompt': analysis_prompt
            })
        else:
            logger.error(f"Character not found: {character_name}")
            return jsonify({
                'success': False,
                'error': f"Character '{character_name}' not found"
            }), 404
    except Exception as e:
        logger.error(f"Error loading prompt for {character_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

@api_bp.route('/interview/create', methods=['POST'])
def create_interview():
    """Create a new interview session."""
    try:
        data = request.json
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Get current time
        now = datetime.datetime.now()
        
        # Prepare the interview data
        interview_data = {
            'session_id': session_id,
            'title': data.get('title', 'Untitled Interview'),
            'project': data.get('project', ''),
            'interview_type': data.get('interview_type', 'custom_interview'),
            'prompt': data.get('prompt', ''),
            'interview_prompt': data.get('interview_prompt', ''),
            'analysis_prompt': data.get('analysis_prompt', ''),
            'character_select': data.get('character_select', ''),
            'voice_id': data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL'),
            'interviewee': {
                'name': data.get('interviewee', {}).get('name', 'Anonymous'),
                'role': data.get('interviewee', {}).get('role', ''),
                'email': data.get('interviewee', {}).get('email', '')
            },
            'created_at': now,
            'creation_date': now.strftime("%Y-%m-%d %H:%M"),
            'last_updated': now,
            'expiration_date': now + datetime.timedelta(days=30),
            'status': 'active',
            'conversation_history': []
        }
        
        # Save the interview data
        save_interview(session_id, interview_data)
        logger.info(f"Saved new interview with ID: {session_id}")
        
        # Return success response with session ID and redirect URL
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'redirect_url': f"/interview_details/{session_id}"
        })
    except Exception as e:
        logger.error(f"Error creating interview: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@api_bp.route('/prompts/create', methods=['POST'])
def create_prompt():
    """Create a new prompt template."""
    try:
        data = request.json
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        template = data.get('template', '').strip()
        
        if not name or not template:
            return jsonify({'success': False, 'error': 'Name and template are required'}), 400
            
        # Generate a unique ID for the prompt
        prompt_id = str(uuid.uuid4())
        
        # Create the prompt data
        prompt_data = {
            'agent_name': name,
            'description': description,
            'dynamic_prompt_prefix': template,
            'role': data.get('role', 'interviewer'),
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Save the prompt
        os.makedirs(PROMPT_DIR, exist_ok=True)
        filepath = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        with open(filepath, 'w') as f:
            yaml.safe_dump(prompt_data, f, sort_keys=False)
            
        return jsonify({
            'success': True,
            'message': 'Prompt created successfully',
            'prompt_id': prompt_id
        })
    except Exception as e:
        logger.error(f"Error creating prompt: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@api_bp.route('/prompts/edit/<prompt_id>', methods=['GET', 'POST'])
def edit_prompt(prompt_id):
    """Edit a prompt template with full YAML structure support."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return jsonify({'success': False, 'error': 'Prompt not found'}), 404
            
        if request.method == 'GET':
            with open(prompt_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Handle lists and complex structures
            return jsonify({
                'success': True,
                'prompt': {
                    'agent_name': config.get('agent_name', ''),
                    'version': config.get('version', 'v1.0'),
                    'description': config.get('description', ''),
                    'role': config.get('role', ''),
                    'tone': config.get('tone', ''),
                    'core_objectives': config.get('core_objectives', []),
                    'contextual_instructions': config.get('contextual_instructions', ''),
                    'dynamic_prompt_prefix': config.get('dynamic_prompt_prefix', ''),
                    'analysis_prompt': config.get('analysis_prompt', ''),
                    'example_questions': config.get('example_questions', []),
                    'example_outputs': config.get('example_outputs', []),
                    'example_assumption_challenges': config.get('example_assumption_challenges', []),
                    'evaluation_metrics': config.get('evaluation_metrics', {}),
                    'common_research_biases': config.get('common_research_biases', ''),
                    'evaluation_notes': config.get('evaluation_notes', [])
                }
            })
        else:  # POST
            data = request.json
            agent_name = data.get('agent_name', '').strip()
            description = data.get('description', '').strip()
            role = data.get('role', '').strip()
            tone = data.get('tone', '').strip()
            version = data.get('version', 'v1.0')
            
            # Handle field validation
            if not agent_name or not description or not role:
                return jsonify({'success': False, 'error': 'Agent name, description, and role are required'}), 400
                
            # Read the existing prompt data to retain any fields not in the form
            with open(prompt_path, 'r') as f:
                config = yaml.safe_load(f) or {}
                
            # Update the prompt data
            config['agent_name'] = agent_name
            config['description'] = description
            config['role'] = role
            config['tone'] = tone
            config['version'] = version
            
            # Handle list fields
            config['core_objectives'] = [obj.strip() for obj in data.get('core_objectives', '').split('\n') if obj.strip()]
            
            # Text areas
            config['contextual_instructions'] = data.get('contextual_instructions', '')
            config['dynamic_prompt_prefix'] = data.get('dynamic_prompt_prefix', '')
            config['analysis_prompt'] = data.get('analysis_prompt', '')
            config['common_research_biases'] = data.get('common_research_biases', '')
            
            # Handle examples
            config['example_questions'] = [q.strip() for q in data.get('example_questions', '').split('\n') if q.strip()]
            config['example_outputs'] = [o.strip() for o in data.get('example_outputs', '').split('\n') if o.strip()]
            config['example_assumption_challenges'] = [a.strip() for a in data.get('example_assumption_challenges', '').split('\n') if a.strip()]
            
            # Evaluation metrics - keep existing if not updated
            if data.get('evaluation_metrics'):
                config['evaluation_metrics'] = data.get('evaluation_metrics', {})
            
            # Add evaluation note if provided
            evaluation_note = data.get('evaluation_note', '').strip()
            if evaluation_note:
                if 'evaluation_notes' not in config:
                    config['evaluation_notes'] = []
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
                config['evaluation_notes'].append(f"{timestamp}: {evaluation_note}")
            
            # Save the prompt back to file
            with open(prompt_path, 'w') as f:
                yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)
                
            # Create a backup in history directory if requested
            create_version = data.get('create_version', True)
            if create_version:
                os.makedirs(HISTORY_DIR, exist_ok=True)
                history_path = os.path.join(HISTORY_DIR, f"{prompt_id}_{int(time.time())}.yml")
                with open(history_path, 'w') as f:
                    yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)
                
            return jsonify({
                'success': True,
                'message': 'Prompt updated successfully'
            })
    except Exception as e:
        logger.error(f"Error with prompt {prompt_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/prompts/delete/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt template."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return jsonify({'success': False, 'error': 'Prompt not found'}), 404
            
        # Create backup in history directory before deleting
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        # Read the prompt to back it up
        with open(prompt_path, 'r') as f:
            prompt_data = yaml.safe_load(f)
            
        # Save backup
        history_path = os.path.join(HISTORY_DIR, f"{prompt_id}_deleted_{int(time.time())}.yml")
        with open(history_path, 'w') as f:
            yaml.safe_dump(prompt_data, f, sort_keys=False)
            
        # Delete the prompt
        os.remove(prompt_path)
        
        return jsonify({
            'success': True,
            'message': 'Prompt deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/prompts/copy/<prompt_id>', methods=['POST'])
def copy_prompt(prompt_id):
    """Copy a prompt template."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return jsonify({'success': False, 'error': 'Prompt not found'}), 404
            
        # Read the prompt to copy
        with open(prompt_path, 'r') as f:
            prompt_data = yaml.safe_load(f)
            
        # Generate a new ID for the copy
        new_prompt_id = str(uuid.uuid4())
        
        # Update the name and timestamps
        prompt_data['agent_name'] = f"{prompt_data.get('agent_name', '')} (Copy)"
        prompt_data['created_at'] = datetime.datetime.now().isoformat()
        prompt_data['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save the copy
        with open(os.path.join(PROMPT_DIR, f"{new_prompt_id}.yml"), 'w') as f:
            yaml.safe_dump(prompt_data, f, sort_keys=False)
            
        return jsonify({
            'success': True,
            'message': 'Prompt copied successfully',
            'prompt_id': new_prompt_id
        })
    except Exception as e:
        logger.error(f"Error copying prompt {prompt_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/prompts/view/<prompt_id>')
def view_prompt_page(prompt_id):
    """Render the prompt view page with full YAML structure support."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return redirect('/prompts/')
            
        with open(prompt_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure all expected fields are present even if empty
        if not config:
            config = {}
            
        agent_name = config.get('agent_name', prompt_id)
        
        return render_template(
            'langchain/view_prompt.html',
            prompt_id=prompt_id,
            agent=agent_name,
            config=config,
            title=f"View Prompt: {agent_name}",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error viewing prompt {prompt_id}: {str(e)}")
        return redirect('/prompts/')

# ========================
# Helper Functions
# ========================

def generate_follow_up_question(user_input, character_name=""):
    """
    Generate a follow-up question based on the user's input and character.
    """
    logger.info(f"Generating response for character: {character_name} based on input: {user_input[:50]}...")
    
    try:
        # If a character is specified, try to use its prompt template
        if character_name and character_name != "interviewer":
            try:
                # Load the character's prompt configuration
                config = prompt_mgr.load_prompt_config(character_name)
                logger.info(f"Loaded prompt for {character_name}")
                
                if config and config.dynamic_prompt_prefix:
                    prompt_template = config.dynamic_prompt_prefix
                    logger.info(f"Using custom prompt template for {character_name}")
                    
                    # In a real app, this would call an LLM with the custom prompt
                    # For now, we'll simulate a more character-specific response
                    custom_responses = [
                        f"As {config.role or character_name}, I'd like to know more about that. How does this relate to your experience?",
                        f"That's an interesting perspective. From my viewpoint as {config.role or character_name}, I wonder how you arrive at that conclusion?",
                        f"In my role as {config.role or character_name}, I've seen similar patterns. Could you elaborate on your specific challenges?",
                        f"Based on {config.description or 'my expertise'}, I'd suggest exploring this further. What obstacles have you encountered?",
                        f"Given what you've shared, and considering my background in {config.role or 'this field'}, how would you approach improving this process?"
                    ]
                    
                    import random
                    return random.choice(custom_responses)
            except Exception as e:
                logger.error(f"Error using character prompt for {character_name}: {str(e)}")
                # Fall back to default responses if there's an error
    
    except Exception as e:
        logger.error(f"Error in character response generation: {str(e)}")
    
    # Default responses if no character is specified or if there was an error
    follow_ups = [
        "That's interesting. Could you tell me more about that?",
        "How did that make you feel?",
        "Can you provide a specific example of that?",
        "What do you think could be improved about that?",
        "How do you see that evolving in the future?",
        "What challenges did you face with that?",
        "Could you elaborate on why you think that is?",
        "What alternatives have you considered?",
        "How does that compare to your previous experiences?",
        "What impact did that have on your work or process?"
    ]
    
    import random
    return random.choice(follow_ups)

# ========================
# UI Routes
# ========================

@interview_bp.route('/')
def index():
    """Redirect to dashboard."""
    return redirect('/dashboard')

@interview_bp.route('/dashboard')
def dashboard():
    """Render the dashboard."""
    interviews = load_all_interviews()
    return render_template('langchain/dashboard.html', interviews=interviews)

@interview_bp.route('/interview_test')
def interview_test():
    """Render the interview test page."""
    return render_template('langchain/interview_session.html')

@interview_bp.route('/interview_setup')
def interview_setup():
    """Render the interview setup page."""
    # Get available voices
    voices = get_elevenlabs_voices()
    
    # Load available characters from the prompt manager
    characters = []
    try:
        # Debug logging
        print("========== DEBUG: INTERVIEW SETUP CHARACTER LOADING ==========")
        print(f"DEBUG: prompt_mgr type: {type(prompt_mgr)}")
        print(f"DEBUG: prompt_mgr class: {prompt_mgr.__class__.__name__}")
        print(f"DEBUG: Using prompt_dir: {PROMPT_DIR}")
        print(f"DEBUG: Prompt directory exists: {os.path.exists(PROMPT_DIR)}")
        print(f"DEBUG: Prompt directory contents: {os.listdir(PROMPT_DIR) if os.path.exists(PROMPT_DIR) else 'directory not found'}")
        
        # Additional debug in the actual prompts directory
        print(f"DEBUG: prompt_mgr.prompt_dir: {prompt_mgr.prompt_dir}")
        print(f"DEBUG: prompt_mgr directory exists: {os.path.exists(prompt_mgr.prompt_dir)}")
        print(f"DEBUG: prompt_mgr directory contents: {os.listdir(prompt_mgr.prompt_dir) if os.path.exists(prompt_mgr.prompt_dir) else 'Not found'}")
        
        # List agents using the list_agents method
        print(f"DEBUG: Calling prompt_mgr.list_agents()")
        agent_names = prompt_mgr.list_agents()
        print(f"DEBUG: Found agent names: {agent_names}")
        
        for agent_name in agent_names:
            try:
                print(f"DEBUG: Loading config for agent: {agent_name}")
                config = prompt_mgr.load_prompt_config(agent_name)
                if config:
                    print(f"DEBUG: Successfully loaded config for {agent_name}")
                    characters.append({
                        "name": agent_name,
                        "role": config.role,
                        "description": config.description
                    })
                    logger.info(f"Added character: {agent_name} - {config.role}")
                else:
                    print(f"DEBUG: Config for {agent_name} was None")
            except Exception as e:
                print(f"DEBUG: Error loading character {agent_name}: {str(e)}")
                logger.error(f"Error loading character {agent_name}: {str(e)}")
    except Exception as e:
        print(f"DEBUG: Main error loading characters: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"Error loading characters: {str(e)}")
    
    print(f"DEBUG: Final characters list length: {len(characters)}")
    print(f"DEBUG: Final characters list: {characters}")
    print("========== END DEBUG ==========")
    logger.info(f"Loaded {len(characters)} characters for interview setup")
    
    # Default interview prompt
    interview_prompt = "You are an expert UX researcher conducting a user interview. Ask open-ended questions to understand the user's needs, goals, and pain points. Be conversational, empathetic, and curious."
    
    return render_template(
        'langchain/interview_setup.html',
        interview_prompt=interview_prompt,
        voices=voices,
        characters=characters
    )

@interview_bp.route('/interview_session')
def interview_session():
    """Render the interview session page."""
    return render_template('langchain/interview_session.html')

@interview_bp.route('/interview_session/<session_id>')
def interview_session_with_id(session_id):
    """Render the interview session page with a specific session ID."""
    # Check if user has already accepted the welcome page
    accepted = request.args.get('accepted', 'false').lower() == 'true'
    voice_id = request.args.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
    
    # Determine if this is a remote interviewee (based on presence of remote=true param)
    is_remote = request.args.get('remote', 'false').lower() == 'true'
    
    # Load interview data
    interview_data = load_interview(session_id)
    if not interview_data:
        return render_template('langchain/interview_error.html', 
                              error=f"No interview found for session: {session_id}")
    
    # If not accepted, show the welcome page first
    if not accepted:
        return render_template(
            'langchain/interview_welcome.html',
            session_id=session_id,
            title=interview_data.get('title', 'Research Interview'),
            voice_id=voice_id,
            is_remote=is_remote
        )
    
    # If the user provided name/email in the form, update the interview data
    name = request.args.get('name')
    email = request.args.get('email')
    
    if name:
        if 'interviewee' not in interview_data:
            interview_data['interviewee'] = {}
        interview_data['interviewee']['name'] = name
        if email:
            interview_data['interviewee']['email'] = email
        save_interview(session_id, interview_data)
    
    # Use the remote template for remote interviewees, otherwise use the standard template
    template = 'langchain/remote_interview_session.html' if is_remote else 'langchain/interview_session.html'
    
    return render_template(
        template,
        session_id=session_id,
        interview=interview_data,
        voice_id=voice_id
    )

@interview_bp.route('/interview_archive')
def interview_archive():
    """Render the interview archive page."""
    interviews = load_all_interviews()
    return render_template('langchain/interview_archive.html', interviews=interviews)

@interview_bp.route('/interview_details/<session_id>')
def interview_details(session_id):
    """Render the interview details page."""
    interview_data = load_interview(session_id)
    if not interview_data:
        return render_template('langchain/interview_error.html', 
                              error=f"No interview found for session: {session_id}")
    
    return render_template('langchain/interview_details.html', interview=interview_data, session_id=session_id)

@interview_bp.route('/monitor_interview/<session_id>')
def monitor_interview(session_id):
    """Render the interview monitoring page."""
    interview_data = load_interview(session_id)
    if not interview_data:
        return render_template('langchain/interview_error.html', 
                              error=f"No interview found for session: {session_id}")
    
    return render_template('langchain/monitor_session.html', interview=interview_data, session_id=session_id)

@interview_bp.route('/monitor_interview')
def monitor_interview_list():
    """Render the list of interviews available for monitoring."""
    interviews = load_all_interviews()
    # Filter to get only active interviews
    active_interviews = {session_id: interview for session_id, interview in interviews.items() 
                        if interview.get('status', '') == 'active'}
    
    return render_template('langchain/monitor_interview_list.html', 
                          interviews=active_interviews,
                          title="Available Interviews for Monitoring")

@interview_bp.route('/view_completed_interview/<session_id>')
def view_completed_interview(session_id):
    """Render the completed interview view page."""
    interview_data = load_interview(session_id)
    if not interview_data:
        return render_template('langchain/interview_error.html', 
                              error=f"No interview found for session: {session_id}")
    
    # Load transcript if available
    transcript_path = os.path.join(INTERVIEWS_DIR, f"{session_id}_transcript.json")
    transcript = None
    if os.path.exists(transcript_path):
        try:
            with open(transcript_path, 'r') as f:
                transcript = json.load(f)
        except Exception as e:
            logger.error(f"Error loading transcript: {str(e)}")
    
    return render_template(
        'langchain/view_completed_interview.html',
        interview=interview_data,
        transcript=transcript
    )

# ========================
# Legacy Route Redirects
# ========================

@interview_bp.route('/langchain_interview_test')
def legacy_interview_test():
    """Redirect legacy route to new route."""
    return redirect('/interview_test')

@interview_bp.route('/langchain_interview_setup')
def legacy_interview_setup():
    """Redirect legacy route to new route."""
    return redirect('/interview_setup')

@interview_bp.route('/langchain_interview_session')
def legacy_interview_session():
    """Redirect legacy route to new route."""
    return redirect('/interview_session')

@interview_bp.route('/langchain/dashboard')
def langchain_dashboard():
    """Redirect legacy route to new route."""
    return redirect('/dashboard')

@interview_bp.route('/langchain/interview_test')
def langchain_interview_test():
    """Redirect legacy route to new route."""
    return redirect('/interview_test')

@interview_bp.route('/langchain/interview_setup')
def langchain_interview_setup():
    """Redirect legacy route to new route."""
    return redirect('/interview_setup')

@interview_bp.route('/langchain/interview_session')
def langchain_interview_session():
    """Redirect legacy route to new route."""
    return redirect('/interview_session')

@interview_bp.route('/langchain/interview/session/<session_id>')
def legacy_interview_session_with_id(session_id):
    """Redirect legacy route to new route with query parameters."""
    # Preserve all query parameters
    voice_id = request.args.get('voice_id', '')
    accepted = request.args.get('accepted', '')
    name = request.args.get('name', '')
    email = request.args.get('email', '')
    
    query_params = []
    if voice_id:
        query_params.append(f'voice_id={voice_id}')
    if accepted:
        query_params.append(f'accepted={accepted}')
    if name:
        query_params.append(f'name={name}')
    if email:
        query_params.append(f'email={email}')
    
    query_string = '&'.join(query_params)
    if query_string:
        query_string = '?' + query_string
    
    return redirect(f'/interview/session/{session_id}{query_string}')

# Add the direct route for interview/session as well
@interview_bp.route('/interview/session/<session_id>')
def interview_session_with_direct_path(session_id):
    """Render the interview session page with a specific session ID."""
    return interview_session_with_id(session_id)

# ========================
# Register blueprints and start app
# ========================

# Register blueprints
app.register_blueprint(interview_bp)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(legacy_bp, url_prefix='/langchain')

# Add prompt manager route
@app.route('/prompts/')
def prompt_manager():
    """Render the prompt manager page."""
    # List all prompt templates from the PROMPT_DIR
    prompts = []
    try:
        if os.path.exists(PROMPT_DIR):
            for filename in os.listdir(PROMPT_DIR):
                if (filename.endswith('.yml') or filename.endswith('.yaml')) and not filename.startswith('.'):
                    prompt_id = filename.replace('.yml', '').replace('.yaml', '')
                    try:
                        filepath = os.path.join(PROMPT_DIR, filename)
                        with open(filepath, 'r') as f:
                            # Load YAML data
                            prompt_data = yaml.safe_load(f)
                            if prompt_data:
                                prompts.append({
                                    'id': prompt_id,
                                    'name': prompt_data.get('agent_name', prompt_id),
                                    'description': prompt_data.get('description', ''),
                                    'role': prompt_data.get('role', ''),
                                    'version': prompt_data.get('version', 'v1.0'),
                                    'created_at': prompt_data.get('created_at', ''),
                                    'updated_at': prompt_data.get('updated_at', '')
                                })
                    except Exception as e:
                        logger.error(f"Error loading prompt {filename}: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing prompts: {str(e)}")
    
    # Sort prompts by name
    prompts.sort(key=lambda x: x['name'])
    
    return render_template(
        'langchain/prompt_manager.html',
        prompts=prompts,
        title="Prompt Manager",
        section="prompts"
    )

# Add direct route for interview creation
@app.route('/interview/create', methods=['POST'])
def app_create_interview():
    """Create a new interview session - direct app route."""
    return create_interview()

# Add route for prompts/edit page
@app.route('/prompts/edit/<prompt_id>')
def edit_prompt_page(prompt_id):
    """Render the prompt edit page with full YAML structure support."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return redirect('/prompts/')
            
        with open(prompt_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure all expected fields are present even if empty
        if not config:
            config = {}
            
        agent_name = config.get('agent_name', prompt_id)
        version = config.get('version', 'v1.0')
        
        # Convert list items for display
        core_objectives = "\n".join(config.get('core_objectives', []))
        eval_notes = "\n".join(config.get('evaluation_notes', []))
        
        # Handle example data
        example_questions = "\n".join(config.get('example_questions', []))
        example_outputs = "\n".join(config.get('example_outputs', []))
        example_assumption_challenges = "\n".join(config.get('example_assumption_challenges', []))
        
        # Format evaluation metrics for display
        evaluation_metrics = config.get('evaluation_metrics', {})
        
        return render_template(
            'langchain/edit_prompt.html',
            prompt_id=prompt_id,
            agent=agent_name,
            config={
                'agent_name': agent_name,
                'version': version,
                'description': config.get('description', ''),
                'role': config.get('role', ''),
                'tone': config.get('tone', ''),
                'core_objectives': core_objectives,
                'contextual_instructions': config.get('contextual_instructions', ''),
                'dynamic_prompt_prefix': config.get('dynamic_prompt_prefix', ''),
                'analysis_prompt': config.get('analysis_prompt', ''),
                'example_questions': example_questions,
                'example_outputs': example_outputs,
                'example_assumption_challenges': example_assumption_challenges,
                'evaluation_metrics': evaluation_metrics,
                'common_research_biases': config.get('common_research_biases', ''),
                'evaluation_notes': eval_notes
            },
            title="Edit Prompt",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error rendering edit page for prompt {prompt_id}: {str(e)}")
        return redirect('/prompts/')

# Add the app level version
@app.route('/prompts/view/<prompt_id>')
def view_prompt_page(prompt_id):
    """Render the prompt view page with full YAML structure support."""
    try:
        # Check for both yml and yaml extensions
        prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yml")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_id}.yaml")
            if not os.path.exists(prompt_path):
                return redirect('/prompts/')
            
        with open(prompt_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure all expected fields are present even if empty
        if not config:
            config = {}
            
        agent_name = config.get('agent_name', prompt_id)
        
        return render_template(
            'langchain/view_prompt.html',
            prompt_id=prompt_id,
            agent=agent_name,
            config=config,
            title=f"View Prompt: {agent_name}",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error viewing prompt {prompt_id}: {str(e)}")
        return redirect('/prompts/')

@app.route('/text_to_speech', methods=['POST'])
def direct_text_to_speech():
    """
    Direct endpoint for text-to-speech conversion (no /api prefix)
    """
    return text_to_speech_elevenlabs()

@app.route('/text_to_speech_elevenlabs', methods=['POST'])
def direct_text_to_speech_elevenlabs():
    """
    Direct endpoint for ElevenLabs text-to-speech (no /api prefix)
    """
    return text_to_speech_elevenlabs()

@app.route('/debug/characters')
def debug_characters():
    """Debug endpoint to check character loading."""
    characters = []
    try:
        # Debug logging
        print("========== DEBUG: CHARACTER LOADING FROM DEBUG ENDPOINT ==========")
        print(f"Using prompt_dir: {PROMPT_DIR}")
        print(f"Prompt directory exists: {os.path.exists(PROMPT_DIR)}")
        print(f"Prompt directory contents: {os.listdir(PROMPT_DIR) if os.path.exists(PROMPT_DIR) else 'directory not found'}")
        
        # List agents using the list_agents method
        agent_names = prompt_mgr.list_agents()
        print(f"Found agent names: {agent_names}")
        
        for agent_name in agent_names:
            try:
                config = prompt_mgr.load_prompt_config(agent_name)
                if config:
                    characters.append({
                        "name": agent_name,
                        "role": config.role,
                        "description": config.description
                    })
                    print(f"Added character: {agent_name} - {config.role}")
            except Exception as e:
                print(f"Error loading character {agent_name}: {str(e)}")
        
        print(f"Final characters list: {characters}")
        print("========== END DEBUG ==========")
        
        # Return the characters as JSON
        return jsonify({
            "status": "success",
            "characters": characters,
            "count": len(characters),
            "prompt_dir": PROMPT_DIR,
            "prompt_dir_exists": os.path.exists(PROMPT_DIR),
            "agent_names": agent_names
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Main error loading characters: {str(e)}")
        print(f"Exception type: {type(e)}")
        print(traceback_str)
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback_str,
            "prompt_dir": PROMPT_DIR
        }), 500

def get_elevenlabs_voices():
    """Return a list of available voices for ElevenLabs."""
    return [
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel (Female)"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni (Male)"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli (Female)"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi (Female)"},
        {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "Fin (Male)"}
    ]

# Run the Flask app
if __name__ == "__main__":
    logger.info(f"Starting LangChain Interview Prototype on port {args.port}...")
    print(f"Access the application at: http://127.0.0.1:{args.port}")
    print(f"Dashboard: http://127.0.0.1:{args.port}/dashboard")
    print(f"Interview Test: http://127.0.0.1:{args.port}/interview_test")
    print(f"Interview Setup: http://127.0.0.1:{args.port}/interview_setup")
    print(f"Prompt Manager: http://127.0.0.1:{args.port}/prompts/")
    
    app.run(debug=True, port=args.port) 