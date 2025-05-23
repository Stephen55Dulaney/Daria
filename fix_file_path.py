#!/usr/bin/env python3
"""
Fix the file_path definition in api_upload_transcript function
"""

import re
import sys
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_file_path():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the api_upload_transcript function
    upload_pattern = r"@app\.route\('/api/upload_transcript'"
    if not re.search(upload_pattern, content):
        logger.error("Could not find api_upload_transcript function")
        return False
    
    # Find the location where we need to add the file_path definition
    # We want to add it just before "# Save the interview data"
    save_pattern = r"(# Save the interview data\s*?)with open\(file_path, 'w'\)"
    if re.search(save_pattern, content):
        logger.info("Found location to add file_path definition")
        session_id = re.search(r"session_id\s*=\s*'(.*?)'", content).group(1)
        replacement = r"\1file_path = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f\"{session_id}.json\")\n        with open(file_path, 'w')"
        content = re.sub(save_pattern, replacement, content)
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"✅ Successfully added file_path definition to api_upload_transcript function")
        return True
    else:
        logger.error("Could not find location to add file_path definition")
        return False

if __name__ == "__main__":
    logger.info("Fixing file_path definition in api_upload_transcript function")
    success = fix_file_path()
    if success:
        logger.info("file_path definition fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix file_path definition")
        sys.exit(1) 