#!/usr/bin/env python
import os
import sys
import logging
import uuid
import json
import tempfile
import argparse
from pathlib import Path
from flask import Flask, redirect, url_for, render_template, Blueprint, send_from_directory, request, jsonify
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run LangChain Interview Prototype')
parser.add_argument('--port', type=int, default=5010, help='Port to run the server on')
args = parser.parse_args()

# Ensure SKIP_EVENTLET is set for Python 3.13 compatibility
os.environ['SKIP_EVENTLET'] = '1'

# Create Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
app.secret_key = str(uuid.uuid4())

# Create blueprint for langchain routes
langchain_bp = Blueprint('langchain', __name__, url_prefix='/langchain')

# Register the blueprint
app.register_blueprint(langchain_bp)

# Add a redirect from root to dashboard
@app.route('/')
def index():
    return redirect('/langchain/dashboard')

# Import the template routes
@langchain_bp.route('/dashboard')
def dashboard():
    """Render the langchain dashboard."""
    return render_template('langchain/dashboard.html')

@langchain_bp.route('/interview_test')
def interview_test():
    """Render the interview test page."""
    return render_template('langchain/interview_session.html')

@langchain_bp.route('/interview_setup')
def interview_setup():
    """Render the interview setup page."""
    return render_template('langchain/interview_setup.html')

@langchain_bp.route('/interview_session')
def interview_session():
    """Render the interview session page."""
    return render_template('langchain/interview_session.html')

# Legacy routes
@app.route('/langchain_interview_test')
def legacy_interview_test():
    """Redirect for backward compatibility."""
    return redirect('/langchain/interview_test')

@app.route('/langchain_interview_setup')
def legacy_interview_setup():
    """Redirect for backward compatibility."""
    return redirect('/langchain/interview_setup')

@app.route('/langchain_interview_session')
def legacy_interview_session():
    """Redirect for backward compatibility."""
    return redirect('/langchain/interview_session')

# Add API endpoints
@app.route('/api/diagnostics/microphone', methods=['POST'])
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

@app.route('/api/langchain/interview/start', methods=['POST'])
def start_interview():
    """Start a new LangChain interview."""
    try:
        data = request.json
        
        # In production, this would initialize an interview session
        # For now, return a placeholder response
        logger.info("Interview start request received")
        
        return jsonify({
            "interview_id": str(uuid.uuid4()),
            "first_question": "Thank you for participating in this interview. Could you please introduce yourself and tell me about your background?",
            "success": True
        })
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using TTS service."""
    try:
        data = request.json
        text = data.get('text', '')
        
        # In production, this would call a TTS service
        # For now, return a placeholder audio file
        logger.info(f"Text-to-speech request received: {text[:30]}...")
        
        return jsonify({
            "status": "success",
            "message": "Text converted to speech successfully."
        })
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add favicon route to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    port = args.port
    print(f"Starting LangChain Interview Prototype on port {port}...")
    print(f"Access the application at: http://127.0.0.1:{port}")
    print(f"LangChain Dashboard: http://127.0.0.1:{port}/langchain/dashboard")
    print(f"Interview Test: http://127.0.0.1:{port}/langchain/interview_test")
    print(f"Interview Setup: http://127.0.0.1:{port}/langchain/interview_setup")
    
    try:
        app.run(host='127.0.0.1', port=port, debug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} is already in use.")
            print(f"Try running with a different port: python {sys.argv[0]} --port {port+1}")
        else:
            raise 