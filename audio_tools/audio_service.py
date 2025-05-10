#!/usr/bin/env python3
"""
Audio Service for DARIA Interview Tool
Provides a central service for audio processing
"""

import os
import argparse
import logging
import json
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run Audio Service')
parser.add_argument('--port', type=int, default=5017, help='Port to run the server on')
parser.add_argument('--tts-service', type=str, default='http://localhost:5015', 
                    help='URL of the Text-to-Speech service')
parser.add_argument('--stt-service', type=str, default='http://localhost:5016',
                    help='URL of the Speech-to-Text service')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Service URLs
TTS_SERVICE_URL = args.tts_service
STT_SERVICE_URL = args.stt_service

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service."""
    # Check if other services are reachable
    tts_status = 'unknown'
    stt_status = 'unknown'
    
    try:
        tts_response = requests.get(f"{TTS_SERVICE_URL}/health", timeout=2)
        tts_status = 'ok' if tts_response.status_code == 200 else 'error'
    except requests.exceptions.RequestException:
        tts_status = 'unavailable'
    
    try:
        stt_response = requests.get(f"{STT_SERVICE_URL}/health", timeout=2)
        stt_status = 'ok' if stt_response.status_code == 200 else 'error'
    except requests.exceptions.RequestException:
        stt_status = 'unavailable'
    
    return jsonify({
        'status': 'ok',
        'service': 'audio',
        'tts_service': tts_status,
        'stt_service': stt_status
    })

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """Forward text-to-speech request to TTS service."""
    try:
        data = request.json
        logger.info(f"Forwarding TTS request: {len(data.get('text', ''))} chars")
        
        # Forward request to TTS service
        response = requests.post(
            f"{TTS_SERVICE_URL}/text_to_speech",
            json=data,
            timeout=30
        )
        
        # If TTS service returns audio, return it as-is
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'audio/' in content_type:
                return Response(
                    response.content,
                    status=200,
                    mimetype=content_type
                )
            else:
                # JSON response
                return jsonify(response.json())
        else:
            # Error response
            try:
                error_data = response.json()
                return jsonify(error_data), response.status_code
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f"TTS service error: {response.status_code}"
                }), response.status_code
    
    except Exception as e:
        logger.error(f"Error in TTS forwarding: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """Forward speech-to-text request to STT service."""
    try:
        logger.info("Forwarding STT request")
        
        # Forward the exact request to STT service
        if request.files:
            # Handle multipart form data with files
            files = {'audio': (
                request.files['audio'].filename,
                request.files['audio'].stream,
                request.files['audio'].content_type
            )}
            
            # Include form data if present
            form_data = {}
            for key in request.form:
                form_data[key] = request.form[key]
            
            response = requests.post(
                f"{STT_SERVICE_URL}/speech_to_text",
                files=files,
                data=form_data,
                timeout=30
            )
        else:
            # Handle JSON data
            response = requests.post(
                f"{STT_SERVICE_URL}/speech_to_text",
                json=request.json,
                timeout=30
            )
        
        # Return response from STT service
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error in STT forwarding: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Forward voices request to TTS service."""
    try:
        # Forward request to TTS service
        response = requests.get(
            f"{TTS_SERVICE_URL}/voices",
            timeout=10
        )
        
        # Return response from TTS service
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print(f"Starting Audio Service on port {args.port}")
    print(f"TTS Service URL: {TTS_SERVICE_URL}")
    print(f"STT Service URL: {STT_SERVICE_URL}")
    print(f"Health check: http://localhost:{args.port}/health")
    app.run(host='0.0.0.0', port=args.port, debug=True) 