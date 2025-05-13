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
from flask import Flask, redirect, render_template, Blueprint, send_from_directory, request, jsonify, send_file, Response, make_response
from werkzeug.utils import secure_filename
import shutil
import tempfile
from io import BytesIO
import yaml
from werkzeug.middleware.proxy_fix import ProxyFix
from langchain_features.prompt_manager.models import PromptManager
from flask_cors import CORS

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

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})
logger.info("CORS enabled for all origins")

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
        # Make sure character_name is in lowercase for consistent comparison
        if character_name:
            character_name = character_name.lower()
            logger.info(f"Starting interview with character: {character_name}")
        
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
            if character_config:
                if hasattr(character_config, 'dynamic_prompt_prefix'):
                    # Handle PromptConfig object
                    system_prompt = character_config.dynamic_prompt_prefix
                elif isinstance(character_config, dict):
                    # Handle dictionary format
                    system_prompt = character_config.get('dynamic_prompt_prefix', '')
                else:
                    logger.error(f"Unknown character config type: {type(character_config)}")
                    system_prompt = "You are a helpful interview assistant."
            else:
                # Try direct YAML loading as a fallback
                try:
                    yaml_file = os.path.join(PROMPT_DIR, f"{character_name}.yml")
                    if os.path.exists(yaml_file):
                        with open(yaml_file, 'r') as f:
                            config_data = yaml.safe_load(f)
                        system_prompt = config_data.get('dynamic_prompt_prefix', '')
                    else:
                        system_prompt = "You are a helpful interview assistant."
                except Exception as yaml_e:
                    logger.error(f"Error loading character YAML: {str(yaml_e)}")
                    system_prompt = "You are a helpful interview assistant."
        except Exception as e:
            logger.error(f"Error loading character prompt: {str(e)}")
            system_prompt = "You are a helpful interview assistant."
        
        # Generate greeting message based on character
        # Note we've already converted character_name to lowercase above
        logger.info(f"Generating greeting for character: {character_name}")
        
        if character_name == "skeptica":
            greeting = "Hello! I'm Skeptica, Deloitte's Assumption Buster. I'll be conducting this interview today to help challenge assumptions and ensure research integrity. Let's get started. Could you please introduce yourself?"
        elif character_name == "eurekia":
            greeting = "Hello! I'm Eurekia, your insight synthesizer. I'll be conducting this interview today to help identify patterns and insights in your research. Let's get started. Could you please introduce yourself?"
        elif character_name == "thesea":
            greeting = "Hello! I'm Thesea, your journey mapping guide. I'll be conducting this interview today to help map out user journeys and experiences. Let's get started. Could you please introduce yourself?"
        elif character_name == "daria":
            greeting = "Hello! I'm Daria, Deloitte's Advanced Research & Interview Assistant. I'll be conducting this interview today. Let's get started. Could you please introduce yourself?"
        elif character_name == "odessia":
            greeting = "Hello! I'm Odessia, Deloitte's Journey Mapper. I'll be conducting this interview today to help analyze user experiences and create comprehensive journey maps. Let's get started. Could you please introduce yourself?"
        elif character_name == "askia":
            greeting = "Hello! I'm Askia, your question expert. I'll be conducting this interview today using strategic questioning techniques to uncover insights. Let's get started. Could you please introduce yourself?"
        elif character_name == "empathica":
            greeting = "Hello! I'm Empathica, your empathy explorer. I'll be conducting this interview today with a focus on understanding emotional experiences and needs. Let's get started. Could you please introduce yourself?"
        elif character_name == "synthia":
            greeting = "Hello! I'm Synthia, your synthesis specialist. I'll be conducting this interview today to help draw conclusions and synthesize findings. Let's get started. Could you please introduce yourself?"
        else:
            # For other characters, capitalize the first letter for a nicer display
            display_name = character_name.capitalize() if character_name else "Interviewer"
            greeting = f"Hello! I'm {display_name}. I'll be conducting this interview today. Let's get started. Could you please introduce yourself?"
            
        logger.info(f"Generated greeting: {greeting[:50]}...")
        
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

# Web UI compatibility routes
@app.route('/langchain/api/interview/start', methods=['POST'])
def langchain_api_interview_start():
    """Legacy route to support the web UI's existing API calls."""
    logger.info("Called legacy /langchain/api/interview/start endpoint")
    return start_interview()

@app.route('/api/interview/start', methods=['POST'])
def api_interview_start():
    """API compatibility route for interview start"""
    logger.info("Called /api/interview/start endpoint")
    return start_interview()

@api_bp.route('/interview/respond', methods=['POST'])
def respond_to_interview():
    """
    Generate a response to user input in an interview.
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        user_input = data.get('message', '')
        character_name = data.get('character', '')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        if not user_input:
            return jsonify({'success': False, 'error': 'Missing user message'}), 400
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'success': False, 'error': f'No interview found for session: {session_id}'}), 404
        
        # Update interview data with user message
        if 'conversation_history' not in interview_data:
            interview_data['conversation_history'] = []
        
        # Add user message to history
        interview_data['conversation_history'].append({
            "role": "user",
            "content": user_input
        })
        
        # Check if this is a remote interview and store interviewee name
        is_remote = data.get('is_remote', False)
        if is_remote and 'interviewee' not in interview_data:
            interviewee_name = data.get('interviewee_name', 'Anonymous')
            interview_data['interviewee'] = {
                'name': interviewee_name
            }
            logger.info(f"Recorded remote interviewee: {interviewee_name}")
        
        # Generate follow-up question using character if specified
        logger.info(f"Generating follow-up question for character: {character_name} and session: {session_id}")
        follow_up = generate_follow_up_question(
            user_input, 
            character_name=character_name,
            session_id=session_id
        )
        
        # Handle case where follow_up is a dict with text and debug info
        if isinstance(follow_up, dict) and 'text' in follow_up:
            response_text = follow_up['text']
            debug_info = follow_up.get('debug', {})
        else:
            response_text = follow_up
            debug_info = {}
        
        # Add assistant message to history
        interview_data['conversation_history'].append({
            "role": "assistant",
            "content": response_text
        })
        
        # Update last_updated timestamp
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        # Create comprehensive debug information
        debug_data = {
            'session_id': session_id,
            'character_name': character_name,
            'user_input': user_input,
            'response': response_text
        }
        
        # If there is interview_prompt in the session data, include it
        if 'interview_prompt' in interview_data:
            debug_data['interview_prompt'] = interview_data['interview_prompt']
        
        # If there is analysis_prompt in the session data, include it
        if 'analysis_prompt' in interview_data:
            debug_data['analysis_prompt'] = interview_data['analysis_prompt']
        
        # Include any extra debug information from generate_follow_up_question
        if debug_info:
            debug_data.update(debug_info)
        
        # Extract character prompt if available
        if character_name and character_name != "interviewer":
            try:
                character_data = get_character(character_name)
                if isinstance(character_data, Response):
                    # Extract data from Response object
                    import json
                    character_json = json.loads(character_data.get_data(as_text=True))
                    if character_json.get('success'):
                        debug_data['character_prompt'] = character_json.get('prompt', '')
                        debug_data['character_role'] = character_json.get('role', '')
                elif isinstance(character_data, dict):
                    debug_data['character_prompt'] = character_data.get('prompt', '')
                    debug_data['character_role'] = character_data.get('role', '')
            except Exception as e:
                logger.error(f"Error extracting character data for debug: {str(e)}")
                debug_data['character_error'] = str(e)
        
        # Include complete prompt construction if possible
        if 'interview_prompt' in interview_data:
            debug_data['full_prompt'] = f"{interview_data.get('interview_prompt')}\n\nUser's response: {user_input}\n\nGenerate a follow-up question based on this response:"
        
        # Return the response with debug information
        return jsonify({
            'success': True,
            'message': response_text,
            'session_id': session_id,
            'debug': debug_data  # Include comprehensive debugging info
        })
    except Exception as e:
        logger.error(f"Error responding to interview: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug': {'exception': str(e), 'traceback': traceback.format_exc()}
        }), 500

# Web UI compatibility routes for respond
@app.route('/langchain/api/interview/respond', methods=['POST'])
def langchain_api_interview_respond():
    """Legacy route to support the web UI's respond API call"""
    logger.info("Called legacy /langchain/api/interview/respond endpoint")
    return respond_to_interview()

