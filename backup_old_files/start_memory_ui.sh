#!/bin/bash
# Script to start the Memory Companion UI on port 5035

echo "===== Starting Memory Companion UI ====="

# Kill any existing memory UI processes
pkill -f "memory_companion_ui.py|integration_ui_fix.py" 2>/dev/null

# Wait a moment for processes to terminate
sleep 2

# Check which file exists and start the appropriate service
if [ -f "memory_companion_ui.py" ]; then
    echo "Starting memory_companion_ui.py on port 5035..."
    python memory_companion_ui.py --port 5035 &
    UI_PID=$!
elif [ -f "integration_ui_fix.py" ]; then
    echo "Starting integration_ui_fix.py on port 5035..."
    python integration_ui_fix.py --port 5035 &
    UI_PID=$!
else
    echo "ERROR: Neither memory_companion_ui.py nor integration_ui_fix.py found!"
    exit 1
fi

# Wait a moment for the server to start
sleep 3

# Check if service is running
if ps -p $UI_PID > /dev/null; then
    echo "✅ Memory Companion UI started successfully (PID: $UI_PID)"
    echo "Access the UI at: http://localhost:5035/"
else
    echo "❌ Failed to start Memory Companion UI"
    exit 1
fi

echo "===== Memory Companion UI Setup Complete =====" 