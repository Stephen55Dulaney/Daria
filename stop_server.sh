#!/bin/bash

# Stop the Daria Interview Tool server
echo "Stopping Daria Interview Tool..."

# Check for stored PID
if [ -f .daria_api_pid ]; then
    PID=$(cat .daria_api_pid)
    if ps -p $PID > /dev/null; then
        echo "Killing Daria process with PID: $PID"
        kill $PID
        rm .daria_api_pid
    else
        echo "No running process found with PID: $PID"
        rm .daria_api_pid
    fi
else
    # Try to find by port
    PID=$(lsof -i :5025 -t)
    if [ ! -z "$PID" ]; then
        echo "Found Daria process on port 5025 with PID: $PID"
        echo "Stopping process..."
        kill $PID
    else
        echo "No Daria process found running on port 5025"
    fi
fi

echo "Done" 