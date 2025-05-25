#!/bin/bash
# Daria Project Journal Utility
# A safe way to manage the project journal without interfering with the main application

# Set script to exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define paths
JOURNAL_FILE="DARIA_PROJECT_JOURNAL.md"
JOURNAL_SCRIPT="update_journal.py"
BACKUP_DIR=".journal_backups"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to create backup of the journal
create_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/${JOURNAL_FILE%.*}_$timestamp.md"
    
    if [ -f "$JOURNAL_FILE" ]; then
        cp "$JOURNAL_FILE" "$backup_file"
        echo -e "${GREEN}Created backup: $backup_file${NC}"
    fi
}

# Function to display journal summary (without using Python script)
display_quick_summary() {
    if [ ! -f "$JOURNAL_FILE" ]; then
        echo -e "${RED}Journal file not found: $JOURNAL_FILE${NC}"
        return 1
    fi
    
    echo -e "\n${YELLOW}=========================================${NC}"
    echo -e "${YELLOW}DARIA PROJECT JOURNAL - QUICK REMINDER${NC}"
    echo -e "${YELLOW}=========================================${NC}"
    
    # Display just the build status section using grep and sed
    echo -e "\n${GREEN}Current Build Status:${NC}"
    sed -n '/^## Current Build Status/,/^## /p' "$JOURNAL_FILE" | sed '$d' | tail -n +2
    
    # Display just the next steps section
    echo -e "\n${GREEN}Next Steps:${NC}"
    sed -n '/^## Next Steps/,/^## /p' "$JOURNAL_FILE" | sed '$d' | tail -n +2
    
    # Get the last session entry
    echo -e "\n${GREEN}Last Session Notes:${NC}"
    sed -n '/^### Session [0-9]*/,/^### Session/p' "$JOURNAL_FILE" | sed '/^### Session [0-9]*/d' | sed '/^### Session/d' | head -10
    
    echo -e "\n${YELLOW}=========================================${NC}"
    echo -e "${YELLOW}For full details, see $JOURNAL_FILE${NC}"
    echo -e "${YELLOW}To update the journal, run: ./journal.sh update${NC}"
    echo -e "${YELLOW}=========================================${NC}\n"
}

# Function to check if Python is installed and available
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed or not in your PATH${NC}"
        return 1
    fi
    return 0
}

# Function to safely run the journal update utility
run_journal_update() {
    if [ ! -f "$JOURNAL_SCRIPT" ]; then
        echo -e "${RED}Error: Journal script not found: $JOURNAL_SCRIPT${NC}"
        return 1
    fi
    
    # Check Python availability
    check_python || return 1
    
    # Create a backup before making changes
    create_backup
    
    # Run the Python script
    python3 "$JOURNAL_SCRIPT"
}

# Main script logic
case "$1" in
    "update")
        run_journal_update
        ;;
    "summary")
        display_quick_summary
        ;;
    "backup")
        create_backup
        echo -e "${GREEN}Journal backup created${NC}"
        ;;
    *)
        # Default action - display summary
        display_quick_summary
        ;;
esac

exit 0 