#!/bin/bash
# Script to stop all debug services

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}       Stopping Debug Services                   ${NC}"
echo -e "${GREEN}================================================${NC}"

# Check if debug_pids file exists
if [ -f .debug_pids ]; then
    echo -e "${YELLOW}Stopping services listed in .debug_pids...${NC}"
    
    # Count the number of processes
    NUM_PIDS=$(wc -l < .debug_pids)
    
    # Stop each process
    for PID in $(cat .debug_pids); do
        if ps -p $PID > /dev/null; then
            echo -e "Stopping process with PID ${PID}..."
            kill $PID
            echo -e "✅ ${GREEN}Process ${PID} stopped${NC}"
        else
            echo -e "⚠️ ${YELLOW}Process ${PID} was not running${NC}"
        fi
    done
    
    # Remove the PID file
    rm .debug_pids
    echo -e "Removed .debug_pids file"
    
    echo -e "${GREEN}Successfully stopped ${NUM_PIDS} debug services${NC}"
else
    echo -e "${YELLOW}No .debug_pids file found. Trying to stop services by name...${NC}"
fi

# Try to stop services by name as fallback
echo -e "\n${YELLOW}Stopping any running debug services...${NC}"

# Stop debug TTS service
KILLED_TTS=$(pkill -f "debug_tts_service.py" || echo "0")
if [ "$KILLED_TTS" != "0" ]; then
    echo -e "✅ ${GREEN}Stopped debug TTS service${NC}"
else
    echo -e "ℹ️ ${YELLOW}No debug TTS service was running${NC}"
fi

# Stop simple TTS service (as fallback)
KILLED_SIMPLE_TTS=$(pkill -f "simple_tts_service.py" || echo "0")
if [ "$KILLED_SIMPLE_TTS" != "0" ]; then
    echo -e "✅ ${GREEN}Stopped simple TTS service${NC}"
else
    echo -e "ℹ️ ${YELLOW}No simple TTS service was running${NC}"
fi

# Stop API server
KILLED_API=$(pkill -f "run_interview_api.py" || echo "0")
if [ "$KILLED_API" != "0" ]; then
    echo -e "✅ ${GREEN}Stopped API server${NC}"
else
    echo -e "ℹ️ ${YELLOW}No API server was running${NC}"
fi

# Report status
if [ "$KILLED_TTS" != "0" ] || [ "$KILLED_SIMPLE_TTS" != "0" ] || [ "$KILLED_API" != "0" ]; then
    echo -e "\n${GREEN}Successfully stopped all running debug services${NC}"
else
    echo -e "\n${YELLOW}No debug services were found running${NC}"
fi

echo -e "\n${GREEN}Done!${NC}"

exit 0 