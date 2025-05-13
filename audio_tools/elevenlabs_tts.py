#!/usr/bin/env python3
"""
ElevenLabs Text-to-Speech Service for DARIA Interview Tool
"""

import os
import logging
import argparse
from typing import Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run ElevenLabs TTS Service')
parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# Default voice settings
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Rachel voice
DEFAULT_MODEL_ID = "eleven_monolingual_v1"
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75
}

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint for the service."""
    if request.method == 'OPTIONS':
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        return response
        
    return jsonify({"status": "ok", "service": "ElevenLabs TTS Service", "api_key_configured": bool(ELEVENLABS_API_KEY)})

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
            logger.error("No JSON data provided in request")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        if not text:
            logger.error("No text provided in request")
            return jsonify({'error': 'No text provided'}), 400
        
        # Get voice settings
        voice_id = data.get('voice_id', DEFAULT_VOICE_ID)
        model_id = data.get('model_id', DEFAULT_MODEL_ID)
        voice_settings = data.get('voice_settings', DEFAULT_VOICE_SETTINGS)
        
        # Log the request
        logger.info(f"TTS Request: {len(text)} chars, voice_id: {voice_id}")
        
        # Call ElevenLabs API if key is configured
        if ELEVENLABS_API_KEY:
            logger.info(f"Calling ElevenLabs API for voice_id: {voice_id}")
            audio_data = call_elevenlabs_api(text, voice_id, model_id, voice_settings)
            if audio_data:
                logger.info(f"Successfully received audio data ({len(audio_data)} bytes)")
                response = Response(audio_data, mimetype='audio/mpeg')
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response
            else:
                # Fallback to mock response
                logger.error("Failed to get audio from ElevenLabs API")
                return jsonify({
                    'success': False,
                    'error': 'Failed to get audio from ElevenLabs API'
                }), 500
        else:
            # Mock response if no API key is configured
            logger.warning("No ElevenLabs API key configured, returning mock response")
            response = jsonify({
                'success': True,
                'message': f'Would convert to speech: "{text[:100]}..." using voice {voice_id}'
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
    
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

def call_elevenlabs_api(
    text: str, 
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID,
    voice_settings: dict = DEFAULT_VOICE_SETTINGS
) -> Optional[bytes]:
    """Call ElevenLabs API to convert text to speech."""
    try:
        url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }
        
        logger.info(f"Sending request to ElevenLabs API: voice_id={voice_id}, model_id={model_id}, text_length={len(text)}")
        response = requests.post(url, json=data, headers=headers, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"Successfully converted text to speech, received {len(response.content)} bytes")
            return response.content
        else:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error calling ElevenLabs API: {str(e)}")
        return None

@app.route('/voices', methods=['GET'])
def list_voices():
    """List available voices from ElevenLabs."""
    try:
        if not ELEVENLABS_API_KEY:
            # Return mock voices if no API key
            return jsonify({
                'voices': [
                    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel"},
                    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Adam"},
                    {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi"},
                    {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli"},
                    {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh"},
                    {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam"}
                ]
            })
        
        url = f"{ELEVENLABS_API_URL}/voices"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return jsonify({'error': f"ElevenLabs API error: {response.status_code}"}), 500
    
    except Exception as e:
        logger.error(f"Error listing voices: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if ELEVENLABS_API_KEY:
        logger.info("ElevenLabs API key is configured")
    else:
        logger.warning("No ElevenLabs API key found. Set ELEVENLABS_API_KEY environment variable for production use.")
        logger.warning("Running in mock mode, responses will be simulated.")
    
    print(f"Starting ElevenLabs TTS Service on port {args.port}")
    print(f"Health check endpoint: http://127.0.0.1:{args.port}/health")
    print(f"API endpoint: http://127.0.0.1:{args.port}/text_to_speech")
    
    app.run(host='0.0.0.0', port=args.port, debug=True) 