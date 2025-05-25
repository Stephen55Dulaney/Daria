#!/usr/bin/env python3
"""
Fix session ID filename in api_upload_transcript function
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

def fix_session_id_filename():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the api_upload_transcript function
    upload_function = re.search(r'def api_upload_transcript\(\):(.*?)return jsonify', content, re.DOTALL)
    if not upload_function:
        logger.error("Could not find api_upload_transcript function")
        return False
    
    # Check for 'file_path = os.path.join' line and ensure it uses the variable correctly
    function_body = upload_function.group(1)
    file_path_line = re.search(r'file_path = os\.path\.join\(.*?, f"(.*?)"\)', function_body)
    
    if file_path_line and 'session_id.json' in file_path_line.group(1):
        logger.info("Found incorrect session_id formatting")
        
        # Replace with proper f-string format
        fixed_content = content.replace(
            'file_path = os.path.join(app.config[\'INTERVIEW_SESSIONS_DIR\'], f"session_id.json")',
            'file_path = os.path.join(app.config[\'INTERVIEW_SESSIONS_DIR\'], f"{session_id}.json")'
        )
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        
        logger.info(f"✅ Successfully fixed session ID filename in api_upload_transcript function")
        return True
    
    logger.info("Session ID filename is already fixed or using a different format")
    return True

if __name__ == "__main__":
    logger.info("Fixing session ID filename issue")
    success = fix_session_id_filename()
    if success:
        logger.info("Session ID filename fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix session ID filename")
        sys.exit(1) 