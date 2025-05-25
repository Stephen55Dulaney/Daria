#!/bin/bash

# DARIA Interview Tool Startup Script
# This script starts all required services with a simple Python 3.13 compatibility patch

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}    Starting DARIA Interview Tool                     ${NC}"
echo -e "${GREEN}======================================================${NC}"

# Ensure data directories exist
echo -e "${YELLOW}Ensuring data directories exist...${NC}"
mkdir -p data/discussions
mkdir -p data/discussions/sessions
mkdir -p data/interviews

# Stop any existing services
echo -e "${YELLOW}Stopping existing services...${NC}"
pkill -f "run_interview_api.py" || true
pkill -f "audio_tools/.*tts" || true
pkill -f "audio_tools/.*stt" || true

# Start TTS service in the correct directory
echo -e "${YELLOW}Starting TTS service...${NC}"
cd audio_tools
python elevenlabs_tts.py --port 5015 > ../tts_service.log 2>&1 &
TTS_PID=$!
echo -e "${GREEN}TTS service started (PID: $TTS_PID).${NC}"

# Start STT service
python simple_stt_server.py --port 5016 > ../stt_service.log 2>&1 &
STT_PID=$!
echo -e "${GREEN}STT service started (PID: $STT_PID).${NC}"

# Back to main directory
cd ..

# Wait a moment for services to initialize
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 2

# Start the main API server with our patched Python
echo -e "${YELLOW}Starting API server with Python 3.13 patch...${NC}"
python -c "import simple_patch; exec(open('run_interview_api.py').read())" --port 5025 --use-langchain > api_server.log 2>&1 &
API_PID=$!
echo -e "${GREEN}API server started (PID: $API_PID).${NC}"

sleep 2

# Check if services are running
echo -e "${YELLOW}Checking services...${NC}"
if ps -p $TTS_PID > /dev/null; then
    echo -e "${GREEN}TTS service is running.${NC}"
else
    echo -e "${RED}Warning: TTS service is not running.${NC}"
fi

if ps -p $STT_PID > /dev/null; then
    echo -e "${GREEN}STT service is running.${NC}"
else
    echo -e "${RED}Warning: STT service is not running.${NC}"
fi

if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}API server is running.${NC}"
else
    echo -e "${RED}Warning: API server is not running.${NC}"
fi

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}    All services started                             ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}TTS Service:       ${NC}http://localhost:5015"
echo -e "${GREEN}STT Service:       ${NC}http://localhost:5016"
echo -e "${GREEN}API Server:        ${NC}http://localhost:5025"
echo -e "${GREEN}Dashboard:         ${NC}http://localhost:5025/dashboard"
echo -e "${GREEN}======================================================${NC}"

# Keep script running to allow easy stopping with Ctrl+C
echo -e "${YELLOW}Press Ctrl+C to stop all services. View logs in api_server.log, tts_service.log, and stt_service.log${NC}"
wait $API_PID 