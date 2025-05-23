#!/bin/bash

echo "====== Shutting down DARIA services ======"

# Find and kill all Python processes running DARIA scripts
echo "Stopping all DARIA Python processes..."
pkill -f "python run_without_langchain.py" || true
pkill -f "python run_interview_api.py" || true

# Wait a moment to ensure processes are terminated
sleep 2

# Check if processes are still running
if pgrep -f "python run_without_langchain.py" > /dev/null || pgrep -f "python run_interview_api.py" > /dev/null; then
  echo "⚠️ Some DARIA processes are still running. Attempting to force kill..."
  pkill -9 -f "python run_without_langchain.py" || true
  pkill -9 -f "python run_interview_api.py" || true
  sleep 1
fi

# Final check
if pgrep -f "python run_without_langchain.py" > /dev/null || pgrep -f "python run_interview_api.py" > /dev/null; then
  echo "❌ Failed to stop all DARIA processes. Please check manually with 'ps aux | grep python'"
else
  echo "✅ All DARIA services stopped successfully!"
fi

echo ""
echo "To restart DARIA, run the restart_after_fix.sh script." 