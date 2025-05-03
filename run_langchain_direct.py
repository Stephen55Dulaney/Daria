#!/usr/bin/env python3
"""
Direct LangChain Interview Runner without Blueprints
Simple standalone interview tool with templates
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

# Import the prompt manager routes
from tools.prompt_manager.prompt_routes import prompt_bp, register_prompt_routes

# Import the prompt manager
from tools.prompt_manager.prompt_manager import get_prompt_manager

# Ensure the prompt manager directories exist
PROMPT_DIR = "langchain_features/prompt_manager/prompts"
HISTORY_DIR = "langchain_features/prompt_manager/prompts/.history"

# Create directories if they don't exist
os.makedirs(PROMPT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

# Create directory for interview data
INTERVIEWS_DIR = "interviews_data"
os.makedirs(INTERVIEWS_DIR, exist_ok=True)
INTERVIEWS_FILE = os.path.join(INTERVIEWS_DIR, "interviews.json")

# Copy prompts from tools directory if they don't exist in langchain_features
tools_prompt_dir = Path("tools/prompt_manager/prompts")
if tools_prompt_dir.exists():
    for prompt_file in tools_prompt_dir.glob("*.yml"):
        target_file = Path(PROMPT_DIR) / prompt_file.name
        if not target_file.exists():
            shutil.copy(prompt_file, target_file)
            logger.info(f"Copied prompt file {prompt_file.name} to {PROMPT_DIR}")

# Initialize prompt manager with the appropriate directories
prompt_manager = get_prompt_manager(PROMPT_DIR, HISTORY_DIR)

# Create default characters if they don't exist
try:
    # Skeptica - UX Researcher with a critical eye
    skeptica_file = Path(PROMPT_DIR) / "skeptica.yml"
    if not skeptica_file.exists():
        skeptica_config = {
            'agent_name': 'Skeptica',
            'version': 'v1.0',
            'role': 'Critical UX Researcher',
            'description': 'A UX researcher who asks probing questions and is skeptical of assumptions.',
            'dynamic_prompt_prefix': """You are Skeptica, a UX researcher with a critical eye. Your job is to interview the user and uncover hidden assumptions. 
            
Ask probing questions and don't accept vague answers. Push for concrete examples and specific details. Be professionally skeptical but not confrontational.

Your goal is to help the user think more deeply about their responses.""",
            'analysis_prompt': """Analyze this interview with a critical lens. Look for:

1. Unsupported claims and assumptions
2. Contradictions in the user's statements
3. Areas where deeper investigation is needed
4. Potential biases in how questions were asked or answered

Summarize your findings and recommend follow-up questions for a future interview."""
        }
        prompt_manager.save_prompt('skeptica', skeptica_config)
        logger.info("Created default Skeptica character")
    
    # Empathica - Empathetic UX Researcher
    empathica_file = Path(PROMPT_DIR) / "empathica.yml"
    if not empathica_file.exists():
        empathica_config = {
            'agent_name': 'Empathica',
            'version': 'v1.0',
            'role': 'Empathetic UX Researcher',
            'description': 'A UX researcher who creates a safe space for sharing experiences and emotions.',
            'dynamic_prompt_prefix': """You are Empathica, an empathetic UX researcher. Your job is to interview the user and understand their emotional experiences.
            
Create a safe space for sharing. Listen actively and validate their feelings. Ask open-ended questions about how experiences made them feel.

Your goal is to understand the emotional aspects of the user's experience.""",
            'analysis_prompt': """Analyze this interview with a focus on emotional insights. Look for:

1. Emotional reactions to experiences
2. Pain points that caused frustration or anxiety
3. Positive experiences that created delight or satisfaction
4. Unmet emotional needs

Summarize your findings and recommend ways to address the emotional aspects of the user experience."""
        }
        prompt_manager.save_prompt('empathica', empathica_config)
        logger.info("Created default Empathica character")
        
except Exception as e:
    logger.error(f"Error creating default characters: {str(e)}")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run LangChain Interview Prototype')
parser.add_argument('--port', type=int, default=5010, help='Port to run the server on')
args = parser.parse_args()

# Ensure SKIP_EVENTLET is set for Python 3.13 compatibility
os.environ['SKIP_EVENTLET'] = '1'

# Function to load interviews from disk
def load_interviews():
    """Load interviews from JSON file."""
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                interviews = json.load(f)
                logger.info(f"Loaded {len(interviews)} interviews from {INTERVIEWS_FILE}")
                return interviews
        except Exception as e:
            logger.error(f"Error loading interviews from {INTERVIEWS_FILE}: {str(e)}")
    logger.info(f"No interviews file found at {INTERVIEWS_FILE}, starting with empty dictionary")
    return {}

