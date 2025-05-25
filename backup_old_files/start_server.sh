#!/bin/bash

echo "==============================================="
echo "     DARIA Interview Tool Server Launcher     "
echo "==============================================="

# Stop any existing processes
pkill -f "python.*run_interview_api\.py"

# Start the main application server with LangChain enabled
python run_interview_api.py --port 5025 --use-langchain > api_server.log 2>&1 &
echo $! > .daria_api_pid

echo "Server started! Access the following URLs:"
echo "- Main App: http://localhost:5025"
echo "- Admin Panel: http://localhost:5025/admin"
echo "- API Docs: http://localhost:5025/api/docs"
echo
echo "To stop the server, run: ./stop_server.sh"
echo "===============================================" 