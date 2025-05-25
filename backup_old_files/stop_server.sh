#!/bin/bash

echo "==============================================="
echo "     DARIA Interview Tool Server Stopper     "
echo "==============================================="

# Stop the main application server
if [ -f .daria_api_pid ]; then
    PID=$(cat .daria_api_pid)
    if ps -p $PID > /dev/null; then
        echo "Stopping server (PID: $PID)..."
        kill $PID
        rm .daria_api_pid
    else
        echo "Server process not found (PID: $PID)"
        rm .daria_api_pid
    fi
else
    echo "No PID file found. Trying to find and stop server process..."
    pkill -f "python.*run_interview_api\.py"
fi

# Double check if port is free
if lsof -i:5025 > /dev/null; then
    echo "Port 5025 is still in use. Force killing any remaining processes..."
    pkill -9 -f "python.*run_interview_api\.py"
fi

echo "Server stopped."
echo "===============================================" 