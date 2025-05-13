#!/usr/bin/env python3
"""
Direct Text-to-Speech service for the DARIA Interview Tool
Simplified version that directly calls ElevenLabs API without complex dependencies
"""

import os
import sys
import argparse
import logging
import requests
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('../logs/direct_tts.log')
    ]
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run Direct TTS Service')
parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Check if ElevenLabs API key is set
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
if ELEVENLABS_API_KEY:
    logger.info("ElevenLabs API key is configured")
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

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint for the service."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        return response
        
    return jsonify({
        'status': 'ok', 
        'service': 'Direct TTS Service', 
        'api_key_configured': bool(ELEVENLABS_API_KEY)
    })

@app.route('/text_to_speech', methods=['POST', 'OPTIONS'])
def text_to_speech():
    """Convert text to speech using ElevenLabs API."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Get request data
        data = request.json
        if not data:
            logger.error("Missing request data")
            return jsonify({'error': 'Missing request data'}), 400
            
        text = data.get('text', '')
        voice_id = data.get('voice_id', DEFAULT_VOICE_ID)
        session_id = data.get('session_id', 'no_session')
        
        if not text:
            logger.error("Missing text parameter")
            return jsonify({'error': 'Missing text parameter'}), 400
        
        logger.info(f"Processing TTS request - {len(text)} chars, voice: {voice_id}, session: {session_id}")
        
        # If ElevenLabs API key is configured, use it
        if ELEVENLABS_API_KEY:
            try:
                # Direct API call to ElevenLabs
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY
                }
                
                payload = {
                    "text": text,
                    "model_id": DEFAULT_MODEL_ID,
                    "voice_settings": DEFAULT_VOICE_SETTINGS
                }
                
                logger.info(f"Calling ElevenLabs API with voice ID: {voice_id}")
                
                # Send the request to ElevenLabs
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"ElevenLabs success - received {len(response.content)} bytes")
                    
                    # Return the audio directly with CORS headers to avoid permission issues
                    audio_response = Response(response.content, mimetype='audio/mpeg')
                    audio_response.headers.add('Access-Control-Allow-Origin', '*')
                    return audio_response
                else:
                    logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
                    return jsonify({
                        'success': False, 
                        'error': f"ElevenLabs API error: {response.status_code}"
                    }), response.status_code
            
            except Exception as e:
                logger.error(f"Error with ElevenLabs: {str(e)}")
                # Continue to fallback
        
        # Fallback for when ElevenLabs is not available
        logger.info("Using browser speech synthesis fallback")
        fallback_response = {
            'success': True,
            'text': text,
            'fallback': True,
            'message': 'Using browser speech synthesis fallback'
        }
        
        return jsonify(fallback_response)
    
    except Exception as e:
        logger.error(f"Unexpected error in TTS service: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == "__main__":
    try:
        logger.info(f"Starting Direct TTS service on port {args.port}")
        print(f"Starting Direct TTS Service on port {args.port}")
        print(f"Health check endpoint: http://127.0.0.1:{args.port}/health")
        print(f"API endpoint: http://127.0.0.1:{args.port}/text_to_speech")
        app.run(host='0.0.0.0', port=args.port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start Direct TTS service: {str(e)}")
        sys.exit(1) 