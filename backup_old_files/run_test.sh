#!/bin/bash

# Kill any existing test servers
if [ -f .test_server_pid ]; then
  pid=$(cat .test_server_pid)
  if ps -p $pid > /dev/null; then
    echo "Stopping existing test server (PID: $pid)"
    kill $pid
  fi
  rm .test_server_pid
fi

# Make sure the Python script is executable
chmod +x test_server_fix.py

# Start the server in the background
echo "Starting test server..."
nohup python3 test_server_fix.py > test_server_fixed.log 2>&1 &
echo $! > .test_server_pid

echo "Test server started"
