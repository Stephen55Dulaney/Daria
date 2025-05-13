#!/bin/bash
# DARIA Interview Tool Audio Testing Setup Script

echo "===================================================="
echo "  DARIA INTERVIEW SYSTEM - AUDIO TESTING SETUP      "
echo "===================================================="

# Stop any existing services first
./stop_daria.sh

# Set environment variables
if [ -z "$ELEVENLABS_API_KEY" ]; then
  echo "No ELEVENLABS_API_KEY found, using demo_key for testing"
  export ELEVENLABS_API_KEY="demo_key"
fi

# Start services in background
echo "Starting main API server on port 5010..."
python run_interview_api.py --port 5010 > main_app.log 2>&1 &
MAIN_PID=$!
echo "  PID: $MAIN_PID"
sleep 2

echo "Starting TTS service on port 5015..."
python audio_tools/elevenlabs_tts.py --port 5015 > tts_service.log 2>&1 &
TTS_PID=$!
echo "  PID: $TTS_PID"
sleep 1

echo "Starting STT service on port 5016..."
python audio_tools/mock_stt.py --port 5016 > stt_service.log 2>&1 &
STT_PID=$!
echo "  PID: $STT_PID"
sleep 1

echo "Starting web server on port 8889..."
python simple_web_server.py --port 8889 > web_server.log 2>&1 &
WEB_PID=$!
echo "  PID: $WEB_PID"
sleep 1

echo "===================================================="
echo "All services started successfully!"
echo ""
echo "Audio Test Page: http://localhost:8889/audio_test"
echo "Main API: http://localhost:5010"
echo "TTS Service: http://localhost:5015"
echo "STT Service: http://localhost:5016"
echo ""
echo "Log files: main_app.log, tts_service.log, stt_service.log, web_server.log"
echo "===================================================="

# Wait for user to press a key
read -n 1 -s -r -p "Press any key to view logs (or Ctrl+C to exit)..."

# Show logs
tail -f main_app.log tts_service.log stt_service.log web_server.log 