@app.route('/api/interview/respond', methods=['POST'])
def api_interview_respond():
    """API compatibility route for interview respond"""
    logger.info("Called /api/interview/respond endpoint")
    return respond_to_interview()

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
        
        # Create transcript from conversation history
        if 'conversation_history' in interview_data:
            # Extract the transcript text for analysis
            transcript = []
            for message in interview_data['conversation_history']:
                if message['role'] != 'system':
                    role_prefix = "Interviewer: " if message['role'] == "assistant" else "Interviewee: "
                    transcript.append(f"{role_prefix}{message['content']}")
            
            transcript_text = "\n\n".join(transcript)
            
            # Generate analysis if the analysis_prompt is available
            if interview_data.get('analysis_prompt'):
                try:
                    # Initialize a basic LLM connection
                    from langchain_openai import ChatOpenAI
                    from langchain.chains import LLMChain
                    from langchain.prompts import ChatPromptTemplate
                    
                    # Get the analysis prompt
                    analysis_prompt = interview_data['analysis_prompt']
                    logger.info(f"Generating analysis using prompt: {analysis_prompt[:100]}...")
                    
                    # Create a prompt that includes the analysis_prompt and the transcript
                    prompt_template = ChatPromptTemplate.from_template(
                        f"{analysis_prompt}\n\nInterview Transcript:\n{transcript_text}\n\nAnalysis:"
                    )
                    
                    # Create LLM chain
                    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
                    llm_chain = LLMChain(llm=llm, prompt=prompt_template)
                    
                    # Generate the analysis
                    analysis = llm_chain.run({})
                    
                    # Add the analysis to the interview data
                    interview_data['analysis'] = analysis
                    logger.info(f"Analysis generated successfully: {analysis[:100]}...")
                    
                    # Add analysis to conversation history
                    interview_data['conversation_history'].append({
                        "role": "system",
                        "content": "Generated analysis"
                    })
                    interview_data['conversation_history'].append({
                        "role": "assistant",
                        "content": analysis
                    })
                except Exception as e:
                    logger.error(f"Error generating analysis: {str(e)}")
            else:
                logger.info("No analysis_prompt provided, skipping analysis generation")
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'reward_code': reward_code,
            'message': "Interview completed successfully. Thank you for your participation!"
        })
    except Exception as e:
        logger.error(f"Error ending interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Web UI compatibility routes for end interview
@app.route('/langchain/api/interview/end', methods=['POST'])
def langchain_api_interview_end():
    """Legacy route to support the web UI's end interview API call"""
    logger.info("Called legacy /langchain/api/interview/end endpoint")
    return end_interview()

@app.route('/api/interview/end', methods=['POST'])
def api_interview_end():
    """API compatibility route for interview end"""
    logger.info("Called /api/interview/end endpoint") 
    return end_interview()

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
            # Use the environment variable for service URL if it exists, or use port 5007
            audio_service_url = os.environ.get('AUDIO_SERVICE_URL', 'http://127.0.0.1:5007')
            if not audio_service_url.endswith('/'):
                audio_service_url += '/'
            audio_service_url += 'text_to_speech'
            
            logger.info(f"Sending TTS request to: {audio_service_url}")
            files = {}
            payload = {
                'text': text,
                'voice_id': voice_id,
                'session_id': session_id
            }
            
            # Send the request to the audio service with a timeout
            response = requests.post(audio_service_url, json=payload, timeout=10)
            
            # Check for successful response
            if response.status_code == 200:
                # Get audio file from response
                audio_content = response.content
                
                # Stream the audio back to the client
                audio_response = make_response(audio_content)
                audio_response.headers.set('Content-Type', 'audio/mpeg')
                audio_response.headers.set('Content-Disposition', 'attachment', filename='speech.mp3')
                
                return audio_response
            else:
                logger.error(f"Error from audio service: {response.status_code} - {response.text}")
                return jsonify({'success': False, 'error': f'Audio service error: {response.text}'}), response.status_code
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to audio service: {str(e)}")
            return jsonify({'success': False, 'error': f'Error connecting to audio service: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in text_to_speech_elevenlabs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/observer/analyze', methods=['POST'])
def analyze_transcript():
    """
    Process a transcript chunk through the AI Observer.
    This endpoint receives a transcript segment and returns AI analysis.
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
            
        # Extract transcript chunk
        transcript_chunk = data.get('transcript_chunk', {})
        if not transcript_chunk:
            return jsonify({'success': False, 'error': 'Missing transcript_chunk'}), 400
            
        # Extract other parameters
        session_id = data.get('session_id', '')
        previous_mood = data.get('previous_mood', None)
        previous_tags = data.get('previous_tags', None)
        
        # Log request
        logger.info(f"Analyzing transcript chunk for session {session_id}")
        
        # Process through AI Observer
        analysis_result = analyze_transcript_chunk(
            transcript_chunk, 
            session_id=session_id,
            previous_mood=previous_mood,
            previous_tags=previous_tags
        )
        
        # Return analysis
        return jsonify({
            'success': True,
            'result': analysis_result
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_transcript: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

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
            # Use the environment variable for service URL if it exists
            audio_service_url = os.environ.get('AUDIO_SERVICE_URL', 'http://127.0.0.1:5007')
            if not audio_service_url.endswith('/'):
                audio_service_url += '/'
            audio_service_url += 'speech_to_text'
            
            logger.info(f"Sending STT request to: {audio_service_url}")
            files = {
                'audio': (audio_file.filename, audio_file.read(), audio_file.content_type)
            }
            
            response = requests.post(
                audio_service_url,
                files=files,
                timeout=10  # 10 second timeout
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
            'endpoint': os.environ.get('AUDIO_SERVICE_URL', 'http://127.0.0.1:5007/')
        }
    }
    
    # Check audio service
    try:
        response = requests.get(services['audio_service']['endpoint'], timeout=2)
        # 404 is normal for these services when accessing root endpoint
        if response.status_code == 200 or response.status_code == 404:
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
        # Extensive debug logging
        logger.info(f"Character API called for: {character_name}")
        logger.info(f"prompt_mgr type: {type(prompt_mgr)}")
        logger.info(f"prompt_mgr.__class__.__name__: {prompt_mgr.__class__.__name__}")
        logger.info(f"Has list_agents method: {'list_agents' in dir(prompt_mgr)}")
        logger.info(f"Has load_prompt_config method: {'load_prompt_config' in dir(prompt_mgr)}")
        logger.info(f"prompt_dir path: {prompt_mgr.prompt_dir}")
        logger.info(f"prompt_dir exists: {os.path.exists(prompt_mgr.prompt_dir)}")
        
        # List files in the prompt directory to verify they exist
        prompt_files = os.listdir(prompt_mgr.prompt_dir) if os.path.exists(prompt_mgr.prompt_dir) else 'Directory not found'
        logger.info(f"prompt_dir contents: {prompt_files}")
        
        # Try to load the config carefully with error checking
        logger.info(f"Attempting to load character config for: {character_name}")
        try:
            config = prompt_mgr.load_prompt_config(character_name)
            logger.info(f"Config load result type: {type(config)}")
            
            # Check if config exists and is properly structured
            if config is None:
                logger.error(f"Config for character '{character_name}' is None")
                return jsonify({
                    'success': False,
                    'error': f"Character '{character_name}' config is None",
                    'debug_info': {
                        'character_name': character_name,
                        'prompt_dir': prompt_mgr.prompt_dir,
                        'prompt_files': prompt_files
                    }
                }), 404
                
            # Verify config structure and access methods
            if not hasattr(config, 'agent_name'):
                logger.error(f"Config missing agent_name attribute: {dir(config)}")
            
            # Safely extract properties, with fallbacks
            agent_name = getattr(config, 'agent_name', character_name)
            role = getattr(config, 'role', 'Interviewer')
            description = getattr(config, 'description', 'No description available')
            dynamic_prompt_prefix = getattr(config, 'dynamic_prompt_prefix', '')
            
            # Safely handle analysis_prompt which may be missing
            try:
                analysis_prompt = getattr(config, 'analysis_prompt', '')
                logger.info(f"Analysis prompt type: {type(analysis_prompt)}, length: {len(analysis_prompt) if analysis_prompt else 0}")
            except Exception as e:
                logger.error(f"Error accessing analysis_prompt: {str(e)}")
                analysis_prompt = ''
            
            logger.info(f"Successfully loaded character data for {character_name}: {role}")
            
            return jsonify({
                'success': True,
                'name': agent_name,
                'role': role,
                'description': description,
                'prompt': dynamic_prompt_prefix,
                'system_prompt': dynamic_prompt_prefix,
                'dynamic_prompt_prefix': dynamic_prompt_prefix,
                'analysis_prompt': analysis_prompt
            })
            
        except Exception as inner_e:
            logger.error(f"Inner error loading character '{character_name}': {str(inner_e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Try alternate loading method - direct YAML file loading
            try:
                logger.info(f"Attempting direct YAML loading for character: {character_name}")
                # Try with multiple possible extensions
                possible_files = [
                    os.path.join(prompt_mgr.prompt_dir, f"{character_name}.yml"),
                    os.path.join(prompt_mgr.prompt_dir, f"{character_name}.yaml")
                ]
                
                for file_path in possible_files:
                    if os.path.exists(file_path):
                        logger.info(f"Found character file at {file_path}")
                        with open(file_path, 'r') as f:
                            yaml_data = yaml.safe_load(f)
                            
                        if yaml_data:
                            return jsonify({
                                'success': True,
                                'name': yaml_data.get('agent_name', character_name),
                                'role': yaml_data.get('role', 'Interviewer'),
                                'description': yaml_data.get('description', 'No description available'),
                                'prompt': yaml_data.get('dynamic_prompt_prefix', ''),
                                'system_prompt': yaml_data.get('dynamic_prompt_prefix', ''),
                                'analysis_prompt': yaml_data.get('analysis_prompt', '')
                            })
                
                logger.error(f"No YAML file found for character '{character_name}'")
                return jsonify({
                    'success': False,
                    'error': f"Character '{character_name}' YAML file not found",
                    'debug_info': {
                        'character_name': character_name,
                        'prompt_dir': prompt_mgr.prompt_dir,
                        'checked_files': possible_files,
                        'prompt_files': prompt_files
                    }
                }), 404
                
            except Exception as yaml_e:
                logger.error(f"Error in direct YAML loading for '{character_name}': {str(yaml_e)}")
                logger.error(traceback.format_exc())
            
            return jsonify({
                'success': False,
                'error': f"Error loading character '{character_name}': {str(inner_e)}",
                'debug_info': {
                    'character_name': character_name,
                    'prompt_dir': prompt_mgr.prompt_dir,
                    'prompt_files': prompt_files
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error loading prompt for {character_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_info': {
                'character_name': character_name,
                'exception_type': str(type(e))
            }
        }), 500

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

def generate_follow_up_question(user_input, character_name="", session_id=None):
    """
    Generate a follow-up question based on the user's input and character.
    If session_id is provided, use the interview_prompt from that session.
    """
    start_time = datetime.datetime.now()
    logger.info(f"Generating response for character: {character_name} based on input: {user_input[:50]}...")
    
    # First, try to load the interview data if session_id is provided
    interview_data = None
    interview_prompt = None
    
    if session_id:
        try:
            interview_data = load_interview(session_id)
            logger.info(f"Loaded interview data for session {session_id}: {interview_data is not None}")
            if interview_data and 'interview_prompt' in interview_data:
                interview_prompt = interview_data['interview_prompt']
                logger.info(f"Found interview prompt in session data: {interview_prompt[:50]}...")
            else:
                logger.warning(f"No interview_prompt found in session data for {session_id}")
                if interview_data:
                    logger.debug(f"Interview data keys: {interview_data.keys()}")
        except Exception as e:
            logger.error(f"Error loading interview data for session {session_id}: {str(e)}")
    
    # Get the character prompt
    character_prompt = None
    character_system_prompt = None
    
    try:
        if character_name:
            character_data = get_character(character_name)
            if character_data is None:
                logger.error(f"Character data is None for character: {character_name}")
            else:
                # Handle different types of responses from get_character
                # If it's a Flask Response object, extract the JSON
                if isinstance(character_data, Response):
                    import json
                    character_json = json.loads(character_data.get_data(as_text=True))
                    if character_json.get('success', False):
                        character_data = character_json
                    else:
                        logger.error(f"Character API returned error: {character_json.get('error', 'Unknown error')}")
                        character_data = None
                
                # Handle dictionary format (from direct API response)
                if isinstance(character_data, dict):
                    logger.debug(f"Character data keys: {character_data.keys()}")
                    # Get prompt from various possible keys
                    character_prompt = character_data.get("prompt") or character_data.get("dynamic_prompt_prefix")
                    if character_prompt is None:
                        logger.error(f"Character prompt is None for character: {character_name}")
                    
                    character_system_prompt = character_data.get("system_prompt") or character_data.get("dynamic_prompt_prefix")
                    if character_system_prompt is None:
                        logger.error(f"Character system_prompt is None for character: {character_name}")
                
                # Handle PromptConfig object format
                elif hasattr(character_data, 'dynamic_prompt_prefix'):
                    logger.debug(f"Character data is a PromptConfig object")
                    character_prompt = getattr(character_data, 'dynamic_prompt_prefix', '')
                    character_system_prompt = character_prompt
                else:
                    logger.error(f"Character data has unexpected type: {type(character_data)}")
    except Exception as e:
        logger.error(f"Error loading character data for {character_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Use interview_prompt from the session if available, otherwise use a default prompt
    DEFAULT_INTERVIEW_PROMPT = "You are a helpful interviewer. Ask thoughtful follow-up questions based on the interviewee's responses."
    prompt_template = interview_prompt or DEFAULT_INTERVIEW_PROMPT
    
    # Combine character prompt with interview prompt if both exist
    combined_prompt = prompt_template
    if character_prompt:
        combined_prompt = f"{character_prompt}\n\n{prompt_template}"
    
    # Create a prompt that includes the interview_prompt and the user's input
    full_prompt = f"{combined_prompt}\n\nUser's response: {user_input}\n\nGenerate a follow-up question based on this response:"
    
    # Create debug information to return with the response
    debug_info = {
        "character_name": character_name,
        "session_id": session_id,
        "interview_prompt": interview_prompt,
        "character_prompt": character_prompt,
        "character_system_prompt": character_system_prompt,
        "using_default_prompt": interview_prompt is None,
        "full_prompt": full_prompt,
        "timestamp": start_time.isoformat(),
        "prompt_construction": {
            "base_prompt": prompt_template,
            "character_prompt_used": character_prompt is not None,
            "combined_prompt": combined_prompt,
            "user_input": user_input
        }
    }
    
    # Log the debug information
    logger.info(f"Debug info: {debug_info}")
    
    # Log the complete prompt in a very visible way
    logger.info("=" * 40)
    logger.info("FULL LLM PROMPT:")
    logger.info("-" * 40)
    logger.info(full_prompt)
    logger.info("=" * 40)
    
    # Generate the follow-up question based on the prompt
    try:
        # Initialize a basic LLM connection
        from langchain_openai import ChatOpenAI
        from langchain.chains import LLMChain
        from langchain.prompts import ChatPromptTemplate
        
        # Log the full prompt sent to the LLM
        logger.info(f"Sending prompt to LLM: {full_prompt[:100]}...")
        llm_start_time = datetime.datetime.now()
        
        # Create prompt template object
        prompt_template_obj = ChatPromptTemplate.from_template(full_prompt)
        
        # Create LLM chain
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
        llm_chain = LLMChain(llm=llm, prompt=prompt_template_obj)
        
        # Generate the follow-up question
        follow_up = llm_chain.run({})
        
        # Track timing
        llm_end_time = datetime.datetime.now()
        llm_duration = (llm_end_time - llm_start_time).total_seconds()
        debug_info["llm_timing"] = {
            "start_time": llm_start_time.isoformat(),
            "end_time": llm_end_time.isoformat(),
            "duration_seconds": llm_duration
        }
        
        logger.info(f"Generated follow-up question in {llm_duration:.2f}s: {follow_up[:50]}...")
        
        # Return both the generated text and debug info
        return {
            "text": follow_up,
            "debug": debug_info
        }
    
    except Exception as e:
        logger.error(f"Error generating follow-up question: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Fall back to default responses if there's an error
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
        fallback_response = random.choice(follow_ups)
        
        # Add error to debug info
        end_time = datetime.datetime.now()
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        debug_info["fallback_used"] = True
        debug_info["total_duration_seconds"] = (end_time - start_time).total_seconds()
        
        return {
            "text": fallback_response,
            "debug": debug_info
        }

def analyze_transcript_chunk(transcript_chunk, session_id=None, previous_mood=None, previous_tags=None):
    """
    AI Observer function that analyzes a transcript chunk and provides:
    1. Semantic note-taking
    2. Tag generation 
    3. Mood/emotion tracking
    
    Args:
        transcript_chunk (dict): A chunk of transcript containing text and speaker
        session_id (str): The interview session ID
        previous_mood (dict): Previous mood state to maintain continuity
        previous_tags (list): List of previously identified tags
        
    Returns:
        dict: Analysis results containing notes, tags, and mood tracking
    """
    try:
        # Initialize default values
        if previous_mood is None:
            previous_mood = {"value": 0, "label": "Neutral"}  # -1 to 1 scale: negative to positive
        
        if previous_tags is None:
            previous_tags = []
            
        # Get text and speaker from the transcript chunk
        text = transcript_chunk.get('content', '')
        role = transcript_chunk.get('role', 'user')  # 'user' or 'assistant'
        
        # Skip system messages as they're not part of the actual conversation
        if role == 'system':
            return {
                "observer_notes": "",
                "semantic_tags": [],
                "observer_mood": previous_mood,
                "observer_tag_list": previous_tags
            }
            
        # Create a speaker label
        speaker = "Interviewer" if role == "assistant" else "Interviewee"
        
        # Build the analysis prompt
        analysis_prompt = f"""
        You are an AI Observer analyzing an interview transcript in real-time. 
        Analyze the following segment from a user research interview:
        
        Speaker: {speaker}
        Text: "{text}"
        
        Provide the following analysis:
        1. A brief, insightful note about this segment (1-2 sentences max)
        2. Up to 3 semantic tags that describe themes, emotions, or topics in this segment
        3. The apparent mood/sentiment of the speaker on a scale from -1 (negative) to 1 (positive)
        
        Format your response as JSON with the following structure:
        {{
            "note": "Your brief insight note here",
            "tags": ["tag1", "tag2", "tag3"],
            "mood_value": 0.5,
            "mood_label": "Mostly Positive"
        }}
        """
        
        # Initialize LLM
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate
        
        # Configure the LLM for structured output
        llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.3)
        
        # Create and run chain for analysis
        prompt = ChatPromptTemplate.from_template(analysis_prompt)
        chain_output = llm.invoke(prompt.format())
        
        # Parse the JSON response
        import json
        try:
            # Extract the content from the message
            content = chain_output.content
            
            # Find JSON content (it might be wrapped in markdown code blocks)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                # Fallback if JSON parsing fails
                analysis = {
                    "note": "Unable to analyze this segment properly.",
                    "tags": [],
                    "mood_value": previous_mood["value"], 
                    "mood_label": previous_mood["label"]
                }
        except json.JSONDecodeError:
            # Fallback for JSON parsing errors
            analysis = {
                "note": "Error parsing analysis results.",
                "tags": [],
                "mood_value": previous_mood["value"],
                "mood_label": previous_mood["label"]
            }
            
        # Process the tags: normalize and merge with previous_tags
        new_tags = analysis.get("tags", [])
        normalized_tags = []
        
        for tag in new_tags:
            # Convert to lowercase and trim
            clean_tag = tag.lower().strip()
            if clean_tag and clean_tag not in normalized_tags:
                normalized_tags.append(clean_tag)
        
        # Merge with previous tags, avoid duplicates
        updated_tags = previous_tags.copy()
        for tag in normalized_tags:
            if tag not in updated_tags:
                updated_tags.append(tag)
        
        # Create mood object
        mood = {
            "value": analysis.get("mood_value", previous_mood["value"]),
            "label": analysis.get("mood_label", previous_mood["label"]),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Prepare the response
        result = {
            "observer_notes": analysis.get("note", ""),
            "semantic_tags": normalized_tags,
            "observer_mood": mood,
            "observer_tag_list": updated_tags
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in AI Observer analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return fallback values in case of error
        return {
            "observer_notes": "Analysis not available at this time.",
            "semantic_tags": [],
            "observer_mood": previous_mood,
            "observer_tag_list": previous_tags
        }

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
    
    # Get character from URL if provided
    character_name = request.args.get('character', '').lower()
    logger.info(f"Character from URL: {character_name}")
    
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
            is_remote=is_remote,
            character=character_name
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
        
        # Update character in interview data if provided in URL
        if character_name:
            interview_data['character'] = character_name
            logger.info(f"Updated interview character to: {character_name}")
        
        save_interview(session_id, interview_data)
    
    # Use the remote template for remote interviewees, otherwise use the standard template
    template = 'langchain/remote_interview_session.html' if is_remote else 'langchain/interview_session.html'
    
    return render_template(
        template,
        session_id=session_id,
        interview=interview_data,
        voice_id=voice_id,
        character=character_name
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

@app.route('/debug/prompts/<session_id>')
def debug_prompts(session_id):
    """
    Debug endpoint to view prompt data for a specific interview session.
    """
    try:
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'error': f'No interview found for session: {session_id}'}), 404
        
        # Extract prompt information
        debug_info = {
            'session_id': session_id,
            'title': interview_data.get('title', 'Untitled Interview'),
            'interview_prompt': interview_data.get('interview_prompt', 'Not set'),
            'analysis_prompt': interview_data.get('analysis_prompt', 'Not set'),
            'character': interview_data.get('character_select', 'Not set')
        }
        
        # Extract character prompt if available
        character_name = interview_data.get('character_select')
        if character_name and character_name != "interviewer":
            try:
                config = prompt_mgr.load_prompt_config(character_name)
                if config and config.dynamic_prompt_prefix:
                    debug_info['character_prompt'] = config.dynamic_prompt_prefix
                else:
                    debug_info['character_prompt'] = 'No prompt available for this character'
            except Exception as e:
                debug_info['character_prompt'] = f'Error loading character prompt: {str(e)}'
        
        # Format full combined prompt
        if 'interview_prompt' in interview_data and character_name and character_name != "interviewer":
            try:
                config = prompt_mgr.load_prompt_config(character_name)
                if config and config.dynamic_prompt_prefix:
                    debug_info['full_combined_prompt'] = f"{config.dynamic_prompt_prefix}\n\n{interview_data['interview_prompt']}"
            except:
                pass
        
        # Return as JSON or formatted HTML
        format_type = request.args.get('format', 'html')
        if format_type == 'json':
            return jsonify(debug_info)
        else:
            # Format as HTML for easier viewing
            html = "<html><head><title>Prompt Debug Info</title>"
            html += "<style>body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.6}"
            html += "h1,h2{color:#333}pre{background:#f5f5f5;padding:10px;overflow:auto;white-space:pre-wrap;border-radius:4px}</style>"
            html += "</head><body>"
            html += f"<h1>Prompt Debug Info for Session: {session_id}</h1>"
            html += f"<p><strong>Title:</strong> {debug_info['title']}</p>"
            html += f"<p><strong>Character:</strong> {debug_info['character']}</p>"
            
            html += "<h2>Interview Prompt</h2>"
            html += f"<pre>{debug_info['interview_prompt']}</pre>"
            
            html += "<h2>Analysis Prompt</h2>"
            html += f"<pre>{debug_info['analysis_prompt']}</pre>"
            
            if 'character_prompt' in debug_info:
                html += "<h2>Character Prompt</h2>"
                html += f"<pre>{debug_info['character_prompt']}</pre>"
            
            if 'full_combined_prompt' in debug_info:
                html += "<h2>Full Combined Prompt</h2>"
                html += f"<pre>{debug_info['full_combined_prompt']}</pre>"
            
            html += "</body></html>"
            return html
    
    except Exception as e:
        logger.error(f"Error in debug_prompts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug/interview/test', methods=['GET', 'POST'])
def debug_interview_test():
    """
    Debug endpoint to test interview flow with specific prompts.
    """
    if request.method == 'GET':
        # Return a simple HTML form for testing
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LangChain Interview Debug</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                h1 { color: #333; }
                label { display: block; margin-top: 10px; font-weight: bold; }
                textarea { width: 100%; height: 120px; margin-bottom: 15px; padding: 8px; }
                input[type="text"] { width: 100%; padding: 8px; margin-bottom: 15px; }
                button { background: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
                .result { margin-top: 20px; padding: 15px; background: #f8f8f8; border-left: 4px solid #4CAF50; }
                pre { white-space: pre-wrap; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>LangChain Interview Debug Tool</h1>
            <form method="POST" action="/debug/interview/test">
                <label for="interview_prompt">Interview Prompt:</label>
                <textarea name="interview_prompt" id="interview_prompt">You are an expert UX researcher conducting a user interview. Ask open-ended questions to understand the user's needs, goals, and pain points. Be conversational, empathetic, and curious.</textarea>
                
                <label for="character_name">Character Name:</label>
                <input type="text" name="character_name" id="character_name" value="interviewer">
                
                <label for="user_input">User Input to Test:</label>
                <textarea name="user_input" id="user_input">I've been working on designing a new mobile app for financial services, and I'm finding it challenging to balance all the features that stakeholders want with keeping the interface simple and user-friendly.</textarea>
                
                <button type="submit">Test Interview Flow</button>
            </form>
        </body>
        </html>
        """
        return html
    else:  # POST
        try:
            # Get form data
            interview_prompt = request.form.get('interview_prompt', '')
            character_name = request.form.get('character_name', 'interviewer')
            user_input = request.form.get('user_input', '')
            
            # Log the test parameters
            logger.info(f"Testing interview flow with character: {character_name}")
            logger.info(f"Interview prompt: {interview_prompt[:100]}...")
            logger.info(f"User input: {user_input[:100]}...")
            
            # Create a test session ID
            session_id = f"debug-test-{uuid.uuid4()}"
            
            # Create and save a test interview with the provided prompt
            now = datetime.datetime.now()
            interview_data = {
                'session_id': session_id,
                'title': 'Debug Test Interview',
                'interview_prompt': interview_prompt,
                'analysis_prompt': 'This is a test analysis prompt.',
                'character_select': character_name,
                'created_at': now,
                'last_updated': now,
                'conversation_history': []
            }
            
            save_interview(session_id, interview_data)
            logger.info(f"Created test interview session: {session_id}")
            
            # Generate a follow-up question using the character
            try:
                logger.info("Calling generate_follow_up_question...")
                response = generate_follow_up_question(
                    user_input=user_input,
                    character_name=character_name,
                    session_id=session_id
                )
                logger.info(f"Response from generate_follow_up_question: {response}")
                
                # Build HTML result display
                html_result = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>LangChain Interview Debug Result</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                        h1, h2 {{ color: #333; }}
                        .section {{ margin-bottom: 20px; padding: 15px; background: #f8f8f8; border-left: 4px solid #4CAF50; }}
                        pre {{ white-space: pre-wrap; overflow-x: auto; background: #f5f5f5; padding: 10px; }}
                        .back-link {{ margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1>Interview Debug Result</h1>
                    
                    <div class="section">
                        <h2>Test Parameters</h2>
                        <p><strong>Character:</strong> {character_name}</p>
                        <p><strong>Session ID:</strong> {session_id}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Interview Prompt</h2>
                        <pre>{interview_prompt}</pre>
                    </div>
                    
                    <div class="section">
                        <h2>User Input</h2>
                        <pre>{user_input}</pre>
                    </div>
                    
                    <div class="section">
                        <h2>Response</h2>
                        <pre>{response}</pre>
                    </div>
                    
                    <div class="section">
                        <h2>Character Data</h2>
                        <pre>
"""
                
                # Add character data if available
                try:
                    character_data = get_character(character_name)
                    if isinstance(character_data, Response):
                        # If it's a Flask Response, extract the JSON
                        import json
                        character_json = json.loads(character_data.get_data(as_text=True))
                        html_result += json.dumps(character_json, indent=2)
                    else:
                        html_result += str(character_data)
                except Exception as e:
                    html_result += f"Error getting character data: {str(e)}"
                
                html_result += """
                        </pre>
                    </div>
                    
                    <a href="/debug/interview/test" class="back-link">← Back to debug form</a>
                </body>
                </html>
                """
                
                return html_result
                
            except Exception as e:
                import traceback
                logger.error(f"Error in debug interview test: {str(e)}")
                logger.error(traceback.format_exc())
                
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>LangChain Interview Debug Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                        h1 {{ color: #d9534f; }}
                        .error {{ margin-top: 20px; padding: 15px; background: #f8d7da; border-left: 4px solid #d9534f; }}
                        pre {{ white-space: pre-wrap; overflow-x: auto; background: #f5f5f5; padding: 10px; }}
                        .back-link {{ margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1>Error in Interview Debug</h1>
                    
                    <div class="error">
                        <h2>Error Details</h2>
                        <p>{str(e)}</p>
                        <pre>{traceback.format_exc()}</pre>
                    </div>
                    
                    <a href="/debug/interview/test" class="back-link">← Back to debug form</a>
                </body>
                </html>
                """
                
        except Exception as e:
            logger.error(f"Error in debug interview test: {str(e)}")
            return f"Error: {str(e)}"

# Update interview status endpoint
@api_bp.route('/interview/update-status', methods=['POST'])
def update_interview_status():
    """Update the status of an interview."""
    try:
        data = request.json
        session_id = data.get('session_id')
        is_active = data.get('is_active', True)
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Update status
        interview_data['status'] = 'active' if is_active else 'inactive'
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview status for {session_id}: is_active={is_active}")
        
        return jsonify({
            "status": "success",
            "message": "Interview status updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Update interview expiration endpoint
@api_bp.route('/interview/update-expiration', methods=['POST'])
def update_interview_expiration():
    """Update the expiration date of an interview."""
    try:
        data = request.json
        session_id = data.get('session_id')
        expiration_date_str = data.get('expiration_date')
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Parse expiration date
        try:
            expiration_date = datetime.datetime.strptime(expiration_date_str, "%Y-%m-%d")
            interview_data['expiration_date'] = expiration_date
            interview_data['last_updated'] = datetime.datetime.now()
        except ValueError:
            return jsonify({'status': 'error', 'error': 'Invalid expiration date format. Use YYYY-MM-DD'}), 400
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview expiration for {session_id}: expiration_date={expiration_date_str}")
        
        return jsonify({
            "status": "success",
            "message": "Expiration date updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview expiration: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Add legacy routes for updating interview status and expiration
@legacy_bp.route('/interview/update-status', methods=['POST'])
def legacy_update_interview_status():
    """Update the status of an interview (legacy route)."""
    try:
        data = request.json
        session_id = data.get('session_id')
        is_active = data.get('is_active', True)
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Update status
        interview_data['status'] = 'active' if is_active else 'inactive'
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview status for {session_id}: is_active={is_active}")
        
        return jsonify({
            "status": "success",
            "message": "Interview status updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@legacy_bp.route('/interview/update-expiration', methods=['POST'])
def legacy_update_interview_expiration():
    """Update the expiration date of an interview (legacy route)."""
    try:
        data = request.json
        session_id = data.get('session_id')
        expiration_date_str = data.get('expiration_date')
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Parse expiration date
        try:
            expiration_date = datetime.datetime.strptime(expiration_date_str, "%Y-%m-%d")
            interview_data['expiration_date'] = expiration_date
            interview_data['last_updated'] = datetime.datetime.now()
        except ValueError:
            return jsonify({'status': 'error', 'error': 'Invalid expiration date format. Use YYYY-MM-DD'}), 400
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview expiration for {session_id}: expiration_date={expiration_date_str}")
        
        return jsonify({
            "status": "success",
            "message": "Expiration date updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview expiration: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Direct route mappings for crucial functionality
@app.route('/langchain/interview/update-status', methods=['POST'])
def app_update_interview_status():
    """Direct route for updating interview status."""
    try:
        data = request.json
        session_id = data.get('session_id')
        is_active = data.get('is_active', True)
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Update status
        interview_data['status'] = 'active' if is_active else 'inactive'
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview status for {session_id}: is_active={is_active}")
        
        return jsonify({
            "status": "success",
            "message": "Interview status updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/langchain/interview/update-expiration', methods=['POST'])
def app_update_interview_expiration():
    """Direct route for updating interview expiration."""
    try:
        data = request.json
        session_id = data.get('session_id')
        expiration_date_str = data.get('expiration_date')
        
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'error': f'No interview found for session: {session_id}'}), 404
        
        # Parse expiration date
        try:
            expiration_date = datetime.datetime.strptime(expiration_date_str, "%Y-%m-%d")
            interview_data['expiration_date'] = expiration_date
            interview_data['last_updated'] = datetime.datetime.now()
        except ValueError:
            return jsonify({'status': 'error', 'error': 'Invalid expiration date format. Use YYYY-MM-DD'}), 400
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        logger.info(f"Updated interview expiration for {session_id}: expiration_date={expiration_date_str}")
        
        return jsonify({
            "status": "success",
            "message": "Expiration date updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating interview expiration: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/debug/prompts/history/<session_id>')
def debug_prompts_history(session_id):
    """
    Debug endpoint to view prompt history for a specific interview session.
    Shows all prompts sent to the LLM during the interview, with timing information.
    """
    try:
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'error': f'No interview found for session: {session_id}'}), 404
        
        # Get basic interview info
        basic_info = {
            'session_id': session_id,
            'title': interview_data.get('title', 'Untitled Interview'),
            'created_at': interview_data.get('creation_date', 'Unknown date'),
            'status': interview_data.get('status', 'unknown'),
            'character': interview_data.get('character_select', 'Not set')
        }
        
        # Get prompts and conversation history
        prompt_info = {
            'interview_prompt': interview_data.get('interview_prompt', 'Not set'),
            'analysis_prompt': interview_data.get('analysis_prompt', 'Not set')
        }
        
        # Extract conversation history and reconstruct prompts
        prompt_history = []
        conversation_history = interview_data.get('conversation_history', [])
        
        # Find character prompt if any
        character_name = interview_data.get('character_select')
        character_prompt = None
        if character_name:
            try:
                character_data = get_character(character_name)
                if isinstance(character_data, dict):
                    character_prompt = character_data.get('prompt', '')
            except Exception as e:
                logger.error(f"Error getting character prompt for {character_name}: {str(e)}")
        
        # Process the conversation to reconstruct each LLM prompt
        user_inputs = [msg['content'] for msg in conversation_history if msg['role'] == 'user']
        ai_responses = [msg['content'] for msg in conversation_history if msg['role'] == 'assistant']
        
        # If we have interview_prompt and user inputs, build the prompt history
        if prompt_info['interview_prompt'] and user_inputs:
            for i, user_input in enumerate(user_inputs):
                # Build a prompt based on the interview prompt and user input
                combined_prompt = prompt_info['interview_prompt']
                if character_prompt:
                    combined_prompt = f"{character_prompt}\n\n{prompt_info['interview_prompt']}"
                
                full_prompt = f"{combined_prompt}\n\nUser's response: {user_input}\n\nGenerate a follow-up question based on this response:"
                
                prompt_entry = {
                    'index': i+1,
                    'timestamp': interview_data.get('last_updated', datetime.datetime.now()).isoformat(),
                    'user_input': user_input,
                    'full_prompt': full_prompt,
                    'ai_response': ai_responses[i] if i < len(ai_responses) else "No response recorded"
                }
                prompt_history.append(prompt_entry)
        
        # Format the output either as JSON or HTML
        format_type = request.args.get('format', 'html')
        
        if format_type == 'json':
            return jsonify({
                'basic_info': basic_info,
                'prompt_info': prompt_info,
                'prompt_history': prompt_history
            })
        else:
            # Render HTML view
            return render_template('langchain/prompt_history.html',
                           basic_info=basic_info,
                           prompt_info=prompt_info,
                           prompt_history=prompt_history,
                           character_prompt=character_prompt,
                           session_id=session_id)
    except Exception as e:
        logger.error(f"Error in debug_prompts_history: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error retrieving prompt history: {str(e)}'}), 500

# Main function for programmatic use
def main(port=5000, debug=True):
    """Run the interview application."""
    # Set up TTS and STT service URLs from environment variables
    if 'TTS_SERVICE_URL' in os.environ:
        logger.info(f"Using TTS service URL from environment: {os.environ.get('TTS_SERVICE_URL')}")
    
    if 'STT_SERVICE_URL' in os.environ:
        logger.info(f"Using STT service URL from environment: {os.environ.get('STT_SERVICE_URL')}")
    
    print("Starting LangChain Interview Prototype on port", port, "...")
    print("Access the application at: http://127.0.0.1:" + str(port))
    print("Dashboard: http://127.0.0.1:" + str(port) + "/dashboard")
    print("Interview Test: http://127.0.0.1:" + str(port) + "/interview_test")
    print("Interview Setup: http://127.0.0.1:" + str(port) + "/interview_setup")
    print("Prompt Manager: http://127.0.0.1:" + str(port) + "/prompts/")
    
    # Set environment variables for development
    os.environ['FLASK_APP'] = 'run_langchain_direct_fixed'
    if debug:
        os.environ['FLASK_ENV'] = 'development'
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)

# Run the Flask app
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LangChain Interview Prototype')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Run the main function with parsed arguments
    main(port=args.port, debug=args.debug)

@app.route('/api/text_to_speech_elevenlabs', methods=['POST'])
def api_text_to_speech_elevenlabs():
    """API for text-to-speech with ElevenLabs"""
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
        session_id = data.get('session_id', '')
        
        # Use the environment variable for TTS service URL if it exists, otherwise default to port 5015
        tts_service_url = os.environ.get('TTS_SERVICE_URL', 'http://127.0.0.1:5015')
        
        try:
            # Try to connect to the TTS service
            tts_url = f"{tts_service_url}/text_to_speech"
            response = requests.post(
                tts_url,
                json={"text": text, "voice_id": voice_id},
                timeout=30
            )
            
            if response.status_code == 200:
                return Response(response.content, mimetype='audio/mpeg')
            else:
                logger.error(f"Error from TTS service: {response.text}")
                return Response("Sorry, I couldn't generate speech for that text.", status=500)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to audio service: {str(e)}")
            return Response("Speech service is unavailable.", status=503)
            
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return Response("An error occurred with text-to-speech.", status=500)

@app.route('/api/speech_to_text', methods=['POST'])
def api_speech_to_text():
    """API for speech-to-text"""
    try:
        # Check if file was included
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        # Use the environment variable for STT service URL if it exists, otherwise default to port 5016
        stt_service_url = os.environ.get('STT_SERVICE_URL', 'http://127.0.0.1:5016')
        
        try:
            # Try to connect to the STT service
            stt_url = f"{stt_service_url}/speech_to_text"
            
            # Create a new multipart form to send to the STT service
            audio_file = request.files['audio']
            files = {'audio': (audio_file.filename, audio_file.read(), audio_file.content_type)}
            
            response = requests.post(stt_url, files=files, timeout=30)
            
            if response.status_code == 200:
                return jsonify(response.json()), 200
            else:
                logger.error(f"Error from STT service: {response.text}")
                return jsonify({"success": False, "error": "Could not process speech"}), 500
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to speech-to-text service: {str(e)}")
            return jsonify({"success": False, "error": "Could not connect to speech-to-text service"}), 503
            
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/interview/transcript', methods=['GET'])
def get_interview_transcript():
    """
    Get the transcript for an interview.
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Missing session_id parameter'}), 400
            
        # Check if interview exists
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'message': f'No interview found with session ID {session_id}'}), 404
            
        # Get the transcript file path
        transcript_path = os.path.join(INTERVIEWS_DIR, f"{session_id}_transcript.json")
        
        # Check if transcript exists
        if not os.path.exists(transcript_path):
            return jsonify({
                'status': 'success',
                'content': 'No transcript available yet.',
                'transcript_chunks': []
            })
            
        # Read the transcript
        try:
            with open(transcript_path, 'r') as f:
                transcript_data = json.load(f)
                
            # Process the JSON structure to get a readable HTML transcript
            formatted_transcript = ""
            
            # Prepare chunks for AI observer
            transcript_chunks = []
            
            for item in transcript_data:
                # Skip system messages for display but include them in chunks
                if item.get('role') == 'system':
                    transcript_chunks.append({
                        'id': item.get('id', str(uuid.uuid4())), 
                        'role': 'system',
                        'content': item.get('content', ''),
                        'timestamp': item.get('timestamp', '')
                    })
                    continue
                    
                # Create unique ID for this message if not present
                if 'id' not in item:
                    item['id'] = str(uuid.uuid4())
                    
                # Get the speaker role and content
                role = item.get('role', '')
                content = item.get('content', '')
                message_id = item.get('id', '')
                timestamp = item.get('timestamp', '')
                
                # Format for display
                if role == 'assistant':
                    formatted_transcript += f'<div class="interviewer-message" data-message-id="{message_id}">'
                    formatted_transcript += f'<strong>Interviewer:</strong> {content}</div>\n'
                elif role == 'user':
                    formatted_transcript += f'<div class="participant-message" data-message-id="{message_id}">'
                    formatted_transcript += f'<strong>Participant:</strong> {content}</div>\n'
                
                # Add to chunks for AI observer
                transcript_chunks.append({
                    'id': message_id,
                    'role': role,
                    'content': content,
                    'timestamp': timestamp
                })
            
            # Prepare stats
            stats = {
                'duration': calculate_interview_duration(transcript_data),
                'questions_count': count_questions(transcript_data),
                'avg_response_time': calculate_avg_response_time(transcript_data),
                'interviewer_percentage': calculate_interviewer_percentage(transcript_data),
                'participant_percentage': calculate_participant_percentage(transcript_data)
            }
            
            # Extract topics (simple keyword extraction for now)
            topics = extract_topics_from_transcript(transcript_data)
            
            return jsonify({
                'status': 'success',
                'content': formatted_transcript,
                'transcript_chunks': transcript_chunks,
                'stats': stats,
                'topics': topics
            })
            
        except Exception as e:
            logger.error(f"Error reading transcript: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error reading transcript: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error getting interview transcript: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Helper functions for transcript analysis
def calculate_interview_duration(transcript_data):
    """Calculate the duration of the interview based on timestamps."""
    try:
        if not transcript_data or len(transcript_data) < 2:
            return "00:00:00"
            
        # Get first and last message timestamps
        first_message = transcript_data[0]
        last_message = transcript_data[-1]
        
        first_time = datetime.datetime.fromisoformat(first_message.get('timestamp', '').replace('Z', '+00:00'))
        last_time = datetime.datetime.fromisoformat(last_message.get('timestamp', '').replace('Z', '+00:00'))
        
        # Calculate duration
        duration = last_time - first_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception as e:
        logger.error(f"Error calculating interview duration: {str(e)}")
        return "00:00:00"

def count_questions(transcript_data):
    """Count the number of questions asked by the interviewer."""
    try:
        question_count = 0
        for item in transcript_data:
            if item.get('role') == 'assistant':
                content = item.get('content', '')
                if '?' in content:
                    # Count the number of question marks
                    question_count += content.count('?')
        return question_count
    except Exception as e:
        logger.error(f"Error counting questions: {str(e)}")
        return 0

def calculate_avg_response_time(transcript_data):
    """Calculate the average time it takes for the participant to respond."""
    try:
        if not transcript_data or len(transcript_data) < 3:
            return "0.0 sec"
            
        response_times = []
        
        # Iterate through messages to find question-answer pairs
        for i in range(len(transcript_data) - 1):
            current = transcript_data[i]
            next_msg = transcript_data[i + 1]
            
            if (current.get('role') == 'assistant' and next_msg.get('role') == 'user' and 
                'timestamp' in current and 'timestamp' in next_msg):
                
                # Convert timestamps to datetime
                question_time = datetime.datetime.fromisoformat(current.get('timestamp', '').replace('Z', '+00:00'))
                answer_time = datetime.datetime.fromisoformat(next_msg.get('timestamp', '').replace('Z', '+00:00'))
                
                # Calculate response time in seconds
                response_time = (answer_time - question_time).total_seconds()
                
                # Only count reasonable response times (less than 2 minutes)
                if 0 < response_time < 120:
                    response_times.append(response_time)
        
        # Calculate average
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            return f"{avg_time:.1f} sec"
        return "0.0 sec"
    except Exception as e:
        logger.error(f"Error calculating average response time: {str(e)}")
        return "0.0 sec"

def calculate_interviewer_percentage(transcript_data):
    """Calculate the percentage of the conversation taken by the interviewer."""
    try:
        interviewer_chars = 0
        total_chars = 0
        
        for item in transcript_data:
            if item.get('role') in ['assistant', 'user']:
                content_length = len(item.get('content', ''))
                total_chars += content_length
                
                if item.get('role') == 'assistant':
                    interviewer_chars += content_length
        
        if total_chars > 0:
            percentage = (interviewer_chars / total_chars) * 100
            return f"{int(percentage)}%"
        return "0%"
    except Exception as e:
        logger.error(f"Error calculating interviewer percentage: {str(e)}")
        return "0%"

def calculate_participant_percentage(transcript_data):
    """Calculate the percentage of the conversation taken by the participant."""
    try:
        participant_chars = 0
        total_chars = 0
        
        for item in transcript_data:
            if item.get('role') in ['assistant', 'user']:
                content_length = len(item.get('content', ''))
                total_chars += content_length
                
                if item.get('role') == 'user':
                    participant_chars += content_length
        
        if total_chars > 0:
            percentage = (participant_chars / total_chars) * 100
            return f"{int(percentage)}%"
        return "0%"
    except Exception as e:
        logger.error(f"Error calculating participant percentage: {str(e)}")
        return "0%"

def extract_topics_from_transcript(transcript_data):
    """Extract main topics from the transcript content."""
    try:
        # Simple keyword extraction approach
        # For a more sophisticated approach, you could use NLP techniques
        
        # Combine all text from the participant
        all_text = " ".join([
            item.get('content', '') 
            for item in transcript_data 
            if item.get('role') == 'user'
        ])
        
        # Remove common stop words (simple approach)
        stop_words = [
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
            'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 
            'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 
            'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 
            'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 
            'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 
            'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 
            'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 
            'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        ]
        
        # Tokenize and filter
        words = all_text.lower().split()
        filtered_words = [word for word in words if word.isalpha() and word not in stop_words]
        
        # Count word frequency
        from collections import Counter
        word_counts = Counter(filtered_words)
        
        # Get the top keywords
        top_keywords = word_counts.most_common(10)
        
        # Generate topics from top keywords
        topics = []
        for word, count in top_keywords:
            if count > 1 and len(word) > 3:  # Only include words that appear multiple times and are longer than 3 chars
                topics.append(word.capitalize())
        
        return topics[:5]  # Return the top 5 topics
    except Exception as e:
        logger.error(f"Error extracting topics: {str(e)}")
        return []

@api_bp.route('/interview/status', methods=['GET'])
def get_interview_status():
    """
    Get the status of an interview.
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Missing session_id parameter'}), 400
            
        # Check if interview exists
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({'status': 'error', 'message': f'No interview found with session ID {session_id}'}), 404
            
        # Get the transcript file path
        transcript_path = os.path.join(INTERVIEWS_DIR, f"{session_id}_transcript.json")
        
        # Check if transcript exists
        if not os.path.exists(transcript_path):
            return jsonify({
                'status': 'success',
                'content': 'No transcript available yet.',
                'transcript_chunks': []
            })
            
        # Read the transcript
        try:
            with open(transcript_path, 'r') as f:
                transcript_data = json.load(f)
                
            # Process the JSON structure to get a readable HTML transcript
            formatted_transcript = ""
            
            # Prepare chunks for AI observer
            transcript_chunks = []
            
            for item in transcript_data:
                # Skip system messages for display but include them in chunks
                if item.get('role') == 'system':
                    transcript_chunks.append({
                        'id': item.get('id', str(uuid.uuid4())), 
                        'role': 'system',
                        'content': item.get('content', ''),
                        'timestamp': item.get('timestamp', '')
                    })
                    continue
                    
                # Create unique ID for this message if not present
                if 'id' not in item:
                    item['id'] = str(uuid.uuid4())
                    
                # Get the speaker role and content
                role = item.get('role', '')
                content = item.get('content', '')
                message_id = item.get('id', '')
                timestamp = item.get('timestamp', '')
                
                # Format for display
                if role == 'assistant':
                    formatted_transcript += f'<div class="interviewer-message" data-message-id="{message_id}">'
                    formatted_transcript += f'<strong>Interviewer:</strong> {content}</div>\n'
                elif role == 'user':
                    formatted_transcript += f'<div class="participant-message" data-message-id="{message_id}">'
                    formatted_transcript += f'<strong>Participant:</strong> {content}</div>\n'
                
                # Add to chunks for AI observer
                transcript_chunks.append({
                    'id': message_id,
                    'role': role,
                    'content': content,
                    'timestamp': timestamp
                })
            
            # Prepare stats
            stats = {
                'duration': calculate_interview_duration(transcript_data),
                'questions_count': count_questions(transcript_data),
                'avg_response_time': calculate_avg_response_time(transcript_data),
                'interviewer_percentage': calculate_interviewer_percentage(transcript_data),
                'participant_percentage': calculate_participant_percentage(transcript_data)
            }
            
            # Extract topics (simple keyword extraction for now)
            topics = extract_topics_from_transcript(transcript_data)
            
            return jsonify({
                'status': 'success',
                'content': formatted_transcript,
                'transcript_chunks': transcript_chunks,
                'stats': stats,
                'topics': topics
            })
            
        except Exception as e:
            logger.error(f"Error reading transcript: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error reading transcript: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error getting interview transcript: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

