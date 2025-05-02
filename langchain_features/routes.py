from flask import request, jsonify, render_template, session, redirect, url_for, send_file
from langchain_features import langchain_blueprint
from langchain_features.services.interview_service import InterviewService
from langchain_features.services.discovery_service import DiscoveryService
from langchain_features.services.research_service import ResearchService
from langchain_features.models import InterviewSession
import logging
import traceback
import uuid
import os
import io
import random

# Get or create a logger for this module
logger = logging.getLogger(__name__)

# Index route for LangChain features
@langchain_blueprint.route('/')
def index():
    """Render the LangChain features home page"""
    return redirect(url_for('langchain_features.dashboard'))

@langchain_blueprint.route('/dashboard')
def dashboard():
    """Render the dashboard with interview statistics"""
    # Get all interview sessions
    sessions = InterviewService.list_sessions()
    
    # Count active, completed, and in-progress interviews
    active_count = sum(1 for session in sessions if session.status == 'active')
    completed_count = sum(1 for session in sessions if session.status == 'completed')
    in_progress_count = sum(1 for session in sessions if session.status == 'in_progress')
    
    return render_template('langchain/dashboard.html',
                          interviews=sessions,
                          active_count=active_count,
                          completed_count=completed_count,
                          in_progress_count=in_progress_count)

