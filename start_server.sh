#!/bin/bash

# Start the Daria Interview Tool with LangChain support
echo "Starting Daria Interview Tool..."

# Check if any Daria processes are already running
EXISTING_PID=$(lsof -i :5025 -t)
if [ ! -z "$EXISTING_PID" ]; then
    echo "Found existing process on port 5025, stopping it..."
    kill $EXISTING_PID
    sleep 2
fi

# Set required environment variables if not already set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY is not set. Some features may not work properly."
fi

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "Warning: ELEVENLABS_API_KEY is not set. Text-to-speech features may not work properly."
fi

# Start Daria with LangChain enabled
echo "Starting Daria on port 5025 with LangChain enabled..."
python run_interview_api.py --use-langchain --port 5025 &

# Save the PID
echo $! > .daria_api_pid
echo "Daria started with PID: $!"
echo ""
echo "Server URLs:"
echo "Main dashboard: http://localhost:5025/dashboard"
echo "Health check: http://localhost:5025/api/health"
echo "Debug toolkit: http://localhost:5025/debug"
echo ""
echo "To stop the server, run: ./stop_server.sh" 