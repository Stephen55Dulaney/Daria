#!/bin/bash

echo "====== Restarting DARIA with Fixes ======"

# Kill any existing processes on port 5025
echo "Stopping any existing processes on port 5025..."
lsof -ti:5025 | xargs kill -9 2>/dev/null || true

# Wait for port to be released
echo "Waiting for port 5025 to be released..."
sleep 3

# Start DARIA service without LangChain on port 5025
echo "Starting DARIA service on port 5025..."
python run_without_langchain.py --port 5025 &

# Store the PID of the started process
DARIA_PID=$!
echo "DARIA started with PID: $DARIA_PID"

# Wait for service to initialize
echo "Waiting for service to start..."
sleep 5

# Test if the server is running
echo "Testing the health check endpoint..."
if curl -s http://localhost:5025/api/health | grep -q "\"status\":\"ok\""; then
  echo "✅ DARIA is running successfully!"
  echo "   Access the main application at: http://localhost:5025/"
  echo "   Access the discussion guide page at: http://localhost:5025/discussion_guide/9d9b0648-5f14-4a22-81df-290bbd67049d"
  echo "   Access the fixed session at: http://localhost:5025/session/400f522b-95db-4dfd-8727-4cdd8988925c"
else
  echo "❌ DARIA health check failed. Check logs for errors."
  tail -20 daria.log
fi

echo ""
echo "Press Ctrl+C to stop the service when done." 