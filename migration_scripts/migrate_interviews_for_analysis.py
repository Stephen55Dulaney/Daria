#!/usr/bin/env python3
"""
Migration script to update existing interviews to support the new analysis format.
"""

import os
import sys
import json
import datetime
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define paths
BASE_DIR = Path(__file__).parent.absolute().parent
DATA_DIR = BASE_DIR / "data" / "interviews"
BACKUP_DIR = BASE_DIR / "data" / "backups" / f"interviews_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

def create_backup():
    """Create a backup of all interview files."""
    print(f"Creating backup in {BACKUP_DIR}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for file_path in DATA_DIR.glob("*.json"):
        backup_path = BACKUP_DIR / file_path.name
        with open(file_path, 'r') as src_file:
            with open(backup_path, 'w') as dst_file:
                dst_file.write(src_file.read())
        count += 1
    
    print(f"Backed up {count} interview files")
    return count

def migrate_interviews():
    """Migrate interviews to new format with analysis support."""
    print(f"Migrating interviews in {DATA_DIR}")
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for file_path in DATA_DIR.glob("*.json"):
        try:
            # Load interview data
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if already has the new structure
            if 'analysis' in data:
                print(f"Skipping {file_path.name} - already has analysis field")
                skipped_count += 1
                continue
            
            # Add the analysis field if needed
            if 'analysis' not in data:
                data['analysis'] = None
            
            # Ensure we have a status field
            if 'status' not in data:
                # Determine status based on conversation_history
                if 'conversation_history' in data and data['conversation_history']:
                    data['status'] = 'completed'
                else:
                    data['status'] = 'active'
            
            # If we already have a transcript field in the new format, keep it
            if 'transcript' not in data and 'conversation_history' in data:
                # Convert conversation_history to transcript format
                data['transcript'] = []
                for message in data.get('conversation_history', []):
                    entry = {
                        "speaker": "Interviewer" if message.get('role') == 'assistant' else "Participant",
                        "speaker_name": message.get('name', "Interviewer" if message.get('role') == 'assistant' else "Participant"),
                        "content": message.get('content', ''),
                        "timestamp": message.get('timestamp', '')
                    }
                    data['transcript'].append(entry)
            
            # Save the updated interview
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Successfully migrated {file_path.name}")
            migrated_count += 1
            
        except Exception as e:
            print(f"Error migrating {file_path.name}: {str(e)}")
            error_count += 1
    
    print(f"\nMigration complete:")
    print(f"  - {migrated_count} interviews migrated")
    print(f"  - {skipped_count} interviews skipped (already in new format)")
    print(f"  - {error_count} interviews had errors")
    
    return migrated_count, skipped_count, error_count

if __name__ == "__main__":
    print("Interview Migration Tool")
    print("=======================")
    
    # Create backup first
    backup_count = create_backup()
    if backup_count == 0:
        print("No interviews found to migrate. Exiting.")
        sys.exit(0)
    
    # Ask for confirmation
    answer = input(f"\nReady to migrate {backup_count} interviews? This will modify the files. (y/n): ")
    if answer.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    migrated, skipped, errors = migrate_interviews()
    
    if errors > 0:
        print(f"\nMigration completed with {errors} errors. Review the output above.")
        sys.exit(1)
    else:
        print("\nMigration completed successfully!")
        sys.exit(0) 