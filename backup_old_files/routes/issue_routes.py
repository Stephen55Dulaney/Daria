import os
import uuid
from flask import (
    Blueprint, request, jsonify, session, current_app,
    render_template, redirect, url_for, flash, send_file, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.issue_tracker import IssueManager, Issue, IssueStatus, IssueType, IssuePriority
import datetime
import json

bp = Blueprint('issues', __name__, url_prefix='/issues')

# Ensure directories exist
base_dir = os.path.dirname(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data', 'issues')
uploads_dir = os.path.join(base_dir, 'uploads', 'screenshots')
attachments_dir = os.path.join(base_dir, 'uploads', 'attachments')

os.makedirs(data_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(attachments_dir, exist_ok=True)

# Initialize issue manager with proper path
issue_manager = IssueManager(data_dir=data_dir)

# Helper functions
def allowed_file(filename):
    """Check if a file extension is allowed for screenshots"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_screenshot(file):
    """Save a screenshot to the uploads directory"""
    if not file or not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{timestamp}_{filename}"
    
    uploads_dir = os.path.join(current_app.root_path, 'uploads', 'screenshots')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, new_filename)
    file.save(file_path)
    
    return os.path.join('uploads', 'screenshots', new_filename)

def save_attachment(file):
    """Save an attachment to the uploads directory"""
    if not file or not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{timestamp}_{filename}"
    
    uploads_dir = os.path.join(current_app.root_path, 'uploads', 'attachments')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, new_filename)
    file.save(file_path)
    
    return os.path.join('uploads', 'attachments', new_filename)

# Routes
@bp.route('/help', methods=['GET'])
@login_required
def help_guide():
    """Display the help guide for using the Issue Tracker"""
    return render_template('issues/help_guide.html')

@bp.route('/', methods=['GET'])
@login_required
def issues_list():
    """List all issues or filter by query parameters"""
    status = request.args.get('status')
    assigned_to = request.args.get('assigned_to')
    created_by = request.args.get('created_by')
    issue_type = request.args.get('type')
    
    # Start with all issues
    issues = issue_manager.get_all_issues()
    
    # Apply filters
    if status:
        issues = [i for i in issues if i.status == status]
    if assigned_to:
        issues = [i for i in issues if i.assigned_to == assigned_to]
    if created_by:
        issues = [i for i in issues if i.creator_id == created_by]
    if issue_type:
        issues = [i for i in issues if i.issue_type == issue_type]
    
    return render_template('issues/issues_list.html', issues=issues)

@bp.route('/my-issues', methods=['GET'])
@login_required
def my_issues():
    """Show issues assigned to the current user"""
    assigned_issues = issue_manager.get_issues_assigned_to(current_user.id)
    created_issues = issue_manager.get_issues_by_creator(current_user.id)
    
    return render_template(
        'issues/my_issues.html', 
        assigned_issues=assigned_issues,
        created_issues=created_issues
    )

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_issue():
    """Create a new issue"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        issue_type = request.form.get('issue_type', IssueType.BUG)
        priority = request.form.get('priority', IssuePriority.MEDIUM)
        
        # Validate form data
        if not title or not description:
            flash('Title and description are required', 'error')
            return render_template('issues/create_issue.html')
        
        # Save screenshots if provided
        screenshots = []
        if 'screenshots' in request.files:
            files = request.files.getlist('screenshots')
            for file in files:
                if file and allowed_file(file.filename):
                    file_path = save_screenshot(file)
                    if file_path:
                        screenshots.append(file_path)
        
        # Capture browser environment
        environment = {
            'user_agent': request.user_agent.string,
            'remote_addr': request.remote_addr
        }
        
        # Create the issue
        issue = issue_manager.create_issue(
            title=title,
            description=description,
            creator_id=current_user.id,
            issue_type=issue_type,
            priority=priority,
            screenshots=screenshots
        )
        
        # Update environment info
        issue.environment = environment
        issue_manager.update_issue(issue)
        
        flash('Issue created successfully', 'success')
        return redirect(url_for('issues.view_issue', issue_id=issue.id))
    
    return render_template('issues/create_issue.html')

@bp.route('/<issue_id>', methods=['GET'])
@login_required
def view_issue(issue_id):
    """View a specific issue"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        flash('Issue not found', 'error')
        return redirect(url_for('issues.issues_list'))
    
    return render_template('issues/view_issue.html', issue=issue)

@bp.route('/<issue_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_issue(issue_id):
    """Edit an issue"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        flash('Issue not found', 'error')
        return redirect(url_for('issues.issues_list'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        issue_type = request.form.get('issue_type')
        priority = request.form.get('priority')
        
        # Update issue
        issue.title = title
        issue.description = description
        issue.issue_type = issue_type
        issue.priority = priority
        
        # Record history
        issue._record_history("Issue updated", user_id=current_user.id)
        
        # Save screenshots if provided
        if 'screenshots' in request.files:
            files = request.files.getlist('screenshots')
            for file in files:
                if file and allowed_file(file.filename):
                    file_path = save_screenshot(file)
                    if file_path:
                        issue.add_screenshot(file_path, current_user.id)
        
        issue_manager.update_issue(issue)
        flash('Issue updated successfully', 'success')
        return redirect(url_for('issues.view_issue', issue_id=issue.id))
    
    return render_template('issues/edit_issue.html', issue=issue)

@bp.route('/<issue_id>/assign', methods=['POST'])
@login_required
def assign_issue(issue_id):
    """Assign an issue to a user"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    data = request.get_json()
    assigned_to = data.get('user_id')
    
    issue.assign_to(assigned_to, current_user.id)
    issue_manager.update_issue(issue)
    
    return jsonify({"success": True, "message": "Issue assigned successfully"})

@bp.route('/<issue_id>/status', methods=['POST'])
@login_required
def update_status(issue_id):
    """Update the status of an issue"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    
    try:
        issue.update_status(new_status, current_user.id)
        issue_manager.update_issue(issue)
        return jsonify({"success": True, "message": "Status updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.route('/<issue_id>/backlog', methods=['POST'])
@login_required
def move_to_backlog(issue_id):
    """Move a feature to the backlog"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    try:
        issue.move_to_backlog(current_user.id)
        issue_manager.update_issue(issue)
        return jsonify({"success": True, "message": "Feature moved to backlog"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route('/screenshot/<path:filename>', methods=['GET'])
@login_required
def get_screenshot(filename):
    """Serve a screenshot file"""
    try:
        file_path = os.path.join(current_app.root_path, filename)
        return send_file(file_path)
    except Exception:
        abort(404)

@bp.route('/<issue_id>/comments', methods=['POST'])
@login_required
def add_comment(issue_id):
    """Add a comment to an issue, with optional attachment"""
    issue = issue_manager.get_issue(issue_id)
    if not issue:
        flash('Issue not found', 'error')
        return redirect(url_for('issues.issues_list'))
    
    content = request.form.get('content')
    if not content:
        flash('Comment content is required', 'error')
        return redirect(url_for('issues.view_issue', issue_id=issue_id))
    
    # Process attachments
    attachments = []
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for file in files:
            if file and allowed_file(file.filename):
                file_path = save_attachment(file)
                if file_path:
                    attachments.append({
                        'filename': file.filename,
                        'path': file_path
                    })
    
    # Add comment to issue
    issue.add_comment(current_user.id, content, attachments)
    issue_manager.update_issue(issue)
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('issues.view_issue', issue_id=issue_id))

@bp.route('/attachment/<path:filename>', methods=['GET'])
@login_required
def get_attachment(filename):
    """Serve an attachment file"""
    try:
        file_path = os.path.join(current_app.root_path, filename)
        return send_file(file_path)
    except Exception:
        abort(404) 