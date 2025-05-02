from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import yaml
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any

from .prompt_manager import get_prompt_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
prompt_bp = Blueprint('prompts', __name__, url_prefix='/prompts')

# Initialize prompt manager
prompt_manager = get_prompt_manager()

@prompt_bp.route('/')
def prompt_list():
    """List all available prompts"""
    agents = prompt_manager.get_available_agents()
    agent_data = []
    
    for agent in agents:
        try:
            config = prompt_manager.load_prompt(agent)
            # Get performance metrics
            performance = prompt_manager.get_prompt_performance(agent)
            
            agent_data.append({
                'name': agent,
                'version': config.get('version', 'unknown'),
                'role': config.get('role', 'unknown'),
                'description': config.get('description', ''),
                'average_score': performance.get('average_score'),
                'total_sessions': performance.get('total_sessions', 0)
            })
        except Exception as e:
            logger.error(f"Error loading prompt for {agent}: {str(e)}")
    
    return render_template('prompts/prompt_list.html', agents=agent_data)

@prompt_bp.route('/<agent>')
def view_prompt(agent):
    """View a specific prompt"""
    try:
        config = prompt_manager.load_prompt(agent)
        history = prompt_manager.get_prompt_history(agent)
        feedback = prompt_manager.get_feedback(agent)
        performance = prompt_manager.get_prompt_performance(agent)
        
        return render_template('prompts/view_prompt.html',
                              agent=agent,
                              config=config,
                              history=history,
                              feedback=feedback,
                              performance=performance)
    except FileNotFoundError:
        flash(f"Prompt for {agent} not found", "error")
        return redirect(url_for('prompts.prompt_list'))
    except Exception as e:
        flash(f"Error loading prompt: {str(e)}", "error")
        logger.error(f"Error loading prompt for {agent}: {str(e)}")
        return redirect(url_for('prompts.prompt_list'))

@prompt_bp.route('/<agent>/edit', methods=['GET', 'POST'])
def edit_prompt(agent):
    """Edit a specific prompt"""
    if request.method == 'POST':
        try:
            # Get form data
            form_data = request.form
            
            # Load existing config to preserve structure
            try:
                config = prompt_manager.load_prompt(agent)
            except FileNotFoundError:
                config = {}
            
            # Update config with form data
            config['description'] = form_data.get('description', '')
            config['role'] = form_data.get('role', '')
            config['tone'] = form_data.get('tone', '')
            config['dynamic_prompt_prefix'] = form_data.get('dynamic_prompt_prefix', '')
            config['analysis_prompt'] = form_data.get('analysis_prompt', '')
            
            # Handle lists
            config['core_objectives'] = [obj.strip() for obj in form_data.get('core_objectives', '').split('\n') if obj.strip()]
            config['contextual_instructions'] = form_data.get('contextual_instructions', '')
            
            # Add evaluation note if provided
            if form_data.get('evaluation_note'):
                if 'evaluation_notes' not in config:
                    config['evaluation_notes'] = []
                config['evaluation_notes'].append(f"{datetime.now().strftime('%Y-%m-%d')}: {form_data.get('evaluation_note')}")
            
            # Save the updated config
            prompt_manager.save_prompt(agent, config)
            
            flash(f"Prompt for {agent} updated successfully", "success")
            return redirect(url_for('prompts.view_prompt', agent=agent))
        except Exception as e:
            flash(f"Error updating prompt: {str(e)}", "error")
            logger.error(f"Error updating prompt for {agent}: {str(e)}")
    
    # GET request or error in POST
    try:
        config = prompt_manager.load_prompt(agent)
        return render_template('prompts/edit_prompt.html', agent=agent, config=config)
    except FileNotFoundError:
        flash(f"Prompt for {agent} not found", "error")
        return redirect(url_for('prompts.prompt_list'))
    except Exception as e:
        flash(f"Error loading prompt: {str(e)}", "error")
        logger.error(f"Error loading prompt for {agent}: {str(e)}")
        return redirect(url_for('prompts.prompt_list'))

@prompt_bp.route('/<agent>/feedback', methods=['GET', 'POST'])
def prompt_feedback(agent):
    """Add feedback for a prompt"""
    if request.method == 'POST':
        try:
            # Get form data
            form_data = request.form
            session_id = form_data.get('session_id', str(datetime.now().timestamp()))
            score = int(form_data.get('score', 3))
            notes = form_data.get('notes', '')
            
            # Add feedback
            prompt_manager.add_feedback(agent, session_id, score, notes)
            
            flash(f"Feedback for {agent} added successfully", "success")
            return redirect(url_for('prompts.view_prompt', agent=agent))
        except Exception as e:
            flash(f"Error adding feedback: {str(e)}", "error")
            logger.error(f"Error adding feedback for {agent}: {str(e)}")
    
    # GET request or error in POST
    return render_template('prompts/add_feedback.html', agent=agent)

