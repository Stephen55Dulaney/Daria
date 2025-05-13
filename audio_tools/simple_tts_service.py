#!/usr/bin/env python3
"""
A simple text-to-speech service using ElevenLabs API.
This is a standalone service that provides a REST API for text-to-speech conversion.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run a simple TTS service')
parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get API keys from environment
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
if not ELEVENLABS_API_KEY:
    logger.error("ELEVENLABS_API_KEY not found in environment variables!")
    logger.error("Please set this in your .env file")
    sys.exit(1)

# Default voice settings
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Rachel voice
DEFAULT_MODEL_ID = "eleven_multilingual_v2"

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'text-to-speech',
        'version': '1.0.0',
        'elevenlabs_api_key': ELEVENLABS_API_KEY is not None
    })

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using ElevenLabs API."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract parameters
        text = data.get('text', '')
        voice_id = data.get('voice_id', DEFAULT_VOICE_ID)
        model_id = data.get('model_id', DEFAULT_MODEL_ID)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        logger.info(f"Converting text to speech: {text[:50]}... (voice: {voice_id})")
        
        # Call ElevenLabs API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Error calling ElevenLabs API: {response.status_code}, {response.text}")
            return jsonify({
                'error': f"Error calling ElevenLabs API: {response.status_code}",
                'details': response.text
            }), response.status_code
        
        # Return the audio data
        return Response(
            response.content, 
            mimetype="audio/mpeg",
            headers={"Content-Disposition": "attachment;filename=speech.mp3"}
        )
        
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voices from ElevenLabs."""
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Error calling ElevenLabs API: {response.status_code}")
            return jsonify({
                'error': f"Error calling ElevenLabs API: {response.status_code}",
                'details': response.text
            }), response.status_code
        
        return jsonify(response.json())
        
    except Exception as e:
        logger.error(f"Error in get_voices: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting TTS service on port {args.port}")
    logger.info(f"Health check endpoint: http://127.0.0.1:{args.port}/health")
    logger.info(f"Text-to-speech endpoint: http://127.0.0.1:{args.port}/text_to_speech")
    app.run(host='0.0.0.0', port=args.port) 