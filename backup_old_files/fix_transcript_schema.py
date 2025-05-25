#!/usr/bin/env python3
"""
Fix transcript schema in api_upload_transcript function
Ensures uploaded transcripts use the same schema as remote transcripts
"""

import re
import sys
import logging
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_transcript_schema():
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
    
    function_body = upload_function.group(1)
    
    # Check if we need to update the schema
    if "interview_data = {" in function_body and "interviewee" not in function_body:
        logger.info("Found transcript schema that needs to be updated")
        
        # Create a pattern to find the interview_data dictionary construction
        interview_data_pattern = r'interview_data = \{(.*?)\}'
        
        # Extract the current interview_data dictionary
        interview_data_match = re.search(interview_data_pattern, function_body, re.DOTALL)
        if not interview_data_match:
            logger.error("Could not find interview_data dictionary")
            return False
        
        # Get the current dictionary content
        current_dict = interview_data_match.group(1)
        
        # Create the updated dictionary with the correct schema
        updated_dict = """
            "id": session_id,
            "guide_id": guide_id,
            "interviewee": {
                "name": participant_name,
                "email": participant_email,
                "role": participant_role,
                "department": "",
                "company": "",
                "demographics": {
                    "age_range": "",
                    "gender": "",
                    "location": ""
                }
            },
            "status": "completed",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
            "messages": []
        """
        
        # Replace the old dictionary with the new one
        updated_content = re.sub(interview_data_pattern, f'interview_data = {{{updated_dict}}}', content, flags=re.DOTALL)
        
        # Also update any references to conversation_history to use messages instead
        if "conversation_history" in updated_content:
            updated_content = updated_content.replace("interview_data['conversation_history']", "interview_data['messages']")
            updated_content = updated_content.replace("'conversation_history':", "'messages':")
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info("✅ Successfully updated transcript schema in api_upload_transcript function")
        return True
    
    logger.info("Transcript schema is already using the correct format or has been modified in an unexpected way")
    return True

if __name__ == "__main__":
    logger.info("Fixing transcript schema in api_upload_transcript function")
    success = fix_transcript_schema()
    if success:
        logger.info("Transcript schema fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix transcript schema")
        sys.exit(1) 