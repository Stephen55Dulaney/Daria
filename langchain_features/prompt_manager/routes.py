from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, jsonify
)

from .models import PromptManager, PromptConfig

prompt_manager = PromptManager()
prompt_blueprint = Blueprint('prompt_manager', __name__, 
                            url_prefix='/prompts',
                            template_folder='templates/prompt_manager')

@prompt_blueprint.route('/')
def list_prompts():
    """List all available prompt configurations."""
    agents = prompt_manager.list_agents()
    return render_template('prompt_list.html', agents=agents)

@prompt_blueprint.route('/new', methods=['GET', 'POST'])
def create_prompt():
    """Create a new prompt configuration."""
    if request.method == 'POST':
        agent_name = request.form.get('agent_name', '').strip()
        
        if not agent_name:
            flash('Agent name is required.', 'error')
            return redirect(url_for('prompt_manager.create_prompt'))
        
        # Create default prompt for the new agent
        config = prompt_manager.create_default_prompt(agent_name)
        
        # Update with form data
        config.version = request.form.get('version', config.version)
        config.description = request.form.get('description', config.description)
        config.role = request.form.get('role', config.role)
        config.tone = request.form.get('tone', config.tone)
        
        # Save the new configuration
        if prompt_manager.save_prompt_config(config):
            flash(f'Prompt configuration for {agent_name} created successfully.', 'success')
            return redirect(url_for('prompt_manager.edit_prompt', agent_name=agent_name))
        else:
            flash(f'Failed to create prompt configuration for {agent_name}.', 'error')
            return redirect(url_for('prompt_manager.create_prompt'))
    
    return render_template('create_prompt.html')

@prompt_blueprint.route('/<agent_name>', methods=['GET'])
def edit_prompt(agent_name):
    """Edit an existing prompt configuration."""
    config = prompt_manager.create_prompt_config(agent_name)
    version_history = prompt_manager.get_version_history(agent_name)
    
    return render_template(
        'edit_prompt.html', 
        config=config, 
        version_history=version_history
    )

@prompt_blueprint.route('/<agent_name>/save', methods=['POST'])
def save_prompt(agent_name):
    """Save changes to a prompt configuration."""
    config = prompt_manager.load_prompt_config(agent_name)
    
    if config is None:
        flash(f'Prompt configuration for {agent_name} not found.', 'error')
        return redirect(url_for('prompt_manager.list_prompts'))
    
    # Update configuration from form data
    config.version = request.form.get('version', config.version)
    config.description = request.form.get('description', config.description)
    config.role = request.form.get('role', config.role)
    config.tone = request.form.get('tone', config.tone)
    config.dynamic_prompt_prefix = request.form.get('dynamic_prompt_prefix', config.dynamic_prompt_prefix)
    config.contextual_instructions = request.form.get('contextual_instructions', config.contextual_instructions)
    
    # Handle list fields
    config.core_objectives = [obj.strip() for obj in request.form.getlist('core_objectives') if obj.strip()]
    config.example_questions = [q.strip() for q in request.form.getlist('example_questions') if q.strip()]
    
    # Add a new evaluation note if provided
    new_note = request.form.get('new_evaluation_note', '').strip()
    if new_note:
        config.evaluation_notes.append(new_note)
    
    # Save the updated configuration
    if prompt_manager.save_prompt_config(config):
        flash(f'Prompt configuration for {agent_name} saved successfully.', 'success')
    else:
        flash(f'Failed to save prompt configuration for {agent_name}.', 'error')
    
    return redirect(url_for('prompt_manager.edit_prompt', agent_name=agent_name))

@prompt_blueprint.route('/<agent_name>/version/<history_file>', methods=['GET'])
def view_version(agent_name, history_file):
    """View a specific version of a prompt configuration."""
    config = prompt_manager.load_prompt_version(history_file)
    
    if config is None:
        flash(f'Version {history_file} not found for {agent_name}.', 'error')
        return redirect(url_for('prompt_manager.edit_prompt', agent_name=agent_name))
    
    version_history = prompt_manager.get_version_history(agent_name)
    
    return render_template(
        'view_version.html', 
        config=config, 
        version_history=version_history,
        history_file=history_file
    )

@prompt_blueprint.route('/<agent_name>/version/<history_file>/restore', methods=['POST'])
def restore_version(agent_name, history_file):
    """Restore a specific version of a prompt configuration."""
    config = prompt_manager.load_prompt_version(history_file)
    
    if config is None:
        flash(f'Version {history_file} not found for {agent_name}.', 'error')
        return redirect(url_for('prompt_manager.edit_prompt', agent_name=agent_name))
    
    # Add a note about the restoration
    timestamp = history_file.split('_', 1)[1].split('.')[0]
    config.evaluation_notes.append(f"Restored from version {timestamp}")
    
    # Save the restored configuration
    if prompt_manager.save_prompt_config(config):
        flash(f'Prompt configuration for {agent_name} restored successfully.', 'success')
    else:
        flash(f'Failed to restore prompt configuration for {agent_name}.', 'error')
    
    return redirect(url_for('prompt_manager.edit_prompt', agent_name=agent_name)) 