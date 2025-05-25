#!/bin/bash

# Final fixes for the DARIA Memory Companion on EC2
echo "Applying final fixes to DARIA Memory Companion deployment..."

cd ~/DariaInterviewTool_new

# Activate the virtual environment
source venv/bin/activate

# Install missing dependencies
echo "Installing missing dependencies..."
pip install openai flask-jwt-extended

# Fix the memory_companion_ui.py script to properly handle host parameter
echo "Fixing the memory_companion_ui.py script..."
cat > memory_companion_ui_fix.py << 'EOF'
#!/usr/bin/env python3

import os
import sys
import json
import requests
import argparse
from flask import Flask, render_template, request, jsonify, send_from_directory

# Configuration
MEMORY_COMPANION_API = "http://3.12.144.184:5030/api/memory_companion"
ISSUE_TRACKER_API = "http://3.12.144.184:5025/api/issues"

app = Flask(__name__)

class MemoryCompanionIntegration:
    """Handles integration with Memory Companion and Issue Tracker"""
    
    def __init__(self, memory_api_url=MEMORY_COMPANION_API, issue_api_url=ISSUE_TRACKER_API):
        """Initialize with API URLs"""
        self.memory_api_url = memory_api_url
        self.issue_api_url = issue_api_url
    
    def get_project_data(self):
        """Get project data from Memory Companion"""
        try:
            response = requests.get(f"{self.memory_api_url}/project")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get project data: {response.status_code}"}
        except Exception as e:
            return {"error": f"Exception: {str(e)}"}
    
    def update_timeline(self, event_data):
        """Add a timeline event to Memory Companion"""
        try:
            response = requests.post(
                f"{self.memory_api_url}/timeline",
                json=event_data
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to add timeline event: {response.status_code}"}
        except Exception as e:
            return {"error": f"Exception: {str(e)}"}
    
    def update_opportunity(self, opportunity_data):
        """Add or update an opportunity in Memory Companion"""
        try:
            response = requests.post(
                f"{self.memory_api_url}/opportunity",
                json=opportunity_data
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to update opportunity: {response.status_code}"}
        except Exception as e:
            return {"error": f"Exception: {str(e)}"}
    
    def update_sprint(self, sprint_name):
        """Update the current sprint"""
        try:
            response = requests.post(
                f"{self.memory_api_url}/sprint",
                json={"sprint": sprint_name}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to update sprint: {response.status_code}"}
        except Exception as e:
            return {"error": f"Exception: {str(e)}"}
    
    def sync_all_opportunities(self, specific_id=None):
        """Sync all opportunities with the Issue Tracker or a specific one by ID"""
        project_data = self.get_project_data()
        if "error" in project_data:
            return project_data
        
        results = []
        opportunities = project_data.get("opportunities", [])
        
        # If a specific ID is provided, only sync that opportunity
        if specific_id:
            for opportunity in opportunities:
                if opportunity["id"] == specific_id:
                    result = self.create_issue_from_opportunity(opportunity)
                    results.append({
                        "opportunity": opportunity["id"],
                        "result": result
                    })
                    return {"synced": results, "count": len(results)}
            
            return {"error": f"Opportunity with ID {specific_id} not found"}
        
        # Sync all opportunities
        for opportunity in opportunities:
            result = self.create_issue_from_opportunity(opportunity)
            results.append({
                "opportunity": opportunity["id"],
                "result": result
            })
        
        return {"synced": results, "count": len(results)}
    
    def create_issue_from_opportunity(self, opportunity):
        """Create an issue in the Issue Tracker from an opportunity"""
        try:
            # Format for the issue tracker
            issue_data = {
                "title": opportunity["title"],
                "description": opportunity["description"],
                "priority": opportunity["priority"].lower(),
                "type": "opportunity"
            }
            
            # Use the base issues API endpoint (without "/create")
            response = requests.post(
                f"{self.issue_api_url}/new",  # Use the /new endpoint for creating new issues
                json=issue_data
            )
            
            if response.status_code == 200:
                return {"success": True, "issue": response.json()}
            else:
                error_text = ""
                try:
                    error_text = response.text
                except:
                    pass
                return {"success": False, "error": f"API Error: {response.status_code}", "details": error_text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
# Initialize integration
integration = MemoryCompanionIntegration()

@app.route('/')
def index():
    """Main page for Memory Companion Integration"""
    return render_template('memory_integration.html')

@app.route('/api/timeline', methods=['POST'])
def add_timeline_event():
    """API endpoint to add a timeline event"""
    data = request.json
    result = integration.update_timeline(data)
    return jsonify(result)

@app.route('/api/opportunity', methods=['POST'])
def add_opportunity():
    """API endpoint to add an opportunity"""
    data = request.json
    result = integration.update_opportunity(data)
    return jsonify(result)

@app.route('/api/sprint', methods=['POST'])
def update_sprint():
    """API endpoint to update sprint"""
    data = request.json
    result = integration.update_sprint(data.get('sprint', ''))
    return jsonify(result)

@app.route('/api/project', methods=['GET'])
def get_project_data():
    """API endpoint to get project data"""
    result = integration.get_project_data()
    return jsonify(result)

@app.route('/api/sync', methods=['POST'])
def sync_opportunities():
    """API endpoint to sync opportunities with Issue Tracker"""
    data = request.json
    specific_id = data.get('id') if data else None
    result = integration.sync_all_opportunities(specific_id)
    return jsonify(result)

@app.route('/api/migrate_opportunities', methods=['POST'])
def migrate_opportunities():
    """API endpoint to migrate existing opportunities to Issue Tracker"""
    try:
        # Get project data
        project_data = integration.get_project_data()
        if "error" in project_data:
            return jsonify({"error": f"Failed to get project data: {project_data['error']}"})
        
        opportunities = project_data.get("opportunities", [])
        if not opportunities:
            return jsonify({"error": "No opportunities found to migrate"})
        
        migrated_count = 0
        migrated_opps = []
        
        # Process each opportunity
        for opp in opportunities:
            # Create issue data
            issue_data = {
                "title": opp["title"],
                "description": opp["description"],
                "priority": opp["priority"].lower(),
                "type": "opportunity"
            }
            
            # Send to Issue Tracker
            response = requests.post(
                f"{ISSUE_TRACKER_API}/new",  # Use the /new endpoint for creating new issues
                json=issue_data
            )
            
            if response.status_code == 200:
                migrated_count += 1
                migrated_opps.append(opp["id"])
            else:
                error_text = ""
                try:
                    error_text = response.text
                except:
                    pass
                return jsonify({"error": f"Failed to migrate opportunity {opp['id']}: {response.status_code} - {error_text}"})
        
        return jsonify({
            "success": True,
            "migrated_count": migrated_count,
            "migrated_opportunities": migrated_opps
        })
            
    except Exception as e:
        return jsonify({"error": f"Failed to migrate opportunities: {str(e)}"})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Memory Companion Integration Tool')
    parser.add_argument('--port', type=int, default=5035, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port, host=args.host)
EOF

# Fix test server Python path
cat > start_test_server_fixed.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
sudo nohup python3 test_server.py > test_server.log 2>&1 &
echo $! > .test_server_pid
echo "Test server started on port 80"
EOF

# Create a simpler memory companion service wrapper
cat > memory_companion_service_wrapper.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import argparse
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory storage for simplicity
project_data = {
    "name": "DARIA Project",
    "currentSprint": "Sprint 1",
    "opportunities": [
        {
            "id": "OPP-001",
            "title": "Add TTS and STT to Daria Memory Companion",
            "description": "We have the memory companion UI where we can chat with Daria about the project milestones. Currently it is text only chat. It would be great to add text-to-speech and speech-to-text capabilities.",
            "priority": "Medium"
        }
    ],
    "timeline": [
        {
            "date": "2023-04-01",
            "title": "Project Started",
            "description": "The DARIA project was officially kicked off"
        },
        {
            "date": "2023-05-15",
            "title": "First Release",
            "description": "The first version of DARIA was released to alpha testers"
        }
    ],
    "statistics": {
        "totalStories": 42,
        "completedStories": 28,
        "inProgressStories": 8,
        "blockedStories": 6
    }
}

# Serve static files from the static directory
@app.route('/static/<path:path>')
def serve_static(path):
    # Create a basic HTML file for memory companion
    if path == 'daria_memory_companion.html':
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>DARIA Memory Companion</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #4285f4;
                }
                .chat-container {
                    height: 400px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin: 20px 0;
                    border-radius: 5px;
                }
                .message {
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                }
                .user {
                    background-color: #e9f5ff;
                    text-align: right;
                }
                .assistant {
                    background-color: #f0f0f0;
                }
                .input-area {
                    display: flex;
                }
                #message-input {
                    flex-grow: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                button {
                    background-color: #4285f4;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    margin-left: 10px;
                    border-radius: 5px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #3367d6;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>DARIA Memory Companion</h1>
                <p>Your project research assistant that remembers everything across sessions.</p>
                
                <div class="chat-container" id="chat-container">
                    <div class="message assistant">
                        Hello! I'm DARIA, your memory companion. I can help you remember details about your project. 
                        What would you like to know about?
                    </div>
                </div>
                
                <div class="input-area">
                    <input type="text" id="message-input" placeholder="Type your message here...">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>

            <script>
                const chatContainer = document.getElementById('chat-container');
                const messageInput = document.getElementById('message-input');
                
                // Sample project data for demo
                const projectData = {
                    opportunities: [
                        {
                            id: "OPP-001",
                            title: "Add TTS and STT to Daria Memory Companion",
                            description: "We have the memory companion UI where we can chat with Daria about the project milestones. Currently it is text only chat. It would be great to add text-to-speech and speech-to-text capabilities.",
                            priority: "Medium"
                        }
                    ],
                    timeline: [
                        {
                            date: "2023-04-01",
                            title: "Project Started",
                            description: "The DARIA project was officially kicked off"
                        },
                        {
                            date: "2023-05-15",
                            title: "First Release",
                            description: "The first version of DARIA was released to alpha testers"
                        }
                    ]
                };
                
                function sendMessage() {
                    const message = messageInput.value.trim();
                    if (message === '') return;
                    
                    // Add user message to chat
                    addMessage(message, 'user');
                    messageInput.value = '';
                    
                    // Process the user's message
                    processMessage(message);
                }
                
                function addMessage(text, sender) {
                    const messageDiv = document.createElement('div');
                    messageDiv.classList.add('message', sender);
                    messageDiv.textContent = text;
                    chatContainer.appendChild(messageDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
                
                function processMessage(message) {
                    // Simple keyword-based responses
                    setTimeout(() => {
                        let response;
                        
                        if (message.toLowerCase().includes('opportunity') || message.toLowerCase().includes('opportunities')) {
                            response = "I found an opportunity: OPP-001: Add TTS and STT to Daria Memory Companion (Medium). It suggests adding text-to-speech and speech-to-text capabilities to the Memory Companion.";
                        } else if (message.toLowerCase().includes('timeline') || message.toLowerCase().includes('milestones')) {
                            response = "Here are the key milestones: Project Started on April 1, 2023, and First Release on May 15, 2023.";
                        } else if (message.toLowerCase().includes('tts') || message.toLowerCase().includes('stt') || message.toLowerCase().includes('speech')) {
                            response = "There is an opportunity (OPP-001) to add TTS and STT capabilities to the Memory Companion UI. This would allow for voice interactions instead of just text.";
                        } else {
                            response = "I'm your memory companion for the DARIA project. You can ask me about project opportunities, timeline events, or specific features like TTS/STT support.";
                        }
                        
                        addMessage(response, 'assistant');
                    }, 1000);
                }
                
                // Handle Enter key in input
                messageInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
        '''
        return html_content
    
    return "Static file not found", 404

@app.route('/api/memory_companion/project', methods=['GET'])
def get_project():
    return jsonify(project_data)

@app.route('/api/memory_companion/timeline', methods=['POST'])
def add_timeline_event():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Add the event to the timeline
    project_data["timeline"].append(data)
    return jsonify({"success": True, "event": data})

@app.route('/api/memory_companion/opportunity', methods=['POST'])
def add_opportunity():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Check if the opportunity already exists
    for i, opp in enumerate(project_data["opportunities"]):
        if opp["id"] == data["id"]:
            # Update existing opportunity
            project_data["opportunities"][i] = data
            return jsonify({"success": True, "updated": True, "opportunity": data})
    
    # Add new opportunity
    project_data["opportunities"].append(data)
    return jsonify({"success": True, "added": True, "opportunity": data})

@app.route('/api/memory_companion/sprint', methods=['POST'])
def update_sprint():
    data = request.json
    if not data or "sprint" not in data:
        return jsonify({"error": "No sprint provided"}), 400
    
    # Update the current sprint
    project_data["currentSprint"] = data["sprint"]
    return jsonify({"success": True, "sprint": data["sprint"]})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Memory Companion Service')
    parser.add_argument('--port', type=int, default=5030, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
EOF

# Make scripts executable
chmod +x memory_companion_ui_fix.py
chmod +x memory_companion_service_wrapper.py
chmod +x start_test_server_fixed.sh

# Create a new start script
cat > start_services_fixed.sh << 'EOF'
#!/bin/bash

# Start all fixed services
echo "Starting Memory Companion services..."

# Change to the application directory
cd $(dirname $0)
source venv/bin/activate

# Start memory companion service wrapper
echo "Starting Memory Companion API..."
nohup python3 memory_companion_service_wrapper.py --host 0.0.0.0 --port 5030 > memory_api_fixed.log 2>&1 &
echo $! > .memory_api_pid

# Start memory companion UI fixed version
echo "Starting Memory Companion UI..."
nohup python3 memory_companion_ui_fix.py --host 0.0.0.0 --port 5035 > memory_ui_fixed.log 2>&1 &
echo $! > .memory_ui_pid

# Start test server
echo "Starting test server..."
source start_test_server_fixed.sh

echo "Services started! Access them at:"
echo "- Test page: http://3.12.144.184/"
echo "- Memory Companion UI: http://3.12.144.184:5030/static/daria_memory_companion.html"
echo "- Memory Companion Integration: http://3.12.144.184:5035/"
EOF

chmod +x start_services_fixed.sh

# Stop current services if running
echo "Stopping any running services..."
if [ -f stop_memory_services.sh ]; then
    ./stop_memory_services.sh
fi

# Start fixed services
echo "Starting fixed services..."
./start_services_fixed.sh

echo "Final fixes applied successfully!"
echo ""
echo "You can now access DARIA Memory Companion at:"
echo "- Test page: http://3.12.144.184/"
echo "- Memory Companion UI: http://3.12.144.184:5030/static/daria_memory_companion.html"
echo "- Memory Companion Integration tool: http://3.12.144.184:5035/" 