#!/usr/bin/env python
"""
Simple test script to verify ElevenLabs API key works correctly.
Run this script to test the ElevenLabs TTS functionality directly.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("Error: ELEVENLABS_API_KEY not found in environment variables.")
    print("Please add it to your .env file.")
    exit(1)

# Test voice ID (Rachel)
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

# Test text
TEXT = "Hello, this is a test of the ElevenLabs text-to-speech API. If you can hear this, your API key is working correctly."

def test_elevenlabs_api():
    """Test the ElevenLabs API with a simple text-to-speech request."""
    print(f"Testing ElevenLabs API with key: {ELEVENLABS_API_KEY[:5]}...")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": TEXT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    print("Sending request to ElevenLabs API...")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: ElevenLabs API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Save the audio file
        output_file = "test_elevenlabs.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        print(f"Success! Audio file saved as {output_file}")
        print(f"File size: {len(response.content)} bytes")
        return True
    
    except Exception as e:
        print(f"Error calling ElevenLabs API: {str(e)}")
        return False

if __name__ == "__main__":
    if test_elevenlabs_api():
        print("ElevenLabs API test successful!")
    else:
        print("ElevenLabs API test failed. Please check your API key and try again.") 