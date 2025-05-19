#!/usr/bin/env python3
"""
Memory Companion UI Integration Tool

This script provides a conversational interface between DARIA's Memory Companion
and the Issue Tracker, allowing UX researchers to update project milestones and
opportunities without needing terminal commands.
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configuration
MEMORY_COMPANION_API = "http://localhost:5030/api/memory_companion"
ISSUE_TRACKER_API = "http://localhost:5025/api/issues"

class MemoryIssueIntegration:
    """Handles integration between Memory Companion and Issue Tracker"""
    
    def __init__(self, memory_api_url, issue_api_url):
        self.memory_api_url = memory_api_url
        self.issue_api_url = issue_api_url
        
    def get_project_data(self):
        """Get current project data from Memory Companion"""
        try:
            response = requests.get(f"{self.memory_api_url}/project_data")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get project data: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error connecting to Memory Companion: {str(e)}"}
    
    def get_issues(self):
        """Get issues from Issue Tracker"""
        try:
            response = requests.get(f"{self.issue_api_url}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get issues: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error connecting to Issue Tracker: {str(e)}"}
    
    def add_timeline_event(self, event):
        """Add a timeline event to Memory Companion"""
        try:
            response = requests.post(
                f"{self.memory_api_url}/timeline",
                json={"event": event}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to add timeline event: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error adding timeline event: {str(e)}"}
    
    def add_opportunity(self, title, description, priority="Medium"):
        """Add an opportunity to Memory Companion"""
        try:
            response = requests.post(
                f"{self.memory_api_url}/opportunity",
                json={
                    "title": title,
                    "description": description,
                    "priority": priority
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to add opportunity: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error adding opportunity: {str(e)}"}
    
    def update_sprint(self, sprint_name):
        """Update the current sprint in Memory Companion"""
        try:
            response = requests.put(
                f"{self.memory_api_url}/sprint",
                json={"sprint": sprint_name}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to update sprint: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error updating sprint: {str(e)}"}
    
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
                f"{self.issue_api_url}/new",
                json=issue_data
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Created issue from opportunity {opportunity['id']}"
                }
            else:
                return {"error": f"Failed to create issue: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error creating issue: {str(e)}"}
    
    def sync_all_opportunities(self, specific_id=None):
        """Sync all opportunities with the Issue Tracker or a specific one by ID"""
        try:
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
                        break
                else:
                    return {"error": f"Opportunity with ID {specific_id} not found"}
            else:
                # Otherwise sync all opportunities
                for opportunity in opportunities:
                    try:
                        result = self.create_issue_from_opportunity(opportunity)
                        results.append({
                            "opportunity": opportunity["id"],
                            "result": result
                        })
                    except Exception as e:
                        results.append({
                            "opportunity": opportunity["id"],
                            "result": {"error": f"Error: {str(e)}"}
                        })
            
            return {
                "success": True,
                "synced": results
            }
        except Exception as e:
            return {"error": f"Sync failed: {str(e)}"}

# Create integration instance
integration = MemoryIssueIntegration(MEMORY_COMPANION_API, ISSUE_TRACKER_API)

@app.route('/')
def index():
    """Render the main integration UI"""
    project_data = integration.get_project_data()
    return render_template(
        'memory_integration.html',
        project_data=project_data
    )

@app.route('/api/timeline', methods=['POST'])
def add_timeline():
    """API endpoint to add a timeline event"""
    data = request.json
    result = integration.add_timeline_event(data.get('event', ''))
    return jsonify(result)

@app.route('/api/opportunity', methods=['POST'])
def add_opportunity():
    """API endpoint to add an opportunity"""
    data = request.json
    result = integration.add_opportunity(
        data.get('title', ''),
        data.get('description', ''),
        data.get('priority', 'Medium')
    )
    return jsonify(result)

@app.route('/api/sprint', methods=['PUT'])
def update_sprint():
    """API endpoint to update the current sprint"""
    data = request.json
    result = integration.update_sprint(data.get('sprint', ''))
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
        
        # Migrate each opportunity to Issue Tracker
        migrated_count = 0
        for opp in opportunities:
            # Create issue format
            issue_data = {
                "title": opp["title"],
                "description": opp["description"],
                "priority": opp["priority"].lower(),
                "type": "opportunity",
                "creator_id": "system",
                "tags": ["migrated", "memory_companion", f"id:{opp['id']}"]
            }
            
            # Send to Issue Tracker
            response = requests.post(
                f"{ISSUE_TRACKER_API}/new",
                json=issue_data
            )
            
            if response.status_code == 200:
                migrated_count += 1
            else:
                error_text = ""
                try:
                    error_text = response.text
                except:
                    pass
                return jsonify({"error": f"Failed to migrate opportunity {opp['id']}: {response.status_code} - {error_text}"})
        
        return jsonify({"success": True, "count": migrated_count})
    except Exception as e:
        return jsonify({"error": f"Error migrating opportunities: {str(e)}"})

def create_template():
    """Create the template file if it doesn't exist"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    template_path = os.path.join(templates_dir, 'memory_integration.html')
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DARIA Memory Companion Integration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .panel {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .timeline-item, .opportunity-item {
            border-left: 3px solid #3498db;
            padding-left: 15px;
            margin-bottom: 10px;
            position: relative;
        }
        .high-priority {
            border-left-color: #e74c3c;
        }
        .medium-priority {
            border-left-color: #f39c12;
        }
        .low-priority {
            border-left-color: #2ecc71;
        }
        input, textarea, select, button {
            width: 100%;
            padding: 8px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            padding: 10px;
        }
        button:hover {
            background-color: #2980b9;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 20px;
        }
        .success {
            color: #2ecc71;
        }
        .error {
            color: #e74c3c;
        }
        #messageArea {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            display: none;
        }
        .action-buttons {
            display: flex;
            justify-content: space-between;
        }
        .action-buttons button {
            flex: 1;
            margin: 0 5px;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #eee;
            border: none;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }
        .tab.active {
            background-color: #3498db;
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>DARIA Memory Companion Integration</h1>
        
        <div id="messageArea"></div>
        
        <div class="tabs">
            <button class="tab active" onclick="openTab('dashboard')">Dashboard</button>
            <button class="tab" onclick="openTab('timeline')">Timeline</button>
            <button class="tab" onclick="openTab('opportunities')">Opportunities</button>
            <button class="tab" onclick="openTab('settings')">Settings</button>
        </div>
        
        <!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <div class="panel">
                <h2>Current Sprint: <span id="currentSprint">{{ project_data.currentSprint }}</span></h2>
                <p><strong>Project:</strong> {{ project_data.name }}</p>
                <p>{{ project_data.overview }}</p>
                
                <div class="action-buttons">
                    <button onclick="syncOpportunities()">Sync All Opportunities to Issue Tracker</button>
                    <button onclick="openTab('timeline')">Add Timeline Event</button>
                    <button onclick="openTab('opportunities')">Add Opportunity</button>
                </div>
            </div>
            
            <div class="grid">
                <div class="panel">
                    <h3>Recent Timeline</h3>
                    <div id="timelineList">
                        {% for event in project_data.timeline[-5:] %}
                        <div class="timeline-item">
                            <strong>{{ event.date }}</strong>: {{ event.event }}
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="panel">
                    <h3>Key Opportunities</h3>
                    <div id="opportunityList">
                        {% for opp in project_data.opportunities %}
                        <div class="opportunity-item {{ opp.priority.lower() }}-priority">
                            <strong>{{ opp.id }}:</strong> {{ opp.title }} ({{ opp.priority }})
                            <p>{{ opp.description }}</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Timeline Tab -->
        <div id="timeline" class="tab-content">
            <div class="panel">
                <h2>Add Timeline Event</h2>
                <form id="timelineForm">
                    <label for="eventText">Event Description:</label>
                    <textarea id="eventText" rows="3" placeholder="Describe the milestone or event" required></textarea>
                    
                    <div class="action-buttons">
                        <button type="submit">Add to Timeline</button>
                        <button type="button" onclick="clearForm('timelineForm')">Clear</button>
                    </div>
                </form>
            </div>
            
            <div class="panel">
                <h3>All Timeline Events</h3>
                <div id="fullTimelineList">
                    {% for event in project_data.timeline %}
                    <div class="timeline-item">
                        <strong>{{ event.date }}</strong>: {{ event.event }}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- Opportunities Tab -->
        <div id="opportunities" class="tab-content">
            <div class="panel">
                <h2>Add Opportunity</h2>
                <form id="opportunityForm">
                    <label for="opportunityTitle">Title:</label>
                    <input type="text" id="opportunityTitle" placeholder="Opportunity title" required>
                    
                    <label for="opportunityDescription">Description:</label>
                    <textarea id="opportunityDescription" rows="3" placeholder="Detailed description" required></textarea>
                    
                    <label for="opportunityPriority">Priority:</label>
                    <select id="opportunityPriority">
                        <option value="High">High</option>
                        <option value="Medium" selected>Medium</option>
                        <option value="Low">Low</option>
                    </select>
                    
                    <div class="action-buttons">
                        <button type="submit">Add Opportunity</button>
                        <button type="button" onclick="createIssueAndOpportunity()">Add to Both Memory & Issues</button>
                        <button type="button" onclick="clearForm('opportunityForm')">Clear</button>
                    </div>
                </form>
            </div>
            
            <div class="panel">
                <h3>All Opportunities</h3>
                <div id="fullOpportunityList">
                    {% for opp in project_data.opportunities %}
                    <div class="opportunity-item {{ opp.priority.lower() }}-priority">
                        <strong>{{ opp.id }}:</strong> {{ opp.title }} ({{ opp.priority }})
                        <p>{{ opp.description }}</p>
                        <button onclick="createIssueFrom('{{ opp.id }}', '{{ opp.title }}', '{{ opp.description }}', '{{ opp.priority }}')">
                            Create Issue from this Opportunity
                        </button>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- Settings Tab -->
        <div id="settings" class="tab-content">
            <div class="panel">
                <h2>Project Settings</h2>
                <form id="sprintForm">
                    <label for="sprintName">Current Sprint:</label>
                    <input type="text" id="sprintName" value="{{ project_data.currentSprint }}" required>
                    
                    <div class="action-buttons">
                        <button type="submit">Update Sprint</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
        // Tab navigation
        function openTab(tabName) {
            const tabContents = document.getElementsByClassName('tab-content');
            for (let i = 0; i < tabContents.length; i++) {
                tabContents[i].classList.remove('active');
            }
            
            const tabs = document.getElementsByClassName('tab');
            for (let i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            document.getElementById(tabName).classList.add('active');
            document.querySelector(`.tab[onclick="openTab('${tabName}')"]`).classList.add('active');
        }
        
        // Show message
        function showMessage(message, isError = false) {
            const messageArea = document.getElementById('messageArea');
            messageArea.textContent = message;
            messageArea.style.display = 'block';
            
            if (isError) {
                messageArea.style.backgroundColor = '#ffebee';
                messageArea.style.color = '#e74c3c';
            } else {
                messageArea.style.backgroundColor = '#e8f5e9';
                messageArea.style.color = '#2ecc71';
            }
            
            setTimeout(() => {
                messageArea.style.display = 'none';
            }, 5000);
        }
        
        // Clear form fields
        function clearForm(formId) {
            document.getElementById(formId).reset();
        }
        
        // Event Listeners for Forms
        document.getElementById('timelineForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const eventText = document.getElementById('eventText').value;
            
            fetch('/api/timeline', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ event: eventText })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage('Timeline event added successfully!');
                    clearForm('timelineForm');
                    setTimeout(() => location.reload(), 1000);
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        });
        
        document.getElementById('opportunityForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const title = document.getElementById('opportunityTitle').value;
            const description = document.getElementById('opportunityDescription').value;
            const priority = document.getElementById('opportunityPriority').value;
            
            fetch('/api/opportunity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    title: title,
                    description: description,
                    priority: priority
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage('Opportunity added successfully!');
                    clearForm('opportunityForm');
                    setTimeout(() => location.reload(), 1000);
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        });
        
        document.getElementById('sprintForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const sprintName = document.getElementById('sprintName').value;
            
            fetch('/api/sprint', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sprint: sprintName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage('Sprint updated successfully!');
                    document.getElementById('currentSprint').textContent = sprintName;
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        });
        
        // Create issue from opportunity
        function createIssueFrom(id, title, description, priority) {
            fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: id })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage(`Created issue from opportunity ${id}`);
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        }
        
        // Create both issue and opportunity
        function createIssueAndOpportunity() {
            const title = document.getElementById('opportunityTitle').value;
            const description = document.getElementById('opportunityDescription').value;
            const priority = document.getElementById('opportunityPriority').value;
            
            if (!title || !description) {
                showMessage('Please fill in all fields', true);
                return;
            }
            
            // First create opportunity
            fetch('/api/opportunity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    title: title,
                    description: description,
                    priority: priority
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    // Then sync to issue tracker
                    return fetch('/api/sync', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage('Created opportunity and issue successfully!');
                    clearForm('opportunityForm');
                    setTimeout(() => location.reload(), 1000);
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        }
        
        // Sync all opportunities
        function syncOpportunities() {
            fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(`Error: ${data.error}`, true);
                } else {
                    showMessage('Synced all opportunities to Issue Tracker!');
                }
            })
            .catch(error => {
                showMessage(`Error: ${error.message}`, true);
            });
        }
    </script>
</body>
</html>""")
        print(f"Created template file: {template_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Memory Companion UI Integration Tool')
    parser.add_argument('--port', type=int, default=5035, help='Port to run the app on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Create template file if needed
    create_template()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=args.port, debug=args.debug) 