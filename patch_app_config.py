#!/usr/bin/env python3
"""
Patch app.config to set INTERVIEW_SESSIONS_DIR in run_interview_api.py
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

def patch_file():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create the replacement lines
    app_config_pattern = r"app\.config\['SECRET_KEY'\] = os\.environ\.get\('SECRET_KEY', '[\w-]+'\)"
    replacement = "app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'daria-interview-tool-secret-key')\n\n# Configure directory paths\napp.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)\napp.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)"
    
    # Apply the replacement
    if re.search(app_config_pattern, content):
        logger.info("Found app.config['SECRET_KEY'] in file")
        new_content = re.sub(app_config_pattern, replacement, content)
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        logger.info(f"✅ Successfully patched {file_path}")
        return True
    else:
        logger.error("Could not find app.config['SECRET_KEY'] in file")
        return False

if __name__ == "__main__":
    logger.info("Patching app.config in run_interview_api.py")
    success = patch_file()
    if success:
        logger.info("Patch applied successfully")
        sys.exit(0)
    else:
        logger.error("Failed to apply patch")
        sys.exit(1) 