# Function to save interviews to disk
def save_interviews(interviews):
    """Save interviews to JSON file."""
    try:
        # Convert datetime objects to strings for JSON serialization
        serializable_interviews = {}
        for session_id, interview in interviews.items():
            serializable_interview = {}
            for key, value in interview.items():
                if isinstance(value, datetime.datetime):
                    serializable_interview[key] = value.isoformat()
                else:
                    serializable_interview[key] = value
            serializable_interviews[session_id] = serializable_interview
            
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(serializable_interviews, f)
        logger.info(f"Saved {len(interviews)} interviews to {INTERVIEWS_FILE}")
    except Exception as e:
        logger.error(f"Error saving interviews to {INTERVIEWS_FILE}: {str(e)}")

# Create Flask app with direct template access
app = Flask(__name__, 
           template_folder='langchain_features/templates',
           static_folder='static')
app.secret_key = str(uuid.uuid4())

# Initialize the interviews dictionary from disk
app.interviews = load_interviews()

# Register the prompt manager blueprint
app.register_blueprint(prompt_bp)

# Add a redirect from root to dashboard
@app.route('/')
def index():
    """Redirect to dashboard."""
    return redirect('/dashboard')

# Direct routes without blueprints
@app.route('/dashboard')
def dashboard():
    """Render the langchain dashboard."""
    return render_template('langchain/dashboard.html')

@app.route('/interview_test')
def interview_test():
    """Render the interview test page."""
    return render_template('langchain/interview_session.html')

@app.route('/interview_setup')
def interview_setup():
    """Render interview setup page."""
    # Define available ElevenLabs voices
    voices = [
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel (Female)"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni (Male)"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli (Female)"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi (Female)"},
        {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "Fin (Male)"}
    ]
    
    # Load available characters from the prompt manager
    characters = []
    try:
        agent_names = prompt_manager.get_available_agents()
        for agent_name in agent_names:
            try:
                config = prompt_manager.load_prompt(agent_name)
                characters.append({
                    "name": agent_name,
                    "role": config.get("role", ""),
                    "description": config.get("description", "")
                })
            except Exception as e:
                logger.error(f"Error loading character {agent_name}: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading characters: {str(e)}")
    
    logger.info(f"Loaded {len(characters)} characters for interview setup")
    
    # Default interview prompt
    interview_prompt = "You are an expert UX researcher conducting a user interview. Ask open-ended questions to understand the user's needs, goals, and pain points. Be conversational, empathetic, and curious."
    
    return render_template(
        'langchain/interview_setup.html',
        interview_prompt=interview_prompt,
        voices=voices,
        characters=characters
    )

@app.route('/interview_session')
def interview_session():
    """Render the interview session page."""
    return render_template('langchain/interview_session.html')

@app.route('/interview_archive')
def interview_archive():
    """Render the interview archive page."""
    return render_template('langchain/interview_archive.html')

@app.route('/interview_details/<session_id>')
def interview_details(session_id):
    """Render the interview details page."""
    # Try to load the interview data from our in-memory storage
    if hasattr(app, 'interviews') and session_id in app.interviews:
        interview = app.interviews[session_id]
        logger.info(f"Loaded interview data for session: {session_id}")
    else:
        # If not found, create a dummy interview object
        logger.warning(f"Interview data not found for session: {session_id}, using dummy data")
        now = datetime.datetime.now()
        expiration_date = now + datetime.timedelta(days=30)
        
        interview = {
            "id": session_id,
            "title": "Interview Session",
            "created_at": now,                               # Datetime object
            "creation_date": now.strftime("%Y-%m-%d %H:%M"), # Formatted string
            "updated_at": now,                               # Datetime object
            "status": "active",
            "project": "Interview Project",
            "expiration_date": expiration_date,              # Datetime object
            "interviewee": {
                "name": "Anonymous",
                "role": "",
                "experience_level": "",
                "department": ""
            },
            "options": {
                "analysis": True,
                "record_transcript": True,
                "use_tts": True
            },
            "custom_questions": []
        }
    
    return render_template('langchain/interview_details.html', 
                           interview=interview, 
                           session_id=session_id)

@app.route('/monitor_interview/<session_id>')
def monitor_interview(session_id):
    """Render the interview monitoring page."""
    return render_template('langchain/monitor_session.html', session_id=session_id)

@app.route('/view_completed_interview/<session_id>')
def view_completed_interview(session_id):
    """Render the completed interview view page."""
    return render_template('langchain/view_completed_interview.html', session_id=session_id)

# Legacy routes
@app.route('/langchain_interview_test')
def legacy_interview_test():
    """Redirect for backward compatibility."""
    return redirect('/interview_test')

