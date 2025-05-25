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

echo "Stopping all DARIA services..."

# Kill all Python processes related to our services
pkill -f "python.*mock_memory_service.py"
pkill -f "python.*mock_stt_service.py"
pkill -f "python.*mock_tts_service.py"
pkill -f "python.*elevenlabs_tts.py"
pkill -f "python.*app.py"

# Additional cleanup - kill any processes on our ports
lsof -ti:5015 | xargs kill -9 2>/dev/null
lsof -ti:5016 | xargs kill -9 2>/dev/null
lsof -ti:5025 | xargs kill -9 2>/dev/null
lsof -ti:5030 | xargs kill -9 2>/dev/null

echo "All services stopped."

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