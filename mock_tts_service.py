#!/usr/bin/env python3
"""Mock TTS service for DARIA"""

import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/tts', methods=['POST'])
def tts():
    """TTS endpoint that matches the main API's expectations"""
    data = request.json
    text = data.get('text', '')
    voice_id = data.get('voice_id', 'default')
    
    # Return a mock audio URL
    return jsonify({
        "status": "success",
        "audio_url": f"mock_audio_{int(time.time())}.mp3",
        "text": text,
        "voice_id": voice_id
    })

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """Mock synthesis endpoint"""
    data = request.json
    text = data.get('text', '')
    voice_id = data.get('voice_id', 'default')
    
    # Return a mock audio URL
    return jsonify({
        "status": "success",
        "audio_url": f"mock_audio_{int(time.time())}.mp3",
        "text": text,
        "voice_id": voice_id
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5016))  # Default to 5016
    app.run(host='0.0.0.0', port=port)
