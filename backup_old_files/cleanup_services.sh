#!/bin/bash
# Comprehensive cleanup script for the Daria Interview Tool
# This script ensures all services are properly terminated

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool Cleanup Script       ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Find and kill all python processes related to the interview services
echo -e "\n${YELLOW}Finding and terminating all related processes...${NC}"

# Kill main API server instances
pkill -f "python.*run_interview_api.py"
echo "✅ Terminated all API server instances"

# Kill TTS service instances
pkill -f "python.*simple_tts_service.py"
echo "✅ Terminated all TTS service instances"

# Kill any remaining audio services
pkill -f "python.*audio_service.py"
pkill -f "python.*stt_service.py"
pkill -f "python.*tts_service.py"
echo "✅ Terminated all audio service instances"

# Clean up PID files
echo -e "\n${YELLOW}Cleaning up PID files...${NC}"
rm -f *.pid
rm -f .service_pids
echo "✅ Removed PID files"

# Check if ports are still in use
echo -e "\n${YELLOW}Verifying services are stopped...${NC}"
if lsof -i :5010 >/dev/null 2>&1; then
    echo -e "${RED}Port 5010 is still in use. Attempting to force close...${NC}"
    fuser -k 5010/tcp >/dev/null 2>&1
    sleep 1
else
    echo "✅ API server port 5010 is free"
fi

if lsof -i :5015 >/dev/null 2>&1; then
    echo -e "${RED}Port 5015 is still in use. Attempting to force close...${NC}"
    fuser -k 5015/tcp >/dev/null 2>&1
    sleep 1
else
    echo "✅ TTS service port 5015 is free"
fi

# Final check
if pgrep -f "python.*run_interview_api.py|python.*simple_tts_service.py" > /dev/null; then
    echo -e "${RED}Warning: Some services may still be running. You may need to manually kill them.${NC}"
    echo -e "Use: ${YELLOW}pkill -9 -f 'python.*run_interview_api.py|python.*simple_tts_service.py'${NC}"
else
    echo -e "${GREEN}All services have been successfully terminated.${NC}"
fi

echo -e "\n${GREEN}Cleanup complete! System is in a clean state.${NC}"
echo -e "${GREEN}===============================================${NC}"

# Make this script executable
chmod +x $0 