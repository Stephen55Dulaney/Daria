#!/usr/bin/env python3
"""
Launch Interview UI

This script provides a web interface for launching interviews with custom prompts
configured in the interview setup page. It allows users to select and run interviews
configured in the system.
"""

import os
import json
import subprocess
import threading
import webbrowser
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "daria_interview_launcher"

# Directory for interview data
DATA_DIR = "data/interviews"

# Flag to track if an interview is in progress
current_interview = None
interview_thread = None

def load_all_interviews():
    """Load all interviews from the data directory"""
    interviews = {}
    if not os.path.exists(DATA_DIR):
        return interviews
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            session_id = filename.replace('.json', '')
            try:
                with open(os.path.join(DATA_DIR, filename), 'r') as f:
                    interview_data = json.load(f)
                    interviews[session_id] = interview_data
            except Exception as e:
                print(f"Error loading interview {filename}: {str(e)}")
    
    return interviews

def run_interview(session_id, use_tts=False, model="gpt-4o"):
    """Run the interview script in a separate thread"""
    global current_interview
    
    # Build command
    cmd = [
        'python', 'langchain_conversation_with_custom_prompts.py',
        '--session_id', session_id,
        '--model', model
    ]
    
    if use_tts:
        cmd.append('--use_tts')
    
    # Set the current interview
    current_interview = {
        'session_id': session_id,
        'start_time': datetime.now().isoformat(),
        'command': ' '.join(cmd)
    }
    
    # Run the command
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Error running interview: {str(e)}")
    
    # Clear the current interview when done
    current_interview = None

@app.route('/')
def index():
    """Main page that lists available interviews"""
    interviews = load_all_interviews()
    
    # Sort interviews by creation date (newest first)
    sorted_interviews = []
    for session_id, interview in interviews.items():
        # Add the session_id to the interview data
        interview['session_id'] = session_id
        
        # Add a formatted creation date
        created_at = interview.get('created_at', '')
        if created_at:
            try:
                # Try parsing the ISO format
                created_date = datetime.fromisoformat(created_at)
                interview['formatted_date'] = created_date.strftime("%b %d, %Y %I:%M %p")
            except:
                interview['formatted_date'] = created_at
        
        sorted_interviews.append(interview)
    
    # Sort by created_at date (newest first)
    sorted_interviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template(
        'interview_launcher.html',
        interviews=sorted_interviews,
        current_interview=current_interview
    )

@app.route('/start_interview', methods=['POST'])
def start_interview():
    """Start a new interview"""
    global interview_thread
    
    # Check if an interview is already running
    if current_interview:
        return jsonify({
            'success': False,
            'error': 'An interview is already in progress'
        })
    
    # Get form data
    session_id = request.form.get('session_id')
    use_tts = 'use_tts' in request.form
    model = request.form.get('model', 'gpt-4o')
    
    # Validate session_id
    if not session_id:
        return jsonify({
            'success': False,
            'error': 'No session ID provided'
        })
    
    # Start the interview in a new thread
    interview_thread = threading.Thread(
        target=run_interview,
        args=(session_id, use_tts, model),
        daemon=True
    )
    interview_thread.start()
    
    # Redirect back to the main page
    return redirect(url_for('index'))

@app.route('/stop_interview', methods=['POST'])
def stop_interview():
    """Stop the current interview"""
    global current_interview
    
    # Check if an interview is running
    if not current_interview:
        return jsonify({
            'success': False,
            'error': 'No interview is currently running'
        })
    
    # We can't really stop the subprocess easily, so we'll just mark it as stopped
    current_interview = None
    
    # Redirect back to the main page
    return redirect(url_for('index'))

@app.route('/interview_status')
def interview_status():
    """Get the status of the current interview"""
    return jsonify({
        'interview_running': current_interview is not None,
        'interview': current_interview
    })

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5050')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template if it doesn't exist
    template_path = 'templates/interview_launcher.html'
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DARIA Interview Launcher</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .interviews {
            margin-top: 20px;
        }
        .interview-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #fff;
        }
        .interview-card h3 {
            margin-top: 0;
            color: #333;
        }
        .interview-card p {
            margin: 5px 0;
            color: #666;
        }
        .interview-card .date {
            color: #999;
            font-size: 0.9em;
        }
        .interview-card .details {
            margin-top: 10px;
            font-size: 0.9em;
        }
        .form-group {
            margin-bottom: 10px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        .form-control {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .btn {
            display: inline-block;
            padding: 8px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
        }
        .btn:hover {
            background-color: #0069d9;
        }
        .btn-danger {
            background-color: #dc3545;
        }
        .btn-danger:hover {
            background-color: #bd2130;
        }
        .current-interview {
            background-color: #d4edda;
            color: #155724;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            border: 1px solid #c3e6cb;
        }
        .prompt-box {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin-top: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>DARIA Interview Launcher</h1>
        
        {% if current_interview %}
        <div class="current-interview">
            <h3>Interview in Progress</h3>
            <p><strong>Session ID:</strong> {{ current_interview.session_id }}</p>
            <p><strong>Started:</strong> {{ current_interview.start_time }}</p>
            <form action="/stop_interview" method="post">
                <button type="submit" class="btn btn-danger">Stop Interview</button>
            </form>
        </div>
        {% endif %}
        
        <div class="interviews">
            <h2>Available Interviews</h2>
            
            {% if interviews %}
                {% for interview in interviews %}
                <div class="interview-card">
                    <h3>{{ interview.title }}</h3>
                    <p class="date">Created: {{ interview.formatted_date }}</p>
                    
                    {% if interview.project %}
                    <p><strong>Project:</strong> {{ interview.project }}</p>
                    {% endif %}
                    
                    {% if interview.interview_type %}
                    <p><strong>Type:</strong> {{ interview.interview_type }}</p>
                    {% endif %}
                    
                    {% if interview.character_select %}
                    <p><strong>Character:</strong> {{ interview.character_select }}</p>
                    {% endif %}
                    
                    <div class="details">
                        {% if interview.interview_prompt %}
                        <p><strong>Interview Prompt:</strong></p>
                        <div class="prompt-box">{{ interview.interview_prompt }}</div>
                        {% endif %}
                        
                        {% if interview.analysis_prompt %}
                        <p><strong>Analysis Prompt:</strong></p>
                        <div class="prompt-box">{{ interview.analysis_prompt }}</div>
                        {% endif %}
                    </div>
                    
                    {% if not current_interview %}
                    <form action="/start_interview" method="post" style="margin-top: 15px;">
                        <input type="hidden" name="session_id" value="{{ interview.session_id }}">
                        
                        <div class="form-group">
                            <label>
                                <input type="checkbox" name="use_tts"> 
                                Use text-to-speech
                            </label>
                        </div>
                        
                        <div class="form-group">
                            <label for="model">AI Model</label>
                            <select name="model" id="model" class="form-control">
                                <option value="gpt-4o">GPT-4o</option>
                                <option value="gpt-4o-mini">GPT-4o Mini</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            </select>
                        </div>
                        
                        <button type="submit" class="btn">Start Interview</button>
                    </form>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <p>No interviews available. Please create one using the interview setup page.</p>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Check for interview status every 5 seconds
        function checkInterviewStatus() {
            fetch('/interview_status')
                .then(response => response.json())
                .then(data => {
                    if (data.interview_running !== ({{ 'true' if current_interview else 'false' }})) {
                        // Reload the page if the interview status has changed
                        window.location.reload();
                    }
                });
        }
        
        // Set up the status check interval
        setInterval(checkInterviewStatus, 5000);
    </script>
</body>
</html>''')
    
    # Open browser
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the app
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False) 