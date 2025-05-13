#!/bin/bash

# Daria Interview Tool Restart Script
# This script gracefully stops any running instances and starts a fresh server

echo "============================================="
echo "     DARIA Interview Tool Restart Script     "
echo "============================================="

# Default settings
PORT=5025
USE_LANGCHAIN=""
DEBUG=""

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port=*) PORT="${1#*=}" ;;
        --langchain) USE_LANGCHAIN="--use-langchain" ;;
        --debug) DEBUG="--debug" ;;
        --help) 
            echo "Usage: ./restart_interview_api.sh [--port=PORT] [--langchain] [--debug]"
            echo ""
            echo "Options:"
            echo "  --port=PORT    Specify port number (default: 5025)"
            echo "  --langchain    Enable LangChain features"
            echo "  --debug        Run in debug mode"
            echo "  --help         Display this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Function to check if port is in use
check_port() {
    if lsof -i:$PORT > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to gracefully stop processes
stop_processes() {
    echo "Stopping any running interview API processes..."
    
    # First try SIGTERM for graceful shutdown
    pkill -f "python run_interview_api.py"
    
    # Wait a moment for processes to terminate
    sleep 2
    
    # Check if any processes are still running
    if pgrep -f "python run_interview_api.py" > /dev/null; then
        echo "Some processes didn't terminate gracefully, force killing..."
        pkill -9 -f "python run_interview_api.py"
        sleep 1
    fi
}

# Function to free up the port
free_port() {
    if check_port; then
        echo "Port $PORT is still in use. Finding and killing the process..."
        
        # Get PID of process using the port
        local PID=$(lsof -t -i:$PORT)
        
        if [ -n "$PID" ]; then
            echo "Process $PID is using port $PORT, attempting to kill it..."
            kill $PID
            sleep 2
            
            # If it's still running, force kill
            if ps -p $PID > /dev/null; then
                echo "Process $PID didn't terminate gracefully, force killing..."
                kill -9 $PID
                sleep 1
            fi
        else
            echo "Could not identify the process using port $PORT"
        fi
    fi
}

# Function to check if everything is clear
verify_clear() {
    if pgrep -f "python run_interview_api.py" > /dev/null; then
        echo "WARNING: Some interview API processes are still running"
        return 1
    fi
    
    if check_port; then
        echo "WARNING: Port $PORT is still in use"
        return 1
    fi
    
    return 0
}

# Main process
echo "Step 1: Stopping existing processes..."
stop_processes

echo "Step 2: Ensuring port $PORT is free..."
free_port

echo "Step 3: Verifying environment is clear..."
if ! verify_clear; then
    echo "WARNING: Could not fully clear the environment. Continuing anyway..."
fi

echo "Step 4: Starting DARIA Interview API on port $PORT..."
COMMAND="python run_interview_api.py --port $PORT $USE_LANGCHAIN $DEBUG"
echo "Executing: $COMMAND"

# Start the process
eval $COMMAND &

# Check if it started successfully
sleep 2
if check_port; then
    echo "Success! DARIA Interview API is now running on port $PORT"
    echo "Open http://127.0.0.1:$PORT in your browser"
    echo "Press Ctrl+C to stop the script"
else
    echo "ERROR: Failed to start the server on port $PORT"
    exit 1
fi

# Final message
echo "============================================="
echo "Server is running in the background"
echo "To stop the server, run: ./restart_interview_api.sh"
echo "=============================================" 