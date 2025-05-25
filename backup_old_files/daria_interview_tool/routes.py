from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from pathlib import Path
import json
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Redirect to home if logged in, otherwise to login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return redirect(url_for('auth.login'))

@main_bp.route('/home')
@login_required
def home():
    """Home page."""
    try:
        # Get list of projects
        projects = []
        PROJECTS_DIR = Path('projects')
        if PROJECTS_DIR.exists():
            for file in sorted(PROJECTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        projects.append(data)
                        logger.info(f"Loaded project: {data.get('name')} with ID: {data.get('id')}")
                except Exception as e:
                    logger.error(f"Error loading project {file}: {str(e)}")
                    continue
        
        # Get recent interviews
        recent_interviews = []
        INTERVIEWS_DIR = Path('interviews/raw')
        if INTERVIEWS_DIR.exists():
            for file in sorted(INTERVIEWS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        # Ensure all required fields are present
                        if 'id' not in data:
                            data['id'] = str(uuid.uuid4())
                        if 'created_at' not in data:
                            data['created_at'] = datetime.now().isoformat()
                        if 'project_name' not in data:
                            data['project_name'] = 'Unknown Project'
                            data['id'] = 'Unknown Project'
                        recent_interviews.append(data)
                        logger.info(f"Loaded interview: {data.get('project_name')} with ID: {data.get('id')}")
                except Exception as e:
                    logger.error(f"Error loading interview {file}: {str(e)}")
                    continue

        return render_template('home.html', projects=projects, recent_interviews=recent_interviews)
    except Exception as e:
        logger.error(f"Error loading home page: {str(e)}")
        return render_template('error.html')

@main_bp.route('/new_project')
@login_required
def new_project():
    """Create a new project."""
    try:
        return render_template('new_project.html')
    except Exception as e:
        logger.error(f"Error in new_project: {str(e)}")
        return render_template('error.html') 