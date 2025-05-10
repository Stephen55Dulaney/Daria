#!/usr/bin/env python3
"""
Text-to-Speech service for the DARIA Interview Tool
Supports ElevenLabs API for high-quality text-to-speech
"""

import os
import argparse
import logging
import json
import time
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
import elevenlabs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run TTS Service')
parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Check if ElevenLabs API key is set
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
if ELEVENLABS_API_KEY:
    elevenlabs.set_api_key(ELEVENLABS_API_KEY)
    logger.info("ElevenLabs API key found. ElevenLabs TTS will be available.")
else:
    logger.warning("No ElevenLabs API key found. ElevenLabs TTS will not be available.")

# Default voices
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Rachel

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service."""
    return jsonify({
        'status': 'ok',
        'service': 'tts',
        'elevenlabs_enabled': bool(ELEVENLABS_API_KEY)
    })

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using the available TTS service."""
    try:
        # Get data from request
        data = request.json
        if not data or not data.get('text'):
            return jsonify({'error': 'Missing text parameter'}), 400
        
        text = data.get('text', '')
        voice_id = data.get('voice_id', DEFAULT_VOICE_ID)
        
        logger.info(f"TTS request received: {len(text)} chars, voice_id: {voice_id}")
        
        # Try ElevenLabs first if API key is available
        if ELEVENLABS_API_KEY:
            try:
                logger.info(f"Using ElevenLabs for TTS with voice ID: {voice_id}")
                
                # Using the elevenlabs library
                audio = elevenlabs.generate(
                    text=text,
                    voice=voice_id,
                    model="eleven_monolingual_v1"
                )
                
                # Return the audio data
                return Response(audio, mimetype='audio/mpeg')
                
            except Exception as e:
                logger.error(f"Error with ElevenLabs TTS: {str(e)}")
                # Fall back to browser TTS if ElevenLabs fails
        
        # Fall back to a simple text response that the browser can use for speech synthesis
        logger.info("Using fallback TTS response")
        return jsonify({
            'success': True,
            'text': text,
            'voice': voice_id,
            'message': 'Please use browser speech synthesis API for fallback TTS'
        })
    
    except Exception as e:
        logger.error(f"Error in TTS service: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voices from ElevenLabs."""
    try:
        if ELEVENLABS_API_KEY:
            try:
                # Get voices from ElevenLabs
                voices = elevenlabs.voices()
                voice_list = []
                
                for voice in voices:
                    voice_list.append({
                        'voice_id': voice.voice_id,
                        'name': voice.name,
                        'category': 'elevenlabs'
                    })
                
                return jsonify({
                    'success': True,
                    'voices': voice_list
                })
            except Exception as e:
                logger.error(f"Error getting ElevenLabs voices: {str(e)}")
        
        # Return default voices if ElevenLabs is not available
        default_voices = [
            {'voice_id': 'EXAVITQu4vr4xnSDxMaL', 'name': 'Rachel', 'category': 'elevenlabs_default'},
            {'voice_id': '21m00Tcm4TlvDq8ikWAM', 'name': 'Adam', 'category': 'elevenlabs_default'},
            {'voice_id': 'AZnzlk1XvdvUeBnXmlld', 'name': 'Domi', 'category': 'elevenlabs_default'},
            {'voice_id': 'MF3mGyEYCl7XYWbV9V6O', 'name': 'Elli', 'category': 'elevenlabs_default'},
            {'voice_id': 'TxGEqnHWrfWFTfGW9XjX', 'name': 'Josh', 'category': 'elevenlabs_default'},
            {'voice_id': 'yoZ06aMxZJJ28mfd3POQ', 'name': 'Sam', 'category': 'elevenlabs_default'}
        ]
        
        return jsonify({
            'success': True,
            'voices': default_voices
        })
    
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print(f"Starting TTS service on port {args.port}")
    print(f"ElevenLabs API key present: {bool(ELEVENLABS_API_KEY)}")
    print(f"Health check: http://localhost:{args.port}/health")
    print(f"Text-to-speech endpoint: http://localhost:{args.port}/text_to_speech")
    app.run(host='0.0.0.0', port=args.port, debug=True) 