@app.route('/langchain_interview_setup')
def legacy_interview_setup():
    """Redirect for backward compatibility."""
    return redirect('/interview_setup')

@app.route('/langchain_interview_session')
def legacy_interview_session():
    """Redirect for backward compatibility."""
    return redirect('/interview_session')

# Handle nested routes from earlier approach
@app.route('/langchain/dashboard')
def langchain_dashboard():
    """Redirect to the dashboard route."""
    return redirect('/dashboard')

@app.route('/langchain/interview_test')
def langchain_interview_test():
    """Redirect to the interview test route."""
    return redirect('/interview_test')

@app.route('/langchain/interview_setup')
def langchain_interview_setup():
    """Redirect to the interview setup route."""
    return redirect('/interview_setup')

@app.route('/langchain/interview_session')
def langchain_interview_session():
    """Redirect to the interview session route."""
    return redirect('/interview_session')

# Prompt manager redirect for compatibility with navigation
@app.route('/prompt_manager/list_prompts')
def prompt_manager_redirect():
    """Redirect to the prompt manager route."""
    return redirect('/prompts/')

# API routes - both under /api and /langchain/api
@app.route('/api/diagnostics/microphone', methods=['POST'])
@app.route('/langchain/api/diagnostics/microphone', methods=['POST'])
def microphone_diagnostics():
    """Test microphone functionality."""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Empty audio file name"}), 400
            
        # In production, this would process the audio for diagnostics
        # For now, return a placeholder success response
        logger.info("Microphone test request received")
        
        return jsonify({
            "status": "success",
            "message": "Microphone is working correctly.",
            "audio_quality": "good"
        })
    except Exception as e:
        logger.error(f"Error testing microphone: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process_audio', methods=['POST'])
@app.route('/langchain/process_audio', methods=['POST'])
def process_audio():
    """Process audio file and return transcription."""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Empty audio file name"}), 400
            
        # In production, this would process the audio file
        # For now, return a placeholder transcription
        logger.info("Audio transcription request received")
        
        return jsonify({
            "transcript": "This is a placeholder transcription from the audio recording.",
            "success": True
        })
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/interview/start', methods=['POST'])
@app.route('/langchain/api/interview/start', methods=['POST'])
def start_interview():
    """Start a new LangChain interview."""
    try:
        data = request.json
        session_id = data.get('session_id', '')
        logger.info(f"Starting interview session: {session_id}")
        
        # Get the interview data for this session
        interview_data = {}
        character_name = None
        
        if hasattr(app, 'interviews') and session_id in app.interviews:
            interview_data = app.interviews[session_id]
            character_name = interview_data.get('character_select', '')
            logger.info(f"Using character: {character_name}")
            
            # Get the first question based on the character
            first_question = "Thank you for participating in this interview. Could you please introduce yourself and tell me about your background?"
            
            if character_name:
                # Here you would load specific character prompts
                # For now we'll use some default questions based on character
                if "UX" in character_name or "User" in character_name:
                    first_question = "Thank you for participating in this UX research interview. Could you tell me about your experience with user research methods?"
                elif "Data" in character_name:
                    first_question = "Thank you for participating in this data science interview. Could you tell me about your experience with data analysis?"
                elif "Developer" in character_name or "Engineer" in character_name:
                    first_question = "Thank you for participating in this technical interview. Could you tell me about your experience with software development?"
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            # Create a generic interview
            first_question = "Thank you for participating in this interview. Could you please introduce yourself?"
            
            # Store it for future reference
            if not hasattr(app, 'interviews'):
                app.interviews = {}
            app.interviews[session_id] = {
                "id": session_id,
                "title": "Interview Session",
                "created_at": datetime.datetime.now(),
                "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        
        # Return the first question to start the interview
        return jsonify({
            "response": first_question,
            "session_id": session_id,
            "status": "active"
        })
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({
            "error": "Failed to start interview",
            "details": str(e)
        }), 500

@app.route('/api/text_to_speech', methods=['POST'])
@app.route('/langchain/api/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using ElevenLabs API or browser fallback."""
    try:
        data = request.json
        text = data.get('text', '')
        session_id = data.get('session_id', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default to Rachel
        
        logger.info(f"Text-to-speech request for session {session_id}: {text[:50]}...")
        
        # Forward to the audio_tools service running on port 5007
        try:
            # Forward the request to the audio_tools simple_tts_test.py service
            tts_url = "http://127.0.0.1:5007/text_to_speech"
            
            response = requests.post(
                tts_url,
                json={
                    "text": text,
                    "voice_id": voice_id,
                    "session_id": session_id
                }
            )
            
            if response.status_code == 200:
                # Return the audio directly
                return Response(
                    response.content,
                    mimetype="audio/mpeg",
                    headers={"Content-Disposition": "attachment;filename=speech.mp3"}
                )
            else:
                logger.error(f"Error from ElevenLabs TTS service: {response.text}")
                return jsonify({"error": f"TTS service error: {response.text}"}), response.status_code
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to TTS service: {str(e)}")
            # Fall back to browser speech synthesis
            return jsonify({"error": "TTS service unavailable, falling back to browser synthesis", "text": text}), 500
            
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/text_to_speech_elevenlabs', methods=['POST'])
@app.route('/langchain/api/text_to_speech_elevenlabs', methods=['POST'])
def text_to_speech_elevenlabs():
    """Text to speech API endpoint using ElevenLabs."""
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default to Rachel voice if not specified
        
        logger.info(f"Received ElevenLabs request with text: '{text[:30]}...' and voice_id: {voice_id}")
        
        if not text:
            logger.error("No text provided for text-to-speech")
            return jsonify({'error': 'No text provided'}), 400
        
        # Forward to the audio_tools service running on port 5007
        try:
            # Forward the request to the audio_tools simple_tts_test.py service
            url = "http://127.0.0.1:5007/text_to_speech"
            
            audio_tools_data = {
                "text": text,
                "voice_id": voice_id
            }
            
            logger.info(f"Forwarding request to audio_tools service at {url}")
            response = requests.post(url, json=audio_tools_data)
            
            if response.status_code != 200:
                error_message = f"Audio tools service error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 500
            
            # Return the audio directly from the response
            logger.info(f"Received audio from audio_tools service, size: {len(response.content)} bytes")
            
            # Return audio file as response
            return send_file(
                BytesIO(response.content),
                mimetype='audio/mpeg',
                as_attachment=False
            )
            
        except Exception as proxy_error:
            logger.error(f"Error forwarding to audio_tools service: {str(proxy_error)}")
            
            # If forwarding fails, try direct API call as fallback
            logger.info("Falling back to direct ElevenLabs API call")
            
            # Get the ElevenLabs API key from environment
            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            if not elevenlabs_api_key:
                logger.error("ELEVENLABS_API_KEY not found in environment. Check .env file.")
                return jsonify({'error': 'ElevenLabs API key is not configured'}), 500
            
            # Make a direct API call to ElevenLabs
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_api_key
            }
            
            elevenlabs_data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            logger.info(f"Sending request to ElevenLabs API: {url}")
            response = requests.post(url, json=elevenlabs_data, headers=headers)
            
            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 500
            
            # Get audio data
            audio_data = BytesIO(response.content)
            
            logger.info(f"ElevenLabs text-to-speech conversion successful, size: {len(response.content)} bytes")
            
            # Return audio file as response
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False
            )
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/interview/respond', methods=['POST'])
@app.route('/langchain/api/interview/respond', methods=['POST'])
def respond_to_interview():
    """Process a user response and generate the next question."""
    try:
        data = request.json
        user_input = data.get('user_input', '')
        session_id = data.get('session_id', '')
        
        # Log the interaction
        logger.info(f"Processing user input for session {session_id}: {user_input[:50]}...")
        
        # Get interview data
        interview_data = None
        if hasattr(app, 'interviews') and session_id in app.interviews:
            interview_data = app.interviews[session_id]
            logger.info(f"Found interview data for session {session_id}")
            
            # In a production system, we would store the conversation history
            if 'conversation' not in interview_data:
                interview_data['conversation'] = []
            
            # Add the user's message to the conversation history
            interview_data['conversation'].append({
                "role": "user",
                "content": user_input
            })
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            if not hasattr(app, 'interviews'):
                app.interviews = {}
            
            # Create a new interview object
            app.interviews[session_id] = {
                "id": session_id,
                "title": "Interview Session",
                "created_at": datetime.datetime.now(),
                "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "conversation": [{
                    "role": "user", 
                    "content": user_input
                }]
            }
            interview_data = app.interviews[session_id]
        
        # Generate a response based on the user input
        # In a production system, you would use an AI model to generate this
        character_name = interview_data.get('character_select', '')
        
        # Generate a follow-up question based on the user's input
        response = generate_follow_up_question(user_input, character_name)
        
        # Add the AI's response to the conversation history
        interview_data['conversation'].append({
            "role": "assistant",
            "content": response
        })
        
        # Save updated interview data to disk
        save_interviews(app.interviews)
        
        return jsonify({
            "response": response,
            "session_id": session_id,
            "status": "active"
        })
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        return jsonify({
            "error": "Failed to process response",
            "details": str(e)
        }), 500

