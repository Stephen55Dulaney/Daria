#!/bin/bash
# Script to stop isolated debug services

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    Stopping Isolated Debug Services            ${NC}"
echo -e "${GREEN}================================================${NC}"

# Check if debug_isolated_pids file exists
if [ -f .debug_isolated_pids ]; then
    echo -e "${YELLOW}Stopping services listed in .debug_isolated_pids...${NC}"
    
    # Count the number of processes
    NUM_PIDS=$(wc -l < .debug_isolated_pids)
    
    # Stop each process
    for PID in $(cat .debug_isolated_pids); do
        if ps -p $PID > /dev/null; then
            echo -e "Stopping process with PID ${PID}..."
            kill $PID
            echo -e "✅ ${GREEN}Process ${PID} stopped${NC}"
        else
            echo -e "⚠️ ${YELLOW}Process ${PID} was not running${NC}"
        fi
    done
    
    # Remove the PID file
    rm .debug_isolated_pids
    echo -e "Removed .debug_isolated_pids file"
    
    echo -e "${GREEN}Successfully stopped ${NUM_PIDS} debug services${NC}"
else
    echo -e "${YELLOW}No .debug_isolated_pids file found. Trying to stop services by name...${NC}"
fi

# Try to stop services by name as fallback
echo -e "\n${YELLOW}Stopping any running isolated debug services...${NC}"

# Stop API server
KILLED_API=$(pkill -f "run_interview_api.py --port 5050" || echo "0")
if [ "$KILLED_API" != "0" ]; then
    echo -e "✅ ${GREEN}Stopped isolated API server${NC}"
else
    echo -e "ℹ️ ${YELLOW}No isolated API server was running${NC}"
fi

# Clean up temp files
if [ -f .debug_guide_id ]; then
    rm .debug_guide_id
    echo -e "✅ ${GREEN}Removed debug guide ID file${NC}"
fi

if [ -f .debug_session_id ]; then
    rm .debug_session_id
    echo -e "✅ ${GREEN}Removed debug session ID file${NC}"
fi

# Report status
if [ "$KILLED_API" != "0" ]; then
    echo -e "\n${GREEN}Successfully stopped all running isolated debug services${NC}"
else
    echo -e "\n${YELLOW}No isolated debug services were found running${NC}"
fi

echo -e "\n${GREEN}Done!${NC}"

exit 0 