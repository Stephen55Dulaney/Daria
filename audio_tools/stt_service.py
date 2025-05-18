#!/usr/bin/env python3
"""
Speech-to-Text service for the DARIA Interview Tool
Provides a simple API for converting speech to text
"""

import os
import argparse
import logging
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run STT Service')
parser.add_argument('--port', type=int, default=5016, help='Port to run the server on')
parser.add_argument('--mock', action='store_true', help='Use mock STT service instead of real STT')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the service."""
    # Return a simple response directly as string to avoid any processing overhead
    return Response('{"status":"ok","service":"stt"}', 
                   mimetype='application/json',
                   status=200)

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """Convert speech to text using the available STT service."""
    try:
        # Get audio data from request
        if request.files and 'audio' in request.files:
            # If a file was uploaded
            audio_file = request.files['audio']
            logger.info(f"Audio file received: {audio_file.filename}, {audio_file.content_type}")
            
            # For now, return the actual text from the form if provided
            if request.form and 'actual_speech' in request.form:
                actual_text = request.form.get('actual_speech', '')
                if actual_text:
                    logger.info(f"Using actual speech text: {actual_text}")
                    return jsonify({
                        'success': True,
                        'text': actual_text
                    })
            
            # If no actual text was provided, return a simulated response
            return generate_mock_response()
            
        elif request.json and 'text' in request.json:
            # If text was directly provided (for testing)
            text = request.json.get('text', '')
            logger.info(f"Text directly provided: {text}")
            return jsonify({
                'success': True,
                'text': text
            })
            
        else:
            # No audio file or text provided
            return generate_mock_response()
            
    except Exception as e:
        logger.error(f"Error in STT service: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_mock_response():
    """Generate a mock response when no real STT is available."""
    logger.info("Generating mock STT response")
    
    # Use actual speech if provided in request
    if request.form and 'actual_speech' in request.form:
        actual_speech = request.form.get('actual_speech', '')
        if actual_speech:
            return jsonify({
                'success': True,
                'text': actual_speech,
                'source': 'actual_speech'
            })
    
    # Return mock responses
    mock_responses = [
        "I'm interested in learning more about this topic.",
        "Could you explain that in more detail?",
        "That's an interesting perspective. I'd like to know more.",
        "I've been thinking about this issue for some time now.",
        "How would this approach work in practice?",
        "What are the implications of this decision?",
        "I'm not sure I fully understand. Could you clarify?",
        "That makes sense. I'd like to build on that idea.",
        "I have some concerns about the implementation details.",
        "How does this compare to alternative approaches?"
    ]
    
    selected_response = random.choice(mock_responses)
    
    return jsonify({
        'success': True,
        'text': selected_response,
        'source': 'mock'
    })

if __name__ == '__main__':
    print(f"Starting STT service on port {args.port}")
    print(f"Health check: http://localhost:{args.port}/health")
    print(f"Speech-to-text endpoint: http://localhost:{args.port}/speech_to_text")
    
    # Configure Flask for better performance in this use case
    # Use threaded=True to handle concurrent requests better
    # Keep debug=True but use a faster response model
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True) 