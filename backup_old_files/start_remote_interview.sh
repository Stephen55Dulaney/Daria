#!/bin/bash

# DARIA Remote Interview System Starter Script
# This script starts all necessary services for the remote interview system

echo "===================================================================="
echo "DARIA REMOTE INTERVIEW SYSTEM"
echo "===================================================================="

# Create necessary directories
mkdir -p interviews
mkdir -p logs
mkdir -p flask_sessions

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
    fi
    return 0
}

# Function to check if a service is running
is_service_running() {
    local name=$1
    if ps aux | grep -v grep | grep "$name" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check Python version
PYTHON="python3"
if ! command -v $PYTHON &> /dev/null; then
    PYTHON="python"
    if ! command -v $PYTHON &> /dev/null; then
        echo "Python not found. Please install Python 3."
        exit 1
    fi
fi

# Set up environment variables
export PYTHONPATH="$(pwd):$PYTHONPATH"
export FLASK_ENV=development
export FLASK_DEBUG=1
export SKIP_EVENTLET=1  # For Python 3.13 compatibility

# Check if services are already running
if is_service_running "simple_tts_test.py"; then
    echo "Audio service is already running."
    AUDIO_RUNNING=true
else
    AUDIO_RUNNING=false
fi

if is_service_running "run_langchain_direct_fixed.py"; then
    echo "Main application is already running."
    APP_RUNNING=true
else
    APP_RUNNING=false
fi

# If both services are running, just print info and exit
if $AUDIO_RUNNING && $APP_RUNNING; then
    echo "All services are already running."
    echo "Main application: http://localhost:5010"
    echo "Audio service: http://localhost:5007"
    echo ""
    echo "To stop services, run:"
    echo "./stop_remote_interview.sh"
    exit 0
fi

# Kill any processes using our ports
check_port 5007 || exit 1  # Audio service port
check_port 5010 || exit 1  # Main application port

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the ElevenLabs Audio Tools service if not running
if ! $AUDIO_RUNNING; then
    echo "Starting ElevenLabs Audio Tools service..."
    cd audio_tools
    $PYTHON simple_tts_test.py --port 5007 > ../logs/audio_service.log 2>&1 &
    AUDIO_PID=$!
    cd ..

    # Check if the audio service started successfully
    sleep 2
    if ! ps -p $AUDIO_PID > /dev/null; then
        echo "Failed to start audio service. Check logs/audio_service.log for details."
        exit 1
    fi

    echo "Audio service started on port 5007 (PID: $AUDIO_PID)"
else
    AUDIO_PID=$(ps aux | grep -v grep | grep "simple_tts_test.py" | awk '{print $2}')
    echo "Using existing audio service (PID: $AUDIO_PID)"
fi

# Start the main application if not running
if ! $APP_RUNNING; then
    echo "Starting main application..."
    $PYTHON run_langchain_direct_fixed.py --port 5010 > logs/main_app.log 2>&1 &
    APP_PID=$!

    # Check if the main application started successfully
    sleep 2
    if ! ps -p $APP_PID > /dev/null; then
        echo "Failed to start main application. Check logs/main_app.log for details."
        kill $AUDIO_PID
        exit 1
    fi

    echo "Main application started on port 5010 (PID: $APP_PID)"
else
    APP_PID=$(ps aux | grep -v grep | grep "run_langchain_direct_fixed.py" | awk '{print $2}')
    echo "Using existing main application (PID: $APP_PID)"
fi

# Save PIDs to file for stopping later
echo "$AUDIO_PID $APP_PID" > logs/service_pids.txt

echo "===================================================================="
echo "All services started successfully!"
echo "Main application: http://localhost:5010"
echo "Audio service: http://localhost:5007"
echo ""
echo "Services are running in the background. To stop them, run:"
echo "./stop_remote_interview.sh"
echo ""
echo "To view logs:"
echo "- Main application: tail -f logs/main_app.log"
echo "- Audio service: tail -f logs/audio_service.log"
echo "====================================================================" 