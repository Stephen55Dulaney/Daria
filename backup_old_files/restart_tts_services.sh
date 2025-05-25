#!/bin/bash

echo "==============================================="
echo "     DARIA TTS/STT Services Launcher     "
echo "==============================================="

# Stop any existing TTS/STT processes
pkill -f "python.*mock_tts_service\.py"
pkill -f "python.*mock_stt_service\.py"

# Start TTS service on port 5015
echo "Starting TTS service..."
python mock_tts_service.py --port 5015 > tts_service.log 2>&1 &
echo $! > .tts_service_pid

# Wait a moment to ensure port is released
sleep 1

# Start STT service on port 5016
echo "Starting STT service..."
python mock_stt_service.py --port 5016 > stt_service.log 2>&1 &
echo $! > .stt_service_pid

echo "Services started. Check logs for details:"
echo "- tts_service.log"
echo "- stt_service.log"
echo
echo "Services should now be running at:"
echo "TTS Service: http://localhost:5015"
echo "STT Service: http://localhost:5016"
echo
echo "To stop the services, run: ./stop_server.sh"
echo "===============================================" 