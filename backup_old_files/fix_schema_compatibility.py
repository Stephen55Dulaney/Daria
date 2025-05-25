#!/usr/bin/env python3
"""
Fix Schema Compatibility for Interview Sessions

This script addresses the schema discrepancy between remote and uploaded
transcript sessions to ensure consistent display and functionality.
"""

import os
import re
import sys
import json
import logging
import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def normalize_session_file(file_path):
    """Normalize the schema of a session file to match the expected format."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if this file needs to be converted (has old format)
        if 'conversation_history' in data and 'messages' not in data:
            logger.info(f"Converting session file: {file_path}")
            
            # Create standardized format
            normalized_data = {
                "id": data.get("id", os.path.basename(file_path).replace(".json", "")),
                "guide_id": data.get("guide_id", ""),
                "interviewee": {
                    "name": data.get("interviewee", {}).get("name") if isinstance(data.get("interviewee"), dict) else data.get("participant_name", ""),
                    "email": data.get("interviewee", {}).get("email") if isinstance(data.get("interviewee"), dict) else data.get("participant_email", ""),
                    "role": data.get("interviewee", {}).get("role") if isinstance(data.get("interviewee"), dict) else data.get("participant_role", ""),
                    "department": data.get("interviewee", {}).get("department", "") if isinstance(data.get("interviewee"), dict) else "",
                    "company": data.get("interviewee", {}).get("company", "") if isinstance(data.get("interviewee"), dict) else "",
                    "demographics": data.get("interviewee", {}).get("demographics", {
                        "age_range": "",
                        "gender": "",
                        "location": ""
                    }) if isinstance(data.get("interviewee"), dict) else {
                        "age_range": "",
                        "gender": "",
                        "location": ""
                    }
                },
                "status": data.get("status", "completed"),
                "title": data.get("title", "Uploaded Interview"),
                "project": data.get("project", ""),
                "interview_type": data.get("interview_type", "discovery_interview"),
                "created_at": data.get("created_at", datetime.datetime.now().isoformat()),
                "updated_at": data.get("updated_at", data.get("last_updated", datetime.datetime.now().isoformat())),
                "messages": []
            }
            
            # Convert conversation_history to messages
            if 'conversation_history' in data and isinstance(data['conversation_history'], list):
                for i, msg in enumerate(data['conversation_history']):
                    normalized_msg = {
                        "id": msg.get("id", f"msg_{i+1:03d}"),
                        "content": msg.get("content", ""),
                        "role": msg.get("role", ""),
                        "timestamp": msg.get("timestamp", "")
                    }
                    normalized_data["messages"].append(normalized_msg)
            
            # Write the normalized data back to the file
            with open(file_path, 'w') as f:
                json.dump(normalized_data, f, indent=2)
            
            logger.info(f"✅ Successfully normalized session file: {file_path}")
            return True
        else:
            logger.info(f"Session file already in correct format or uses different schema: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error normalizing session file {file_path}: {str(e)}")
        return False

def fix_session_display_template():
    """Update templates to handle both schema formats."""
    template_files = [
        "templates/langchain/discussion_guide_details.html",
        "templates/langchain/session.html"
    ]
    
    for template_file in template_files:
        if not os.path.exists(template_file):
            logger.warning(f"Template file not found: {template_file}")
            continue
        
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Add fallback handling for both messages and conversation_history
            if "session.messages" in content and "session.conversation_history" not in content:
                logger.info(f"Adding schema compatibility to template: {template_file}")
                
                # Replace session.messages references to handle both formats
                updated_content = content.replace(
                    "session.messages", 
                    "session.messages if session.messages is defined else session.conversation_history"
                )
                
                # Replace session.interviewee.name with fallback
                updated_content = updated_content.replace(
                    "session.interviewee.name", 
                    "session.interviewee.name if session.interviewee is defined else session.participant_name"
                )
                
                with open(template_file, 'w') as f:
                    f.write(updated_content)
                
                logger.info(f"✅ Successfully updated template: {template_file}")
            else:
                logger.info(f"Template already contains compatibility or uses different schema: {template_file}")
        except Exception as e:
            logger.error(f"Error updating template {template_file}: {str(e)}")

def normalize_all_session_files():
    """Normalize all session files in the sessions directory."""
    sessions_dir = Path("data/interviews/sessions")
    if not sessions_dir.exists():
        logger.error(f"Sessions directory not found: {sessions_dir}")
        return False
    
    files_count = 0
    normalized_count = 0
    
    for file_path in sessions_dir.glob("*.json"):
        files_count += 1
        if normalize_session_file(file_path):
            normalized_count += 1
    
    logger.info(f"Processed {files_count} session files, normalized {normalized_count} files")
    return True

def fix_api_upload_transcript():
    """Update the upload_transcript function to use the standardized schema."""
    file_path = 'run_interview_api.py'
    if not os.path.exists(file_path):
        logger.error(f"API file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the api_upload_transcript function
        upload_function = re.search(r'def api_upload_transcript\(\):(.*?)return jsonify', content, re.DOTALL)
        if not upload_function:
            logger.error("Could not find api_upload_transcript function")
            return False
        
        function_body = upload_function.group(1)
        
        # Create a pattern to find the interview_data dictionary construction
        interview_data_pattern = r'interview_data = \{(.*?)conversation_history'
        
        # Extract the current interview_data dictionary
        interview_data_match = re.search(interview_data_pattern, function_body, re.DOTALL)
        if not interview_data_match:
            logger.error("Could not find interview_data dictionary with conversation_history")
            return False
        
        # Create the updated dictionary with the correct schema
        updated_dict = """
            'id': session_id,
            'guide_id': guide_id,
            'interviewee': {
                'name': participant_name,
                'email': participant_email,
                'role': participant_role,
                'department': '',
                'company': '',
                'demographics': {
                    'age_range': '',
                    'gender': '',
                    'location': ''
                }
            },
            'status': 'completed',  # Mark as completed since we have the full transcript
            'title': title,
            'project': project,
            'interview_type': interview_type,
            'created_at': now,
            'updated_at': now,
            'messages': [],
            """
        
        # Replace the old dictionary prefix with the new one
        updated_content = re.sub(interview_data_pattern, f'interview_data = {{{updated_dict}', content, flags=re.DOTALL)
        
        # Update conversation_history references in the function
        if 'conversation_history' in updated_content:
            # Keep both for backward compatibility
            updated_content = updated_content.replace(
                "interview_data['conversation_history'] = conversation_history", 
                "interview_data['conversation_history'] = conversation_history\n        interview_data['messages'] = conversation_history"
            )
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info(f"✅ Successfully updated api_upload_transcript function to use standardized schema")
        return True
    except Exception as e:
        logger.error(f"Error updating api_upload_transcript function: {str(e)}")
        return False

def fix_discussion_service():
    """Update the discussion service to handle both schema formats."""
    file_path = 'langchain_features/services/discussion_service.py'
    if not os.path.exists(file_path):
        logger.warning(f"Discussion service file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Update the get_messages method to handle both formats
        if 'def get_messages(' in content:
            logger.info(f"Updating get_messages method in discussion service")
            
            messages_method_pattern = r'def get_messages\(self, session_id: str\)(.*?)return session\.get\("messages", \[\]\)'
            messages_method_match = re.search(messages_method_pattern, content, re.DOTALL)
            
            if messages_method_match:
                updated_messages_method = """def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        \"\"\"Get all messages for a session.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            List[Dict]: List of messages or empty list if not found
        \"\"\"
        session = self._load_session(session_id)
        if not session:
            return []
        
        # Handle both schema formats
        if "messages" in session:
            return session.get("messages", [])
        elif "conversation_history" in session:
            return session.get("conversation_history", [])
        
        return []"""
                
                updated_content = content.replace(messages_method_match.group(0), updated_messages_method)
                
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                
                logger.info(f"✅ Successfully updated get_messages method in discussion service")
                return True
            else:
                logger.warning("Could not find get_messages method in the expected format")
                return False
        else:
            logger.warning("get_messages method not found in discussion service")
            return False
    except Exception as e:
        logger.error(f"Error updating discussion service: {str(e)}")
        return False

def run_all_fixes():
    """Run all schema compatibility fixes."""
    logger.info("Running schema compatibility fixes...")
    
    # Fix API upload function to use standard schema
    logger.info("1. Fixing API upload_transcript function...")
    api_fix_result = fix_api_upload_transcript()
    
    # Fix discussion service to handle both schemas
    logger.info("2. Fixing discussion service...")
    service_fix_result = fix_discussion_service()
    
    # Fix templates to handle both schemas
    logger.info("3. Fixing session display templates...")
    template_fix_result = fix_session_display_template()
    
    # Normalize existing session files
    logger.info("4. Normalizing existing session files...")
    session_fix_result = normalize_all_session_files()
    
    # Report results
    if api_fix_result and service_fix_result and template_fix_result and session_fix_result:
        logger.info("✅ All schema compatibility fixes applied successfully")
        return True
    else:
        logger.warning("⚠️ Some fixes could not be applied:")
        if not api_fix_result:
            logger.warning("  - Failed to fix API upload_transcript function")
        if not service_fix_result:
            logger.warning("  - Failed to fix discussion service")
        if not template_fix_result:
            logger.warning("  - Failed to fix session display templates")
        if not session_fix_result:
            logger.warning("  - Failed to normalize existing session files")
        return False

if __name__ == "__main__":
    logger.info("Starting schema compatibility fixes")
    success = run_all_fixes()
    if success:
        logger.info("Schema compatibility fixes completed successfully")
        sys.exit(0)
    else:
        logger.error("Schema compatibility fixes completed with some errors")
        sys.exit(1) 