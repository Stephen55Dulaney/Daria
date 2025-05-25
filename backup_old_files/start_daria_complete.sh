#!/bin/bash

echo "====== Starting DARIA Interview Tool with All Fixes ======"

# Set the base directory
BASEDIR=$(pwd)
echo "Base directory: $BASEDIR"

# Stop any existing processes
echo "Stopping any existing DARIA processes..."
pkill -f "python.*run_interview_api.py" 2>/dev/null || true
pkill -f "python.*elevenlabs_tts.py" 2>/dev/null || true
pkill -f "python.*stt_service.py" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
sleep 3

# Make all scripts executable
chmod +x fix_directory_structure.py
chmod +x fix_interview_sessions_dir.py
chmod +x fix_file_path_direct.py
chmod +x fix_json_datetime.py
if [ -f "fix_pydantic_forward_refs.py" ]; then
    chmod +x fix_pydantic_forward_refs.py
fi

# First, run the directory structure fix
echo "Setting up data directories..."
python fix_directory_structure.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to fix directory structure. Check the error logs."
    exit 1
fi

echo "✅ Directory structure fixed successfully"

# Then run the INTERVIEW_SESSIONS_DIR configuration fix
echo "Fixing INTERVIEW_SESSIONS_DIR configuration..."
python fix_interview_sessions_dir.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to fix INTERVIEW_SESSIONS_DIR configuration. Check the error logs."
    exit 1
fi

echo "✅ INTERVIEW_SESSIONS_DIR configuration fixed successfully"

# Fix the file_path in the upload_transcript function
echo "Fixing file_path in upload_transcript function..."
python fix_file_path_direct.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to fix file_path. Check the error logs."
    exit 1
fi

echo "✅ file_path fix applied successfully"

# Fix the datetime JSON serialization
echo "Fixing datetime JSON serialization..."
python fix_json_datetime.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to fix datetime JSON serialization. Check the error logs."
    exit 1
fi

echo "✅ Datetime JSON serialization fixed successfully"

# Fix the session ID filename
echo "Verifying session ID filename..."
sed -i '' 's/f"session_id.json"/f"{session_id}.json"/' run_interview_api.py
echo "✅ Session ID filename verified"

# Set the command based on Python version
PY_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python version: $PY_VERSION"

if [[ $(echo "$PY_VERSION >= 3.13" | bc -l) -eq 1 ]]; then
    echo "Using Python 3.13+ compatibility patch..."
    
    # Apply the patch when launching services
    # First check if we have the pydantic patch
    if [ -f "fix_pydantic_forward_refs.py" ]; then
        echo "Applying pydantic compatibility patch..."
        STARTUP_CMD="python fix_pydantic_forward_refs.py run_interview_api.py --use-langchain --port 5025"
    else
        echo "No pydantic patch found, just using standard run..."
        STARTUP_CMD="python run_interview_api.py --use-langchain --port 5025"
    fi
else
    echo "Using standard command for Python < 3.13..."
    STARTUP_CMD="python run_interview_api.py --use-langchain --port 5025"
fi

# Create a test discussion guide if it doesn't exist
if [ ! -f "$BASEDIR/data/interviews/test_guide_123456.json" ]; then
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
  "sessions": []
}
EOL
fi

# Start the DARIA server
echo "Starting DARIA server with LangChain enabled..."
mkdir -p logs
$STARTUP_CMD > logs/daria.log 2>&1 &
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
    
    # Test guide endpoint
    echo "Testing guide endpoint..."
    GUIDE_CHECK=$(curl -s "http://localhost:5025/api/discussion_guide/test_guide_123456" 2>/dev/null)
    if [[ $GUIDE_CHECK == *"\"success\":true"* ]]; then
        echo "✅ Discussion guide endpoint is working"
    else
        echo "❌ Discussion guide endpoint failed"
    fi
    
    echo "======================"
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