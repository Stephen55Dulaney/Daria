#!/bin/bash
# Script to test DARIA functionality without PyTorch dependencies

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Testing DARIA Without PyTorch Dependencies  ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Create backup of original requirements
if [ ! -f requirements.txt.bak ]; then
  echo -e "${YELLOW}Creating backup of original requirements.txt...${NC}"
  cp requirements.txt requirements.txt.bak
else
  echo -e "${YELLOW}Backup of requirements.txt already exists.${NC}"
fi

# Function to restore original requirements
restore_requirements() {
  echo -e "${YELLOW}Restoring original requirements.txt...${NC}"
  cp requirements.txt.bak requirements.txt
  echo -e "${GREEN}Original requirements.txt restored.${NC}"
}

# Trap for clean exit
trap restore_requirements EXIT INT TERM

# Stop all running services first
echo -e "${YELLOW}Stopping any running DARIA services...${NC}"
./restart_all_daria.sh > /dev/null 2>&1
sleep 2

# Try starting the service with minimal dependencies
echo -e "${YELLOW}Starting DARIA with minimal dependencies...${NC}"
./restart_all_daria.sh

# Check if services are running properly
echo -e "${YELLOW}Checking if all services started correctly...${NC}"
sleep 5

# Check main API health
echo -e "${YELLOW}Checking main API health...${NC}"
HEALTH_CHECK=$(curl -s http://localhost:5025/api/health | grep -o '"status":"[^"]*"')
if [[ "$HEALTH_CHECK" == *"ok"* ]]; then
  echo -e "${GREEN}Main API is healthy!${NC}"
else
  echo -e "${RED}Main API health check failed: $HEALTH_CHECK${NC}"
fi

# Check TTS service
echo -e "${YELLOW}Checking TTS service...${NC}"
TTS_CHECK=$(curl -s http://localhost:5025/api/check_services | grep -o '"tts_service":{"status":[^}]*}')
if [[ "$TTS_CHECK" == *"true"* ]]; then
  echo -e "${GREEN}TTS Service is working!${NC}"
else
  echo -e "${RED}TTS Service check failed: $TTS_CHECK${NC}"
fi

# Check STT service
echo -e "${YELLOW}Checking STT service...${NC}"
STT_CHECK=$(curl -s http://localhost:5025/api/check_services | grep -o '"stt_service":{"status":[^}]*}')
if [[ "$STT_CHECK" == *"true"* ]]; then
  echo -e "${GREEN}STT Service is working!${NC}"
else
  echo -e "${RED}STT Service check failed: $STT_CHECK${NC}"
fi

# Check Memory Companion
echo -e "${YELLOW}Checking Memory Companion...${NC}"
MEM_CHECK=$(curl -s http://localhost:5030/api/memory_companion/test | grep -o 'Memory Companion is running')
if [[ "$MEM_CHECK" == "Memory Companion is running" ]]; then
  echo -e "${GREEN}Memory Companion is working!${NC}"
else
  echo -e "${RED}Memory Companion check failed${NC}"
fi

echo -e "\n${GREEN}Test completed. Check the results above to determine if DARIA works without PyTorch.${NC}"
echo -e "${YELLOW}Note: Some advanced AI features that depend on PyTorch (like local semantic analysis) may not work.${NC}"
echo -e "${YELLOW}But core functionality using OpenAI APIs should still work properly.${NC}"

echo -e "\n${GREEN}===============================================${NC}"
echo -e "${YELLOW}Do you want to keep the lighter requirements.txt without PyTorch? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
  echo -e "${GREEN}Keeping lighter requirements.txt without PyTorch.${NC}"
  # Remove the trap to prevent auto-restore
  trap - EXIT INT TERM
else
  echo -e "${YELLOW}Restoring original requirements.txt with PyTorch...${NC}"
  restore_requirements
fi 