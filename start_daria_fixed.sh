#!/bin/bash

echo "====== Starting DARIA Interview Tool with All Fixes (Python 3.13 Compatible) ======"

# Set the base directory
BASEDIR=$(pwd)
echo "Base directory: $BASEDIR"

# Stop any existing processes
echo "Stopping any existing DARIA processes..."
pkill -f "python.*run_interview_api.py" 2>/dev/null || true
pkill -f "python.*elevenlabs_tts.py" 2>/dev/null || true
pkill -f "python.*stt_service.py" 2>/dev/null || true
pkill -f "python.*simple_stt_server.py" 2>/dev/null || true
pkill -f "python.*memory_companion" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
lsof -ti:5015 | xargs kill -9 2>/dev/null || true
lsof -ti:5016 | xargs kill -9 2>/dev/null || true
lsof -ti:5030 | xargs kill -9 2>/dev/null || true
lsof -ti:5035 | xargs kill -9 2>/dev/null || true
sleep 3

# Create required directories
echo "Setting up data directories..."
mkdir -p "$BASEDIR/data/interviews/sessions" 
mkdir -p "$BASEDIR/logs"

# Set the command based on Python version
PY_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version: $PY_VERSION"

if [[ $(echo "$PY_VERSION >= 3.13" | bc -l) -eq 1 ]]; then
    echo "Using Python 3.13+ compatibility patch..."
    
    # Test the patch first
    echo "Testing patch functionality..."
    python test_langchain_patch.py
    if [ $? -ne 0 ]; then
        echo "Patch test failed, but continuing anyway..."
    fi
    
    # Apply the patch when launching services
    PATCH_CMD="python fix_pydantic_forward_refs.py"
else
    echo "Using standard command for Python < 3.13..."
    PATCH_CMD="python"
fi

# Create a session file with the right structure
echo "Creating compatible test session file..."
cat > "$BASEDIR/data/interviews/sessions/test_session_123456.json" << EOL
{
  "id": "test_session_123456",
  "title": "Test Interview Session",
  "session_id": "test_session_123456",
  "status": "active", 
  "created_at": "2025-05-23T00:00:00.000000",
  "updated_at": "2025-05-23T00:00:00.000000",
  "character": "daria",
  "messages": [
    {
      "content": "Hello! I'm DARIA, your Digital Automated Research Interview Assistant. I'll be conducting this interview today. Could you please introduce yourself?",
      "role": "assistant",
      "message_id": "msg-test-001",
      "timestamp": "2025-05-23T00:01:00.000000"
    },
    {
      "content": "Hi! I'm a user researcher testing the DARIA tool.",
      "role": "user",
      "message_id": "msg-test-002",
      "timestamp": "2025-05-23T00:01:30.000000"
    },
    {
      "content": "Thank you for introducing yourself. Could you tell me about your experience with user research?",
      "role": "assistant",
      "message_id": "msg-test-003",
      "timestamp": "2025-05-23T00:02:00.000000"
    },
    {
      "content": "I've been conducting user research for about 5 years, primarily using interviews and surveys.",
      "role": "user",
      "message_id": "msg-test-004",
      "timestamp": "2025-05-23T00:02:30.000000"
    }
  ],
  "conversation_history": [
    {
      "content": "Hello! I'm DARIA, your Digital Automated Research Interview Assistant. I'll be conducting this interview today. Could you please introduce yourself?",
      "role": "assistant",
      "timestamp": "2025-05-23T00:01:00.000000"
    },
    {
      "content": "Hi! I'm a user researcher testing the DARIA tool.",
      "role": "user",
      "timestamp": "2025-05-23T00:01:30.000000"
    },
    {
      "content": "Thank you for introducing yourself. Could you tell me about your experience with user research?",
      "role": "assistant",
      "timestamp": "2025-05-23T00:02:00.000000"
    },
    {
      "content": "I've been conducting user research for about 5 years, primarily using interviews and surveys.",
      "role": "user",
      "timestamp": "2025-05-23T00:02:30.000000"
    }
  ],
  "options": {
    "analysis": true,
    "record_transcript": true,
    "use_tts": true
  }
}
EOL

# Create a discussion guide to reference the session
echo "Creating test discussion guide..."
cat > "$BASEDIR/data/interviews/test_guide_123456.json" << EOL
{
  "id": "test_guide_123456",
  "title": "Test Discussion Guide",
  "project": "DARIA Test Project",
  "status": "active",
  "created_at": "2025-05-23T00:00:00.000000",
  "updated_at": "2025-05-23T00:00:00.000000",
  "options": {
    "analysis": true,
    "record_transcript": true,
    "use_tts": true
  },
  "interview_type": "discovery_interview",
  "character_select": "daria",
  "custom_questions": [
    {"priority": "high", "text": "What is your experience with user research?"},
    {"priority": "medium", "text": "What tools do you currently use?"},
    {"priority": "low", "text": "How would you like to improve your workflow?"}
  ],
  "sessions": ["test_session_123456"]
}
EOL