@prompt_bp.route('/<agent>/history/<filename>')
def view_history(agent, filename):
    """View a specific version from history"""
    try:
        history_file = Path(prompt_manager.history_dir) / filename
        
        if not history_file.exists():
            flash(f"History file not found", "error")
            return redirect(url_for('prompts.view_prompt', agent=agent))
        
        with open(history_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return render_template('prompts/view_history.html',
                              agent=agent,
                              config=config,
                              filename=filename)
    except Exception as e:
        flash(f"Error loading history: {str(e)}", "error")
        logger.error(f"Error loading history for {agent}: {str(e)}")
        return redirect(url_for('prompts.view_prompt', agent=agent))

@prompt_bp.route('/<agent>/restore/<filename>')
def restore_history(agent, filename):
    """Restore a prompt from history"""
    try:
        history_file = Path(prompt_manager.history_dir) / filename
        
        if not history_file.exists():
            flash(f"History file not found", "error")
            return redirect(url_for('prompts.view_prompt', agent=agent))
        
        with open(history_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update version to indicate restoration
        if 'version' in config:
            version_parts = config['version'].split('.')
            if len(version_parts) >= 2:
                try:
                    major = version_parts[0]
                    minor = int(version_parts[1]) + 1
                    config['version'] = f"{major}.{minor}"
                except:
                    config['version'] = f"{config['version']}.restored"
        
        # Add restoration note
        if 'evaluation_notes' not in config:
            config['evaluation_notes'] = []
        config['evaluation_notes'].append(f"{datetime.now().strftime('%Y-%m-%d')}: Restored from {filename}")
        
        # Save the restored config
        prompt_manager.save_prompt(agent, config)
        
        flash(f"Prompt for {agent} restored successfully", "success")
        return redirect(url_for('prompts.view_prompt', agent=agent))
    except Exception as e:
        flash(f"Error restoring prompt: {str(e)}", "error")
        logger.error(f"Error restoring prompt for {agent}: {str(e)}")
        return redirect(url_for('prompts.view_prompt', agent=agent))

@prompt_bp.route('/new', methods=['GET', 'POST'])
def new_prompt():
    """Create a new prompt"""
    if request.method == 'POST':
        try:
            # Get form data
            form_data = request.form
            agent_name = form_data.get('agent_name', '').lower().strip()
            
            if not agent_name:
                flash("Agent name is required", "error")
                return render_template('prompts/new_prompt.html')
            
            # Check if prompt already exists
            try:
                existing_config = prompt_manager.load_prompt(agent_name)
                flash(f"Prompt for {agent_name} already exists", "error")
                return redirect(url_for('prompts.edit_prompt', agent=agent_name))
            except FileNotFoundError:
                pass
            
            # Create new prompt template
            config = prompt_manager.create_prompt_template(
                agent_name=agent_name,
                role=form_data.get('role', ''),
                description=form_data.get('description', ''),
                tone=form_data.get('tone', ''),
                core_objectives=[obj.strip() for obj in form_data.get('core_objectives', '').split('\n') if obj.strip()],
                contextual_instructions=form_data.get('contextual_instructions', ''),
                dynamic_prompt_prefix=form_data.get('dynamic_prompt_prefix', ''),
                analysis_prompt=form_data.get('analysis_prompt', '')
            )
            
            # Save the new prompt
            prompt_manager.save_prompt(agent_name, config, create_version=False)
            
            flash(f"Prompt for {agent_name} created successfully", "success")
            return redirect(url_for('prompts.view_prompt', agent=agent_name))
        except Exception as e:
            flash(f"Error creating prompt: {str(e)}", "error")
            logger.error(f"Error creating prompt: {str(e)}")
    
    # GET request or error in POST
    return render_template('prompts/new_prompt.html')

@prompt_bp.route('/api/<agent>')
def api_get_prompt(agent):
    """API endpoint to get a prompt configuration"""
    try:
        config = prompt_manager.load_prompt(agent)
        return jsonify({"success": True, "prompt": config})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Prompt not found"}), 404
    except Exception as e:
        logger.error(f"Error in API get_prompt for {agent}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@prompt_bp.route('/api/<agent>/feedback', methods=['POST'])
def api_add_feedback(agent):
    """API endpoint to add feedback for a prompt"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        session_id = data.get('session_id', str(datetime.now().timestamp()))
        score = int(data.get('score', 3))
        notes = data.get('notes', '')
        
        # Add feedback
        feedback = prompt_manager.add_feedback(agent, session_id, score, notes)
        
        return jsonify({"success": True, "feedback": feedback})
    except Exception as e:
        logger.error(f"Error in API add_feedback for {agent}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def register_prompt_routes(app):
    """Set up prompt routes for the Flask app"""
    # The blueprint is already registered in __init__.py,
    # just ensure the template directory exists
    template_dir = Path(app.root_path) / 'templates' / 'prompts'
    template_dir.mkdir(parents=True, exist_ok=True) 