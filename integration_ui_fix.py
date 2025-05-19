#!/bin/bash
# Upload this to EC2 to fix the Memory Companion Integration UI

cat > ~/DariaInterviewTool_new/integration_ui_fix.py << 'EOF'
#!/usr/bin/env python3

import os
import sys
import json
import requests
import argparse
from flask import Flask, request, jsonify, send_from_directory

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
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DARIA Memory Companion Integration</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { 
                padding: 20px;
                background-color: #f8f9fa;
            }
            .container {
                background-color: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .nav-tabs {
                margin-bottom: 20px;
            }
            .badge {
                margin-left: 5px;
            }
            .priority-high {
                background-color: #dc3545;
            }
            .priority-medium {
                background-color: #fd7e14;
            }
            .priority-low {
                background-color: #20c997;
            }
            .opportunity-card {
                margin-bottom: 15px;
                border-left: 5px solid #6c757d;
            }
            .timeline-item {
                margin-bottom: 15px;
                padding-left: 20px;
                border-left: 3px solid #0d6efd;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">DARIA Memory Companion Integration</h1>
            <p class="lead">Manage project memory, timeline, and synchronize with Issue Tracker</p>
            
            <ul class="nav nav-tabs" id="myTab" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="timeline-tab" data-bs-toggle="tab" data-bs-target="#timeline" type="button" role="tab">Timeline</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="sprint-tab" data-bs-toggle="tab" data-bs-target="#sprint" type="button" role="tab">Sprint</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="stats-tab" data-bs-toggle="tab" data-bs-target="#stats" type="button" role="tab">Statistics</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="sync-tab" data-bs-toggle="tab" data-bs-target="#sync" type="button" role="tab">Sync</button>
                </li>
            </ul>
            
            <div class="tab-content" id="myTabContent">
                <!-- Timeline Tab -->
                <div class="tab-pane fade show active" id="timeline" role="tabpanel" aria-labelledby="timeline-tab">
                    <h2 class="mb-3">Project Timeline</h2>
                    <div id="timeline-list" class="mb-4">
                        <!-- Timeline events will be loaded here -->
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    
                    <h3 class="mb-3">Add Timeline Event</h3>
                    <form id="timeline-form" class="row g-3">
                        <div class="col-md-6">
                            <label for="event-date" class="form-label">Date</label>
                            <input type="date" class="form-control" id="event-date" required>
                        </div>
                        <div class="col-md-6">
                            <label for="event-title" class="form-label">Title</label>
                            <input type="text" class="form-control" id="event-title" placeholder="Major milestone title" required>
                        </div>
                        <div class="col-12">
                            <label for="event-description" class="form-label">Description</label>
                            <textarea class="form-control" id="event-description" rows="3" placeholder="Detailed description of the milestone" required></textarea>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-primary">Add Timeline Event</button>
                        </div>
                    </form>
                </div>
                
                <!-- Sprint Tab -->
                <div class="tab-pane fade" id="sprint" role="tabpanel" aria-labelledby="sprint-tab">
                    <h2 class="mb-3">Sprint Management</h2>
                    <div class="mb-4">
                        <h3>Current Sprint: <span id="currentSprint">Loading...</span></h3>
                    </div>
                    
                    <h3 class="mb-3">Update Sprint</h3>
                    <form id="sprint-form" class="row g-3">
                        <div class="col-md-6">
                            <label for="sprint-name" class="form-label">Sprint Name</label>
                            <input type="text" class="form-control" id="sprint-name" placeholder="e.g., Sprint 3" required>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-primary">Update Sprint</button>
                        </div>
                    </form>
                </div>
                
                <!-- Statistics Tab -->
                <div class="tab-pane fade" id="stats" role="tabpanel" aria-labelledby="stats-tab">
                    <h2 class="mb-3">Project Statistics</h2>
                    <div id="stats-container" class="row">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
                
                <!-- Sync Tab -->
                <div class="tab-pane fade" id="sync" role="tabpanel" aria-labelledby="sync-tab">
                    <h2 class="mb-3">Synchronization with Issue Tracker</h2>
                    <p>View current opportunities in DARIA's memory and synchronize them with the Issue Tracker system.</p>
                    
                    <div id="opportunities-list" class="mb-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    
                    <button id="migrate-all-button" class="btn btn-success mb-3">Migrate All Opportunities</button>
                    <div id="sync-result" class="alert alert-info d-none"></div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Load project data on page load
            document.addEventListener('DOMContentLoaded', function() {
                fetchProjectData();
                
                // Setup form handlers
                document.getElementById('timeline-form').addEventListener('submit', handleTimelineSubmit);
                document.getElementById('sprint-form').addEventListener('submit', handleSprintSubmit);
                document.getElementById('migrate-all-button').addEventListener('click', migrateAllOpportunities);
            });
            
            // Fetch project data from API
            function fetchProjectData() {
                fetch('/api/project')
                    .then(response => response.json())
                    .then(data => {
                        // Update sprint
                        document.getElementById('currentSprint').textContent = data.currentSprint || 'None';
                        
                        // Update timeline
                        renderTimeline(data.timeline || []);
                        
                        // Update opportunities
                        renderOpportunities(data.opportunities || []);
                        
                        // Update stats
                        renderStats(data.statistics || {});
                    })
                    .catch(error => {
                        console.error('Error fetching project data:', error);
                        alert('Failed to load project data. Please try again later.');
                    });
            }
            
            // Render timeline events
            function renderTimeline(timeline) {
                const container = document.getElementById('timeline-list');
                container.innerHTML = '';
                
                if (timeline.length === 0) {
                    container.innerHTML = '<div class="alert alert-info">No timeline events yet.</div>';
                    return;
                }
                
                // Sort by date (newest first)
                timeline.sort((a, b) => new Date(b.date) - new Date(a.date));
                
                timeline.forEach(event => {
                    const date = new Date(event.date).toLocaleDateString();
                    const item = document.createElement('div');
                    item.className = 'timeline-item p-3';
                    item.innerHTML = `
                        <h5>${event.title} <small class="text-muted">${date}</small></h5>
                        <p>${event.description}</p>
                    `;
                    container.appendChild(item);
                });
            }
            
            // Render opportunities
            function renderOpportunities(opportunities) {
                const container = document.getElementById('opportunities-list');
                container.innerHTML = '';
                
                if (opportunities.length === 0) {
                    container.innerHTML = '<div class="alert alert-info">No opportunities found.</div>';
                    return;
                }
                
                opportunities.forEach(opp => {
                    const priorityClass = `priority-${opp.priority.toLowerCase()}`;
                    const card = document.createElement('div');
                    card.className = 'card opportunity-card mb-3';
                    card.innerHTML = `
                        <div class="card-body">
                            <h5 class="card-title">${opp.id}: ${opp.title} 
                                <span class="badge ${priorityClass}">${opp.priority}</span>
                            </h5>
                            <p class="card-text">${opp.description}</p>
                            <button class="btn btn-sm btn-outline-primary sync-btn" data-id="${opp.id}">
                                Sync with Issue Tracker
                            </button>
                        </div>
                    `;
                    container.appendChild(card);
                    
                    // Add event listener to sync button
                    card.querySelector('.sync-btn').addEventListener('click', function() {
                        syncOpportunity(opp.id);
                    });
                });
            }
            
            // Render statistics
            function renderStats(stats) {
                const container = document.getElementById('stats-container');
                container.innerHTML = '';
                
                if (Object.keys(stats).length === 0) {
                    container.innerHTML = '<div class="alert alert-info">No statistics available.</div>';
                    return;
                }
                
                // Create cards for each stat
                const statsToShow = [
                    { key: 'totalStories', label: 'Total Stories', color: 'primary' },
                    { key: 'completedStories', label: 'Completed', color: 'success' },
                    { key: 'inProgressStories', label: 'In Progress', color: 'warning' },
                    { key: 'blockedStories', label: 'Blocked', color: 'danger' }
                ];
                
                statsToShow.forEach(stat => {
                    if (stats[stat.key] !== undefined) {
                        const card = document.createElement('div');
                        card.className = 'col-md-3 col-sm-6 mb-3';
                        card.innerHTML = `
                            <div class="card text-white bg-${stat.color}">
                                <div class="card-body text-center">
                                    <h5 class="card-title">${stat.label}</h5>
                                    <p class="card-text display-4">${stats[stat.key]}</p>
                                </div>
                            </div>
                        `;
                        container.appendChild(card);
                    }
                });
            }
            
            // Handle timeline form submission
            function handleTimelineSubmit(event) {
                event.preventDefault();
                
                const timelineData = {
                    date: document.getElementById('event-date').value,
                    title: document.getElementById('event-title').value,
                    description: document.getElementById('event-description').value
                };
                
                fetch('/api/timeline', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(timelineData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        // Reset form and refresh data
                        document.getElementById('timeline-form').reset();
                        fetchProjectData();
                        alert('Timeline event added successfully!');
                    }
                })
                .catch(error => {
                    console.error('Error adding timeline event:', error);
                    alert('Failed to add timeline event. Please try again.');
                });
            }
            
            // Handle sprint form submission
            function handleSprintSubmit(event) {
                event.preventDefault();
                
                const sprintName = document.getElementById('sprint-name').value;
                
                fetch('/api/sprint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ sprint: sprintName })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        // Reset form and refresh data
                        document.getElementById('sprint-form').reset();
                        document.getElementById('currentSprint').textContent = sprintName;
                        alert('Sprint updated successfully!');
                    }
                })
                .catch(error => {
                    console.error('Error updating sprint:', error);
                    alert('Failed to update sprint. Please try again.');
                });
            }
            
            // Sync a specific opportunity
            function syncOpportunity(oppId) {
                fetch('/api/sync', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ id: oppId })
                })
                .then(response => response.json())
                .then(data => {
                    const resultDiv = document.getElementById('sync-result');
                    resultDiv.classList.remove('d-none', 'alert-success', 'alert-danger');
                    
                    if (data.error) {
                        resultDiv.textContent = 'Error: ' + data.error;
                        resultDiv.classList.add('alert-danger');
                    } else {
                        resultDiv.textContent = `Successfully synced opportunity ${oppId} with Issue Tracker.`;
                        resultDiv.classList.add('alert-success');
                    }
                    
                    resultDiv.classList.remove('d-none');
                })
                .catch(error => {
                    console.error('Error syncing opportunity:', error);
                    alert('Failed to sync opportunity. Please try again.');
                });
            }
            
            // Migrate all opportunities
            function migrateAllOpportunities() {
                if (confirm('Do you want to migrate all opportunities to the Issue Tracker?')) {
                    fetch('/api/migrate_opportunities', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({})
                    })
                    .then(response => response.json())
                    .then(data => {
                        const resultDiv = document.getElementById('sync-result');
                        resultDiv.classList.remove('d-none', 'alert-success', 'alert-danger');
                        
                        if (data.error) {
                            resultDiv.textContent = 'Error: ' + data.error;
                            resultDiv.classList.add('alert-danger');
                        } else {
                            resultDiv.textContent = `Successfully migrated ${data.migrated_count} opportunities to the Issue Tracker.`;
                            resultDiv.classList.add('alert-success');
                        }
                        
                        resultDiv.classList.remove('d-none');
                    })
                    .catch(error => {
                        console.error('Error migrating opportunities:', error);
                        alert('Failed to migrate opportunities. Please try again.');
                    });
                }
            }
        </script>
    </body>
    </html>
    """
    return html

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

cat > ~/DariaInterviewTool_new/restart_integration_ui.sh << 'EOF'
#!/bin/bash

# Stop the old Memory Companion UI process
if [ -f .memory_ui_pid ]; then
    pid=$(cat .memory_ui_pid)
    if ps -p $pid > /dev/null; then
        echo "Stopping Memory Companion UI (PID: $pid)"
        kill $pid
    fi
    rm .memory_ui_pid
fi

# Start the new integration UI
echo "Starting new Integration UI..."
source venv/bin/activate
nohup python3 integration_ui_fix.py --host 0.0.0.0 --port 5035 > integration_ui.log 2>&1 &
echo $! > .memory_ui_pid

echo "Integration UI restarted on port 5035"
echo "You can access it at: http://3.12.144.184:5035/"
EOF

chmod +x ~/DariaInterviewTool_new/restart_integration_ui.sh
cd ~/DariaInterviewTool_new && ./restart_integration_ui.sh 