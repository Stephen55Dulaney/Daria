#!/bin/bash

# DARIA Remote Interview System RC1 Stop Script
# This script stops all services started by start_rc1.sh

echo "===================================================================="
echo "STOPPING DARIA REMOTE INTERVIEW SYSTEM - RELEASE CANDIDATE 1"
echo "===================================================================="

LOGS_DIR="./logs"
PID_FILE="$LOGS_DIR/rc1_pids.txt"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found at $PID_FILE"
    echo "Attempting to find and kill services on standard ports..."
    
    # Try to kill processes by ports
    if lsof -ti :5007 > /dev/null; then
        echo "Killing process on port 5007..."
        lsof -ti :5007 | xargs kill -9
    else
        echo "No process found on port 5007"
    fi
    
    if lsof -ti :5010 > /dev/null; then
        echo "Killing process on port 5010..."
        lsof -ti :5010 | xargs kill -9
    else
        echo "No process found on port 5010"
    fi
else
    # Read PIDs from file
    PIDS=$(cat "$PID_FILE")
    
    if [ -z "$PIDS" ]; then
        echo "No PIDs found in $PID_FILE"
    else
        echo "Stopping services with PIDs: $PIDS"
        kill $PIDS 2>/dev/null || echo "Failed to kill all processes with SIGTERM, trying SIGKILL..."
        
        # Give processes a moment to terminate gracefully
        sleep 2
        
        # Check if processes are still running and force kill if necessary
        for PID in $PIDS; do
            if ps -p $PID > /dev/null; then
                echo "Process $PID still running, forcing termination..."
                kill -9 $PID 2>/dev/null
            fi
        done
    fi
    
    # Remove PID file
    rm "$PID_FILE"
fi

# Double-check that ports are cleared
echo "Verifying ports are free..."

if lsof -i :5007 > /dev/null; then
    echo "WARNING: Port 5007 is still in use. You may need to manually terminate the process."
else
    echo "Port 5007 is free."
fi

if lsof -i :5010 > /dev/null; then
    echo "WARNING: Port 5010 is still in use. You may need to manually terminate the process."
else
    echo "Port 5010 is free."
fi

echo "===================================================================="
echo "SERVICES STOPPED"
echo "====================================================================" 