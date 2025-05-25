#!/usr/bin/env python3
"""ElevenLabs TTS service for DARIA"""

import os
import sys
import time
import argparse
import requests
from flask import Flask, request, jsonify, send_file
from io import BytesIO

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Default voice
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/"

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    if not ELEVENLABS_API_KEY:
        return jsonify({"status": "error", "detail": "Missing ELEVENLABS_API_KEY"}), 500
    return jsonify({"status": "ok"})

@app.route('/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text', '')
    voice_id = data.get('voice_id', ELEVENLABS_VOICE_ID)
    if not text:
        return jsonify({"status": "error", "detail": "No text provided"}), 400
    if not ELEVENLABS_API_KEY:
        return jsonify({"status": "error", "detail": "Missing ELEVENLABS_API_KEY"}), 500
    try:
        url = f"{ELEVENLABS_URL}{voice_id}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            # Save audio to a temp file and return a URL or stream
            audio_data = response.content
            # For now, return as a downloadable file
            return send_file(BytesIO(audio_data), mimetype='audio/mpeg', as_attachment=True, download_name=f"tts_{int(time.time())}.mp3")
        else:
            return jsonify({"status": "error", "detail": f"ElevenLabs API error: {response.status_code} {response.text}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    return tts()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ElevenLabs TTS Service for DARIA")
    parser.add_argument('--port', type=int, default=5016, help='Port to run the service on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port) 