# Start the TTS service if configured
if [ -f "elevenlabs_tts.py" ]; then
    echo "Starting TTS service..."
    $PATCH_CMD elevenlabs_tts.py --port 5015 > logs/tts_service.log 2>&1 &
    TTS_PID=$!
    echo "TTS service started with PID: $TTS_PID"
fi

# Start the STT service if configured
if [ -f "stt_service.py" ]; then
    echo "Starting STT service..."
    $PATCH_CMD stt_service.py --port 5016 > logs/stt_service.log 2>&1 &
    STT_PID=$!
    echo "STT service started with PID: $STT_PID"
elif [ -f "simple_stt_server.py" ]; then
    echo "Starting simple STT service..."
    $PATCH_CMD simple_stt_server.py --port 5016 > logs/simple_stt_service.log 2>&1 &
    STT_PID=$!
    echo "Simple STT service started with PID: $STT_PID"
fi

# Start the memory companion service if configured
if [ -f "memory_companion/app.py" ]; then
    echo "Starting memory companion service..."
    (cd memory_companion && $PATCH_CMD app.py --port 5030) > logs/memory_companion.log 2>&1 &
    MC_PID=$!
    echo "Memory companion service started with PID: $MC_PID"
fi

# Start the DARIA server
echo "Starting DARIA server with LangChain enabled..."
$PATCH_CMD run_interview_api.py --use-langchain --port 5025 > logs/daria.log 2>&1 &
DARIA_PID=$!
echo "DARIA started with PID: $DARIA_PID"
echo "View logs with: tail -f logs/daria.log"

# Wait for service to initialize
echo "Waiting for services to start..."
sleep 10

# Test if the server is running
echo "Testing the health check endpoint..."
HEALTH_CHECK=$(curl -s http://localhost:5025/api/health 2>/dev/null)
if [[ $HEALTH_CHECK == *"\"status\":\"ok\""* ]]; then
    echo "✅ DARIA API server is running successfully!"
    
    # Test guide and session endpoints
    echo "Testing guide endpoint..."
    GUIDE_CHECK=$(curl -s "http://localhost:5025/api/discussion_guide/test_guide_123456" 2>/dev/null)
    if [[ $GUIDE_CHECK == *"\"success\":true"* ]]; then
        echo "✅ Discussion guide endpoint is working"
    else
        echo "❌ Discussion guide endpoint failed"
    fi
    
    echo "Testing session endpoint..."
    SESSION_CHECK=$(curl -s "http://localhost:5025/api/session/test_session_123456/messages" 2>/dev/null)
    if [[ $SESSION_CHECK == *"\"success\":true"* ]]; then
        echo "✅ Session endpoint is working"
    else
        echo "❌ Session endpoint failed"
    fi
    
    # Test TTS service if started
    if [ ! -z "$TTS_PID" ]; then
        TTS_CHECK=$(curl -s "http://localhost:5015/health" 2>/dev/null)
        if [[ $TTS_CHECK == *"\"status\":\"ok\""* ]]; then
            echo "✅ TTS service is running"
        else
            echo "❌ TTS service check failed"
        fi
    fi
    
    # Test STT service if started
    if [ ! -z "$STT_PID" ]; then
        STT_CHECK=$(curl -s "http://localhost:5016/health" 2>/dev/null)
        if [[ $STT_CHECK == *"\"status\":\"ok\""* ]]; then
            echo "✅ STT service is running"
        else
            echo "❌ STT service check failed"
        fi
    fi
    
    # Test memory companion service if started
    if [ ! -z "$MC_PID" ]; then
        MC_CHECK=$(curl -s "http://localhost:5030/health" 2>/dev/null)
        if [[ $MC_CHECK == *"\"status\":\"ok\""* ]]; then
            echo "✅ Memory companion service is running"
        else
            echo "❌ Memory companion service check failed"
        fi
    fi
    
    echo ""
    echo "📱 Access the main application at: http://localhost:5025/"
    echo "🧪 Access the interview debug page at: http://localhost:5025/static/debug_interview_flow.html?port=5025"
    echo "🔍 Access the character test tool at: http://localhost:5025/static/debug_character_test.html"
    
else
    echo "❌ DARIA health check failed. Check logs for errors."
    echo "Last 30 lines of log:"
    tail -30 logs/daria.log
fi

echo ""
echo "Press Ctrl+C to stop all DARIA services when done." 