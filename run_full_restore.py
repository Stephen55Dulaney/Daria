#!/usr/bin/env python
import os
import sys
import logging
import uuid
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, jsonify, abort, send_file
from werkzeug.utils import secure_filename
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app factory
from daria_interview_tool import create_app

# Create the app
app = create_app()

# Direct legacy routes
@app.route('/langchain_interview_test')
def langchain_interview_test():
    """Render langchain interview test page directly"""
    return render_template('langchain_interview_test.html')

@app.route('/langchain_interview_setup')
def langchain_interview_setup():
    """Render langchain interview setup page directly"""
    return render_template('langchain_interview_setup.html')

@app.route('/langchain_interview_session')
def langchain_interview_session():
    """Render langchain interview session page directly"""
    return render_template('langchain_interview_session.html')

# API Endpoints
@app.route('/api/text_to_speech_elevenlabs', methods=['POST'])
def text_to_speech_elevenlabs():
    """Text to speech API endpoint using ElevenLabs"""
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'default')
        
        # For demo purposes, just return a sample audio file
        # In production, this would call ElevenLabs API
        logger.info(f"Text to speech request: {text[:50]}... using voice {voice_id}")
        
        # Create a simple WAV file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        
        # In production, replace with actual TTS API call
        # For now, just return a placeholder text file
        with open(temp_file.name, 'w') as f:
            f.write("Audio placeholder")
            
        return send_file(temp_file.name, mimetype='audio/wav')
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """Process audio file and return transcription"""
    try:
        project_name = request.args.get('project_name', 'Default Project')
        
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Empty audio file name"}), 400
            
        filename = secure_filename(audio_file.filename or f"recording_{uuid.uuid4()}.wav")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        audio_file.save(file_path)
        
        # In production, this would process the audio file with a transcription service
        # For now, return a placeholder transcription
        logger.info(f"Processing audio for project: {project_name}")
        
        return jsonify({
            "transcript": "This is a placeholder transcription from the audio recording.",
            "success": True
        })
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview/start', methods=['POST'])
def start_interview():
    """Start a new LangChain interview"""
    try:
        data = request.json
        interview_prompt = data.get('interview_prompt', '')
        
        # In production, this would initialize a new interview session
        # For now, return a placeholder response
        interview_id = str(uuid.uuid4())
        logger.info(f"Starting interview with prompt: {interview_prompt[:50]}...")
        
        return jsonify({
            "interview_id": interview_id,
            "first_question": "Thank you for joining this interview. Could you please introduce yourself and tell me about your background in UX research?",
            "success": True
        })
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview/respond', methods=['POST'])
def respond_to_interview():
    """Process user response and generate next question"""
    try:
        data = request.json
        user_input = data.get('user_input', '')
        
        # In production, this would process the user input and generate the next question
        # For now, return a placeholder response
        logger.info(f"Processing user input: {user_input[:50]}...")
        
        return jsonify({
            "next_question": "That's interesting. Could you tell me more about your experience with user testing methodologies?",
            "success": True
        })
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview/analyze', methods=['POST'])
def analyze_interview():
    """Analyze the completed interview"""
    try:
        # In production, this would analyze the interview content
        # For now, return a placeholder analysis
        logger.info("Analyzing interview...")
        
        return jsonify({
            "analysis": """
            # Interview Analysis
            
            ## Key Insights
            1. The participant has extensive experience in UX research methods
            2. They favor qualitative research techniques
            3. Pain points include stakeholder alignment and research timeline constraints
            
            ## Recommendations
            - Consider more structured research frameworks
            - Implement earlier stakeholder involvement
            - Establish clearer expectations about research timelines
            """,
            "success": True
        })
    except Exception as e:
        logger.error(f"Error analyzing interview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/diagnostics/microphone', methods=['POST'])
def microphone_diagnostics():
    """Test microphone functionality"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Empty audio file name"}), 400
            
        filename = secure_filename(audio_file.filename or f"test_{uuid.uuid4()}.wav")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        audio_file.save(file_path)
        
        # In production, this would process the audio for a diagnostic test
        # For now, return a placeholder success response
        logger.info("Microphone test completed successfully")
        
        return jsonify({
            "status": "success",
            "transcription": "Microphone is working correctly.",
            "audio_quality": "good"
        })
    except Exception as e:
        logger.error(f"Error testing microphone: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Run the app on a port that's likely free
if __name__ == '__main__':
    # Try various ports until one works
    ports_to_try = [5004, 5005, 5006, 5007, 5008, 5009]
    
    for port in ports_to_try:
        try:
            print(f"\n===========================================================")
            print(f"DARIA INTERVIEW TOOL RESTORATION")
            print(f"===========================================================")
            print(f"Attempting to start server on port {port}...")
            print(f"Access the application at: http://127.0.0.1:{port}")
            print(f"Dashboard: http://127.0.0.1:{port}/langchain/dashboard")
            print(f"Interview Test: http://127.0.0.1:{port}/langchain_interview_test")
            print(f"Interview Setup: http://127.0.0.1:{port}/langchain_interview_setup")
            print(f"===========================================================\n")
            app.run(host='127.0.0.1', port=port, debug=True)
            break
        except OSError as e:
            print(f"Port {port} is in use, trying next port...")
            continue
    else:
        print("All ports are in use. Please free up a port and try again.") 