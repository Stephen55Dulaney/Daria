from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from pathlib import Path
import json
import logging
import os
import uuid
import tempfile
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
from io import BytesIO

logger = logging.getLogger(__name__)

langchain_bp = Blueprint('langchain', __name__, url_prefix='/langchain')

@langchain_bp.route('/interview_test')
@login_required
def interview_test():
    """LangChain Interview Test Page."""
    try:
        return render_template('langchain/interview_session.html')
    except Exception as e:
        logger.error(f"Error loading interview test page: {str(e)}")
        return render_template('error.html')

@langchain_bp.route('/dashboard')
@login_required
def dashboard():
    """LangChain Interview Dashboard."""
    try:
        # Get list of interviews
        interviews = []
        INTERVIEWS_DIR = Path('interviews/raw')
        if INTERVIEWS_DIR.exists():
            for file in sorted(INTERVIEWS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        interviews.append(data)
                        logger.info(f"Loaded interview: {data.get('title')} with ID: {data.get('id')}")
                except Exception as e:
                    logger.error(f"Error loading interview {file}: {str(e)}")
                    continue

        # Count interview statuses
        active_interviews = len([i for i in interviews if i.get('status') == 'active'])
        completed_sessions = len([i for i in interviews if i.get('status') == 'completed'])
        in_progress = len([i for i in interviews if i.get('status') == 'in_progress'])

        return render_template('langchain/dashboard.html',
                             interviews=interviews,
                             active_interviews=active_interviews,
                             completed_sessions=completed_sessions,
                             in_progress=in_progress)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('error.html')

@langchain_bp.route('/interview/new', methods=['GET', 'POST'])
@login_required
def new_interview():
    """Create a new interview."""
    if request.method == 'POST':
        # Handle interview creation
        pass
    return render_template('langchain/interview_setup.html')

@langchain_bp.route('/interview/<interview_id>')
@login_required
def view_interview(interview_id):
    """View an existing interview."""
    try:
        interview_file = Path(f'interviews/raw/{interview_id}.json')
        if not interview_file.exists():
            flash('Interview not found', 'error')
            return redirect(url_for('langchain.dashboard'))

        with open(interview_file, 'r') as f:
            interview = json.load(f)

        return render_template('langchain/interview_session.html', interview=interview)
    except Exception as e:
        logger.error(f"Error loading interview {interview_id}: {str(e)}")
        return render_template('error.html')

@langchain_bp.route('/interview_setup')
@login_required
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
    
    # Default interview prompt
    interview_prompt = "You are an expert UX researcher conducting a user interview. Ask open-ended questions to understand the user's needs, goals, and pain points. Be conversational, empathetic, and curious."
    
    return render_template('langchain/interview_setup.html', 
                          interview_prompt=interview_prompt,
                          voices=voices)

# API endpoints for Langchain features
@langchain_bp.route('/api/interview/start', methods=['POST'])
@login_required
def api_interview_start():
    """Start a new interview."""
    try:
        data = request.json
        interview_id = data.get('interview_id', str(uuid.uuid4()))
        title = data.get('title', 'New Interview')
        description = data.get('description', '')
        
        interview_data = {
            'id': interview_id,
            'title': title,
            'description': description,
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'user_id': current_user.id if current_user.is_authenticated else None,
            'messages': []
        }
        
        # Create interviews directory if it doesn't exist
        interviews_dir = Path('interviews/raw')
        interviews_dir.mkdir(parents=True, exist_ok=True)
        
        # Save interview data
        with open(interviews_dir / f"{interview_id}.json", 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        return jsonify({
            'success': True, 
            'interview_id': interview_id,
            'redirect_url': url_for('langchain.view_interview', interview_id=interview_id)
        })
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@langchain_bp.route('/api/interview/respond', methods=['POST'])
@login_required
def api_interview_respond():
    """Respond to an interview message."""
    try:
        data = request.json
        interview_id = data.get('interview_id')
        message = data.get('message', '')
        
        if not interview_id:
            return jsonify({'success': False, 'error': 'Interview ID is required'}), 400
        
        # Load interview data
        interview_file = Path(f'interviews/raw/{interview_id}.json')
        if not interview_file.exists():
            return jsonify({'success': False, 'error': 'Interview not found'}), 404
        
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
        
        # Add message to interview
        new_message = {
            'id': str(uuid.uuid4()),
            'content': message,
            'role': 'user',
            'timestamp': datetime.now().isoformat()
        }
        
        if 'messages' not in interview_data:
            interview_data['messages'] = []
        
        interview_data['messages'].append(new_message)
        interview_data['updated_at'] = datetime.now().isoformat()
        
        # Save updated interview data
        with open(interview_file, 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        # Generate AI response (placeholder)
        ai_response = "Thank you for your response. This is a placeholder AI message."
        
        ai_message = {
            'id': str(uuid.uuid4()),
            'content': ai_response,
            'role': 'assistant',
            'timestamp': datetime.now().isoformat()
        }
        
        interview_data['messages'].append(ai_message)
        
        # Save updated interview data
        with open(interview_file, 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
    except Exception as e:
        logger.error(f"Error responding to interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@langchain_bp.route('/api/interview/complete', methods=['POST'])
@login_required
def api_interview_complete():
    """Complete an interview."""
    try:
        data = request.json
        interview_id = data.get('interview_id')
        
        if not interview_id:
            return jsonify({'success': False, 'error': 'Interview ID is required'}), 400
        
        # Load interview data
        interview_file = Path(f'interviews/raw/{interview_id}.json')
        if not interview_file.exists():
            return jsonify({'success': False, 'error': 'Interview not found'}), 404
        
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
        
        # Update interview status
        interview_data['status'] = 'completed'
        interview_data['updated_at'] = datetime.now().isoformat()
        
        # Save updated interview data
        with open(interview_file, 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'redirect_url': url_for('langchain.dashboard')
        })
    except Exception as e:
        logger.error(f"Error completing interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@langchain_bp.route('/api/diagnostics/microphone', methods=['POST'])
def api_diagnostics_microphone():
    """Process microphone diagnostics."""
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"success": False, "error": "Empty audio file name"}), 400
            
        filename = secure_filename(audio_file.filename or f"recording_{uuid.uuid4()}.wav")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        audio_file.save(file_path)
        
        # For testing, just return success
        return jsonify({
            "success": True,
            "message": "Microphone test successful",
            "audio_level": 0.75
        })
    except Exception as e:
        logger.error(f"Error in microphone diagnostics: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@langchain_bp.route('/api/interview/transcript', methods=['GET'])
@login_required
def api_interview_transcript():
    """Get transcript of an interview."""
    try:
        interview_id = request.args.get('interview_id')
        
        if not interview_id:
            return jsonify({'success': False, 'error': 'Interview ID is required'}), 400
        
        # Load interview data
        interview_file = Path(f'interviews/raw/{interview_id}.json')
        if not interview_file.exists():
            return jsonify({'success': False, 'error': 'Interview not found'}), 404
        
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
        
        # Extract messages
        messages = interview_data.get('messages', [])
        
        # Format transcript
        transcript = []
        for msg in messages:
            role = 'Interviewer' if msg.get('role') == 'assistant' else 'Participant'
            transcript.append(f"{role}: {msg.get('content', '')}")
        
        transcript_text = "\n\n".join(transcript)
        
        # Create a temporary file to store the transcript
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
        temp_file.write(transcript_text)
        temp_file.close()
        
        # Return the file
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f"interview_{interview_id}_transcript.txt",
            mimetype='text/plain'
        )
    except Exception as e:
        logger.error(f"Error getting interview transcript: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@langchain_bp.route('/api/text_to_speech_elevenlabs', methods=['POST'])
def api_text_to_speech_elevenlabs():
    """Text to speech API endpoint using ElevenLabs."""
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default to Rachel voice if not specified
        
        if not text:
            logger.error("No text provided for text-to-speech")
            return jsonify({'error': 'No text provided'}), 400
        
        logger.info(f"Text-to-speech request received: {text[:30]}...")
        
        # Get the ElevenLabs API key from environment
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not elevenlabs_api_key:
            logger.error("ELEVENLABS_API_KEY not found in environment")
            return jsonify({'error': 'ElevenLabs API key is not configured'}), 500
        
        # Make a direct API call to ElevenLabs
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 500
            
            # Get audio data
            audio_data = BytesIO(response.content)
            
            logger.info(f"Text-to-speech conversion successful, size: {len(response.content)} bytes")
            
            # Return audio file as response
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False
            )
            
        except Exception as elevenlabs_error:
            logger.error(f"ElevenLabs API error: {str(elevenlabs_error)}")
            return jsonify({'error': f'ElevenLabs API error: {str(elevenlabs_error)}'}), 500
        
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({'error': str(e)}), 500

@langchain_bp.route('/process_audio', methods=['POST'])
def api_process_audio():
    """Process audio file and return transcription."""
    try:
        project_name = request.args.get('project_name', 'Default Project')
        
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"success": False, "error": "Empty audio file name"}), 400
            
        filename = secure_filename(audio_file.filename or f"recording_{uuid.uuid4()}.wav")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        audio_file.save(file_path)
        
        # For testing, return a placeholder transcription
        return jsonify({
            "success": True,
            "transcription": "This is a placeholder transcription for the recorded audio.",
            "confidence": 0.95
        })
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500 