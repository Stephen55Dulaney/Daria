#!/bin/bash

# Script to start the fixed TTS service

echo "================================================================"
echo "              Starting Fixed TTS Service                        "
echo "================================================================"

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for ElevenLabs API key
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo -e "${RED}ElevenLabs API key not found in environment!${NC}"
    echo "Please run ./set_elevenlabs_api_key.sh first or set it manually:"
    echo "  export ELEVENLABS_API_KEY=your_key_here"
    read -p "Do you want to run the setup script now? (y/n) " run_setup
    if [[ "$run_setup" == "y" || "$run_setup" == "Y" ]]; then
        bash ./set_elevenlabs_api_key.sh
    else
        echo -e "${YELLOW}Continuing without a proper API key...${NC}"
        echo "The service will fall back to browser TTS."
    fi
else
    # Show first 5 and last 5 characters of the key
    masked_key=${ELEVENLABS_API_KEY:0:5}...${ELEVENLABS_API_KEY: -5}
    echo -e "${GREEN}ElevenLabs API key found: $masked_key${NC}"
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        return 0 # Port is in use
    else
        return 1 # Port is free
    fi
}

# Check if the TTS port is free
echo "Checking if port 5015 is available..."
if check_port 5015; then
    echo -e "${RED}Port 5015 is already in use.${NC}"
    echo -e "Run '${YELLOW}lsof -i :5015${NC}' to check and '${YELLOW}kill <PID>${NC}' to stop it if needed."
    read -p "Do you want to kill the process using port 5015? (y/n) " kill_port
    if [[ "$kill_port" == "y" || "$kill_port" == "Y" ]]; then
        pid=$(lsof -i :5015 -t)
        if [ -n "$pid" ]; then
            kill -9 $pid
            echo "Process killed."
        fi
    else
        echo "Please free up port 5015 manually before continuing."
        exit 1
    fi
else
    echo -e "${GREEN}Port 5015 is available${NC}"
fi

# Stop any existing TTS services
echo "Stopping any existing TTS services..."
pkill -f "python.*audio_tools/.*tts" || true

# Starting the fixed TTS service
echo -e "${YELLOW}Starting fixed TTS service on port 5015...${NC}"
python audio_tools/elevenlabs_tts_direct.py --port 5015 > tts_service.log 2>&1 &
TTS_PID=$!
echo $TTS_PID > .tts_service_pid

# Wait for service to start
echo "Waiting for service to start..."
sleep 2

# Check if service is running
if ps -p $TTS_PID > /dev/null; then
    echo -e "${GREEN}TTS service started successfully with PID: $TTS_PID${NC}"
    echo "Service logs are being written to tts_service.log"
    echo
    echo -e "${GREEN}To test the service:${NC}"
    echo "1. Open debug_tts.html in your browser"
    echo "2. Enter some text and click 'Test TTS with ElevenLabs'"
    echo
    echo -e "${YELLOW}To stop the service:${NC}"
    echo "kill $TTS_PID"
    echo "or run: kill \$(cat .tts_service_pid)"
else
    echo -e "${RED}Failed to start TTS service!${NC}"
    echo "Check tts_service.log for errors"
fi

echo "================================================================" 