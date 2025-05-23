#!/usr/bin/env python3
"""
Fix the file_path definition in api_upload_transcript function directly
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

def fix_file_path_direct():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the api_upload_transcript function
    upload_func_index = -1
    save_interview_index = -1
    
    for i, line in enumerate(lines):
        if "def api_upload_transcript():" in line:
            upload_func_index = i
        elif upload_func_index != -1 and "# Save the interview data" in line:
            save_interview_index = i
    
    if upload_func_index != -1 and save_interview_index != -1:
        logger.info(f"Found api_upload_transcript function at line {upload_func_index+1}")
        logger.info(f"Found 'Save the interview data' comment at line {save_interview_index+1}")
        
        # Find the line with "with open(file_path, 'w')" after the comment
        for i in range(save_interview_index, len(lines)):
            if "with open(file_path, 'w')" in lines[i]:
                # Insert the file_path definition before this line
                logger.info(f"Found 'with open(file_path, 'w')' at line {i+1}")
                
                # Add the file_path definition
                session_id = "session_id"  # Replace with actual session_id
                lines.insert(i, f"        file_path = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f\"{session_id}.json\")\n")
                logger.info("Added file_path definition")
                
                # Write the modified content back to the file
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                
                logger.info(f"✅ Successfully added file_path definition to api_upload_transcript function")
                return True
        
        logger.error("Could not find 'with open(file_path, 'w')' line")
        return False
    else:
        logger.error("Could not find api_upload_transcript function or 'Save the interview data' comment")
        return False

if __name__ == "__main__":
    logger.info("Fixing file_path definition in api_upload_transcript function directly")
    success = fix_file_path_direct()
    if success:
        logger.info("file_path definition fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix file_path definition")
        sys.exit(1) 