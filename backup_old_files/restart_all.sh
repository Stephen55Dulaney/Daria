#!/bin/bash

echo "=== DARIA Services Restart Script ==="
echo "Stopping all Python processes..."
pkill -f "python" || true

echo "Ensuring ports 5007 and 5010 are free..."
lsof -i :5007 | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null || true
lsof -i :5010 | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null || true

# Wait for everything to properly terminate
sleep 2

echo "Starting Audio Service..."
cd audio_tools
python simple_tts_test.py > audio_service.log 2>&1 &
AUDIO_PID=$!
echo "Audio Service started with PID: $AUDIO_PID"
cd ..

# Wait for audio service to initialize
sleep 2

echo "Starting Main Application..."
python run_langchain_direct_fixed.py > main_app.log 2>&1 &
APP_PID=$!
echo "Main Application started with PID: $APP_PID"

# Give the main app time to start
sleep 2

# Check if services are running
echo "Verifying services..."
if curl -s http://127.0.0.1:5007 > /dev/null; then
    echo "✅ Audio Service is running"
else
    echo "❌ Audio Service failed to start. Check audio_service.log for details."
fi

if curl -s http://127.0.0.1:5010 > /dev/null; then
    echo "✅ Main Application is running"
else
    echo "❌ Main Application failed to start. Check main_app.log for details."
fi

echo "=== Services Started ==="
echo "Audio Service: http://127.0.0.1:5007"
echo "Main Application: http://127.0.0.1:5010"
echo "Dashboard: http://127.0.0.1:5010/dashboard"
echo "Interview Setup: http://127.0.0.1:5010/interview_setup"
echo ""
echo "Check main_app.log and audio_service.log for detailed logs" 