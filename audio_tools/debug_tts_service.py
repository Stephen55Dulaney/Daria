#!/usr/bin/env python3
"""
Debug Text-to-Speech service for the DARIA Interview Tool
Enhanced version with more logging and debugging options
"""

import os
import sys
import argparse
import logging
import time
import json
from flask import Flask, request, Response, jsonify, render_template
from flask_cors import CORS
import requests
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/debug_tts.log')
    ]
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run Debug TTS Service')
parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()

if args.debug:
    logger.setLevel(logging.DEBUG)
    logger.info("Debug mode enabled - verbose logging activated")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Check if ElevenLabs API key is set
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

if ELEVENLABS_API_KEY:
    logger.info("ElevenLabs API key found. ElevenLabs TTS will be available.")
else:
    logger.warning("No ElevenLabs API key found in environment. ElevenLabs TTS will not be available.")
    logger.warning("Set ELEVENLABS_API_KEY environment variable to enable ElevenLabs.")

# Default voices
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Rachel
DEFAULT_MODEL_ID = "eleven_monolingual_v1"
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.71,
    "similarity_boost": 0.5
}

# Dictionary to track requests
request_log = {}
request_counter = 0
lock = threading.Lock()

def log_request(request_id, request_data, response_status, response_data=None):
    """Log request and response details"""
    with lock:
        request_log[request_id] = {
            'timestamp': time.time(),
            'request': request_data,
            'response_status': response_status,
            'response_data': response_data
        }
        # Keep only the most recent 100 requests
        if len(request_log) > 100:
            oldest_key = min(request_log.keys())
            del request_log[oldest_key]

@app.route('/')
def index():
    """Serve a simple debug interface"""
    return render_template('debug_tts.html', elevenlabs_enabled=bool(ELEVENLABS_API_KEY))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service."""
    return jsonify({
        'status': 'ok',
        'service': 'debug_tts',
        'elevenlabs_enabled': bool(ELEVENLABS_API_KEY),
        'request_count': len(request_log)
    })

@app.route('/requests', methods=['GET'])
def view_requests():
    """View recent request history"""
    return jsonify(request_log)

@app.route('/clear_requests', methods=['POST'])
def clear_requests():
    """Clear request history"""
    global request_log
    request_log = {}
    return jsonify({'status': 'ok', 'message': 'Request history cleared'})

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using ElevenLabs with detailed logging"""
    global request_counter
    
    try:
        # Get request data
        start_time = time.time()
        request_counter += 1
        request_id = request_counter
        
        # Parse request
        data = request.json
        if not data or not data.get('text'):
            logger.error(f"Request {request_id}: Missing text parameter")
            log_request(request_id, data, 'error', 'Missing text parameter')
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data.get('text', '')
        voice_id = data.get('voice_id', DEFAULT_VOICE_ID)
        session_id = data.get('session_id', 'no_session')
        
        logger.info(f"Request {request_id}: Processing TTS request - {len(text)} chars, voice: {voice_id}, session: {session_id}")
        if args.debug:
            logger.debug(f"Request {request_id}: Text content: {text[:100]}...")
        
        # Try ElevenLabs first if API key is available
        if ELEVENLABS_API_KEY:
            try:
                logger.info(f"Request {request_id}: Calling ElevenLabs API with voice ID: {voice_id}")
                
                # Call ElevenLabs API directly
                url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY
                }
                
                data = {
                    "text": text,
                    "model_id": DEFAULT_MODEL_ID,
                    "voice_settings": DEFAULT_VOICE_SETTINGS
                }
                
                # Make the request to ElevenLabs
                elevenlabs_response = requests.post(url, json=data, headers=headers)
                
                if elevenlabs_response.status_code == 200:
                    audio_content = elevenlabs_response.content
                    logger.info(f"Request {request_id}: ElevenLabs success - received {len(audio_content)} bytes in {time.time() - start_time:.2f}s")
                    
                    log_request(request_id, {
                        'text': text[:100] + '...' if len(text) > 100 else text,
                        'voice_id': voice_id,
                        'session_id': session_id
                    }, 'success', {'size': len(audio_content)})
                    
                    return Response(audio_content, mimetype='audio/mpeg')
                else:
                    error_msg = f"ElevenLabs error: {elevenlabs_response.status_code} - {elevenlabs_response.text}"
                    logger.error(f"Request {request_id}: {error_msg}")
                    log_request(request_id, {
                        'text': text[:100] + '...' if len(text) > 100 else text,
                        'voice_id': voice_id,
                        'session_id': session_id
                    }, 'error', error_msg)
                    # Fall back to browser TTS
            
            except Exception as e:
                logger.error(f"Request {request_id}: Error with ElevenLabs TTS: {str(e)}")
                log_request(request_id, {
                    'text': text[:100] + '...' if len(text) > 100 else text,
                    'voice_id': voice_id,
                    'session_id': session_id
                }, 'error', str(e))
                # Continue to fallback
        
        # Fall back to a simple text response that the browser can use for speech synthesis
        logger.info(f"Request {request_id}: Using fallback TTS response")
        fallback_response = {
            'success': True,
            'text': text,
            'voice': voice_id,
            'message': 'Please use browser speech synthesis API for fallback TTS'
        }
        
        log_request(request_id, {
            'text': text[:100] + '...' if len(text) > 100 else text,
            'voice_id': voice_id,
            'session_id': session_id
        }, 'fallback')
        
        return jsonify(fallback_response)
    
    except Exception as e:
        logger.error(f"Request {request_id if 'request_id' in locals() else 'unknown'}: Unexpected error in TTS service: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_page():
    """Test page for TTS"""
    return render_template('tts_test.html', 
                           elevenlabs_enabled=bool(ELEVENLABS_API_KEY),
                           voices=[
                               {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel (Female)"},
                               {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Adam (Male)"},
                               {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi (Female)"},
                               {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli (Female)"},
                               {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh (Male)"},
                               {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam (Male)"}
                           ])

if __name__ == "__main__":
    try:
        logger.info(f"Starting Debug TTS service on port {args.port}")
        app.run(host='0.0.0.0', port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Failed to start Debug TTS service: {str(e)}")
        sys.exit(1) 