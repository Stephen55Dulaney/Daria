#!/bin/bash
# Script to start the mock STT service for debugging

echo "================================================================"
echo "              Starting Mock STT Service                          "
echo "================================================================"

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for existing service and stop it
pkill -f "audio_tools/mock_stt.py" || true
echo -e "${YELLOW}Stopped any existing mock STT services${NC}"

# Start the mock STT service
echo -e "${YELLOW}Starting mock STT service on port 5016...${NC}"
python audio_tools/mock_stt.py --port 5016 > stt_service.log 2>&1 &
STT_PID=$!

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Mock STT service started with PID: ${STT_PID}${NC}"
    
    # Wait briefly to ensure the service starts up
    sleep 2
    
    # Check if the service is running
    if kill -0 $STT_PID 2>/dev/null; then
        echo -e "${GREEN}Mock STT service is running.${NC}"
        echo -e "${YELLOW}Health check: http://localhost:5016/health${NC}"
        echo -e "${YELLOW}Service endpoint: http://localhost:5016/speech_to_text${NC}"
        echo -e "\nLogs are being written to stt_service.log"
    else
        echo -e "${RED}Failed to start Mock STT service. Check logs for details.${NC}"
    fi
else
    echo -e "${RED}Failed to start Mock STT service.${NC}"
fi

echo -e "\n${GREEN}To stop the service, run:${NC}"
echo -e "${YELLOW}pkill -f \"audio_tools/mock_stt.py\"${NC}" 