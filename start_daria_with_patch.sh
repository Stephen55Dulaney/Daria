#!/bin/bash

echo "====== Starting DARIA Interview Tool with Patch for Python 3.13 ======"

# Set the base directory
BASEDIR=$(pwd)
echo "Base directory: $BASEDIR"

# Stop any existing processes
echo "Stopping any existing DARIA processes..."
pkill -f "python.*run_interview_api.py" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
sleep 2

# Create required directories
echo "Setting up data directories..."
mkdir -p "$BASEDIR/data/interviews"
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
        echo "Patch test failed. Creating fixed session file to ensure compatibility..."
    fi
    
    # Apply the patch when launching the server
    PATCH_CMD="python fix_pydantic_forward_refs.py"
else
    echo "Using standard command for Python < 3.13..."
    PATCH_CMD="python"
fi

# Create a session file with the right structure
echo "Creating compatible test session file..."
cat > "$BASEDIR/data/interviews/test_session_123456.json" << EOL
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

# Start the DARIA server
echo "Starting DARIA server with LangChain enabled..."
$PATCH_CMD run_interview_api.py --use-langchain --port 5025 > logs/daria.log 2>&1 &
DARIA_PID=$!
echo "DARIA started with PID: $DARIA_PID"
echo "View logs with: tail -f logs/daria.log"

# Wait for service to initialize
echo "Waiting for service to start..."
sleep 8

# Test if the server is running
echo "Testing the health check endpoint..."
HEALTH_CHECK=$(curl -s http://localhost:5025/api/health 2>/dev/null)
if [[ $HEALTH_CHECK == *"\"status\":\"ok\""* ]]; then
  echo "✅ DARIA is running successfully!"
  echo "   Access the main application at: http://localhost:5025/"
  echo "   Access the interview debug page at: http://localhost:5025/static/debug_interview_flow.html?port=5025"
else
  echo "❌ DARIA health check failed. Check logs for errors."
  echo "Last 20 lines of log:"
  tail -20 logs/daria.log
fi

echo ""
echo "Press Ctrl+C to stop the service when done." 