#!/usr/bin/env python
import os
import sys
import logging
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, render_template, request, jsonify, abort, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app factory
from daria_interview_tool import create_app

# Create the app
app = create_app()

# First, copy the templates from langchain_features to daria_interview_tool
def copy_templates():
    """Copy templates from langchain_features to daria_interview_tool"""
    src_dir = Path('langchain_features/templates/langchain')
    dest_dir = Path('daria_interview_tool/templates/langchain')
    
    if not src_dir.exists():
        logger.error(f"Source directory {src_dir} does not exist!")
        return False
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all files
    count = 0
    for src_file in src_dir.glob('*.html'):
        dest_file = dest_dir / src_file.name
        try:
            shutil.copy2(src_file, dest_file)
            count += 1
            logger.info(f"Copied {src_file.name} to {dest_file}")
        except Exception as e:
            logger.error(f"Failed to copy {src_file.name}: {str(e)}")
    
    logger.info(f"Successfully copied {count} template files")
    return count > 0

# Direct routes for all langchain templates
@app.route('/langchain/session')
def langchain_session():
    """Render langchain interview session page directly"""
    return render_template('langchain/interview_session.html')

@app.route('/langchain/welcome')
def langchain_welcome():
    """Render langchain welcome page directly"""
    return render_template('langchain/interview_welcome.html')

@app.route('/langchain/monitor')
def langchain_monitor():
    """Render langchain monitor session page directly"""
    return render_template('langchain/monitor_session.html')

