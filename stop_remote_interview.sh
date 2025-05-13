#!/bin/bash

# DARIA Remote Interview System Stop Script
# This script stops all services started by start_remote_interview.sh

echo "===================================================================="
echo "STOPPING DARIA REMOTE INTERVIEW SYSTEM"
echo "===================================================================="

# Check if we have PIDs file
if [ -f "logs/service_pids.txt" ]; then
    # Read PIDs from file
    read AUDIO_PID APP_PID < logs/service_pids.txt
    
    # Stop main application
    if ps -p $APP_PID > /dev/null; then
        echo "Stopping main application (PID: $APP_PID)..."
        kill $APP_PID
        sleep 1
        
        # Force kill if still running
        if ps -p $APP_PID > /dev/null; then
            echo "Forcing termination of main application..."
            kill -9 $APP_PID
        fi
        
        echo "Main application stopped."
    else
        echo "Main application is not running."
    fi
    
    # Stop audio service
    if ps -p $AUDIO_PID > /dev/null; then
        echo "Stopping audio service (PID: $AUDIO_PID)..."
        kill $AUDIO_PID
        sleep 1
        
        # Force kill if still running
        if ps -p $AUDIO_PID > /dev/null; then
            echo "Forcing termination of audio service..."
            kill -9 $AUDIO_PID
        fi
        
        echo "Audio service stopped."
    else
        echo "Audio service is not running."
    fi
    
    # Remove PIDs file
    rm logs/service_pids.txt
else
    echo "PID file not found. Attempting to find and kill services by port and name..."
    
    # Kill process on port 5010 (main application)
    if lsof -i :5010 > /dev/null; then
        echo "Stopping process on port 5010..."
        lsof -ti :5010 | xargs kill -9
        echo "Process on port 5010 stopped."
    else
        echo "No process found on port 5010."
    fi
    
    # Kill process on port 5007 (audio service)
    if lsof -i :5007 > /dev/null; then
        echo "Stopping process on port 5007..."
        lsof -ti :5007 | xargs kill -9
        echo "Process on port 5007 stopped."
    else
        echo "No process found on port 5007."
    fi
    
    # Kill by name as a fallback
    pkill -f "run_langchain_direct_fixed.py" 2>/dev/null
    pkill -f "simple_tts_test.py" 2>/dev/null
fi

echo "===================================================================="
echo "All services stopped."
echo "====================================================================" 