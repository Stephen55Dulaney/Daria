#!/usr/bin/env python3
"""
Simplified DARIA Application
This is a basic version of DARIA that doesn't use LangChain or other problematic dependencies.
It provides the core functionality needed for transcript uploads and session management.
"""

import os
import sys
import re
import uuid
import json
import datetime
import logging
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Constants
DATA_DIR = os.path.join(os.getcwd(), "data")
INTERVIEWS_DIR = os.path.join(DATA_DIR, "interviews")
SESSIONS_DIR = os.path.join(INTERVIEWS_DIR, "sessions")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INTERVIEWS_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})

@app.route('/api/discussion_guides', methods=['GET'])
def get_discussion_guides():
    """List all discussion guides"""
    guides = []
    try:
        for file_path in Path(INTERVIEWS_DIR).glob("*.json"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            
            with open(file_path, 'r') as f:
                guide_data = json.load(f)
                guides.append(guide_data)
        
        return jsonify(guides)
    except Exception as e:
        logger.error(f"Error fetching discussion guides: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>', methods=['GET'])
def get_discussion_guide(guide_id):
    """Get a specific discussion guide by ID"""
    try:
        file_path = os.path.join(INTERVIEWS_DIR, f"{guide_id}.json")
        if not os.path.exists(file_path):
            return jsonify({"error": f"Guide {guide_id} not found"}), 404
        
        with open(file_path, 'r') as f:
            guide_data = json.load(f)
            return jsonify(guide_data)
    except Exception as e:
        logger.error(f"Error fetching discussion guide {guide_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>/sessions', methods=['GET'])
def get_guide_sessions(guide_id):
    """Get all sessions for a specific guide"""
    try:
        guide_file = os.path.join(INTERVIEWS_DIR, f"{guide_id}.json")
        if not os.path.exists(guide_file):
            return jsonify({"error": f"Guide {guide_id} not found"}), 404
        
        with open(guide_file, 'r') as f:
            guide_data = json.load(f)
            session_ids = guide_data.get("sessions", [])
        
        sessions = []
        for session_id in session_ids:
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    sessions.append(session_data)
        
        return jsonify(sessions)
    except Exception as e:
        logger.error(f"Error fetching sessions for guide {guide_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session by ID"""
    try:
        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": f"Session {session_id} not found"}), 404
        
        with open(file_path, 'r') as f:
            session_data = json.load(f)
            return jsonify(session_data)
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/upload_transcript', methods=['POST'])
def api_upload_transcript():
    """Handle transcript upload and conversion to interview format"""
    try:
        # Ensure files were uploaded
        if 'transcript_file' not in request.files:
            return jsonify({'success': False, 'error': 'No transcript file provided'}), 400
        
        transcript_file = request.files['transcript_file']
        if transcript_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get metadata from form
        title = request.form.get('title', 'Untitled Interview')
        project = request.form.get('project', '')
        interview_type = request.form.get('interview_type', 'discovery_interview')
        participant_name = request.form.get('participant_name', 'Anonymous')
        participant_role = request.form.get('participant_role', '')
        participant_email = request.form.get('participant_email', '')
        guide_id = request.form.get('guide_id', '')
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Read and process the transcript content
        try:
            transcript_content = transcript_file.read().decode('utf-8')
        except UnicodeDecodeError:
            # Try another encoding if utf-8 fails
            transcript_file.seek(0)
            transcript_content = transcript_file.read().decode('latin-1')
        
        # Process transcript into conversation chunks (simplified implementation)
        lines = transcript_content.strip().split('\n')
        messages = []
        raw_transcript = ""
        current_speaker = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple colon pattern matching
            colon_match = re.match(r'^([^:]+):\s*(.*)', line)
            if colon_match:
                # Save previous speaker's content
                if current_speaker and current_content:
                    # Determine role based on speaker
                    role = 'assistant' if any(term in current_speaker.lower() for term in 
                                          ['interviewer', 'researcher', 'moderator']) else 'user'
                    
                    # Add to messages
                    messages.append({
                        'id': str(uuid.uuid4()),
                        'content': ' '.join(current_content),
                        'role': role,
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    
                    # Add to raw transcript
                    speaker_label = "Moderator" if role == 'assistant' else "Participant"
                    raw_transcript += f"\n\n{speaker_label}: {' '.join(current_content)}"
                    
                    current_content = []
                
                # Extract new speaker and content
                current_speaker = colon_match.group(1).strip()
                content = colon_match.group(2).strip()
                if content:
                    current_content.append(content)
            elif current_speaker:
                # Continue previous speaker
                current_content.append(line)
        
        # Add the last speaker's content
        if current_speaker and current_content:
            # Determine role based on speaker
            role = 'assistant' if any(term in current_speaker.lower() for term in 
                                  ['interviewer', 'researcher', 'moderator']) else 'user'
            
            # Add to messages
            messages.append({
                'id': str(uuid.uuid4()),
                'content': ' '.join(current_content),
                'role': role,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # Add to raw transcript
            speaker_label = "Moderator" if role == 'assistant' else "Participant"
            raw_transcript += f"\n\n{speaker_label}: {' '.join(current_content)}"
        
        # Create the session data in the required format
        now = datetime.datetime.now().isoformat()
        session_data = {
            "id": session_id,
            "guide_id": guide_id,
            "interviewee": {
                "name": participant_name,
                "email": participant_email or "",
                "role": participant_role or "",
                "department": "",
                "company": "",
                "demographics": {
                    "age_range": "",
                    "gender": "",
                    "location": ""
                }
            },
            "status": "active",
            "messages": messages,
            "transcript": raw_transcript.strip(),
            "analysis": None,
            "created_at": now,
            "updated_at": now,
            "title": title,
            "project": project,
            "interview_type": interview_type
        }
        
        # Save the session data
        session_file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        with open(session_file_path, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"Saved session data to {session_file_path}")
        
        # If a guide ID was provided, update the guide with this session
        if guide_id:
            guide_file_path = os.path.join(INTERVIEWS_DIR, f"{guide_id}.json")
            if os.path.exists(guide_file_path):
                try:
                    with open(guide_file_path, 'r') as f:
                        guide_data = json.load(f)
                    
                    if "sessions" not in guide_data:
                        guide_data["sessions"] = []
                    
                    if session_id not in guide_data["sessions"]:
                        guide_data["sessions"].append(session_id)
                        guide_data["updated_at"] = now
                        
                        with open(guide_file_path, 'w') as f:
                            json.dump(guide_data, f, indent=2)
                        
                        logger.info(f"Updated guide {guide_id} with session {session_id}")
                except Exception as e:
                    logger.error(f"Error updating guide: {str(e)}")
        
        # Return success with redirect URL
        redirect_url = f"/discussion_guide/{guide_id}" if guide_id else f"/session/{session_id}"
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Transcript uploaded successfully',
            'redirect_url': redirect_url
        })
    
    except Exception as e:
        logger.error(f"Error uploading transcript: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Error processing transcript: {str(e)}"
        }), 500

@app.route('/', methods=['GET'])
def home():
    """Render the home page"""
    return render_template('index.html')

@app.route('/discussion_guide/<guide_id>', methods=['GET'])
def discussion_guide_details(guide_id):
    """Render the discussion guide details page"""
    return render_template('guide.html', guide_id=guide_id)

@app.route('/session/<session_id>', methods=['GET'])
def session_details(session_id):
    """Render the session details page"""
    return render_template('session.html', session_id=session_id)

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/api/sessions', methods=['GET'])
def get_all_sessions():
    """Get all interview sessions"""
    try:
        sessions = []
        for file_path in Path(SESSIONS_DIR).glob("*.json"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            
            with open(file_path, 'r') as f:
                session_data = json.load(f)
                # Filter out sensitive or unnecessary information
                filtered_data = {
                    'id': session_data.get('id'),
                    'title': session_data.get('title'),
                    'project': session_data.get('project'),
                    'topic': session_data.get('topic'),
                    'context': session_data.get('context'),
                    'goals': session_data.get('goals'),
                    'created_at': session_data.get('created_at'),
                    'updated_at': session_data.get('updated_at'),
                    'interview_type': session_data.get('interview_type')
                }
                sessions.append(filtered_data)
        
        return jsonify(sessions)
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transcript/<session_id>', methods=['GET'])
def get_transcript(session_id):
    """Get the full transcript and details for a session"""
    try:
        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.exists(file_path):
            return jsonify({"error": f"Session {session_id} not found"}), 404
        
        with open(file_path, 'r') as f:
            session_data = json.load(f)
            # Return all data needed for transcript view
            return jsonify({
                'id': session_data.get('id'),
                'title': session_data.get('title'),
                'project': session_data.get('project'),
                'topic': session_data.get('topic'),
                'context': session_data.get('context'),
                'goals': session_data.get('goals'),
                'messages': session_data.get('messages', []),
                'analysis': session_data.get('analysis'),
                'created_at': session_data.get('created_at'),
                'updated_at': session_data.get('updated_at')
            })
    except Exception as e:
        logger.error(f"Error fetching transcript for session {session_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/interview_archive')
def interview_archive():
    interviews = load_interviews()
    return render_template('langchain/interview_archive.html', interviews=interviews)

def load_interviews():
    directory = SESSIONS_DIR  # already defined as data/interviews/sessions
    interviews = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename), 'r') as f:
                data = json.load(f)
                interviews.append(data)
    return interviews

# Main entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DARIA Interview API')
    parser.add_argument('--port', type=int, default=5025, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    port = args.port
    debug_mode = args.debug
    
    print(f"Starting DARIA Interview API on port {port}")
    print(f"Health check endpoint: http://127.0.0.1:{port}/api/health")
    print(f"API docs: http://127.0.0.1:{port}/static/api_docs.html")
    
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    
    # Create basic templates if they don't exist
    if not os.path.exists("templates/index.html"):
        with open("templates/index.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>DARIA Interview Tool</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .guide { border: 1px solid #ddd; margin: 10px 0; padding: 10px; border-radius: 5px; }
        .guide h3 { margin-top: 0; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>DARIA Interview Tool</h1>
    <p>Welcome to the DARIA Interview Tool. This is a simplified version that supports basic functionality.</p>
    
    <h2>Discussion Guides</h2>
    <div id="guides-list">Loading...</div>
    
    <script>
        // Fetch and display discussion guides
        fetch('/api/discussion_guides')
            .then(response => response.json())
            .then(guides => {
                const guidesList = document.getElementById('guides-list');
                if (guides.length === 0) {
                    guidesList.innerHTML = '<p>No discussion guides found.</p>';
                    return;
                }
                
                let html = '';
                guides.forEach(guide => {
                    html += `<div class="guide">
                        <h3>${guide.title || 'Untitled Guide'}</h3>
                        <p>Project: ${guide.project || 'N/A'}</p>
                        <p>Sessions: ${(guide.sessions || []).length}</p>
                        <a href="/discussion_guide/${guide.id}">View Guide</a>
                    </div>`;
                });
                guidesList.innerHTML = html;
            })
            .catch(error => {
                document.getElementById('guides-list').innerHTML = 
                    `<p>Error loading guides: ${error.message}</p>`;
            });
    </script>
</body>
</html>""")
    
    if not os.path.exists("templates/guide.html"):
        with open("templates/guide.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Discussion Guide Details</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .session { border: 1px solid #ddd; margin: 10px 0; padding: 10px; border-radius: 5px; }
        .session h3 { margin-top: 0; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .upload-form { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .form-row { margin-bottom: 10px; }
        label { display: inline-block; width: 150px; }
        input, select { padding: 5px; width: 300px; }
        button { padding: 8px 15px; background: #0066cc; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <a href="/">&larr; Back to home</a>
    <h1 id="guide-title">Loading guide...</h1>
    <div id="guide-details"></div>
    
    <h2>Sessions</h2>
    <div id="sessions-list">Loading...</div>
    
    <div class="upload-form">
        <h2>Upload Transcript</h2>
        <form id="upload-form" enctype="multipart/form-data">
            <div class="form-row">
                <label for="transcript_file">Transcript File:</label>
                <input type="file" id="transcript_file" name="transcript_file" required>
            </div>
            <div class="form-row">
                <label for="title">Title:</label>
                <input type="text" id="title" name="title" placeholder="Interview Title">
            </div>
            <div class="form-row">
                <label for="project">Project:</label>
                <input type="text" id="project" name="project" placeholder="Project Name">
            </div>
            <div class="form-row">
                <label for="interview_type">Interview Type:</label>
                <select id="interview_type" name="interview_type">
                    <option value="discovery_interview">Discovery Interview</option>
                    <option value="usability_testing">Usability Testing</option>
                    <option value="customer_feedback">Customer Feedback</option>
                </select>
            </div>
            <div class="form-row">
                <label for="participant_name">Participant Name:</label>
                <input type="text" id="participant_name" name="participant_name" placeholder="Participant Name">
            </div>
            <div class="form-row">
                <label for="participant_email">Participant Email:</label>
                <input type="email" id="participant_email" name="participant_email" placeholder="Participant Email">
            </div>
            <div class="form-row">
                <label for="participant_role">Participant Role:</label>
                <input type="text" id="participant_role" name="participant_role" placeholder="Participant Role">
            </div>
            <input type="hidden" id="guide_id" name="guide_id">
            <div class="form-row">
                <button type="submit">Upload Transcript</button>
            </div>
        </form>
        <div id="upload-result"></div>
    </div>
    
    <script>
        // Get guide ID from URL
        const guideId = window.location.pathname.split('/').pop();
        document.getElementById('guide_id').value = guideId;
        
        // Fetch and display guide details
        fetch(`/api/discussion_guide/${guideId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Guide not found');
                }
                return response.json();
            })
            .then(guide => {
                document.getElementById('guide-title').textContent = guide.title || 'Untitled Guide';
                
                let detailsHtml = `
                    <p>Project: ${guide.project || 'N/A'}</p>
                    <p>Created: ${new Date(guide.created_at).toLocaleString()}</p>
                    <p>Updated: ${new Date(guide.updated_at).toLocaleString()}</p>
                `;
                document.getElementById('guide-details').innerHTML = detailsHtml;
                
                // Populate form fields
                document.getElementById('title').value = guide.title || '';
                document.getElementById('project').value = guide.project || '';
            })
            .catch(error => {
                document.getElementById('guide-title').textContent = 'Error Loading Guide';
                document.getElementById('guide-details').innerHTML = 
                    `<p>Error: ${error.message}</p>`;
            });
        
        // Fetch and display sessions
        fetch(`/api/discussion_guide/${guideId}/sessions`)
            .then(response => response.json())
            .then(sessions => {
                const sessionsList = document.getElementById('sessions-list');
                if (!sessions || sessions.length === 0) {
                    sessionsList.innerHTML = '<p>No sessions found for this guide.</p>';
                    return;
                }
                
                let html = '';
                sessions.forEach(session => {
                    const participantName = session.interviewee && session.interviewee.name 
                        ? session.interviewee.name : 'Anonymous';
                    
                    html += `<div class="session">
                        <h3>${session.title || 'Untitled Session'}</h3>
                        <p>Participant: ${participantName}</p>
                        <p>Created: ${new Date(session.created_at).toLocaleString()}</p>
                        <p>Status: ${session.status || 'Unknown'}</p>
                        <a href="/session/${session.id}">View Session</a>
                    </div>`;
                });
                sessionsList.innerHTML = html;
            })
            .catch(error => {
                document.getElementById('sessions-list').innerHTML = 
                    `<p>Error loading sessions: ${error.message}</p>`;
            });
        
        // Handle form submission
        document.getElementById('upload-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const uploadResult = document.getElementById('upload-result');
            uploadResult.innerHTML = '<p>Uploading transcript...</p>';
            
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/upload_transcript', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    uploadResult.innerHTML = `<p style="color: green;">
                        Transcript uploaded successfully! 
                        <a href="${result.redirect_url}">View Session</a>
                    </p>`;
                    
                    // Refresh the sessions list
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    uploadResult.innerHTML = `<p style="color: red;">
                        Error: ${result.error || 'Unknown error'}
                    </p>`;
                }
            } catch (error) {
                uploadResult.innerHTML = `<p style="color: red;">
                    Error: ${error.message}
                </p>`;
            }
        });
    </script>
</body>
</html>""")
    
    if not os.path.exists("templates/session.html"):
        with open("templates/session.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Session Details</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .message.user { background-color: #f0f0f0; }
        .message.assistant { background-color: #e6f7ff; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .metadata { margin-bottom: 20px; }
        .metadata p { margin: 5px 0; }
    </style>
</head>
<body>
    <a href="/">&larr; Back to home</a>
    <div id="session-nav"></div>
    <h1 id="session-title">Loading session...</h1>
    
    <div class="metadata" id="session-metadata"></div>
    
    <h2>Messages</h2>
    <div id="messages-list">Loading...</div>
    
    <h2>Raw Transcript</h2>
    <pre id="raw-transcript"></pre>
    
    <script>
        // Get session ID from URL
        const sessionId = window.location.pathname.split('/').pop();
        
        // Fetch and display session details
        fetch(`/api/session/${sessionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Session not found');
                }
                return response.json();
            })
            .then(session => {
                document.title = `${session.title || 'Untitled Session'} - DARIA`;
                document.getElementById('session-title').textContent = session.title || 'Untitled Session';
                
                // Set up navigation if guide_id is present
                if (session.guide_id) {
                    document.getElementById('session-nav').innerHTML = 
                        `<a href="/discussion_guide/${session.guide_id}">&larr; Back to guide</a>`;
                }
                
                // Display metadata
                const participantName = session.interviewee && session.interviewee.name 
                    ? session.interviewee.name : 'Anonymous';
                
                let metadataHtml = `
                    <p><strong>Participant:</strong> ${participantName}</p>
                    <p><strong>Project:</strong> ${session.project || 'N/A'}</p>
                    <p><strong>Created:</strong> ${new Date(session.created_at).toLocaleString()}</p>
                    <p><strong>Status:</strong> ${session.status || 'Unknown'}</p>
                `;
                
                if (session.interviewee) {
                    if (session.interviewee.email) {
                        metadataHtml += `<p><strong>Email:</strong> ${session.interviewee.email}</p>`;
                    }
                    if (session.interviewee.role) {
                        metadataHtml += `<p><strong>Role:</strong> ${session.interviewee.role}</p>`;
                    }
                }
                
                document.getElementById('session-metadata').innerHTML = metadataHtml;
                
                // Display messages
                const messagesList = document.getElementById('messages-list');
                if (!session.messages || session.messages.length === 0) {
                    messagesList.innerHTML = '<p>No messages found for this session.</p>';
                } else {
                    let html = '';
                    session.messages.forEach(message => {
                        const role = message.role || 'user';
                        const timestamp = message.timestamp 
                            ? new Date(message.timestamp).toLocaleTimeString() 
                            : '';
                        
                        html += `<div class="message ${role}">
                            <div class="message-header">
                                <strong>${role === 'assistant' ? 'Interviewer' : 'Participant'}</strong>
                                ${timestamp ? `<span style="float:right">${timestamp}</span>` : ''}
                            </div>
                            <div class="message-content">
                                ${message.content}
                            </div>
                        </div>`;
                    });
                    messagesList.innerHTML = html;
                }
                
                // Display raw transcript
                document.getElementById('raw-transcript').textContent = session.transcript || 'No transcript available.';
            })
            .catch(error => {
                document.getElementById('session-title').textContent = 'Error Loading Session';
                document.getElementById('session-metadata').innerHTML = 
                    `<p>Error: ${error.message}</p>`;
            });
    </script>
</body>
</html>""")
    
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 