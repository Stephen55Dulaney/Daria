#!/bin/bash
# Script to start all Daria services in the correct order

echo "===== DARIA COMPLETE SERVICES STARTUP SCRIPT ====="
echo "Starting all Daria services..."

# Kill any existing processes
echo "Cleaning up any existing processes..."
pkill -f "mock_tts|debug_memory|memory_companion_ui|integration_ui_fix|py313_patch"
sleep 2

# Start Mock TTS service
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
echo "Starting Memory Companion API on port 5030..."
python debug_memory_api.py --port 5030 &
MEMORY_PID=$!
sleep 2

# Check if memory companion service is running
if curl -s http://localhost:5030/api/memory_companion/test > /dev/null; then
    echo "✅ Memory Companion API started successfully (PID: $MEMORY_PID)"
else
    echo "❌ Failed to start Memory Companion API"
    exit 1
fi

# Start Memory Companion UI
echo "Starting Memory Companion UI on port 5035..."
if [ -f "memory_companion_ui.py" ]; then
    python memory_companion_ui.py --port 5035 &
    UI_PID=$!
elif [ -f "integration_ui_fix.py" ]; then
    python integration_ui_fix.py --port 5035 &
    UI_PID=$!
else
    echo "⚠️ Warning: Memory Companion UI files not found, skipping this service"
    UI_PID=0
fi

if [ $UI_PID -ne 0 ] && curl -s http://localhost:5035/ > /dev/null; then
    echo "✅ Memory Companion UI started successfully (PID: $UI_PID)"
else
    if [ $UI_PID -ne 0 ]; then
        echo "❌ Failed to start Memory Companion UI"
    fi
fi

# Now start the main interview API with LangChain enabled
echo "Starting Main Interview API on port 5025..."
python py313_patch.py run_interview_api.py --port 5025 --no-langchain &
API_PID=$!
sleep 3

# Check if main API is running
if curl -s http://localhost:5025/api/health > /dev/null; then
    echo "✅ Main Interview API started successfully (PID: $API_PID)"
else
    echo "❌ Failed to start Main Interview API"
    exit 1
fi

# Check all services are running together
echo "Verifying all services..."
if curl -s http://localhost:5025/api/check_services > /dev/null; then
    echo "✅ All services are communicating properly"
else
    echo "⚠️ Service communication check failed"
fi

echo ""
echo "===== DARIA SERVICES STARTUP COMPLETE ====="
echo "TTS Service: http://localhost:5015/health"
echo "Memory API: http://localhost:5030/api/memory_companion/test"
echo "Memory UI: http://localhost:5035/"
echo "Main API: http://localhost:5025/api/health"
echo "Interview UI: http://localhost:5025/static/debug_interview_flow.html?port=5025"
echo ""
echo "To stop all services: pkill -f \"mock_tts|debug_memory|memory_companion_ui|integration_ui_fix|py313_patch\"" 