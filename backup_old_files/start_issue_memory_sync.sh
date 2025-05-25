#!/bin/bash

# Start Issue to Memory Companion Sync Service
# This script starts the service that syncs data from Issue Tracker to Memory Companion

echo "Starting Issue to Memory Companion Sync Service..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Check if python is available
if ! command -v python &> /dev/null; then
    echo "Python not found. Please install Python 3.8 or later."
    exit 1
fi

# Make sure schedule package is installed
pip install schedule requests

# Set the log file
LOG_FILE="issue_memory_sync.log"

# Start the sync service in the background
nohup python issue_to_memory_sync.py --interval 10 > $LOG_FILE 2>&1 &

# Save the PID to a file for easy stopping later
echo $! > .issue_memory_sync_pid
echo "Issue to Memory Companion Sync Service started with PID: $!"
echo "Logs available in: $LOG_FILE"

# Add a command to stop the service
echo "To stop the service, run: kill \$(cat .issue_memory_sync_pid)" 