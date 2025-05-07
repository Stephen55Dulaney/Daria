#!/bin/bash
# Script to launch isolated interview components for testing
# This script isolates LangChain conversation testing from TTS/STT interference

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   DARIA Interview Tool - Isolated Testing Mode  ${NC}"
echo -e "${GREEN}================================================${NC}"

# Create necessary directories
mkdir -p logs
mkdir -p data/discussions
mkdir -p data/discussions/sessions

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY not found in environment${NC}"
    echo -e "${YELLOW}Set the key with: export OPENAI_API_KEY=your_key_here${NC}"
    exit 1
fi

# Kill any existing services
echo -e "\n${YELLOW}Stopping any existing services...${NC}"
pkill -f "run_interview_api.py" || true

# Create empty PID file
rm -f .debug_isolated_pids
touch .debug_isolated_pids

# Start API service with LangChain but without audio services
echo -e "\n${YELLOW}Starting API service with isolated LangChain conversation...${NC}"
APP_PORT=5050  # Different port to avoid conflicts

# Start API service with LangChain enabled but disable audio services
python run_interview_api.py --port $APP_PORT --use-langchain --debug > logs/isolated_api.log 2>&1 &
APP_PID=$!
echo -e "${GREEN}Isolated API service started with PID: ${APP_PID}${NC}"
echo $APP_PID >> .debug_isolated_pids

# Wait for service to start
echo -e "\n${YELLOW}Waiting for service to initialize...${NC}"
sleep 3

# Verify service is running
if ps -p $APP_PID > /dev/null; then
    echo -e "✅ ${GREEN}Isolated API server is running.${NC}"
else
    echo -e "❌ ${RED}API server failed to start. Check logs/isolated_api.log for details.${NC}"
    exit 1
fi

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:$APP_PORT/api/health)
if echo $HEALTH_RESPONSE | grep -q "\"status\":\"ok\""; then
    echo -e "✅ ${GREEN}API service health check passed${NC}"
    
    # Check if LangChain is enabled
    if echo $HEALTH_RESPONSE | grep -q "\"langchain_enabled\":true"; then
        echo -e "✅ ${GREEN}LangChain is enabled${NC}"
    else
        echo -e "❌ ${RED}LangChain is not enabled${NC}"
        echo -e "${YELLOW}Check logs/isolated_api.log for errors${NC}"
    fi
else
    echo -e "❌ ${RED}API service health check failed${NC}"
    echo -e "${YELLOW}Response: ${HEALTH_RESPONSE}${NC}"
fi

# Create a debug discussion guide
echo -e "\n${YELLOW}Creating a debug discussion guide...${NC}"
GUIDE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"title":"Debug Interview Guide", "project":"Debug Testing", "interview_type":"debug_test", "prompt":"Testing conversation history with isolated LangChain"}' \
    http://localhost:$APP_PORT/discussion_guide/create)

if echo $GUIDE_RESPONSE | grep -q "\"status\":\"success\""; then
    GUIDE_ID=$(echo $GUIDE_RESPONSE | sed -n 's/.*"guide_id":"\([^"]*\)".*/\1/p')
    echo -e "✅ ${GREEN}Created debug discussion guide with ID: ${GUIDE_ID}${NC}"
    
    # Save guide ID for later use
    echo $GUIDE_ID > .debug_guide_id
else
    echo -e "❌ ${RED}Failed to create debug discussion guide${NC}"
    echo -e "${YELLOW}Response: ${GUIDE_RESPONSE}${NC}"
fi

# Display useful URLs
echo -e "\n${GREEN}Debug resources available at:${NC}"
echo -e "${YELLOW}Dashboard: http://localhost:${APP_PORT}/dashboard${NC}"
echo -e "${YELLOW}Health API: http://localhost:${APP_PORT}/api/health${NC}"
echo -e "${YELLOW}Discussion Guides: http://localhost:${APP_PORT}/discussion_guides${NC}"
echo -e "${YELLOW}TTS Debug: http://localhost:${APP_PORT}/static/debug_stt_tts.html${NC}"
echo -e "${YELLOW}Interview TTS Debug: http://localhost:${APP_PORT}/static/debug_interview_tts.html${NC}"
echo -e "${YELLOW}TTS-STT Orchestration Debug: http://localhost:${APP_PORT}/static/debug_orchestration.html${NC}"
echo -e "${YELLOW}Full Interview Flow Debug: http://localhost:${APP_PORT}/static/debug_interview_flow.html${NC}"

if [ -n "$GUIDE_ID" ]; then
    echo -e "${YELLOW}Debug Guide: http://localhost:${APP_PORT}/discussion_guide/${GUIDE_ID}${NC}"
    
    # Create a debug interview session
    echo -e "\n${YELLOW}Creating a debug interview session...${NC}"
    SESSION_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "{\"guide_id\":\"${GUIDE_ID}\", \"interviewee\":{\"name\":\"Debug User\"}}" \
        http://localhost:$APP_PORT/api/session/create)
    
    if echo $SESSION_RESPONSE | grep -q "\"success\":true"; then
        SESSION_ID=$(echo $SESSION_RESPONSE | sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p')
        echo -e "✅ ${GREEN}Created debug session with ID: ${SESSION_ID}${NC}"
        echo -e "${YELLOW}Debug Session: http://localhost:${APP_PORT}/session/${SESSION_ID}${NC}"
        echo -e "${YELLOW}Interview TTS Debug with Session: http://localhost:${APP_PORT}/static/debug_interview_tts.html?session_id=${SESSION_ID}${NC}"
        echo -e "${YELLOW}Full Interview Flow Debug with Session: http://localhost:${APP_PORT}/static/debug_interview_flow.html?port=${APP_PORT}&session_id=${SESSION_ID}${NC}"
        
        # Save session ID for later use
        echo $SESSION_ID > .debug_session_id
    else
        echo -e "❌ ${RED}Failed to create debug session${NC}"
        echo -e "${YELLOW}Response: ${SESSION_RESPONSE}${NC}"
    fi
fi

# Open dashboard in browser
echo -e "\n${YELLOW}Opening Dashboard page...${NC}"
if command -v open >/dev/null 2>&1; then
    open "http://localhost:${APP_PORT}/dashboard"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:${APP_PORT}/dashboard"
fi

echo -e "\n${GREEN}Isolated debug session is running. Services will keep running until stopped.${NC}"
echo -e "${YELLOW}To stop services, run:${NC}"
echo -e "${GREEN}./stop_isolated_debug.sh${NC}"
echo -e "${GREEN}or${NC}"
echo -e "${GREEN}pkill -f \"run_interview_api.py\"${NC}"

# Start tailing the logs
echo -e "\n${YELLOW}Tailing the logs...${NC}"
echo -e "${GREEN}Press Ctrl+C to stop viewing logs (services will continue running)${NC}"
tail -f logs/isolated_api.log 