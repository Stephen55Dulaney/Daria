#!/bin/bash
# Restart services script
# This script kills existing Python processes and starts the audio service and main application

echo "=== DARIA Services Restart ==="
echo "Stopping all running Python processes..."

# Kill all running Python processes
killall -9 python python3 2>/dev/null

# Wait for processes to fully terminate
sleep 2

echo "Starting audio service..."
# Start the audio service in the background
cd audio_tools
python simple_tts_test.py > audio_service.log 2>&1 &

# Store the PID of the audio service
AUDIO_PID=$!
echo "Audio service started with PID: $AUDIO_PID"

# Go back to the main directory
cd ..

echo "Starting main application service..."
# Start the main application with the fixed direct implementation
python run_langchain_direct_fixed.py > app_service.log 2>&1 &

# Store the PID of the main application
APP_PID=$!
echo "Main application started with PID: $APP_PID"

echo "=== Services Started ==="
echo "Audio Service: http://127.0.0.1:5007"
echo "Main Application: http://127.0.0.1:5000"
echo ""
echo "To stop services, run: killall -9 python python3"
echo "================================="

# Save the PIDs to a file for later use if needed
echo "$AUDIO_PID" > audio_service.pid
echo "$APP_PID" > app_service.pid 