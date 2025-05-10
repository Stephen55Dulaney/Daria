#!/usr/bin/env python3
"""
Script to update the Daria Project Journal with new session notes.
"""

import os
import datetime
import re
from pathlib import Path

JOURNAL_FILE = "DARIA_PROJECT_JOURNAL.md"

def get_current_date():
    """Return the current date in a readable format."""
    return datetime.datetime.now().strftime("%B %d, %Y")

def read_journal():
    """Read the existing journal file."""
    if not os.path.exists(JOURNAL_FILE):
        print(f"Error: Journal file {JOURNAL_FILE} not found.")
        return None
    
    with open(JOURNAL_FILE, 'r') as file:
        content = file.read()
    return content

def update_session_notes(content, session_number, notes):
    """Add a new session entry to the journal."""
    if content is None:
        return None
    
    # Find the Session Notes section
    session_pattern = r"## Session Notes\n(.*?)(?=\n## |$)"
    match = re.search(session_pattern, content, re.DOTALL)
    
    if not match:
        print("Error: Could not find Session Notes section in the journal.")
        return content
    
    # Prepare new session entry
    new_session = f"\n### Session {session_number} ({get_current_date()})\n"
    for note in notes:
        new_session += f"- {note}\n"
    
    # Add new session right after the Session Notes header
    updated_content = content.replace(
        "## Session Notes",
        f"## Session Notes{new_session}"
    )
    
    return updated_content

def get_session_number(content):
    """Determine the next session number."""
    if content is None:
        return 1
    
    # Find all session entries
    session_pattern = r"### Session (\d+)"
    matches = re.findall(session_pattern, content)
    
    if not matches:
        return 1
    
    # Find the highest session number and increment by 1
    return max([int(num) for num in matches]) + 1

def save_journal(content):
    """Save the updated journal content."""
    if content is None:
        return False
    
    with open(JOURNAL_FILE, 'w') as file:
        file.write(content)
    
    return True

def print_journal_summary():
    """Print a summary of the journal for quick reference."""
    content = read_journal()
    if content is None:
        return
    
    # Extract project overview
    overview_pattern = r"## Project Overview\n(.*?)(?=\n## )"
    overview_match = re.search(overview_pattern, content, re.DOTALL)
    overview = overview_match.group(1).strip() if overview_match else "Not found"
    
    # Extract current build status
    status_pattern = r"## Current Build Status\n(.*?)(?=\n## )"
    status_match = re.search(status_pattern, content, re.DOTALL)
    status = status_match.group(1).strip() if status_match else "Not found"
    
    # Extract next steps
    steps_pattern = r"## Next Steps\n(.*?)(?=\n## )"
    steps_match = re.search(steps_pattern, content, re.DOTALL)
    steps = steps_match.group(1).strip() if steps_match else "Not found"
    
    # Get last session
    session_pattern = r"### Session \d+ \((.*?)\)(.*?)(?=\n### Session|\Z)"
    sessions = re.findall(session_pattern, content, re.DOTALL)
    last_session = sessions[-1] if sessions else ("None", "None")
    
    # Print summary
    print("\n" + "="*50)
    print("DARIA PROJECT JOURNAL - QUICK SUMMARY")
    print("="*50)
    print("\nProject Overview:")
    print(f"{overview[:200]}..." if len(overview) > 200 else overview)
    
    print("\nCurrent Build Status:")
    print(status)
    
    print("\nNext Steps:")
    print(steps)
    
    print(f"\nLast Session ({last_session[0]}):")
    print(last_session[1].strip())
    print("\n" + "="*50)
    print(f"For full details, see {JOURNAL_FILE}")
    print("="*50 + "\n")

def add_session_notes():
    """Interactive function to add new session notes."""
    content = read_journal()
    session_number = get_session_number(content)
    
    print(f"\nAdding notes for Session {session_number} ({get_current_date()})")
    print("Enter each note on a new line. Type 'done' when finished.")
    
    notes = []
    while True:
        note = input("> ")
        if note.lower() == 'done':
            break
        notes.append(note)
    
    if not notes:
        print("No notes added. Journal unchanged.")
        return
    
    updated_content = update_session_notes(content, session_number, notes)
    if save_journal(updated_content):
        print(f"Session {session_number} notes added to {JOURNAL_FILE}")
    else:
        print("Error updating journal.")

def main():
    """Main function to run the script."""
    if not os.path.exists(JOURNAL_FILE):
        print(f"Warning: Journal file {JOURNAL_FILE} not found.")
        create_new = input("Do you want to create a new journal file? (y/n): ")
        if create_new.lower() == 'y':
            # Create a basic template
            with open(JOURNAL_FILE, 'w') as file:
                file.write("# Daria Interview Tool - Project Journal\n\n"
                          "## Project Overview\nAdd project overview here.\n\n"
                          "## Current Build Status\nAdd current build status here.\n\n"
                          "## Next Steps\nAdd next steps here.\n\n"
                          "## Session Notes\n")
            print(f"Created new journal file: {JOURNAL_FILE}")
        else:
            print("Exiting without creating journal.")
            return
    
    while True:
        print("\nDaria Project Journal Utility")
        print("1. Show journal summary")
        print("2. Add new session notes")
        print("3. Exit")
        
        choice = input("Select an option (1-3): ")
        
        if choice == '1':
            print_journal_summary()
        elif choice == '2':
            add_session_notes()
        elif choice == '3':
            print("Exiting journal utility.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main() 