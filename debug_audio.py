#!/usr/bin/env python3
"""
Debug script to check audio services and ElevenLabs integration
"""
import os
import sys
import requests
import json

def check_audio_service():
    """Check if the audio service is running"""
    try:
        response = requests.get("http://127.0.0.1:5007/", timeout=3)
        return {
            "status": "running" if response.status_code == 200 else "error",
            "response": response.text if response.status_code == 200 else f"Error {response.status_code}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "not_running",
            "error": str(e)
        }

def test_elevenlabs_voice():
    """Test the ElevenLabs voice API"""
    voice_id = "EXAVITQu4vr4xnSDxMaL"  # Rachel (Female)
    test_text = "This is a test of the ElevenLabs voice API."
    
    try:
        # Try to call the ElevenLabs proxy endpoint from the main app
        response = requests.post(
            "http://127.0.0.1:5010/api/text_to_speech_elevenlabs",
            json={
                "text": test_text,
                "voice_id": voice_id
            },
            timeout=10
        )
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            content_length = len(response.content)
            
            return {
                "status": "success",
                "content_type": content_type,
                "content_length": content_length,
                "message": "Successfully received audio from ElevenLabs"
            }
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("error", error_text)
            except:
                pass
                
            return {
                "status": "error",
                "http_code": response.status_code,
                "error": error_text
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "connection_error",
            "error": str(e)
        }

def test_direct_audio_service():
    """Test the audio service directly"""
    voice_id = "EXAVITQu4vr4xnSDxMaL"  # Rachel (Female)
    test_text = "This is a direct test of the audio service."
    
    try:
        response = requests.post(
            "http://127.0.0.1:5007/text_to_speech",
            json={
                "text": test_text,
                "voice_id": voice_id
            },
            timeout=10
        )
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            content_length = len(response.content)
            
            return {
                "status": "success",
                "content_type": content_type,
                "content_length": content_length,
                "message": "Successfully received audio from direct audio service"
            }
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("error", error_text)
            except:
                pass
                
            return {
                "status": "error",
                "http_code": response.status_code,
                "error": error_text
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "connection_error",
            "error": str(e)
        }

def list_available_voices():
    """List the voices defined in the application"""
    # Hard-coded list from run_langchain_direct_fixed.py
    voices = [
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel (Female)"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni (Male)"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli (Female)"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi (Female)"},
        {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "Fin (Male)"}
    ]
    
    return voices

def check_template_rendering():
    """Check if the voices are being passed to the template"""
    try:
        response = requests.get("http://127.0.0.1:5010/interview_setup")
        
        if response.status_code == 200:
            html = response.text
            
            # Check if any of the voice names appear in the HTML
            voices = list_available_voices()
            found_voices = []
            
            for voice in voices:
                if voice["name"] in html:
                    found_voices.append(voice["name"])
            
            return {
                "status": "success",
                "found_voices": found_voices,
                "all_voices_found": len(found_voices) == len(voices),
                "total_voices": len(voices)
            }
        else:
            return {
                "status": "error",
                "http_code": response.status_code,
                "error": "Failed to load interview_setup page"
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "connection_error",
            "error": str(e)
        }

def main():
    """Main function"""
    print("=== DARIA Interview Tool Audio Services Debug ===\n")
    
    print("1. Checking audio service...")
    audio_service_status = check_audio_service()
    print(f"   Status: {audio_service_status['status']}")
    if audio_service_status['status'] != 'running':
        print(f"   Error: {audio_service_status.get('error', 'Unknown error')}")
    print()
    
    if audio_service_status['status'] == 'running':
        print("2. Testing direct audio service...")
        direct_test_result = test_direct_audio_service()
        print(f"   Status: {direct_test_result['status']}")
        if direct_test_result['status'] == 'success':
            print(f"   Content type: {direct_test_result['content_type']}")
            print(f"   Content length: {direct_test_result['content_length']} bytes")
        else:
            print(f"   Error: {direct_test_result.get('error', 'Unknown error')}")
        print()
    
    print("3. Testing ElevenLabs voice through main app...")
    elevenlabs_test_result = test_elevenlabs_voice()
    print(f"   Status: {elevenlabs_test_result['status']}")
    if elevenlabs_test_result['status'] == 'success':
        print(f"   Content type: {elevenlabs_test_result['content_type']}")
        print(f"   Content length: {elevenlabs_test_result['content_length']} bytes")
    else:
        print(f"   Error: {elevenlabs_test_result.get('error', 'Unknown error')}")
    print()
    
    print("4. Checking voices in template...")
    voices = list_available_voices()
    print(f"   Available voices ({len(voices)}):")
    for voice in voices:
        print(f"   - {voice['name']} (ID: {voice['id']})")
    
    template_check = check_template_rendering()
    print(f"\n   Template status: {template_check['status']}")
    if template_check['status'] == 'success':
        print(f"   Found {len(template_check['found_voices'])}/{template_check['total_voices']} voices in template")
        if template_check['found_voices']:
            print(f"   Found voices: {', '.join(template_check['found_voices'])}")
        else:
            print(f"   No voices found in template!")
    else:
        print(f"   Error: {template_check.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main() 