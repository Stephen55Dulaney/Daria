#!/bin/bash

echo "====== Starting All DARIA Required Services (Python 3.13 Compatible) ======"
echo "Base directory: $(pwd)"

# Stop any existing processes
echo "Stopping any existing processes..."
pkill -f "python.*run_interview_api.py" 2>/dev/null || true
pkill -f "python.*elevenlabs_tts.py" 2>/dev/null || true
pkill -f "python.*stt_service.py" 2>/dev/null || true
pkill -f "python.*memory_companion.py" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
lsof -ti:5015 | xargs kill -9 2>/dev/null || true
lsof -ti:5016 | xargs kill -9 2>/dev/null || true
lsof -ti:5030 | xargs kill -9 2>/dev/null || true
sleep 3

# Create necessary directories
echo "Setting up required directories..."
mkdir -p data/interviews/sessions
mkdir -p logs
mkdir -p static
mkdir -p templates

# Fix any syntax issues in discussion_service.py
echo "Fixing syntax error in discussion_service.py..."
python -c "
import re
with open('langchain_features/services/discussion_service.py', 'r') as f:
    content = f.read()
fixed_content = re.sub(r'elif \"conversation_history\" in session:[^\n]*\n[^\n]*\n[^\n]*\n\s+elif \"conversation_history\" in session:', 
                      'elif \"conversation_history\" in session:', 
                      content)
with open('langchain_features/services/discussion_service.py', 'w') as f:
    f.write(fixed_content)
print('Fixed discussion service syntax error')
"

# Make scripts executable
chmod +x fix_pydantic_forward_refs.py

# Start TTS service (port 5015)
echo "Starting TTS service on port 5015..."
if [ -f "elevenlabs_tts.py" ]; then
    python fix_pydantic_forward_refs.py elevenlabs_tts.py --port 5015 > logs/tts.log 2>&1 &
    echo "TTS service started with PID: $!"
else
    echo "TTS script not found. Unable to start TTS service."
fi

# Start STT service (port 5016)
echo "Starting STT service on port 5016..."
if [ -f "stt_service.py" ]; then
    python fix_pydantic_forward_refs.py stt_service.py --port 5016 > logs/stt.log 2>&1 &
    echo "STT service started with PID: $!"
else
    echo "STT script not found. Unable to start STT service."
fi

# Wait for audio services to initialize
echo "Waiting for audio services to initialize..."
sleep 5

# Start Memory Companion service (port 5030)
echo "Starting Memory Companion service on port 5030..."
if [ -f "memory_companion.py" ]; then
    python fix_pydantic_forward_refs.py memory_companion.py --port 5030 > logs/memory.log 2>&1 &
    echo "Memory Companion service started with PID: $!"
else
    echo "Memory Companion script not found. Using simplified memory service."
fi

# Wait for memory services to initialize
echo "Waiting for memory services to initialize..."
sleep 3

# Start main DARIA service
echo "Starting main DARIA API on port 5025 with LangChain enabled..."
python fix_pydantic_forward_refs.py run_interview_api.py --use-langchain --port 5025 > logs/daria.log 2>&1 &
DARIA_PID=$!
echo "DARIA started with PID: $DARIA_PID"

# Wait for all services to initialize
echo "Waiting for all services to initialize..."
sleep 10

# Check if DARIA is running
echo "Testing the health check endpoint..."
if curl -s "http://localhost:5025/api/health" > /dev/null; then
    echo "✅ DARIA is running successfully!"
    echo "   Main application: http://localhost:5025/"
    echo "   Debug interview flow: http://localhost:5025/static/debug_interview_flow.html?port=5025"
    echo "   Debug toolkit: http://localhost:5025/static/debug_toolkit.html"
else
    echo "❌ DARIA health check failed. Check logs/daria.log for more information."
fi

# Test other services
echo "Testing audio and memory services..."
TTS_RUNNING=false
STT_RUNNING=false
MEMORY_RUNNING=false

if curl -s "http://localhost:5015/health" > /dev/null; then
    echo "✅ TTS service is running successfully!"
    TTS_RUNNING=true
else
    echo "❓ TTS service not detected - may be using alternative configuration"
fi

if curl -s "http://localhost:5016/health" > /dev/null; then
    echo "✅ STT service is running successfully!"
    STT_RUNNING=true
else
    echo "❓ STT service not detected - may be using alternative configuration"
fi

if curl -s "http://localhost:5030/health" > /dev/null; then
    echo "✅ Memory Companion service is running successfully!"
    MEMORY_RUNNING=true
else
    echo "❓ Memory Companion service not detected - may be using alternative configuration"
fi

echo ""
echo "Services status:"
echo "DARIA API: Running (PID: $DARIA_PID)"
echo "TTS Service: ${TTS_RUNNING}"
echo "STT Service: ${STT_RUNNING}"
echo "Memory Service: ${MEMORY_RUNNING}"
echo ""
echo "Press Ctrl+C to stop all services when done."

# Keep the script running until user interrupts
wait $DARIA_PID 