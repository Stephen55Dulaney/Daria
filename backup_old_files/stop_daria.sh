#!/bin/bash
# DARIA Interview Tool Shutdown Script

echo "=================================================="
echo "   DARIA INTERVIEW SYSTEM - SHUTDOWN SCRIPT     "
echo "=================================================="

echo "Stopping services by port..."

# Function to stop service on a specific port
stop_service() {
  PORT=$1
  echo -n "Stopping service on port $PORT... "
  
  # Find PID using the port
  PID=$(lsof -ti:$PORT)
  
  if [ -z "$PID" ]; then
    echo "No service running"
    return
  fi
  
  # Kill the process
  kill -15 $PID 2>/dev/null
  
  # Wait a moment to let it shut down gracefully
  sleep 0.5
  
  # Check if it's still running and force kill if necessary
  if lsof -ti:$PORT >/dev/null 2>&1; then
    kill -9 $PID 2>/dev/null
    sleep 0.5
  fi
  
  # Verify it's stopped
  if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "FAILED"
  else
    echo "SUCCESS"
  fi
}

# Stop all services
stop_service 5010  # Main API
stop_service 5015  # TTS service
stop_service 5016  # STT service
stop_service 8889  # Web server

echo "All services have been stopped successfully"
echo "=================================================="
echo "DARIA Interview System has been shut down"
echo "=================================================="

echo "====== Stopping DARIA Service ======"

# Find and kill any processes on port 5025
echo "Finding processes on port 5025..."
PIDS=$(lsof -ti:5025 2>/dev/null)

if [ -z "$PIDS" ]; then
  echo "No DARIA processes found running on port 5025."
else
  echo "Stopping DARIA processes with PIDs: $PIDS"
  kill -15 $PIDS 2>/dev/null || true
  
  # Wait a moment for graceful shutdown
  sleep 2
  
  # Check if processes are still running and force kill if needed
  REMAINING=$(lsof -ti:5025 2>/dev/null)
  if [ ! -z "$REMAINING" ]; then
    echo "Force killing remaining processes: $REMAINING"
    kill -9 $REMAINING 2>/dev/null || true
  fi
  
  echo "✅ DARIA service stopped."
fi 