# Interview routes
@langchain_blueprint.route('/interview/setup', methods=['GET'])
def interview_setup():
    """Render the interview setup page"""
    # Default interview prompt
    default_prompt = """#Role: you are Daria, a UX researcher conducting an interview
#Objective: You are conducting an interview to understand the interviewee's experience with a product or service
#Instructions: Ask questions to understand the interviewee's role, experience, and needs related to the topic.
#Important: Be conversational, empathetic, and ask follow-up questions based on their responses."""
    
    # Get available voices from ElevenLabs (hardcoded for now)
    voices = [
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel - Professional Female"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni - Female"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli - Female"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi - Female"},
        {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh - Male"},
        {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold - Male"},
        {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam - Male"}
    ]
    
    return render_template('langchain/interview_setup.html',
                          interview_prompt=default_prompt,
                          voices=voices)

@langchain_blueprint.route('/interview/create', methods=['POST'])
def create_interview():
    """Create a new interview session."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "error": "No data provided"}), 400
            
        # Log received data for debugging
        logging.info(f"Received interview creation data: {data}")
            
        # Required fields
        if not data.get('interview_prompt'):
            logging.error("Missing interview_prompt in request")
            return jsonify({"status": "error", "error": "Interview prompt is required"}), 400
            
        if not data.get('title'):
            return jsonify({"status": "error", "error": "Interview title is required"}), 400
            
        if not data.get('project'):
            return jsonify({"status": "error", "error": "Project name is required"}), 400
            
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Create new interview session
        session = InterviewSession(
            id=session_id,
            title=data.get('title'),
            project=data.get('project'),
            interview_type=data.get('interview_type'),
            interview_prompt=data.get('interview_prompt'),
            analysis_prompt=data.get('analysis_prompt', ''),
            interviewee=data.get('interviewee', {}),
            custom_questions=data.get('custom_questions', []),
            time_per_question=data.get('time_per_question', 2),
            options=data.get('options', {})
        )
        
        # Save session
        result = InterviewService.save_session(session)
        if not result:
            return jsonify({"status": "error", "error": "Failed to save interview session"}), 500
        
        return jsonify({
            "status": "success", 
            "session_id": session_id,
            "message": "Interview session created successfully",
            "redirect_url": url_for('langchain_features.interview_details', session_id=session_id)
        })
        
    except Exception as e:
        logging.exception(f"Error in create_interview: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@langchain_blueprint.route('/interview/session/<session_id>', methods=['GET'])
def interview_session(session_id):
    """Render the interview session page"""
    interview = InterviewService.get_session(session_id)
    if not interview:
        return redirect(url_for('langchain_features.interview_setup'))
    
    # Check if interview has expired
    if interview.status == 'expired':
        return redirect(url_for('langchain_features.interview_expired', session_id=session_id))
    
    # For interview creators, redirect to the details page
    referer = request.referrer or ""
    if "create" in referer or "/langchain/interview/create" in referer:
        return redirect(url_for('langchain_features.interview_details', session_id=session_id))
    
    # Get "accepted" parameter from query string
    accepted = request.args.get('accepted', 'false').lower() == 'true'
    
    # For interviewees, check if they've accepted the terms via query param or session cookie
    if not (accepted or session.get(f'terms_{session_id}', False)):
        # Get voice ID from query parameter
        voice_id = request.args.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default to Rachel
        return render_template('langchain/interview_welcome.html',
                              session_id=session_id,
                              voice_id=voice_id,
                              title=interview.title)
    
    # If accepted via GET, update the interview with the provided data
    if accepted and not session.get(f'terms_{session_id}', False):
        try:
            # Set the session flag to avoid showing the welcome page again
            session[f'terms_{session_id}'] = True
            
            # Get form data from query parameters
            name = request.args.get('name', 'Anonymous')
            email = request.args.get('email', '')
            
            # Update interviewee information
            interview.interviewee['name'] = name
            interview.interviewee['email'] = email
            interview.status = 'in_progress'
            InterviewService.save_session(interview)
            
            logger.info(f"Updated interview {session_id} with participant info: {name}")
        except Exception as e:
            logger.error(f"Error updating interview with GET data: {str(e)}")
            # Continue even with errors
    
    # Regular interview session for participants
    voice_id = request.args.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default to Rachel
    return render_template('langchain/interview_session.html',
                          session_id=session_id,
                          voice_id=voice_id,
                          title=interview.title)

@langchain_blueprint.route('/api/interview/start', methods=['POST'])
def start_interview():
    """Start an interview and get the first question"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Start the interview
    result = InterviewService.start_interview(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/interview/respond', methods=['POST'])
def process_response():
    """Process user response and get next question"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    user_input = data.get('user_input')
    
    if not session_id or not user_input:
        return jsonify({"error": "Session ID and user input are required"}), 400
    
    # Process the response
    result = InterviewService.process_response(session_id, user_input)
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/interview/analyze', methods=['POST'])
def analyze_interview():
    """Analyze the interview transcript"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Analyze the interview
    result = InterviewService.analyze_interview(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/interview/save', methods=['POST'])
def save_interview():
    """Save the interview data to a file"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Save the interview
    result = InterviewService.save_session(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/interview/monitor/<session_id>', methods=['GET'])
def monitor_interview(session_id):
    """Render the interview monitoring page"""
    interview = InterviewService.get_session(session_id)
    if not interview:
        return redirect(url_for('langchain_features.interview_setup'))
    
    return render_template('langchain/monitor_session.html',
                          session_id=session_id,
                          title=interview.title,
                          transcript=interview.transcript)

@langchain_blueprint.route('/interview/details/<session_id>', methods=['GET'])
def interview_details(session_id):
    """Render the interview details page"""
    interview = InterviewService.get_session(session_id)
    if not interview:
        return redirect(url_for('langchain_features.interview_setup'))
    
    return render_template('langchain/interview_details.html',
                          session_id=session_id,
                          interview=interview)

# Discovery plan routes
@langchain_blueprint.route('/discovery/create', methods=['POST'])
def create_discovery_plan():
    """Create a new discovery plan"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    title = data.get('title', 'Untitled Discovery Plan')
    description = data.get('description', '')
    
    # Create the discovery plan
    plan = DiscoveryService.create_plan(title, description)
    
    return jsonify({
        "status": "success",
        "plan_id": plan.id,
        "title": plan.title
    })

@langchain_blueprint.route('/discovery/plan/<plan_id>', methods=['GET'])
def view_discovery_plan(plan_id):
    """Render the discovery plan page"""
    plan = DiscoveryService.get_plan(plan_id)
    if not plan:
        return redirect(url_for('langchain_features.index'))
    
    return render_template('langchain/discovery_plan.html',
                          plan=plan)

@langchain_blueprint.route('/api/discovery/generate', methods=['POST'])
def generate_discovery_plan():
    """Generate a discovery plan based on interview transcripts"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    plan_id = data.get('plan_id')
    interview_transcripts = data.get('transcripts', [])
    
    if not plan_id:
        return jsonify({"error": "Plan ID is required"}), 400
    
    if not interview_transcripts:
        return jsonify({"error": "At least one interview transcript is required"}), 400
    
    # Generate the discovery plan
    result = DiscoveryService.generate_plan(plan_id, interview_transcripts)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/discovery/save', methods=['POST'])
def save_discovery_plan():
    """Save the discovery plan to a file"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    plan_id = data.get('plan_id')
    if not plan_id:
        return jsonify({"error": "Plan ID is required"}), 400
    
    # Save the discovery plan
    result = DiscoveryService.save_plan(plan_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

# Research plan routes
@langchain_blueprint.route('/research/create', methods=['POST'])
def create_research_plan():
    """Create a new research plan"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    title = data.get('title', 'Untitled Research Plan')
    description = data.get('description', '')
    
    # Create the research plan
    plan = ResearchService.create_plan(title, description)
    
    return jsonify({
        "status": "success",
        "plan_id": plan.id,
        "title": plan.title
    })

@langchain_blueprint.route('/research/plan/<plan_id>', methods=['GET'])
def view_research_plan(plan_id):
    """Render the research plan page"""
    plan = ResearchService.get_plan(plan_id)
    if not plan:
        return redirect(url_for('langchain_features.index'))
    
    return render_template('langchain/research_plan.html',
                          plan=plan)

@langchain_blueprint.route('/api/research/generate', methods=['POST'])
def generate_research_plan():
    """Generate a research plan based on a research brief"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    plan_id = data.get('plan_id')
    research_brief = data.get('brief', '')
    
    if not plan_id:
        return jsonify({"error": "Plan ID is required"}), 400
    
    if not research_brief:
        return jsonify({"error": "Research brief is required"}), 400
    
    # Generate the research plan
    result = ResearchService.generate_plan(plan_id, research_brief)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/research/interview-script', methods=['POST'])
def generate_interview_script():
    """Generate an interview script based on a research plan"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    plan_id = data.get('plan_id')
    participant_info = data.get('participant_info', {})
    
    if not plan_id:
        return jsonify({"error": "Plan ID is required"}), 400
    
    # Generate the interview script
    result = ResearchService.generate_interview_script(plan_id, participant_info)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@langchain_blueprint.route('/api/research/save', methods=['POST'])
def save_research_plan():
    """Save the research plan to a file"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    plan_id = data.get('plan_id')
    if not plan_id:
        return jsonify({"error": "Plan ID is required"}), 400
    
    # Save the research plan
    result = ResearchService.save_plan(plan_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

# API for listing active interviews
@langchain_blueprint.route('/api/interviews/active', methods=['GET'])
def list_active_interviews():
    """List all active interview sessions"""
    sessions = InterviewService.list_sessions()
    
    # Filter to only active sessions
    active_sessions = [session for session in sessions if session.status == "active"]
    
    # Convert to JSON-serializable format
    result = []
    for session in active_sessions:
        result.append({
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "status": session.status
        })
    
    return jsonify({
        "status": "success",
        "interviews": result
    })

# API for getting interview transcript
@langchain_blueprint.route('/api/interview/transcript', methods=['GET'])
def get_interview_transcript():
    """Get the transcript for an interview session"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    session = InterviewService.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "status": "success",
        "transcript": session.transcript
    })

@langchain_blueprint.route('/interview/accept-terms/<session_id>', methods=['POST'])
def accept_interview_terms(session_id):
    """Accept terms and continue to interview session."""
    try:
        # Instead of storing the entire terms acceptance data, just store a simple flag
        session[f'terms_{session_id}'] = True
        
        # Get form data
        voice_id = request.form.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
        name = request.form.get('name', 'Anonymous')
        email = request.form.get('email', '')
        
        # Get the interview session
        interview = InterviewService.get_session(session_id)
        if interview:
            # Update interviewee information
            interview.interviewee['name'] = name
            interview.interviewee['email'] = email
            interview.status = 'in_progress'
            InterviewService.save_session(interview)
        
        # Redirect to the interview session
        return redirect(url_for('langchain_features.interview_session', 
                               session_id=session_id, 
                               voice_id=voice_id))
    except Exception as e:
        logger.error(f"Error accepting terms: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error accepting terms', 'error')
        return redirect(url_for('langchain_features.interview_welcome', session_id=session_id))

@langchain_blueprint.route('/api/interview/update-status', methods=['POST'])
def update_interview_status():
    """Update the interview status (active/inactive)"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    is_active = data.get('is_active')
    
    if not session_id:
        return jsonify({"status": "error", "error": "Session ID is required"}), 400
    
    if is_active is None:
        return jsonify({"status": "error", "error": "Active status is required"}), 400
    
    # Get the interview session
    interview = InterviewService.get_session(session_id)
    if not interview:
        return jsonify({"status": "error", "error": "Interview not found"}), 404
    
    # Update status
    interview.status = 'active' if is_active else 'inactive'
    
    # Save changes
    result = InterviewService.save_session(interview)
    if not result:
        return jsonify({"status": "error", "error": "Failed to save interview status"}), 500
    
    return jsonify({
        "status": "success",
        "message": "Interview status updated successfully"
    })

@langchain_blueprint.route('/api/interview/update-expiration', methods=['POST'])
def update_interview_expiration():
    """Update the interview expiration date"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    expiration_date = data.get('expiration_date')
    
    if not session_id:
        return jsonify({"status": "error", "error": "Session ID is required"}), 400
    
    if not expiration_date:
        return jsonify({"status": "error", "error": "Expiration date is required"}), 400
    
    # Get the interview session
    interview = InterviewService.get_session(session_id)
    if not interview:
        return jsonify({"status": "error", "error": "Interview not found"}), 404
    
    # Update expiration date
    try:
        from datetime import datetime
        interview.expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
    except Exception as e:
        return jsonify({"status": "error", "error": f"Invalid date format: {str(e)}"}), 400
    
    # Save changes
    result = InterviewService.save_session(interview)
    if not result:
        return jsonify({"status": "error", "error": "Failed to save expiration date"}), 500
    
    return jsonify({
        "status": "success",
        "message": "Expiration date updated successfully"
    })

@langchain_blueprint.route('/interview/expired/<session_id>', methods=['GET'])
def interview_expired(session_id):
    """Render the interview expired page"""
    interview = InterviewService.get_session(session_id)
    if not interview:
        return redirect(url_for('langchain_features.interview_setup'))
    
    return render_template('langchain/interview_expired.html',
                          session_id=session_id,
                          title=interview.title)

@langchain_blueprint.context_processor
def inject_interviews():
    """Add interviews to all template contexts that use the LangChain base template."""
    sessions = InterviewService.list_sessions()
    return dict(interviews=sessions)

@langchain_blueprint.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    """Convert speech to text (fallback for the main app route)"""
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
            
        # Save the audio file
        audio_file = request.files['audio']
        filename = os.path.join('uploads', f"temp_audio_{uuid.uuid4()}.webm")
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        
        audio_file.save(filename)
        
        # In a real implementation, you would use a speech-to-text service
        # For now, return a success with some dummy text since this is just a fallback
        # Check if the session_id is provided to detect the context
        session_id = request.form.get('session_id')
        
        # In a production implementation, this would call a real speech-to-text service
        # For now, we're simulating a response
        transcription = "This is a sample transcription response. In a real implementation, we would use a speech-to-text service."
        
        # Flag to indicate if the user requested to end the interview
        end_interview_detected = False
        
        # Use a randomized response to simulate varying transcription results
        responses = [
            "I think that covers everything I wanted to share.",
            "That's my perspective on the current system.",
            "Those are my main pain points with the process.",
            "I'd like to see those improvements in the future version."
        ]
        
        # Randomly select an "end interview" phrase about 10% of the time to simulate detection
        if random.random() < 0.1:
            end_phrases = [
                "Can we end the interview now?",
                "I think we can end the interview.",
                "Let's end the interview here.",
                "I'd like to finish the interview now."
            ]
            transcription = random.choice(end_phrases)
            end_interview_detected = True
        else:
            transcription = random.choice(responses)
        
        # Clean up the temp file
        try:
            os.remove(filename)
        except Exception as e:
            logger.error(f"Error removing temp file: {str(e)}")
        
        response = {
            "success": True,
            "text": transcription,
            "end_interview_detected": end_interview_detected
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@langchain_blueprint.route('/api/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech (fallback for the main app route)"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"success": False, "error": "No text provided"}), 400
            
        # In a real implementation, you would use a text-to-speech service
        # For now, return a success response with a blank audio
        
        # Create a minimal MP3 file that's mostly silent but valid
        # This is just a placeholder for testing - in production you'd use a real TTS service
        blank_mp3 = b'\xff\xf3\x18\xc4\x00\x00\x00\x03H\x00\x00\x00\x00LAME3.100\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        return send_file(
            io.BytesIO(blank_mp3),
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='speech.mp3'
        )
        
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@langchain_blueprint.route('/api/interview/suggest-question', methods=['POST'])
def suggest_question():
    """Handle question suggestions during an interview"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "error": "No data provided"}), 400
            
        session_id = data.get('session_id')
        question = data.get('question')
        
        if not session_id:
            return jsonify({"status": "error", "error": "Session ID is required"}), 400
        
        if not question:
            return jsonify({"status": "error", "error": "Question is required"}), 400
        
        # Here you would typically add the logic to send the question to the interviewer
        # For now, we'll just return a success response
        
        return jsonify({
            "status": "success",
            "message": "Question suggestion sent successfully"
        })
        
    except Exception as e:
        logging.exception(f"Error in suggest_question: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@langchain_blueprint.route('/api/interview/end', methods=['POST'])
def end_interview():
    """End an interview session and generate analysis if requested"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "error": "No data provided"}), 400
            
        session_id = data.get('session_id')
        generate_analysis = data.get('generate_analysis', True)
        
        if not session_id:
            return jsonify({"status": "error", "error": "Session ID is required"}), 400
        
        # Get the interview session
        interview = InterviewService.get_session(session_id)
        if not interview:
            return jsonify({"status": "error", "error": "Interview not found"}), 404
        
        # Add a final message to the transcript indicating the interview has ended
        if not interview.transcript.endswith("The interview has been completed. Thank you for your participation.\n"):
            interview.transcript += "\nDaria: The interview has been completed. Thank you for your participation.\n"
            interview.messages.append({"role": "assistant", "content": "The interview has been completed. Thank you for your participation."})
        
        # Update status
        interview.status = 'completed'
        
        # Save changes
        result = InterviewService.save_session(interview)
        if not result:
            return jsonify({"status": "error", "error": "Failed to end interview"}), 500
        
        # Generate analysis if requested
        analysis_result = None
        if generate_analysis:
            analysis_result = InterviewService.analyze_interview(session_id)
        
        return jsonify({
            "status": "success",
            "message": "Interview ended successfully",
            "analysis": analysis_result.get("analysis") if analysis_result and "analysis" in analysis_result else None
        })
        
    except Exception as e:
        logging.exception(f"Error in end_interview: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@langchain_blueprint.route('/interview/archive')
def interview_archive():
    """Render the interview archive page with completed interviews"""
    # Get all interview sessions
    sessions = InterviewService.list_sessions()
    
    return render_template('langchain/interview_archive.html',
                          interviews=sessions)

@langchain_blueprint.route('/interview/view/<session_id>')
def view_completed_interview(session_id):
    """Render the view completed interview page"""
    interview = InterviewService.get_session(session_id)
    if not interview:
        return redirect(url_for('langchain_features.interview_archive'))
    
    return render_template('langchain/view_completed_interview.html',
                          interview=interview,
                          session_id=session_id)

@langchain_blueprint.route('/api/interview/save-notes', methods=['POST'])
def save_interview_notes():
    """Save notes for an interview"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    notes = data.get('notes')
    
    if not session_id:
        return jsonify({"status": "error", "error": "Session ID is required"}), 400
    
    # Get the interview session
    interview = InterviewService.get_session(session_id)
    if not interview:
        return jsonify({"status": "error", "error": "Interview not found"}), 404
    
    # Update notes
    interview.notes = notes
    
    # Save changes
    result = InterviewService.save_session(interview)
    if not result:
        return jsonify({"status": "error", "error": "Failed to save notes"}), 500
    
    return jsonify({
        "status": "success",
        "message": "Notes saved successfully"
    })

@langchain_blueprint.route('/api/interview/generate-analysis', methods=['POST'])
def generate_interview_analysis():
    """Generate analysis for a completed interview"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": "No data provided"}), 400
        
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"status": "error", "error": "Session ID is required"}), 400
    
    # Get the interview session
    interview = InterviewService.get_session(session_id)
    if not interview:
        return jsonify({"status": "error", "error": "Interview not found"}), 404
    
    # Generate analysis
    result = InterviewService.analyze_interview(session_id)
    
    if result.get("status") == "error":
        return jsonify(result), 500
    
    return jsonify({
        "status": "success",
        "analysis": result.get("analysis"),
        "message": "Analysis generated successfully"
    }) 