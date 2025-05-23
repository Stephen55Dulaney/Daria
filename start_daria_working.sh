#!/bin/bash

echo "====== Starting DARIA Interview Tool (Python 3.13 Compatible) ======"
BASE_DIR=$(pwd)
echo "Base directory: $BASE_DIR"

# Stop any existing processes
echo "Stopping any existing DARIA processes..."
pkill -f "python.*run" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
sleep 3

# Create necessary directories
echo "Setting up data directories..."
mkdir -p data/interviews/sessions
mkdir -p data/interviews/discussion_guides
mkdir -p logs
mkdir -p static
mkdir -p templates

# Create test data
echo "Creating test discussion guide..."
cat > data/interviews/discussion_guides/test_guide.json << 'EOF'
{
    "id": "test_guide_123",
    "title": "Test Discussion Guide",
    "description": "A test guide for DARIA",
    "questions": [
        {
            "id": "q1",
            "text": "What are your thoughts on AI?",
            "type": "open_ended"
        }
    ]
}
EOF

echo "Creating test session..."
cat > data/interviews/sessions/test_session.json << 'EOF'
{
    "id": "test_session_123",
    "guide_id": "test_guide_123",
    "status": "active",
    "messages": []
}
EOF

# Start the main service
echo "Starting DARIA server with LangChain enabled..."
python fix_pydantic_forward_refs.py run_interview_api.py --use-langchain --port 5025 > logs/daria.log 2>&1 &
DARIA_PID=$!

echo "DARIA started with PID: $DARIA_PID"
echo "View logs with: tail -f logs/daria.log"

# Wait for service to start
echo "Waiting for service to start..."
sleep 5

# Test endpoints
echo "Testing the health check endpoint..."
if curl -s http://localhost:5025/api/health | grep -q "success"; then
    echo "✅ DARIA API server is running successfully!"
    echo "📱 Access the main application at: http://localhost:5025/"
    echo "🧪 Access the interview debug page at: http://localhost:5025/static/debug_interview_flow.html?port=5025"
    echo "🔍 Access the character test tool at: http://localhost:5025/static/debug_character_test.html"
else
    echo "❌ DARIA health check failed. Check logs for errors."
    echo "Last 20 lines of log:"
    tail -n 20 logs/daria.log
fi

echo "Press Ctrl+C to stop all DARIA services when done."
wait $DARIA_PID 