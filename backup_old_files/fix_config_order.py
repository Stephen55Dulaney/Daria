#!/usr/bin/env python3
"""
Fix the order of app.config settings in run_interview_api.py
"""

import re
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_config_order():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    with open(file_path, 'r') as f:
        content = f.read()
    
    # First, remove the incorrect app.config lines
    wrong_config_pattern = r"# Configure directory paths\napp\.config\['INTERVIEW_DATA_DIR'\] = str\(DATA_DIR\)\napp\.config\['INTERVIEW_SESSIONS_DIR'\] = str\(SESSIONS_DIR\)"
    if re.search(wrong_config_pattern, content):
        logger.info("Found incorrect app.config settings, removing them")
        content = re.sub(wrong_config_pattern, "", content)
    
    # Now add the app.config lines after DATA_DIR.mkdir
    mkdir_pattern = r"(DATA_DIR\.mkdir\(parents=True, exist_ok=True\))"
    if re.search(mkdir_pattern, content):
        logger.info("Found DATA_DIR.mkdir, adding app.config settings after it")
        
        replacement = r"\1\n\n# Configure directory paths\napp.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)\napp.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)"
        content = re.sub(mkdir_pattern, replacement, content)
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"✅ Successfully fixed configuration order in {file_path}")
        return True
    else:
        logger.error("Could not find DATA_DIR.mkdir in file")
        return False

if __name__ == "__main__":
    logger.info("Fixing configuration order in run_interview_api.py")
    success = fix_config_order()
    if success:
        logger.info("Configuration order fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix configuration order")
        sys.exit(1) 