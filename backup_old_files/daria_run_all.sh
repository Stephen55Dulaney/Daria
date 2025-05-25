#!/bin/bash
# daria_run_all.sh - Script to start all Daria services in the proper order

echo "===== DARIA INTERVIEW TOOL STARTUP SCRIPT ====="
echo "Starting all required services..."

# Kill any existing processes
echo "Cleaning up any existing processes..."
pkill -f "mock_tts|debug_memory|py313_patch"
sleep 2

# Start mock TTS service first
echo "Starting Mock TTS Service on port 5015..."
python mock_tts_service.py --port 5015 &
TTS_PID=$!
sleep 2

# Check if TTS service is running
if curl -s http://localhost:5015/health > /dev/null; then
    echo "✅ TTS Service started successfully (PID: $TTS_PID)"
else
    echo "❌ Failed to start TTS Service"
    exit 1
fi

# Start memory companion service
echo "Starting Memory Companion Service on port 5030..."
python debug_memory_api.py --port 5030 &
MEMORY_PID=$!
sleep 2

# Check if memory companion service is running
if curl -s http://localhost:5030/api/memory_companion/test > /dev/null; then
    echo "✅ Memory Companion Service started successfully (PID: $MEMORY_PID)"
else
    echo "❌ Failed to start Memory Companion Service"
    exit 1
fi

# Start main API service with LangChain enabled
echo "Starting DARIA Interview API on port 5025..."
python py313_patch.py run_interview_api.py --port 5025 --use-langchain &
API_PID=$!
sleep 3

# Check if main API is running
if curl -s http://localhost:5025/api/health > /dev/null; then
    echo "✅ DARIA Interview API started successfully (PID: $API_PID)"
else
    echo "❌ Failed to start DARIA Interview API"
    # Try starting without LangChain as fallback
    echo "Attempting to start without LangChain..."
    python py313_patch.py run_interview_api.py --port 5025 --no-langchain &
    API_PID=$!
    sleep 3
    
    if curl -s http://localhost:5025/api/health > /dev/null; then
        echo "✅ DARIA Interview API started successfully without LangChain (PID: $API_PID)"
    else
        echo "❌ Failed to start DARIA Interview API"
        exit 1
    fi
fi

echo ""
echo "===== ALL SERVICES STARTED SUCCESSFULLY ====="
echo "TTS Service: http://localhost:5015"
echo "Memory Companion: http://localhost:5030"
echo "DARIA Interview API: http://localhost:5025"
echo ""
echo "Open http://127.0.0.1:5025/static/debug_interview_flow.html?port=5025 to access the debug interview flow."
echo "Open http://127.0.0.1:5030/static/daria_memory_companion_tts.html to access the memory companion with TTS." 