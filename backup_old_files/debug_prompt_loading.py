#!/usr/bin/env python3
"""
Debug script to check all prompt YAML files in the directory
"""

import os
import sys
import yaml
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def validate_yaml_file(file_path):
    """Validate a YAML file and print any errors"""
    try:
        with open(file_path, 'r') as f:
            yaml_content = f.read()
            yaml_data = yaml.safe_load(yaml_content)
            logger.info(f"✅ Successfully parsed {os.path.basename(file_path)}")
            return True, yaml_data
    except Exception as e:
        logger.error(f"❌ Error parsing {os.path.basename(file_path)}: {str(e)}")
        return False, None

def list_prompt_files(prompt_dir):
    """List all YAML files in the prompt directory"""
    if not os.path.exists(prompt_dir):
        logger.error(f"Directory not found: {prompt_dir}")
        return []
    
    return [os.path.join(prompt_dir, f) for f in os.listdir(prompt_dir) 
            if f.endswith('.yml') and not f.startswith('.')]

def check_all_prompts(prompt_dir):
    """Check all prompt files in the directory"""
    prompt_files = list_prompt_files(prompt_dir)
    logger.info(f"Found {len(prompt_files)} prompt files in {prompt_dir}")
    
    valid_count = 0
    invalid_count = 0
    
    for file_path in prompt_files:
        valid, data = validate_yaml_file(file_path)
        if valid:
            valid_count += 1
            # Check required fields
            agent_name = data.get('agent_name', '')
            role = data.get('role', '')
            description = data.get('description', '')
            logger.info(f"   Agent: {agent_name}, Role: {role}")
        else:
            invalid_count += 1
    
    logger.info(f"Summary: {valid_count} valid files, {invalid_count} invalid files")
    return valid_count, invalid_count

if __name__ == "__main__":
    # Default prompt directory
    default_prompt_dir = "langchain_features/prompt_manager/prompts"
    
    # Allow passing a different prompt directory as an argument
    prompt_dir = sys.argv[1] if len(sys.argv) > 1 else default_prompt_dir
    
    logger.info(f"Checking YAML files in {prompt_dir}...")
    valid_count, invalid_count = check_all_prompts(prompt_dir)
    
    if invalid_count > 0:
        sys.exit(1)
    sys.exit(0) 