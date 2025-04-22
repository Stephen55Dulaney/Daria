import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, Any, List, Optional

def parse_timestamp(text: str) -> Optional[str]:
    """Try to extract timestamp from text in various formats."""
    # Try to find HH:MM:SS pattern
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    match = re.search(time_pattern, text)
    if match:
        return match.group(0)
    return None

def parse_speaker(text: str) -> Optional[str]:
    """Try to extract speaker name from text."""
    # Look for patterns like "Name:" or "Name (Role):"
    speaker_pattern = r'^([^:]+):'
    match = re.search(speaker_pattern, text.strip())
    if match:
        return match.group(1).strip()
    return None

def format_transcript(old_transcript: str, old_analysis: str) -> str:
    """Convert old transcript format to new timestamped format."""
    if not old_transcript and old_analysis:
        # If transcript is empty but analysis has the conversation
        text_to_parse = old_analysis
    else:
        text_to_parse = old_transcript

    # Split into lines and process
    lines = text_to_parse.split('\n')
    formatted_lines = []
    current_time = datetime.strptime("13:00:00", "%H:%M:%S")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to extract existing timestamp
        timestamp = parse_timestamp(line)
        if not timestamp:
            # If no timestamp, generate one and increment by 30 seconds
            timestamp = current_time.strftime("%H:%M:%S")
            current_time = current_time + timedelta(seconds=30)

        # Try to extract speaker
        speaker = parse_speaker(line)
        if speaker:
            # Remove speaker prefix from line
            line = re.sub(f"^{re.escape(speaker)}:", "", line).strip()
        else:
            speaker = "Unknown Speaker"

        formatted_lines.append(f"[{speaker}] {timestamp}\n{line}\n")

    return "\n".join(formatted_lines)

def extract_project_info(content: Dict[str, Any]) -> Dict[str, Any]:
    """Extract project information from interview content."""
    project_id = content.get("id", "").split("-")[0]  # Use first part of UUID as project ID
    return {
        "id": project_id,
        "name": content.get("project_name", "Unassigned"),
        "description": "",
        "created_at": content.get("date", datetime.now().isoformat()),
        "status": "active",
        "interviews": [content["id"]]
    }

def migrate_interview(file_path: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Migrate a single interview file to new schema."""
    with open(file_path, 'r') as f:
        content = json.load(f)

    # Create new schema
    new_schema = {
        "id": content["id"],
        "transcript_name": content.get("metadata", {}).get("interviewee", {}).get("name", "Unknown"),
        "project_name": content.get("project_name", "Unassigned"),
        "interview_type": content.get("interview_type", "General Interview"),
        "project_description": "",
        "date": content.get("date", datetime.now().isoformat()),
        "transcript": format_transcript(content.get("transcript", ""), content.get("analysis", "")),
        "analysis": None,
        "metadata": {
            "researcher": {
                "name": content.get("metadata", {}).get("researcher", {}).get("name", ""),
                "email": content.get("metadata", {}).get("researcher", {}).get("email", ""),
                "role": content.get("metadata", {}).get("researcher", {}).get("role", "UX Researcher")
            },
            "interviewee": content.get("metadata", {}).get("interviewee", {
                "name": "Unknown",
                "age": "",
                "gender": "",
                "location": "",
                "occupation": "",
                "industry": "",
                "experience": "",
                "education": ""
            }),
            "technology": content.get("metadata", {}).get("technology", {
                "primaryDevice": "",
                "operatingSystem": "",
                "browserPreference": "",
                "technicalProficiency": ""
            }),
            "interview_details": {
                "interviewDate": content.get("date", ""),
                "interviewDuration": "60",
                "interviewFormat": "video-call",
                "interviewLanguage": "english",
                "interviewNotes": "",
                "keyInsights": "",
                "followUpActions": ""
            },
            "consent": True
        }
    }

    # Extract project info
    project_info = extract_project_info(content)

    return new_schema, project_info

def test_migration(test_file: str):
    """Test migration on a single file."""
    # Create backup
    backup_path = test_file + '.backup'
    os.system(f'cp "{test_file}" "{backup_path}"')

    try:
        # Migrate file
        new_schema, project_info = migrate_interview(test_file)
        
        # Save migrated interview
        with open(test_file, 'w') as f:
            json.dump(new_schema, f, indent=2)

        # Ensure projects directory exists
        os.makedirs("projects", exist_ok=True)

        # Save or update project file
        project_file = f"projects/{project_info['id']}.json"
        if os.path.exists(project_file):
            with open(project_file, 'r') as f:
                existing_project = json.load(f)
                # Merge interviews list
                existing_project['interviews'] = list(set(existing_project.get('interviews', []) + project_info['interviews']))
                project_info = existing_project

        with open(project_file, 'w') as f:
            json.dump(project_info, f, indent=2)

        print(f"Successfully migrated {test_file}")
        print(f"Project info saved to {project_file}")
        
    except Exception as e:
        # Restore backup on error
        os.system(f'mv "{backup_path}" "{test_file}"')
        print(f"Error during migration: {str(e)}")
        raise e

    # Remove backup if successful
    os.remove(backup_path)

def migrate_all_interviews():
    """Migrate all interviews in the interviews directory."""
    interviews_dir = Path('interviews')
    for interview_file in interviews_dir.glob('*.json'):
        if not interview_file.name.endswith('.backup'):
            print(f"Migrating {interview_file}")
            test_migration(str(interview_file))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test single file
        test_migration(sys.argv[1])
    else:
        # Migrate all files
        migrate_all_interviews() 