#!/bin/bash

# Kill any existing Python processes running the langchain scripts
echo "Stopping any running langchain processes..."
pkill -f "python.*run_langchain.*" || echo "No langchain processes found to stop"

# Wait a moment for the processes to fully terminate
sleep 1

# Start the langchain direct script
echo "Starting run_langchain_direct.py..."
python run_langchain_direct.py --port 5010 &

# Print a message with the access URL
echo ""
echo "Langchain interview system started! Access it at:"
echo "http://127.0.0.1:5010"
echo ""
echo "Dashboard: http://127.0.0.1:5010/dashboard"
echo "Interview Test: http://127.0.0.1:5010/interview_test"
echo "Interview Setup: http://127.0.0.1:5010/interview_setup"
echo "Prompt Manager: http://127.0.0.1:5010/prompts/" 