@app.route('/langchain/dashboard')
def langchain_dashboard():
    """Render langchain dashboard page directly"""
    # Get list of interviews
    interviews = []
    INTERVIEWS_DIR = Path('interviews/raw')
    if INTERVIEWS_DIR.exists():
        for file in sorted(INTERVIEWS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    interviews.append(data)
                    logger.info(f"Loaded interview: {data.get('title')} with ID: {data.get('id')}")
            except Exception as e:
                logger.error(f"Error loading interview {file}: {str(e)}")
                continue

    # Count interview statuses
    active_interviews = len([i for i in interviews if i.get('status') == 'active'])
    completed_sessions = len([i for i in interviews if i.get('status') == 'completed'])
    in_progress = len([i for i in interviews if i.get('status') == 'in_progress'])

    return render_template('langchain/dashboard.html',
                          interviews=interviews,
                          active_interviews=active_interviews,
                          completed_sessions=completed_sessions,
                          in_progress=in_progress)

@app.route('/langchain/completed/<interview_id>')
def langchain_completed(interview_id):
    """Render langchain completed interview view page"""
    return render_template('langchain/view_completed_interview.html', interview_id=interview_id)

@app.route('/langchain/archive')
def langchain_archive():
    """Render langchain interview archive page"""
    return render_template('langchain/interview_archive.html')

@app.route('/langchain/details/<interview_id>')
def langchain_details(interview_id):
    """Render langchain interview details page"""
    return render_template('langchain/interview_details.html', interview_id=interview_id)

@app.route('/langchain/setup')
def langchain_setup():
    """Render langchain interview setup page"""
    return render_template('langchain/interview_setup.html')

@app.route('/langchain/expired')
def langchain_expired():
    """Render langchain interview expired page"""
    return render_template('langchain/interview_expired.html')

@app.route('/langchain')
def langchain_index():
    """Render langchain index page"""
    return render_template('langchain/index.html')

@app.route('/langchain/discovery')
def langchain_discovery():
    """Render langchain discovery plan page"""
    return render_template('langchain/discovery_plan.html')

@app.route('/langchain/research')
def langchain_research():
    """Render langchain research plan page"""
    return render_template('langchain/research_plan.html')

# Legacy URL support
@app.route('/langchain_interview_test')
def langchain_interview_test_legacy():
    """For backward compatibility"""
    return redirect('/langchain/session')

@app.route('/langchain_interview_setup')
def langchain_interview_setup_legacy():
    """For backward compatibility"""
    return redirect('/langchain/setup')

@app.route('/langchain_interview_session')
def langchain_interview_session_legacy():
    """For backward compatibility"""
    return redirect('/langchain/session')

@app.route('/langchain/interview_test')
def langchain_interview_test():
    """Render langchain interview test page directly"""
    return render_template('langchain/interview_session.html')

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

@app.route('/langchain/generate_link', methods=['GET', 'POST'])
def generate_interview_link():
    """Generate a secure interview link that can be shared with participants"""
    if request.method == 'POST':
        interview_type = request.form.get('interview_type', 'general')
        participant_email = request.form.get('participant_email', '')
        interview_duration = request.form.get('interview_duration', '60')
        interview_prompt = request.form.get('interview_prompt', 'Tell me about your background and experience.')
        expiration_days = int(request.form.get('expiration_days', '7'))
        
        # Generate a secure token
        interview_id = str(uuid.uuid4())
        token = str(uuid.uuid4())
        
        # In production, this would be stored in a database with proper encryption
        # For now, just save it in a JSON file
        interview_data = {
            "id": interview_id,
            "token": token,
            "interview_type": interview_type,
            "participant_email": participant_email,
            "interview_prompt": interview_prompt,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=expiration_days)).isoformat(),
            "status": "pending",
            "title": f"Interview with {participant_email.split('@')[0]}"
        }
        
        # Save the interview data
        interviews_dir = Path('interviews/raw')
        interviews_dir.mkdir(parents=True, exist_ok=True)
        with open(interviews_dir / f"{interview_id}.json", 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        # Generate the secure link
        interview_link = f"/langchain/participate/{interview_id}?token={token}"
        full_link = request.host_url.rstrip('/') + interview_link
        
        return render_template('langchain/link_generated.html', 
                               interview_link=full_link, 
                               interview_data=interview_data)
    
    return render_template('langchain/generate_link.html')

@app.route('/langchain/participate/<interview_id>')
def participate_in_interview(interview_id):
    """Public endpoint for interview participants"""
    token = request.args.get('token', '')
    if not token:
        return render_template('langchain/interview_error.html', 
                               error="Missing authentication token"), 400
    
    # Verify the token matches and interview is valid
    interviews_dir = Path('interviews/raw')
    interview_file = interviews_dir / f"{interview_id}.json"
    
    if not interview_file.exists():
        return render_template('langchain/interview_error.html', 
                               error="Interview not found"), 404
    
    try:
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
        
        # Verify token
        if interview_data.get('token') != token:
            return render_template('langchain/interview_error.html', 
                                   error="Invalid authentication token"), 403
        
        # Check if expired
        expires_at = datetime.fromisoformat(interview_data.get('expires_at'))
        if datetime.now() > expires_at:
            return render_template('langchain/interview_expired.html')
        
        # Update status to active if it was pending
        if interview_data.get('status') == 'pending':
            interview_data['status'] = 'active'
            with open(interview_file, 'w') as f:
                json.dump(interview_data, f, indent=2)
        
        # Pass interview data to template
        return render_template('langchain/participant_interview.html', 
                               interview=interview_data,
                               interview_id=interview_id,
                               secure_token=token)
        
    except Exception as e:
        logger.error(f"Error loading interview {interview_id}: {str(e)}")
        return render_template('langchain/interview_error.html', 
                               error="Error loading interview"), 500

@app.route('/langchain/monitor/<interview_id>')
def monitor_interview(interview_id):
    """Monitor an ongoing interview - requires authentication in production"""
    # In production, this would require proper authorization
    # to ensure only authorized personnel can monitor interviews
    
    interviews_dir = Path('interviews/raw')
    interview_file = interviews_dir / f"{interview_id}.json"
    
    if not interview_file.exists():
        return render_template('langchain/interview_error.html', 
                               error="Interview not found"), 404
    
    try:
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
        
        # Load transcript if available
        transcript = []
        transcript_file = interviews_dir / f"{interview_id}_transcript.json"
        if transcript_file.exists():
            with open(transcript_file, 'r') as f:
                transcript = json.load(f)
        
        return render_template('langchain/monitor_interview.html', 
                               interview=interview_data,
                               transcript=transcript,
                               interview_id=interview_id)
        
    except Exception as e:
        logger.error(f"Error loading interview {interview_id}: {str(e)}")
        return render_template('langchain/interview_error.html', 
                               error="Error loading interview"), 500

# API endpoint for microphone diagnostics
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

# Save interview responses
@app.route('/api/langchain_interview/save_response', methods=['POST'])
def save_interview_response():
    """Save a participant's response to an interview question"""
    try:
        data = request.json
        interview_id = data.get('interview_id')
        token = data.get('token')
        question = data.get('question', '')
        response = data.get('response', '')
        
        if not interview_id or not token:
            return jsonify({"error": "Missing interview ID or authentication token"}), 400
            
        # Verify the token matches and interview is valid
        interviews_dir = Path('interviews/raw')
        interview_file = interviews_dir / f"{interview_id}.json"
        
        if not interview_file.exists():
            return jsonify({"error": "Interview not found"}), 404
            
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
            
        # Verify token
        if interview_data.get('token') != token:
            return jsonify({"error": "Invalid authentication token"}), 403
            
        # Load existing transcript or create new one
        transcript_file = interviews_dir / f"{interview_id}_transcript.json"
        if transcript_file.exists():
            with open(transcript_file, 'r') as f:
                transcript = json.load(f)
        else:
            transcript = []
            
        # Add new exchange
        timestamp = datetime.now().isoformat()
        transcript.append({
            "timestamp": timestamp,
            "question": question,
            "response": response
        })
            
        # Save updated transcript
        with open(transcript_file, 'w') as f:
            json.dump(transcript, f, indent=2)
            
        # Update interview status if needed
        if interview_data.get('status') != 'completed':
            interview_data['status'] = 'in_progress'
            with open(interview_file, 'w') as f:
                json.dump(interview_data, f, indent=2)
                
        return jsonify({
            "success": True,
            "message": "Response saved successfully"
        })
            
    except Exception as e:
        logger.error(f"Error saving response: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview/complete', methods=['POST'])
def complete_interview():
    """Mark an interview as completed"""
    try:
        data = request.json
        interview_id = data.get('interview_id')
        token = data.get('token')
        
        if not interview_id or not token:
            return jsonify({"error": "Missing interview ID or authentication token"}), 400
            
        # Verify the token matches and interview is valid
        interviews_dir = Path('interviews/raw')
        interview_file = interviews_dir / f"{interview_id}.json"
        
        if not interview_file.exists():
            return jsonify({"error": "Interview not found"}), 404
            
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
            
        # Verify token
        if interview_data.get('token') != token:
            return jsonify({"error": "Invalid authentication token"}), 403
            
        # Update interview status
        interview_data['status'] = 'completed'
        interview_data['completed_at'] = datetime.now().isoformat()
        
        with open(interview_file, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        return jsonify({
            "success": True,
            "message": "Interview completed successfully"
        })
            
    except Exception as e:
        logger.error(f"Error completing interview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/langchain_interview/transcript', methods=['GET'])
def get_interview_transcript():
    """Get the transcript for an interview"""
    try:
        interview_id = request.args.get('interview_id')
        
        if not interview_id:
            return jsonify({"error": "Missing interview ID"}), 400
            
        # In production, this would verify user authorization
        # to ensure only authorized personnel can access transcripts
        
        # Load transcript
        interviews_dir = Path('interviews/raw')
        transcript_file = interviews_dir / f"{interview_id}_transcript.json"
        
        if not transcript_file.exists():
            return jsonify({
                "success": True,
                "transcript": []
            })
            
        with open(transcript_file, 'r') as f:
            transcript = json.load(f)
            
        return jsonify({
            "success": True,
            "transcript": transcript
        })
            
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Run the app on a port that's likely free
if __name__ == '__main__':
    # First, copy templates from langchain_features
    if not copy_templates():
        print("ERROR: Failed to copy templates from langchain_features. Make sure the directory exists.")
        sys.exit(1)
    
    # Try various ports until one works
    ports_to_try = [8000, 8001, 8002, 8003, 8004, 8005]
    
    for port in ports_to_try:
        try:
            print(f"\n===========================================================")
            print(f"DARIA INTERVIEW TOOL - LANGCHAIN FEATURES RESTORATION")
            print(f"===========================================================")
            print(f"Attempting to start server on port {port}...")
            print(f"Access the application at: http://127.0.0.1:{port}")
            print(f"Dashboard: http://127.0.0.1:{port}/langchain/dashboard")
            print(f"Interview Session: http://127.0.0.1:{port}/langchain/session")
            print(f"Interview Setup: http://127.0.0.1:{port}/langchain/setup")
            print(f"===========================================================\n")
            app.run(host='127.0.0.1', port=port, debug=True)
            break
        except OSError as e:
            print(f"Port {port} is in use, trying next port...")
            continue
    else:
        print("All ports are in use. Please free up a port and try again.") 