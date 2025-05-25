#!/bin/bash
# Start all Daria Interview Tool services (ElevenLabs version)
# Python 3.11+ venv must be activated before running this script

set -e

# Print header
echo "====== Starting All DARIA Services (ElevenLabs Edition) ======"

# Stop any existing services
pkill -f "python run_interview_api.py" 2>/dev/null || true
pkill -f "python elevenlabs_tts.py" 2>/dev/null || true
pkill -f "python mock_stt_service.py" 2>/dev/null || true
pkill -f "python mock_memory_service.py" 2>/dev/null || true
pkill -f "python memory_companion_ui.py" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
lsof -ti:5015 | xargs kill -9 2>/dev/null || true
lsof -ti:5016 | xargs kill -9 2>/dev/null || true
lsof -ti:5030 | xargs kill -9 2>/dev/null || true
lsof -ti:5035 | xargs kill -9 2>/dev/null || true
sleep 2

# Start ElevenLabs TTS service (port 5015)
echo "Starting ElevenLabs TTS service on port 5015..."
python elevenlabs_tts.py --port 5015 > logs/tts_service.log 2>&1 &
TTS_PID=$!

# Start STT service (mock, port 5016)
echo "Starting STT service on port 5016..."
python mock_stt_service.py --port 5016 > logs/stt_service.log 2>&1 &
STT_PID=$!

# Start Memory Companion service (mock, port 5030)
echo "Starting Memory Companion service on port 5030..."
python mock_memory_service.py --port 5030 > logs/memory_companion.log 2>&1 &
MEMORY_PID=$!

# Start main API server (port 5025)
echo "Starting DARIA API server on port 5025..."
python run_interview_api.py --use-langchain --port 5025 > logs/api_server.log 2>&1 &
API_PID=$!

# Start Memory Companion UI (port 5035)
echo "Starting Memory Companion UI on port 5035..."
python memory_companion_ui.py --port 5035 > logs/memory_ui.log 2>&1 &
MEMORY_UI_PID=$!

# Wait for services to initialize
sleep 8

echo "\nService status:"
echo "  ElevenLabs TTS (5015):   PID $TTS_PID"
echo "  STT Service (5016):       PID $STT_PID"
echo "  Memory Service (5030):    PID $MEMORY_PID"
echo "  API Server (5025):        PID $API_PID"
echo "  Memory UI (5035):         PID $MEMORY_UI_PID"
echo "\nCheck logs/ for output."
echo "\nAccess the Debug Toolkit at: http://localhost:5025/static/debug_toolkit.html"
echo "Access the Memory Companion UI at: http://localhost:5035/"
echo "\nPress Ctrl+C to stop all services when done."

# Wait for main API server to exit
wait $API_PID 