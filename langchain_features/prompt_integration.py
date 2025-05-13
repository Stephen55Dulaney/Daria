"""
Prompt Manager Integration Module

This module provides integration functions for adding prompt management 
capabilities to the Daria Interview Tool application.
"""

from flask import Flask, Blueprint
import os
import logging

from tools.prompt_manager import prompt_bp, get_prompt_manager
from tools.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

def configure_prompt_manager(app: Flask, 
                             prompt_dir: str = "tools/prompt_manager/prompts", 
                             name_prefix: str = None) -> PromptManager:
    """
    Configure and register the prompt manager with a Flask application
    
    Args:
        app: Flask application
        prompt_dir: Directory where prompt files are stored
        name_prefix: Optional prefix for route names to avoid conflicts
        
    Returns:
        Configured PromptManager instance
    """
    logger.info(f"Configuring prompt manager with prompt_dir={prompt_dir}, name_prefix={name_prefix}")
    
    # Ensure the prompt directory exists
    os.makedirs(prompt_dir, exist_ok=True)
    history_dir = os.path.join(prompt_dir, ".history")
    os.makedirs(history_dir, exist_ok=True)
    
    # Initialize prompt manager
    prompt_manager = get_prompt_manager(prompt_dir, history_dir)
    
    # Register the blueprint with optional name prefix to avoid route conflicts
    if name_prefix:
        app.register_blueprint(prompt_bp, url_prefix=f'/prompts', name=f'{name_prefix}_prompts')
    else:
        app.register_blueprint(prompt_bp, url_prefix=f'/prompts')
    
    # Add template directory
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               '..', 'tools', 'prompt_manager', 'templates')
    
    if templates_dir not in app.jinja_loader.searchpath:
        app.jinja_loader.searchpath.append(os.path.abspath(templates_dir))
        logger.info(f"Added prompt manager templates directory: {templates_dir}")
    
    # Return the prompt manager instance for use in the application
    return prompt_manager

def register_prompt_routes(app: Flask, prefix: str = "/prompts") -> None:
    """
    Register prompt manager routes with a Flask application
    
    Args:
        app: Flask application
        prefix: URL prefix for prompt manager routes
    """
    app.register_blueprint(prompt_bp, url_prefix=prefix)
    logger.info(f"Registered prompt manager routes with prefix: {prefix}")

def add_prompt_template_directory(app: Flask) -> None:
    """
    Add the prompt manager template directory to the Flask application's Jinja2 loader
    
    Args:
        app: Flask application
    """
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               '..', 'tools', 'prompt_manager', 'templates')
    
    if templates_dir not in app.jinja_loader.searchpath:
        app.jinja_loader.searchpath.append(os.path.abspath(templates_dir))
        logger.info(f"Added prompt manager templates directory: {templates_dir}")

def get_prompt_template(agent_name: str, prompt_manager: PromptManager = None) -> dict:
    """
    Get a prompt template from the prompt manager
    
    Args:
        agent_name: Name of the agent prompt to retrieve
        prompt_manager: PromptManager instance (if None, creates a new one)
    
    Returns:
        Dictionary containing the prompt template
    """
    if prompt_manager is None:
        prompt_manager = get_prompt_manager()
    
    try:
        return prompt_manager.load_prompt(agent_name)
    except FileNotFoundError:
        logger.warning(f"Prompt template for {agent_name} not found, creating default")
        # Create default template
        template = prompt_manager.create_prompt_template(
            agent_name=agent_name,
            role="AI Assistant",
            description=f"{agent_name} is an AI assistant",
            tone="Helpful, informative",
            core_objectives=["Assist the user effectively"],
            contextual_instructions="Provide helpful responses based on the context",
            dynamic_prompt_prefix=f"You are {agent_name}, a helpful AI assistant.",
            analysis_prompt="Analyze the conversation for key insights"
        )
        prompt_manager.save_prompt(agent_name, template)
        return template 