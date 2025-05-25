#!/usr/bin/env python3
"""
Mock Speech-to-Text Service for DARIA Interview Tool
"""

import os
import logging
import argparse
import random
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import pathlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run Mock STT Service')
parser.add_argument('--port', type=int, default=5016, help='Port to run the server on')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Sample transcription responses
SAMPLE_RESPONSES = [
    "This is a test transcription. The system seems to be working correctly.",
    "Hello, my name is Stephen and I'm testing the speech to text service.",
    "I'm providing feedback on the product usability and features.",
    "The interview system is working well but could use some improvements in the UI.",
    "I find the voice recognition to be quite accurate most of the time.",
    "Daria seems to be responding appropriately to my questions.",
    "The system needs better error handling when the network connection is unstable.",
    "I think the response times could be improved in the next version."
]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'mock_stt',
        'version': '1.0.0'
    })

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """Mock transcription of speech to text."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        audio_file = request.files['file']
        
        # If user does not select file, browser submits an empty file
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if audio_file:
            # Save the file temporarily
            filename = secure_filename(audio_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            audio_file.save(file_path)
            
            # Log the received file
            file_size = pathlib.Path(file_path).stat().st_size
            logger.info(f"Received audio file: {filename}, size: {file_size} bytes")
            
            # Simulate processing time
            time.sleep(1)
            
            # Get the optional text parameter, which allows the UI to send what was actually said
            text = request.form.get('text', '')
            
            # If no text was provided, use one of the samples
            if not text:
                text = "I'm speaking into the microphone and this is what I actually said."
                logger.info("No text provided with request, using default text")
            else:
                logger.info(f"Using provided text: {text}")
            
            # Clean up the temporary file
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return jsonify({
                'success': True,
                'text': text,
                'confidence': random.uniform(0.85, 0.98)
            })
        
        return jsonify({'error': 'Failed to process file'}), 400
    
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/implement_elevenlabs_stt', methods=['POST'])
def elevenlabs_stt_placeholder():
    """Placeholder for future ElevenLabs STT implementation."""
    return jsonify({
        'success': False,
        'error': 'ElevenLabs STT integration is not yet implemented',
        'message': 'This endpoint will be implemented in a future version using the ElevenLabs Speech-to-Text API'
    }), 501

if __name__ == '__main__':
    print(f"Starting Mock STT Service on port {args.port}")
    print(f"Health check endpoint: http://127.0.0.1:{args.port}/health")
    print(f"API endpoint: http://127.0.0.1:{args.port}/speech_to_text")
    print(f"Temporary files will be stored in: {UPLOAD_FOLDER}")
    
    app.run(host='0.0.0.0', port=args.port, debug=True) 