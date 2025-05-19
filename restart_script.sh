#!/bin/bash

# Stop existing UI process
if [ -f .memory_ui_pid ]; then
  pid=$(cat .memory_ui_pid)
  if ps -p $pid > /dev/null; then
    echo "Stopping existing Memory UI process (PID: $pid)"
    kill $pid
  fi
  rm .memory_ui_pid
fi

# Make sure the integration UI script is executable
chmod +x integration_ui_fix.py

# Start the new integration UI
echo "Starting new Integration UI..."
source venv/bin/activate
nohup python3 integration_ui_fix.py --host 0.0.0.0 --port 5035 > integration_ui.log 2>&1 &
echo $! > .memory_ui_pid

echo "Integration UI restarted on port 5035"
echo "You can access it at: http://3.12.144.184:5035/"
