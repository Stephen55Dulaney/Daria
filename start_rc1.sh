#!/bin/bash

# DARIA Remote Interview System RC1 Starter Script
# This script starts all services required for the Remote Interview System

echo "===================================================================="
echo "DARIA REMOTE INTERVIEW SYSTEM - RELEASE CANDIDATE 1"
echo "===================================================================="

# Function to check if a port is in use
check_port() {
    if lsof -i :$1 > /dev/null ; then
        echo "Port $1 is already in use. Attempting to kill the process..."
        lsof -ti :$1 | xargs kill -9
        sleep 1
        if lsof -i :$1 > /dev/null ; then
            echo "Failed to free port $1. Please manually terminate the process."
            return 1
        else
            echo "Successfully freed port $1."
            return 0
        fi
    else
        return 0
    fi
}

# Check required ports
check_port 5007 || exit 1  # Audio service port
check_port 5010 || exit 1  # Main application port

# Directory setup
AUDIO_DIR="./audio_tools"
LOGS_DIR="./logs"

# Create logs directory if it doesn't exist
mkdir -p $LOGS_DIR

# Check for ElevenLabs API key
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "WARNING: ELEVENLABS_API_KEY environment variable is not set."
    echo "Voice features may not work correctly without an API key."
    read -p "Do you want to enter an API key now? (y/n): " answer
    if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
        read -p "Enter your ElevenLabs API key: " api_key
        export ELEVENLABS_API_KEY="$api_key"
        echo "API key set for this session."
    else
        echo "Continuing without API key..."
    fi
fi

# Start ElevenLabs Audio service
echo "Starting ElevenLabs Audio Tools service on port 5007..."
cd $AUDIO_DIR
python simple_tts_test.py --port 5007 > ../$LOGS_DIR/audio_service.log 2>&1 &
AUDIO_PID=$!
cd ..

# Wait for audio service to be ready
sleep 2
if ! ps -p $AUDIO_PID > /dev/null; then
    echo "Error: Failed to start Audio service. Check logs at $LOGS_DIR/audio_service.log"
    exit 1
fi
echo "Audio service started with PID: $AUDIO_PID"

# Start main application
echo "Starting main application on port 5010..."
python run_langchain_direct.py --port 5010 > $LOGS_DIR/application.log 2>&1 &
APP_PID=$!

# Wait for main application to be ready
sleep 2
if ! ps -p $APP_PID > /dev/null; then
    echo "Error: Failed to start main application. Check logs at $LOGS_DIR/application.log"
    kill $AUDIO_PID
    exit 1
fi
echo "Main application started with PID: $APP_PID"

echo "===================================================================="
echo "SERVICES STARTED SUCCESSFULLY"
echo "===================================================================="
echo "Audio Service: http://127.0.0.1:5007"
echo "Main Application: http://127.0.0.1:5010"
echo "Dashboard: http://127.0.0.1:5010/dashboard"
echo "Interview Setup: http://127.0.0.1:5010/interview_setup"
echo "Interview Test: http://127.0.0.1:5010/interview_test"
echo ""
echo "Log files:"
echo "- Audio Service: $LOGS_DIR/audio_service.log"
echo "- Main Application: $LOGS_DIR/application.log"
echo ""
echo "To stop services, run: kill $AUDIO_PID $APP_PID"
echo "===================================================================="

# Save PIDs for easy killing later
echo "$AUDIO_PID $APP_PID" > $LOGS_DIR/rc1_pids.txt
echo "Service PIDs saved to $LOGS_DIR/rc1_pids.txt" 