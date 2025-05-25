#!/usr/bin/env python3

import os
import json
from datetime import datetime
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_interview_file(file_path: Path) -> bool:
    """
    Migrate a single interview file to fix participant name inconsistencies.
    Returns True if file was modified, False otherwise.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        modified = False
        
        # Get the most authoritative name source
        participant_name = (
            data.get('transcript_name') or  # Most authoritative
            data.get('metadata', {}).get('interviewee', {}).get('name') or
            data.get('metadata', {}).get('participant', {}).get('name') or
            'Anonymous'
        )
        
        # Update all name occurrences
        if data.get('metadata', {}).get('interviewee', {}).get('name') != participant_name:
            if 'metadata' not in data:
                data['metadata'] = {}
            if 'interviewee' not in data['metadata']:
                data['metadata']['interviewee'] = {}
            data['metadata']['interviewee']['name'] = participant_name
            modified = True
            logger.info(f"Updated interviewee.name to {participant_name}")
        
        if data.get('metadata', {}).get('participant', {}).get('name') != participant_name:
            if 'metadata' not in data:
                data['metadata'] = {}
            if 'participant' not in data['metadata']:
                data['metadata']['participant'] = {}
            data['metadata']['participant']['name'] = participant_name
            modified = True
            logger.info(f"Updated participant.name to {participant_name}")
        
        # Update the title
        date_str = data.get('created_at', '').split('T')[0]
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        new_title = f"Interview with {participant_name} - {date_str}"
        if data.get('title') != new_title:
            data['title'] = new_title
            modified = True
            logger.info(f"Updated title to {new_title}")
        
        # Save changes if modified
        if modified:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved changes to {file_path}")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return False

def migrate_all_interviews():
    """Migrate all interview files in the interviews directory."""
    interviews_dir = Path('interviews')
    if not interviews_dir.exists():
        logger.error("Interviews directory not found")
        return
    
    total_files = 0
    modified_files = 0
    
    for file_path in interviews_dir.glob('*.json'):
        total_files += 1
        if migrate_interview_file(file_path):
            modified_files += 1
    
    logger.info(f"Migration complete. Modified {modified_files} out of {total_files} files.")

if __name__ == '__main__':
    migrate_all_interviews() 