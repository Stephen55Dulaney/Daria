#!/bin/bash

echo "====== DARIA Service Manager ======"
echo "Stopping all DARIA processes..."

# Kill all Python processes related to DARIA
pkill -9 -f ".*run_without_langchain.py.*" || echo "No run_without_langchain.py processes running"
pkill -9 -f ".*run_interview_api.py.*" || echo "No run_interview_api.py processes running"

# Wait to ensure ports are fully released
echo "Waiting for ports to be released..."
sleep 3

# Check if port 5025 is still in use
if lsof -i:5025 > /dev/null 2>&1; then
  echo "Port 5025 is still in use. Attempting to force close..."
  lsof -i:5025 -t | xargs kill -9 2>/dev/null || echo "Could not kill process on port 5025"
  sleep 2
fi

echo "Starting DARIA without LangChain on port 5025..."
python run_without_langchain.py --port 5025 &

# Wait for server to initialize
echo "Waiting for server to start..."
sleep 5

# Test if the server is running
if curl -s http://localhost:5025/api/health | grep -q "\"status\":\"ok\""; then
  echo "✅ DARIA is running successfully!"
  echo "   Access the main application at: http://localhost:5025/"
  echo "   Access the debug toolkit at: http://localhost:5025/static/debug_toolkit.html"
else
  echo "❌ Failed to start DARIA service. Check logs for errors."
fi

echo ""
echo "To stop all DARIA services, run this script again." 