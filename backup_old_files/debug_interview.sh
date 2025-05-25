#!/bin/bash
# Script to launch just the necessary services for isolated interview testing

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool - Debug Mode          ${NC}"
echo -e "${GREEN}================================================${NC}"

# Create necessary directories
mkdir -p logs
mkdir -p audio_tools/templates

# Check if template files exist
if [ ! -d "audio_tools/templates" ]; then
    mkdir -p audio_tools/templates
    echo -e "${YELLOW}Created templates directory${NC}"
fi

# Check for ElevenLabs API key
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo -e "${YELLOW}Warning: ELEVENLABS_API_KEY not found in environment${NC}"
    echo -e "${YELLOW}Text-to-speech will fall back to browser synthesis${NC}"
    echo -e "Set the key with: export ELEVENLABS_API_KEY=your_key_here${NC}"
fi

# Kill any existing services
echo -e "\n${YELLOW}Stopping any existing services...${NC}"
pkill -f "debug_tts_service.py" || true
pkill -f "simple_tts_service.py" || true
pkill -f "run_interview_api.py" || true

# Create empty PID file
rm -f .debug_pids
touch .debug_pids

# Start TTS service
echo -e "\n${YELLOW}Starting Debug TTS service...${NC}"
AUDIO_PORT=5015  # Fixed port for TTS service

# Start debug TTS service with verbose logging
python audio_tools/debug_tts_service.py --port $AUDIO_PORT --debug > logs/debug_tts.log 2>&1 &
AUDIO_PID=$!
echo -e "${GREEN}Debug TTS service started with PID: ${AUDIO_PID}${NC}"
echo $AUDIO_PID >> .debug_pids

# Wait briefly for TTS service to initialize
sleep 2

# Start main application with minimal features
echo -e "\n${YELLOW}Starting API service...${NC}"
APP_PORT=5010  # Fixed port for main app

# Start API service with full feature set including langchain for discussion service
python run_interview_api.py --port $APP_PORT --use-langchain --debug > logs/api_server.log 2>&1 &
APP_PID=$!
echo -e "${GREEN}API service started with PID: ${APP_PID}${NC}"
echo $APP_PID >> .debug_pids

# Wait for services to start
echo -e "\n${YELLOW}Waiting for services to initialize...${NC}"
sleep 3

# Verify services are running
if ps -p $APP_PID > /dev/null; then
    echo -e "✅ ${GREEN}API server is running.${NC}"
else
    echo -e "❌ ${RED}API server failed to start. Check logs/api_server.log for details.${NC}"
    exit 1
fi

if ps -p $AUDIO_PID > /dev/null; then
    echo -e "✅ ${GREEN}TTS service is running.${NC}"
else
    echo -e "❌ ${RED}TTS service failed to start. Check logs/debug_tts.log for details.${NC}"
    exit 1
fi

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"
curl -s http://localhost:$AUDIO_PORT/health | grep -q "ok" && \
    echo -e "✅ ${GREEN}TTS service health check passed${NC}" || \
    echo -e "❌ ${RED}TTS service health check failed${NC}"

# Copy debug TTS test page to make it accessible
echo -e "\n${YELLOW}Setting up debug pages...${NC}"
cp debug_tts.html "$(python -c 'import os; print(os.path.dirname(os.path.realpath(__file__)))')/static/debug_tts.html" 2>/dev/null || true

# Open TTS debug page
echo -e "\n${GREEN}TTS Debug page available at:${NC}"
echo -e "${YELLOW}http://localhost:${APP_PORT}/static/debug_tts.html${NC}"

# If session_id was provided, construct the URL
if [ -n "$1" ]; then
    SESSION_ID=$1
    INTERVIEW_URL="http://localhost:${APP_PORT}/interview/${SESSION_ID}?remote=true"
    TTS_DEBUG_URL="http://localhost:${APP_PORT}/static/debug_tts.html?session_id=${SESSION_ID}"
    
    echo -e "\n${GREEN}Opening interview session: ${SESSION_ID}${NC}"
    echo -e "${YELLOW}Interview URL: ${INTERVIEW_URL}${NC}"
    echo -e "${YELLOW}TTS Debug URL: ${TTS_DEBUG_URL}${NC}"
    
    # Try to open the URL in the default browser
    if command -v open >/dev/null 2>&1; then
        open "${INTERVIEW_URL}"
        open "${TTS_DEBUG_URL}"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${INTERVIEW_URL}"
        xdg-open "${TTS_DEBUG_URL}"
    else
        echo -e "${YELLOW}Please open these URLs in your browser:${NC}"
        echo -e "${INTERVIEW_URL}"
        echo -e "${TTS_DEBUG_URL}"
    fi
else
    echo -e "\n${YELLOW}No session ID provided. Create a new interview:${NC}"
    echo -e "${GREEN}1. Go to: http://localhost:${APP_PORT}/dashboard${NC}"
    echo -e "${GREEN}2. Create a new Discussion Guide${NC}"
    echo -e "${GREEN}3. Create a new Interview from that guide${NC}"
    echo -e "${GREEN}4. Get the session ID and run: ./debug_interview.sh <session_id>${NC}"
    
    # Open dashboard page
    echo -e "\n${YELLOW}Opening Dashboard page...${NC}"
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:${APP_PORT}/dashboard"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${APP_PORT}/dashboard"
    fi
    
    # Open TTS test page without session ID
    echo -e "\n${YELLOW}Opening TTS Debug page...${NC}"
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:${APP_PORT}/static/debug_tts.html"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${APP_PORT}/static/debug_tts.html"
    fi
fi

echo -e "\n${GREEN}Debug session is running. Services will keep running until stopped.${NC}"
echo -e "${YELLOW}To stop services, run:${NC}"
echo -e "${GREEN}./stop_debug.sh${NC}"
echo -e "${GREEN}or${NC}"
echo -e "${GREEN}pkill -f \"debug_tts_service.py\"; pkill -f \"run_interview_api.py\"${NC}"

# Start tailing the logs
echo -e "\n${YELLOW}Tailing the logs...${NC}"
echo -e "${GREEN}Press Ctrl+C to stop viewing logs (services will continue running)${NC}"
tail -f logs/api_server.log logs/debug_tts.log 