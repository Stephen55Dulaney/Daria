#!/bin/bash
# Script to stop all DARIA Interview Tool services

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool Service Stopper     ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Check if service PIDs file exists
if [ -f .service_pids ]; then
    echo -e "${YELLOW}Found .service_pids file. Stopping services...${NC}"
    PIDS=$(cat .service_pids)
    for PID in $PIDS; do
        if ps -p $PID > /dev/null; then
            echo -e "Stopping process with PID: ${RED}$PID${NC}"
            kill $PID
        else
            echo -e "Process with PID ${YELLOW}$PID${NC} is not running"
        fi
    done
    rm .service_pids
    echo -e "${GREEN}Removed .service_pids file${NC}"
else
    echo -e "${YELLOW}No .service_pids file found.${NC}"
    echo -e "Attempting to find and stop services by name..."
    
    # Find and kill audio service
    AUDIO_PIDS=$(ps aux | grep 'simple_tts_test.py' | grep -v grep | awk '{print $2}')
    if [ -n "$AUDIO_PIDS" ]; then
        echo -e "${YELLOW}Found audio service processes:${NC} $AUDIO_PIDS"
        for PID in $AUDIO_PIDS; do
            echo -e "Stopping audio service with PID: ${RED}$PID${NC}"
            kill $PID
        done
    else
        echo -e "${GREEN}No audio service processes found${NC}"
    fi
    
    # Find and kill main application
    APP_PIDS=$(ps aux | grep 'run_langchain_direct_fixed.py' | grep -v grep | awk '{print $2}')
    if [ -n "$APP_PIDS" ]; then
        echo -e "${YELLOW}Found main application processes:${NC} $APP_PIDS"
        for PID in $APP_PIDS; do
            echo -e "Stopping main application with PID: ${RED}$PID${NC}"
            kill $PID
        done
    else
        echo -e "${GREEN}No main application processes found${NC}"
    fi
fi

# Check ports to ensure services are stopped
echo -e "\n${YELLOW}Checking if ports are still in use...${NC}"

# Check port 5007 (audio service)
if lsof -i :5007 >/dev/null 2>&1; then
    echo -e "${RED}Port 5007 is still in use. You may need to manually stop the process.${NC}"
    echo -e "Run '${YELLOW}lsof -i :5007${NC}' to identify the process and '${YELLOW}kill <PID>${NC}' to stop it."
else
    echo -e "${GREEN}Port 5007 is free. Audio service stopped successfully.${NC}"
fi

# Check port 5010 (main application)
if lsof -i :5010 >/dev/null 2>&1; then
    echo -e "${RED}Port 5010 is still in use. You may need to manually stop the process.${NC}"
    echo -e "Run '${YELLOW}lsof -i :5010${NC}' to identify the process and '${YELLOW}kill <PID>${NC}' to stop it."
else
    echo -e "${GREEN}Port 5010 is free. Main application stopped successfully.${NC}"
fi

echo -e "\n${GREEN}All services should now be stopped.${NC}"
echo -e "${GREEN}===============================================${NC}" 