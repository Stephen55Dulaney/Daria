#!/usr/bin/env python3
"""
Fix Session Association with Discussion Guides

This script ensures that all session files in the sessions directory are
properly associated with their corresponding discussion guides by adding
the session IDs to the guide's sessions list.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def associate_sessions_with_guides():
    """
    Find all sessions with guide_id and ensure they're associated with that guide.
    """
    sessions_dir = Path("data/interviews/sessions")
    guides_dir = Path("data/interviews")
    
    if not sessions_dir.exists():
        logger.error(f"Sessions directory not found: {sessions_dir}")
        return False
    
    if not guides_dir.exists():
        logger.error(f"Guides directory not found: {guides_dir}")
        return False
    
    # Create a mapping of guide IDs to their session lists
    guide_sessions = {}
    
    # Initialize the guide_sessions map from existing guides
    for guide_file in guides_dir.glob("*.json"):
        if guide_file.name.startswith("."):
            continue
            
        try:
            with open(guide_file, 'r') as f:
                guide_data = json.load(f)
            
            guide_id = guide_data.get("id")
            if guide_id:
                sessions = guide_data.get("sessions", [])
                guide_sessions[guide_id] = sessions
        except Exception as e:
            logger.warning(f"Error reading guide file {guide_file}: {e}")
            continue
    
    # Process all session files
    sessions_count = 0
    associated_count = 0
    for session_file in sessions_dir.glob("*.json"):
        if session_file.name.startswith(".") or session_file.name == "session_id.json":
            continue
            
        try:
            sessions_count += 1
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            session_id = session_data.get("id")
            guide_id = session_data.get("guide_id")
            
            if not session_id or not guide_id:
                continue
            
            # Check if the session needs to be associated with the guide
            if guide_id in guide_sessions:
                if session_id not in guide_sessions[guide_id]:
                    logger.info(f"Adding session {session_id} to guide {guide_id}")
                    guide_sessions[guide_id].append(session_id)
                    associated_count += 1
        except Exception as e:
            logger.warning(f"Error processing session file {session_file}: {e}")
            continue
    
    # Update the guide files with the new sessions lists
    updated_guides = 0
    for guide_id, sessions in guide_sessions.items():
        guide_file = guides_dir / f"{guide_id}.json"
        if not guide_file.exists():
            logger.warning(f"Guide file not found: {guide_file}")
            continue
            
        try:
            with open(guide_file, 'r') as f:
                guide_data = json.load(f)
            
            # Update the sessions list
            if guide_data.get("sessions", []) != sessions:
                guide_data["sessions"] = sessions
                
                # Write the updated guide data back to the file
                with open(guide_file, 'w') as f:
                    json.dump(guide_data, f, indent=2)
                
                updated_guides += 1
                logger.info(f"Updated guide {guide_id} with {len(sessions)} sessions")
        except Exception as e:
            logger.error(f"Error updating guide file {guide_file}: {e}")
            continue
    
    logger.info(f"Processed {sessions_count} session files")
    logger.info(f"Associated {associated_count} sessions with their guides")
    logger.info(f"Updated {updated_guides} guide files")
    
    return True

def fix_upload_transcript_function():
    """
    Modify the api_upload_transcript function to update the guide's sessions list.
    """
    file_path = 'run_interview_api.py'
    if not os.path.exists(file_path):
        logger.error(f"API file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find where to add code to update the guide's sessions list
        upload_function = "def api_upload_transcript():"
        save_interview = "# Save the interview data"
        
        if upload_function in content and save_interview in content:
            # Split the content to find where to add our code
            pre_save = content.split(save_interview)[0]
            post_save = save_interview + content.split(save_interview)[1]
            
            # Check if we've already added the guide update code
            if "# Update the guide with the new session ID" in content:
                logger.info("Guide update code already exists in upload_transcript function")
                return True
            
            # Add code to update the guide's sessions list after saving the interview data
            guide_update_code = """
        # Update the guide with the new session ID
        if guide_id:
            guide_file = os.path.join(DATA_DIR, f"{guide_id}.json")
            if os.path.exists(guide_file):
                try:
                    with open(guide_file, 'r') as f:
                        guide_data = json.load(f)
                    
                    # Add the session ID to the guide's sessions list if not already there
                    if "sessions" not in guide_data:
                        guide_data["sessions"] = []
                    if session_id not in guide_data["sessions"]:
                        guide_data["sessions"].append(session_id)
                        guide_data["updated_at"] = now
                    
                    # Save the updated guide data
                    with open(guide_file, 'w') as f:
                        json.dump(guide_data, f, indent=2)
                except Exception as e:
                    logger.error(f"Error updating guide {guide_id} with session {session_id}: {str(e)}")
        
        """
            
            # Combine the content with our new code
            updated_content = pre_save + guide_update_code + save_interview + post_save
            
            # Write the updated content back to the file
            with open(file_path, 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Successfully added guide update code to upload_transcript function")
            return True
        else:
            logger.error("Could not find appropriate location to add guide update code")
            return False
    except Exception as e:
        logger.error(f"Error updating upload_transcript function: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Fixing session association with guides...")
    
    # First, fix the upload_transcript function for future uploads
    logger.info("1. Adding guide update code to upload_transcript function...")
    fix_function_result = fix_upload_transcript_function()
    
    # Then associate existing sessions with their guides
    logger.info("2. Associating existing sessions with their guides...")
    associate_result = associate_sessions_with_guides()
    
    if fix_function_result and associate_result:
        logger.info("✅ Successfully fixed session association with guides")
        sys.exit(0)
    else:
        logger.error("⚠️ Some issues occurred while fixing session association")
        sys.exit(1) 