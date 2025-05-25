#!/bin/bash

# Start LangChain-powered Interview System
# This script starts all the necessary services for the DARIA Interview Tool
# with LangChain integration for more intelligent interviews

# Setup variables
API_PORT=5010
TTS_PORT=5015
STT_PORT=5016
AUDIO_PORT=5017
AUDIO_TOOLS_DIR="./audio_tools"
LOG_DIR="./logs"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

echo "Starting DARIA LangChain Interview System..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found. Please install Python 3 and try again."
    exit 1
fi

# Check if required env variable is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set."
    echo "LangChain requires an OpenAI API key for its functionality."
    read -p "Would you like to set an OpenAI API key now? (y/n): " set_key
    
    if [[ $set_key == "y" ]]; then
        read -p "Enter your OpenAI API key: " api_key
        export OPENAI_API_KEY=$api_key
        echo "OPENAI_API_KEY set for this session."
    else
        echo "Warning: Proceeding without OpenAI API key. LangChain features will be disabled."
    fi
fi

# Start the services in the background
echo "Starting Text-to-Speech service on port $TTS_PORT..."
python3 $AUDIO_TOOLS_DIR/simple_tts_service.py --port $TTS_PORT > $LOG_DIR/tts_service.log 2>&1 &
echo $! > tts_service.pid

echo "Starting Speech-to-Text service on port $STT_PORT..."
python3 $AUDIO_TOOLS_DIR/stt_service.py --port $STT_PORT > $LOG_DIR/stt_service.log 2>&1 &
echo $! > stt_service.pid

echo "Starting Audio Service on port $AUDIO_PORT..."
python3 $AUDIO_TOOLS_DIR/audio_service.py --port $AUDIO_PORT > $LOG_DIR/audio_service.log 2>&1 &
echo $! > audio_service.pid

# Record all service PIDs in a single file for easier shutdown
echo "tts_service:$(cat tts_service.pid)" > .service_pids
echo "stt_service:$(cat stt_service.pid)" >> .service_pids
echo "audio_service:$(cat audio_service.pid)" >> .service_pids

# Wait for services to initialize (3 seconds)
echo "Waiting for services to initialize..."
sleep 3

# Start the main API with LangChain enabled
echo "Starting API server on port $API_PORT with LangChain enabled..."
python3 run_interview_api.py --port $API_PORT --use-langchain > $LOG_DIR/api_server.log 2>&1 &
echo $! > api_server.pid
echo "api_server:$(cat api_server.pid)" >> .service_pids

echo "All services started successfully!"
echo ""
echo "To access the interview setup page, go to: http://localhost:$API_PORT/interview_setup"
echo "To access the test interview page, open: test_interview_page.html in your browser"
echo ""
echo "To stop all services, run: ./stop_services.sh"

# Output the status
echo "Service status:"
echo "- API Server: Running on port $API_PORT (PID: $(cat api_server.pid))"
echo "- TTS Service: Running on port $TTS_PORT (PID: $(cat tts_service.pid))"
echo "- STT Service: Running on port $STT_PORT (PID: $(cat stt_service.pid))"
echo "- Audio Service: Running on port $AUDIO_PORT (PID: $(cat audio_service.pid))"
echo ""
echo "Log files are stored in the $LOG_DIR directory." 