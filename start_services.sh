#!/bin/bash
# Script to start all services for DARIA Interview Tool

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool Service Launcher     ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        return 0 # Port is in use
    else
        return 1 # Port is free
    fi
}

# Start audio service
echo -e "\n${YELLOW}Starting audio service...${NC}"
if check_port 5007; then
    echo -e "${RED}Port 5007 is already in use. Audio service may already be running.${NC}"
    echo -e "Run '${YELLOW}lsof -i :5007${NC}' to check and '${YELLOW}kill <PID>${NC}' to stop it if needed."
else
    echo -e "Starting audio service on port 5007"
    cd audio_tools && python simple_tts_test.py --port 5007 &
    AUDIO_PID=$!
    echo -e "${GREEN}Audio service started with PID: ${AUDIO_PID}${NC}"
    cd ..
fi

# Start main application
echo -e "\n${YELLOW}Starting main application...${NC}"
if check_port 5010; then
    echo -e "${RED}Port 5010 is already in use. Main application may already be running.${NC}"
    echo -e "Run '${YELLOW}lsof -i :5010${NC}' to check and '${YELLOW}kill <PID>${NC}' to stop it if needed."
else
    echo -e "Starting main application on port 5010"
    python run_langchain_direct_fixed.py --port 5010 &
    APP_PID=$!
    echo -e "${GREEN}Main application started with PID: ${APP_PID}${NC}"
fi

# Print access information
echo -e "\n${GREEN}Services should now be running:${NC}"
echo -e "Main application: ${YELLOW}http://localhost:5010${NC}"
echo -e "Audio service: ${YELLOW}http://localhost:5007${NC}"

echo -e "\n${GREEN}You can access the following pages:${NC}"
echo -e "Dashboard: ${YELLOW}http://localhost:5010/dashboard${NC}"
echo -e "Interview Setup: ${YELLOW}http://localhost:5010/interview_setup${NC}"
echo -e "Prompt Manager: ${YELLOW}http://localhost:5010/prompts/${NC}"

echo -e "\n${YELLOW}To stop the services, run:${NC}"
echo -e "kill $AUDIO_PID $APP_PID"

# Save PIDs to a file for easy cleanup
echo -e "$AUDIO_PID $APP_PID" > .service_pids

echo -e "\n${GREEN}Service PIDs saved to .service_pids file${NC}"
echo -e "You can stop all services with: ${YELLOW}kill \$(cat .service_pids)${NC}"

echo -e "\n${GREEN}===============================================${NC}" 