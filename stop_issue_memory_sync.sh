#!/bin/bash

# Stop Issue to Memory Companion Sync Service
# This script stops the running sync service

echo "Stopping Issue to Memory Companion Sync Service..."

# Check if PID file exists
if [ -f .issue_memory_sync_pid ]; then
    PID=$(cat .issue_memory_sync_pid)
    
    # Check if process is running
    if ps -p $PID > /dev/null; then
        echo "Stopping service with PID: $PID"
        kill $PID
        echo "Service stopped successfully."
    else
        echo "Service is not running. PID $PID not found."
    fi
    
    # Remove PID file
    rm .issue_memory_sync_pid
else
    echo "PID file not found. Service may not be running."
    
    # Try to find and kill the process anyway
    PID=$(ps aux | grep "issue_to_memory_sync.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PID" ]; then
        echo "Found process with PID: $PID"
        kill $PID
        echo "Service stopped successfully."
    fi
fi 