def generate_follow_up_question(user_input, character_name=""):
    """Generate a follow-up question based on the user's input."""
    # In a real system, this would use an AI model like Claude or GPT
    # For now, we'll use some simple pattern matching for demonstration
    
    # Convert input to lowercase for easier matching
    input_lower = user_input.lower()
    
    # Check for keywords to determine response
    if "experience" in input_lower or "background" in input_lower:
        return "That's interesting! Could you tell me more about a specific project or challenge you've worked on recently?"
    
    elif "project" in input_lower or "challenge" in input_lower:
        return "How did you approach that challenge? What methods or tools did you use?"
    
    elif "method" in input_lower or "tool" in input_lower or "approach" in input_lower:
        return "What were the outcomes or results of using that approach? Were there any unexpected findings?"
    
    elif "result" in input_lower or "outcome" in input_lower or "finding" in input_lower:
        return "If you could do that project again, what would you do differently? Have your methods evolved since then?"
    
    elif "team" in input_lower or "collaborate" in input_lower or "work with" in input_lower:
        return "How do you typically collaborate with others in your work? What's your preferred team structure?"
    
    elif "future" in input_lower or "plan" in input_lower or "goal" in input_lower:
        return "That's a great perspective. Where do you see your field evolving in the next few years?"
    
    # Character-specific responses
    elif character_name and "UX" in character_name:
        return "From a user experience perspective, how do you balance user needs with business requirements?"
    
    elif character_name and "Data" in character_name:
        return "How do you approach data quality issues in your analysis workflows?"
    
    elif character_name and ("Developer" in character_name or "Engineer" in character_name):
        return "What software development practices have you found most effective for maintaining code quality?"
    
    # Generic follow-up if no specific patterns match
    return "Thank you for sharing that. Could you tell me more about how that has influenced your current approach to your work?"

