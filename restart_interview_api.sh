#!/bin/bash

echo "Gracefully stopping any running interview API processes..."

# Find and kill any running Python processes that match our interview API
pkill -f "python run_interview_api.py"

# Wait a moment to ensure processes have terminated
sleep 2

# Check if any processes are still running and force kill if needed
if pgrep -f "python run_interview_api.py" > /dev/null; then
    echo "Some processes didn't terminate gracefully, force killing..."
    pkill -9 -f "python run_interview_api.py"
    sleep 1
fi

# Check if port 5025 is still in use
if lsof -i:5025 > /dev/null; then
    echo "Port 5025 is still in use. Finding and killing the process..."
    lsof -i:5025 -t | xargs kill -9
    sleep 1
fi

echo "Starting DARIA Interview API..."
python run_interview_api.py --use-langchain --port 5025 &

echo "DARIA Interview API started in background."
echo "To view logs, run: tail -f *.log" 