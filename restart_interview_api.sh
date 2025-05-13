#!/bin/bash

# Daria Interview Tool Restart Script
# This script gracefully stops any running instances and starts a fresh server

echo "============================================="
echo "     DARIA Interview Tool Restart Script     "
echo "============================================="

# Save the current directory
CURRENT_DIR=$(pwd)

# Default port
PORT=5025

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port=*) PORT="${1#*=}" ;;
        --langchain) USE_LANGCHAIN="--use-langchain" ;;
        --help) 
            echo "Usage: ./restart_interview_api.sh [--port=PORT] [--langchain]"
            echo ""
            echo "Options:"
            echo "  --port=PORT    Specify port number (default: 5025)"
            echo "  --langchain    Enable LangChain features"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "Checking for running interview API processes..."

# Get PID of any running interview API process
PIDS=$(pgrep -f "python run_interview_api.py")

if [ -n "$PIDS" ]; then
    echo "Found running processes: $PIDS"
    echo "Stopping processes..."
    
    # Gracefully terminate processes
    for PID in $PIDS; do
        echo "Sending SIGTERM to process $PID"
        kill $PID
    done
    
    # Wait up to 5 seconds for processes to terminate
    for i in {1..5}; do
        if pgrep -f "python run_interview_api.py" > /dev/null; then
            echo "Waiting for processes to terminate ($i/5)..."
            sleep 1
        else
            echo "All processes terminated successfully."
            break
        fi
        
        # If we've waited 5 seconds and processes are still running, force kill
        if [ $i -eq 5 ] && pgrep -f "python run_interview_api.py" > /dev/null; then
            echo "Processes still running after 5 seconds. Force killing..."
            pkill -9 -f "python run_interview_api.py"
            sleep 1
        fi
    done
else
    echo "No running interview API processes found."
fi

# Check if the specified port is in use
if lsof -i:$PORT -t &> /dev/null; then
    echo "Port $PORT is in use. Attempting to free it..."
    PORT_PID=$(lsof -i:$PORT -t)
    
    # Try to kill the process using the port
    if [ -n "$PORT_PID" ]; then
        echo "Sending SIGTERM to process using port $PORT (PID: $PORT_PID)"
        kill $PORT_PID
        
        # Wait for the port to become available
        for i in {1..5}; do
            if lsof -i:$PORT -t &> /dev/null; then
                echo "Waiting for port $PORT to become available ($i/5)..."
                sleep 1
            else
                echo "Port $PORT is now available."
                break
            fi
            
            # If we've waited 5 seconds and port is still in use, force kill
            if [ $i -eq 5 ] && lsof -i:$PORT -t &> /dev/null; then
                echo "Port $PORT still in use after 5 seconds. Force killing..."
                PORT_PID=$(lsof -i:$PORT -t)
                if [ -n "$PORT_PID" ]; then
                    kill -9 $PORT_PID
                    sleep 1
                fi
            fi
        done
    fi
    
    # Final check if port is available
    if lsof -i:$PORT -t &> /dev/null; then
        echo "ERROR: Port $PORT is still in use. Cannot start server."
        echo "Please manually free the port or specify a different one with --port=XXXX"
        exit 1
    fi
fi

# Make sure we're in the correct directory
if [ -f "run_interview_api.py" ]; then
    echo "Found run_interview_api.py in current directory."
else
    echo "run_interview_api.py not found in current directory."
    echo "Checking if this script is in the Daria Interview Tool directory..."
    
    # Try to find the directory containing run_interview_api.py
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/run_interview_api.py" ]; then
        echo "Found run_interview_api.py in script directory."
        cd "$SCRIPT_DIR"
    else
        echo "ERROR: Could not find run_interview_api.py"
        echo "Please run this script from the Daria Interview Tool directory."
        exit 1
    fi
fi

# Start the server
echo ""
echo "Starting DARIA Interview API on port $PORT"
if [ -n "$USE_LANGCHAIN" ]; then
    echo "LangChain features: ENABLED"
    python run_interview_api.py --use-langchain --port $PORT &
else
    echo "LangChain features: DISABLED"
    python run_interview_api.py --port $PORT &
fi

echo "Server started in background with PID $!"
echo "Monitor interviews at: http://127.0.0.1:$PORT/monitor_interview"
echo "Health check endpoint: http://127.0.0.1:$PORT/api/health"

echo ""
echo "To stop the server: pkill -f 'python run_interview_api.py'"
echo "To restart: ./restart_interview_api.sh"
echo ""

# Return to original directory
cd "$CURRENT_DIR" 