#!/bin/bash

# start_with_guide_redirect.sh - Script to start DARIA with guide transcript redirect support

# Kill any running instances
echo "Stopping any running DARIA instances..."
pkill -f "python py313_patch.py run_interview_api.py" || true

# Set environment variables
export OPENAI_API_KEY=${OPENAI_API_KEY:-"YOUR_API_KEY_HERE"}
export PYTHONPATH=${PYTHONPATH:-.}
export FLASK_DEBUG=1
export DEBUG_ANALYSIS=1
export ENABLE_GUIDE_TRANSCRIPT=1

# Define log file
LOG_FILE="daria_debug_$(date +%Y%m%d_%H%M%S).log"

echo "Starting DARIA with guide transcript support..."
echo "Logs will be saved to $LOG_FILE"

# Copy the blueprint registration code
if [ ! -f "$PWD/upload_guide_transcript.py" ]; then
    echo "Creating upload_guide_transcript.py..."
    cat > "$PWD/upload_guide_transcript.py" << 'EOF'
#!/usr/bin/env python
"""
upload_guide_transcript.py - Helper script to upload a transcript and redirect back to the discussion guide page.

This script uses Flask and will be integrated with the DARIA Interview Tool.
"""

import os
import sys
import json
import logging
import datetime
import uuid
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, abort

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Blueprint
guide_transcript_bp = Blueprint('guide_transcript', __name__)

@guide_transcript_bp.route('/guide_upload_transcript', methods=['GET'])
def guide_upload_transcript_page():
    """Render the upload transcript page specifically for a discussion guide."""
    guide_id = request.args.get('guide_id', None)
    
    if not guide_id:
        return redirect('/discussion_guides')
    
    # Render the upload form with guide_id
    return render_template('upload_transcript.html', 
                          title="Upload Transcript for Guide", 
                          guide_id=guide_id,
                          redirect_to_guide=True)

@guide_transcript_bp.route('/api/guide_upload_transcript', methods=['POST'])
def api_guide_upload_transcript():
    """Handle transcript upload for a discussion guide, always redirecting back to the guide page."""
    from run_interview_api import api_upload_transcript
    
    # Get the guide_id from the form
    guide_id = request.form.get('guide_id')
    
    # Call the original upload transcript function
    response = api_upload_transcript()
    
    # If it's successful and we have a guide_id, modify the redirect URL
    if isinstance(response, tuple):
        # Error response
        return response
    
    try:
        response_data = response.get_json()
        if response_data.get('success') and guide_id:
            response_data['redirect_url'] = f"/discussion_guide/{guide_id}"
            return jsonify(response_data)
        return response
    except:
        return response
EOF
    chmod +x "$PWD/upload_guide_transcript.py"
fi

# Add a patch to modify the redirect in the upload_transcript.html
# This will ensure the redirect goes back to the discussion guide
if grep -q 'redirect_to_guide' "$PWD/templates/upload_transcript.html"; then
    echo "Template already has redirect_to_guide field."
else
    echo "Adding redirect_to_guide field to upload_transcript.html..."
    sed -i.bak 's/<input type="hidden" id="guide_id" name="guide_id" value="">/<input type="hidden" id="guide_id" name="guide_id" value="">\n        <input type="hidden" id="redirect_to_guide" name="redirect_to_guide" value="true">/' "$PWD/templates/upload_transcript.html"
fi

# Create integration code
cat > "$PWD/register_guide_blueprint.py" << 'EOF'
#!/usr/bin/env python
"""Register guide transcript blueprint with Flask app."""

def register_blueprint(app):
    """Register the blueprint with the Flask app."""
    try:
        from upload_guide_transcript import guide_transcript_bp
        app.register_blueprint(guide_transcript_bp)
        app.logger.info("Registered guide_transcript blueprint")
        return True
    except Exception as e:
        app.logger.error(f"Failed to register guide_transcript blueprint: {e}")
        return False
EOF

# Add integration to the end of run_interview_api.py if not already there
if grep -q "register_guide_blueprint" "$PWD/run_interview_api.py"; then
    echo "Integration code already exists in run_interview_api.py"
else
    echo "Adding integration code to run_interview_api.py..."
    cat >> "$PWD/run_interview_api.py" << 'EOF'

# Guide transcript blueprint integration
if os.environ.get('ENABLE_GUIDE_TRANSCRIPT', '0').lower() in ('1', 'true', 'yes'):
    try:
        import register_guide_blueprint
        register_guide_blueprint.register_blueprint(app)
        logger.info("Registered guide transcript blueprint")
    except Exception as e:
        logger.error(f"Failed to register guide transcript blueprint: {e}")
EOF
fi

# Start the application with debug flags
python py313_patch.py run_interview_api.py --port 5025 --debug 2>&1 | tee "$LOG_FILE" 