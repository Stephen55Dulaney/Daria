#!/usr/bin/env python3
"""
Simple text-to-speech service for DARIA Interview Tool
Serves as a proxy for ElevenLabs TTS API
"""
import os
import sys
import json
import flask
import logging
import requests
import argparse
from flask import Flask, request, Response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Set CORS headers for all responses
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """
    Simple text-to-speech proxy API
    """
    data = request.json
    text = data.get('text', '')
    voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default ElevenLabs voice
    
    if not text:
        return {'error': 'No text provided'}, 400
    
    # ElevenLabs API key (get from environment variable)
    api_key = os.environ.get('ELEVENLABS_API_KEY', '')
    
    if not api_key:
        logger.warning("No ElevenLabs API key found in environment variables. Using dummy audio.")
        # Return a dummy mp3 file
        with open(os.path.join(os.path.dirname(__file__), 'dummy_audio.mp3'), 'rb') as f:
            audio_data = f.read()
        return Response(audio_data, mimetype='audio/mpeg')
    
    # Make request to ElevenLabs API
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {
        'xi-api-key': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'text': text,
        'model_id': 'eleven_monolingual_v1',
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.5
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return Response(response.content, mimetype='audio/mpeg')
        else:
            logger.error(f"Error from ElevenLabs API: {response.text}")
            return {'error': f'ElevenLabs API error: {response.text}'}, 500
    except Exception as e:
        logger.error(f"Error connecting to ElevenLabs API: {str(e)}")
        return {'error': f'Error connecting to ElevenLabs API: {str(e)}'}, 500

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """
    Simple speech-to-text API (currently just a dummy implementation)
    """
    # Check if audio file was uploaded
    if 'audio' not in request.files:
        return {'error': 'No audio file provided'}, 400
    
    # Process audio file
    audio_file = request.files['audio']
    
    # For testing, just return a fixed response
    return {'success': True, 'text': 'This is a dummy transcription for testing purposes.'}

def main():
    parser = argparse.ArgumentParser(description='Simple TTS/STT Service')
    parser.add_argument('--port', type=int, default=5015, help='Port to run the service on')
    args = parser.parse_args()
    
    logger.info(f"Starting text-to-speech server on port {args.port}")
    
    # Force skip eventlet for Python 3.13 compatibility
    if sys.version_info.major == 3 and sys.version_info.minor >= 13:
        os.environ['SKIP_EVENTLET'] = '1'
    
    # Make sure PORT env var is consistent with command line arg
    os.environ['PORT'] = str(args.port)
    
    app.run(debug=True, host='127.0.0.1', port=args.port)

if __name__ == '__main__':
    main() 