@app.route('/api/interview/end', methods=['POST'])
@app.route('/langchain/api/interview/end', methods=['POST'])
def end_interview():
    """End the interview session and save the transcript."""
    try:
        data = request.json
        session_id = data.get('session_id', '')
        
        logger.info(f"Ending interview session: {session_id}")
        
        # Get the interview data
        if hasattr(app, 'interviews') and session_id in app.interviews:
            interview_data = app.interviews[session_id]
            
            # Update the status
            interview_data['status'] = 'completed'
            interview_data['ended_at'] = datetime.datetime.now()
            interview_data['end_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # In a production system, you would save the transcript and analysis
            # For now, just log that we're ending the session
            logger.info(f"Interview {session_id} completed successfully")
            
            # Optional: generate a simple transcript from the conversation
            if 'conversation' in interview_data:
                conversation = interview_data['conversation']
                transcript = ""
                for entry in conversation:
                    role = "AI" if entry['role'] == 'assistant' else "User"
                    transcript += f"{role}: {entry['content']}\n\n"
                
                # Save the transcript in the interview data
                interview_data['transcript'] = transcript
                
                # Create a directory for transcripts if it doesn't exist
                transcript_dir = Path("transcripts")
                transcript_dir.mkdir(exist_ok=True)
                
                # Save the transcript to a file
                transcript_path = transcript_dir / f"{session_id}.txt"
                with open(transcript_path, 'w') as f:
                    f.write(transcript)
                    
                logger.info(f"Transcript saved to {transcript_path}")
                
                # Generate analysis if requested and an analysis prompt is available
                if interview_data.get('analysis', True):
                    try:
                        # Get the analysis prompt based on the character or use a default
                        analysis_prompt = ""
                        character_name = interview_data.get('character_select', '')
                        
                        if character_name:
                            # Try to load the character's analysis prompt
                            try:
                                config = prompt_manager.load_prompt(character_name)
                                analysis_prompt = config.get('analysis_prompt', '')
                                logger.info(f"Using analysis prompt from character: {character_name}")
                            except Exception as e:
                                logger.warning(f"Could not load character prompt: {str(e)}")
                        
                        # If no character-specific analysis prompt, use the one from the interview data
                        if not analysis_prompt:
                            analysis_prompt = interview_data.get('analysis_prompt', '')
                            logger.info("Using analysis prompt from interview data")
                        
                        # If we have an analysis prompt, generate the analysis
                        if analysis_prompt:
                            # Initialize OpenAI client for analysis
                            from langchain.llms import OpenAI
                            analysis_llm = OpenAI(temperature=0.2)
                            
                            # Prepare the prompt with the transcript
                            full_prompt = f"{analysis_prompt}\n\nInterview Transcript:\n{transcript}"
                            
                            # Generate the analysis
                            logger.info("Generating interview analysis...")
                            analysis = analysis_llm.predict(full_prompt)
                            
                            # Save the analysis in the interview data
                            interview_data['analysis_result'] = analysis
                            
                            # Save the analysis to a file
                            analysis_dir = Path("analyses")
                            analysis_dir.mkdir(exist_ok=True)
                            
                            analysis_path = analysis_dir / f"{session_id}.txt"
                            with open(analysis_path, 'w') as f:
                                f.write(analysis)
                                
                            logger.info(f"Analysis saved to {analysis_path}")
                    except Exception as e:
                        logger.error(f"Error generating analysis: {str(e)}")
                        # Continue with saving the interview data even if analysis fails
            
            # Save updated interview data to disk
            save_interviews(app.interviews)
            
            return jsonify({
                "success": True,
                "message": "Interview ended successfully",
                "session_id": session_id
            })
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            return jsonify({
                "success": False,
                "error": "Interview session not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error ending interview: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/character/<character_name>', methods=['GET'])
def get_character(character_name):
    """Get a character's prompt data."""
    try:
        config = prompt_manager.load_prompt(character_name)
        logger.info(f"Retrieved character data for {character_name}: {config.get('role', '')}")
        return jsonify({
            'success': True,
            'name': config.get('agent_name', character_name),
            'role': config.get('role', ''),
            'description': config.get('description', ''),
            'dynamic_prompt_prefix': config.get('dynamic_prompt_prefix', ''),
            'analysis_prompt': config.get('analysis_prompt', '')
        })
    except Exception as e:
        logger.error(f"Error loading prompt for {character_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

@app.route('/interview/create', methods=['POST'])
@app.route('/langchain/interview/create', methods=['POST'])
def create_interview():
    """Create a new interview from the setup form."""
    try:
        data = request.json
        logger.info(f"Creating interview with data: {data}")
        
        # Save character data if using a character
        character_name = data.get('character_select', '')
        if character_name:
            try:
                # Check if this is a custom character name that doesn't exist yet
                is_custom_character = False
                try:
                    prompt_manager.load_prompt(character_name)
                except FileNotFoundError:
                    is_custom_character = True
                
                if is_custom_character or character_name.lower() == 'custom':
                    # Create or update the character with the provided prompts
                    config = {
                        'agent_name': character_name,
                        'role': data.get('interview_type', 'UX Researcher'),
                        'description': f"Interview persona for {data.get('title', 'Untitled Interview')}",
                        'dynamic_prompt_prefix': data.get('interview_prompt', ''),
                        'analysis_prompt': data.get('analysis_prompt', '')
                    }
                    prompt_manager.save_prompt(character_name, config)
                    logger.info(f"Saved character data for {character_name}")
            except Exception as e:
                logger.error(f"Error saving character data: {str(e)}")
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create timestamps for both created_at and creation_date
        now = datetime.datetime.now()
        
        # Add created_at as datetime object and creation_date as formatted string
        data['created_at'] = now
        data['creation_date'] = now.strftime("%Y-%m-%d %H:%M")
        
        # Add expiration date (30 days from now)
        expiration_date = now + datetime.timedelta(days=30)
        data['expiration_date'] = expiration_date
        
        logger.info(f"Generated session ID: {session_id}")
        redirect_url = f"/interview_details/{session_id}"
        logger.info(f"Redirecting to: {redirect_url}")
        
        # Store the interview data with the session_id as the key
        if not hasattr(app, 'interviews'):
            app.interviews = {}
        
        app.interviews[session_id] = data
        logger.info(f"Stored interview data with ID: {session_id}")
        
        # Save interviews to disk
        save_interviews(app.interviews)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "redirect_url": redirect_url
        })
    except Exception as e:
        logger.error(f"Error creating interview: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Add favicon route to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/debug/prompts')
def debug_prompts():
    """Debug endpoint to list all available prompts."""
    try:
        prompt_files = list(Path(PROMPT_DIR).glob("*.yml"))
        prompts = []
        
        for file in prompt_files:
            try:
                with open(file, 'r') as f:
                    content = yaml.safe_load(f)
                    prompts.append({
                        'filename': file.name,
                        'agent_name': content.get('agent_name', file.stem),
                        'role': content.get('role', ''),
                        'version': content.get('version', 'unknown')
                    })
            except Exception as e:
                prompts.append({
                    'filename': file.name,
                    'error': str(e)
                })
        
        return jsonify({
            'prompt_dir': str(PROMPT_DIR),
            'history_dir': str(HISTORY_DIR),
            'prompts': prompts
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/interview/update-status', methods=['POST'])
@app.route('/langchain/api/interview/update-status', methods=['POST'])
def update_interview_status():
    """Update the status of an interview."""
    try:
        data = request.json
        session_id = data.get('session_id')
        is_active = data.get('is_active', True)
        
        # In a production system, this would update the database
        logger.info(f"Updating interview status for {session_id}: is_active={is_active}")
        
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

@app.route('/api/interview/update-expiration', methods=['POST'])
@app.route('/langchain/api/interview/update-expiration', methods=['POST'])
def update_interview_expiration():
    """Update the expiration date of an interview."""
    try:
        data = request.json
        session_id = data.get('session_id')
        expiration_date = data.get('expiration_date')
        
        # In a production system, this would update the database
        logger.info(f"Updating interview expiration for {session_id}: expiration_date={expiration_date}")
        
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

@app.route('/langchain/interview/session/<session_id>')
def langchain_interview_session_with_id(session_id):
    """Handle interview session with a specific ID."""
    logger.info(f"Accessing interview session with ID: {session_id}")
    
    # Check if we have interview data for this session
    interview_data = None
    if hasattr(app, 'interviews') and session_id in app.interviews:
        interview_data = app.interviews[session_id]
        logger.info(f"Found interview data for session {session_id}: {interview_data.get('title', 'Untitled Interview')}")
    else:
        logger.warning(f"No interview data found for session: {session_id}")
        # Initialize an empty interview object if not found
        interview_data = {
            "id": session_id,
            "title": "Interview Session",
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        # Store it for future use
        if not hasattr(app, 'interviews'):
            app.interviews = {}
        app.interviews[session_id] = interview_data
        logger.info(f"Created new interview data for session: {session_id}")
    
    # Pass the session_id and interview data to the interview_session template
    return render_template('langchain/interview_session.html', 
                          session_id=session_id,
                          interview=interview_data)

@app.route('/api/interviews', methods=['GET'])
@app.route('/langchain/api/interviews', methods=['GET'])
def get_interviews():
    """Get a list of all interviews."""
    try:
        # Return the in-memory interviews if available
        interviews = []
        if hasattr(app, 'interviews'):
            for session_id, interview_data in app.interviews.items():
                # Create a summary of each interview for the list
                interview_summary = {
                    "id": session_id,
                    "title": interview_data.get("title", "Untitled Interview"),
                    "created_at": interview_data.get("creation_date", "Unknown date"),
                    "status": interview_data.get("status", "active"),
                    "project": interview_data.get("project", ""),
                }
                interviews.append(interview_summary)
        
        logger.info(f"Returning {len(interviews)} interviews")
        return jsonify({
            "status": "success",
            "interviews": interviews
        })
    except Exception as e:
        logger.error(f"Error getting interviews: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/speech_to_text', methods=['POST'])
@app.route('/langchain/api/speech_to_text', methods=['POST'])
def speech_to_text():
    """Convert speech to text using ElevenLabs API."""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', '')
        
        logger.info(f"Speech-to-text request received for session {session_id}")
        
        # Forward to the audio_tools service running on port 5007
        try:
            # Forward the request to the audio_tools simple_tts_test.py service
            stt_url = "http://127.0.0.1:5007/speech_to_text"
            
            # Create a new multipart form request
            files = {'audio': (audio_file.filename, audio_file.stream, audio_file.content_type)}
            data = {'session_id': session_id}
            
            response = requests.post(stt_url, files=files, data=data)
            
            if response.status_code == 200:
                # Return the transcription result
                return jsonify(response.json())
            else:
                logger.error(f"Error from ElevenLabs STT service: {response.text}")
                return jsonify({"error": f"STT service error: {response.text}"}), response.status_code
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to STT service: {str(e)}")
            return jsonify({"error": f"STT service unavailable: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_services', methods=['GET'])
@app.route('/langchain/api/check_services', methods=['GET'])
def check_services():
    """Check if the required services are running."""
    try:
        services = {
            "main": {
                "status": "ok",
                "message": "Main application running"
            },
            "audio_tools": {
                "status": "unknown",
                "message": "Checking audio tools service..."
            }
        }
        
        # Check if the audio_tools service is running
        try:
            response = requests.get("http://127.0.0.1:5007/", timeout=2)
            if response.status_code == 200:
                services["audio_tools"] = {
                    "status": "ok",
                    "message": "Audio tools service running"
                }
            else:
                services["audio_tools"] = {
                    "status": "error",
                    "message": f"Audio tools service returned status code {response.status_code}"
                }
        except requests.RequestException as e:
            services["audio_tools"] = {
                "status": "error",
                "message": f"Audio tools service not available: {str(e)}"
            }
        
        # Determine overall status
        if all(service["status"] == "ok" for service in services.values()):
            overall_status = "ok"
        else:
            overall_status = "degraded"
            
        return jsonify({
            "status": overall_status,
            "services": services,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking services: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# Add API endpoint to generate analysis on demand
@app.route('/api/interview/generate_analysis', methods=['POST'])
@app.route('/langchain/api/interview/generate_analysis', methods=['POST'])
def generate_analysis():
    """Generate analysis for an interview transcript."""
    try:
        data = request.json
        session_id = data.get('session_id', '')
        
        logger.info(f"Generating analysis for interview session: {session_id}")
        
        # Get the interview data
        if hasattr(app, 'interviews') and session_id in app.interviews:
            interview_data = app.interviews[session_id]
            
            # Check if we have a transcript to analyze
            if 'transcript' not in interview_data or not interview_data['transcript']:
                logger.warning(f"No transcript found for session: {session_id}")
                return jsonify({
                    "success": False,
                    "error": "No transcript found for this interview"
                }), 400
            
            transcript = interview_data['transcript']
            
            # Get the analysis prompt based on the character or use a default
            analysis_prompt = ""
            character_name = interview_data.get('character_select', '')
            
            if character_name:
                # Try to load the character's analysis prompt
                try:
                    config = prompt_manager.load_prompt(character_name)
                    analysis_prompt = config.get('analysis_prompt', '')
                    logger.info(f"Using analysis prompt from character: {character_name}")
                except Exception as e:
                    logger.warning(f"Could not load character prompt: {str(e)}")
            
            # If no character-specific analysis prompt, use the one from the interview data
            if not analysis_prompt:
                analysis_prompt = interview_data.get('analysis_prompt', '')
                logger.info("Using analysis prompt from interview data")
            
            # If we still don't have an analysis prompt, use a default
            if not analysis_prompt:
                analysis_prompt = """Analyze this interview transcript and provide insights about:
                
1. Key points and themes discussed
2. User needs, goals, and pain points identified
3. Notable quotes or insights
4. Recommendations based on the discussion"""
                logger.info("Using default analysis prompt")
            
            # Initialize OpenAI client for analysis
            from langchain.llms import OpenAI
            analysis_llm = OpenAI(temperature=0.2)
            
            # Prepare the prompt with the transcript
            full_prompt = f"{analysis_prompt}\n\nInterview Transcript:\n{transcript}"
            
            # Generate the analysis
            logger.info("Generating interview analysis...")
            analysis = analysis_llm.predict(full_prompt)
            
            # Save the analysis in the interview data
            interview_data['analysis_result'] = analysis
            
            # Save the analysis to a file
            analysis_dir = Path("analyses")
            analysis_dir.mkdir(exist_ok=True)
            
            analysis_path = analysis_dir / f"{session_id}.txt"
            with open(analysis_path, 'w') as f:
                f.write(analysis)
                
            logger.info(f"Analysis saved to {analysis_path}")
            
            # Save updated interview data to disk
            save_interviews(app.interviews)
            
            return jsonify({
                "success": True,
                "message": "Analysis generated successfully"
            })
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            return jsonify({
                "success": False,
                "error": "Interview session not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error generating analysis: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Add API endpoint to save notes
@app.route('/api/interview/save_notes', methods=['POST'])
@app.route('/langchain/api/interview/save_notes', methods=['POST'])
def save_notes():
    """Save notes for an interview."""
    try:
        data = request.json
        session_id = data.get('session_id', '')
        notes = data.get('notes', '')
        
        logger.info(f"Saving notes for interview session: {session_id}")
        
        # Get the interview data
        if hasattr(app, 'interviews') and session_id in app.interviews:
            interview_data = app.interviews[session_id]
            
            # Save the notes
            interview_data['notes'] = notes
            
            # Save updated interview data to disk
            save_interviews(app.interviews)
            
            return jsonify({
                "success": True,
                "message": "Notes saved successfully"
            })
        else:
            logger.warning(f"No interview data found for session: {session_id}")
            return jsonify({
                "success": False,
                "error": "Interview session not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error saving notes: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = args.port
    print(f"Starting LangChain Interview Prototype on port {port}...")
    print(f"Access the application at: http://127.0.0.1:{port}")
    print(f"Dashboard: http://127.0.0.1:{port}/dashboard")
    print(f"Interview Test: http://127.0.0.1:{port}/interview_test")
    print(f"Interview Setup: http://127.0.0.1:{port}/interview_setup")
    print(f"Prompt Manager: http://127.0.0.1:{port}/prompts/")
    
    try:
        app.run(host='127.0.0.1', port=port, debug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} is already in use.")
            print(f"Try running with a different port: python {sys.argv[0]} --port {port+1}")
        else:
            raise 