#!/usr/bin/env python3
"""
Debug script to directly test the prompt_manager and character loading
"""

import os
import sys
import logging
from langchain_features.prompt_manager.models import PromptManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def debug_prompt_manager():
    """Test the PromptManager functionality directly"""
    # Initialize prompt manager with the prompt directory
    prompt_dir = "langchain_features/prompt_manager/prompts"
    logger.info(f"Initializing PromptManager with prompt_dir: {prompt_dir}")
    
    # Check if the directory exists
    if not os.path.exists(prompt_dir):
        logger.error(f"Directory not found: {prompt_dir}")
        return False
    
    try:
        # Create the prompt manager
        prompt_manager = PromptManager(prompt_dir=prompt_dir)
        logger.info(f"PromptManager created: {type(prompt_manager)}")
        
        # List available agents
        logger.info("Listing available agents...")
        agent_names = prompt_manager.list_agents()
        logger.info(f"Found {len(agent_names)} agents: {agent_names}")
        
        # Try to load each agent's data
        logger.info("Attempting to load each agent's data:")
        for agent_name in agent_names:
            try:
                config = prompt_manager.load_prompt_config(agent_name)
                if config:
                    logger.info(f"  ✅ {agent_name} - {config.role}")
                else:
                    logger.error(f"  ❌ {agent_name} - Failed to load config (None returned)")
            except Exception as e:
                logger.error(f"  ❌ {agent_name} - Error: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing PromptManager: {str(e)}")
        return False

if __name__ == "__main__":
    success = debug_prompt_manager()
    if success:
        logger.info("PromptManager test completed successfully")
        sys.exit(0)
    else:
        logger.error("PromptManager test failed")
        sys.exit(1) 