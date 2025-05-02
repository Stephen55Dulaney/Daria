#!/bin/bash

# Colors for better output formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -i:$1 >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Port $1 is already in use. Another process may be running.${NC}"
        return 1
    fi
    return 0
}

# Function to kill a process on a specific port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Attempting to kill process on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null
    sleep 1
    if ! check_port $port; then
        echo -e "${RED}Failed to kill process on port $port.${NC}"
        return 1
    fi
    echo -e "${GREEN}Process on port $port successfully terminated.${NC}"
    return 0
}

# Print banner
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}    DARIA INTERVIEW TOOL - ElevenLabs Integration    ${NC}"
echo -e "${GREEN}====================================================${NC}"

# Check for the audio_tools directory
if [ ! -d "audio_tools" ]; then
    echo -e "${RED}Error: audio_tools directory not found${NC}"
    exit 1
fi

# Check if the .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating a new one...${NC}"
    touch .env
fi

# Check if the ElevenLabs API key is set
if ! grep -q "ELEVENLABS_API_KEY" .env 2>/dev/null; then
    echo -e "${YELLOW}Warning: ELEVENLABS_API_KEY not found in .env file${NC}"
    echo -e "${YELLOW}ElevenLabs voice functionality may not work properly${NC}"
    
    # Ask if the user wants to add it now
    read -p "Do you want to add your ElevenLabs API key now? (y/n): " add_key
    if [[ $add_key == "y" || $add_key == "Y" ]]; then
        read -p "Enter your ElevenLabs API key: " api_key
        echo "ELEVENLABS_API_KEY=$api_key" >> .env
        echo -e "${GREEN}API key added to .env file${NC}"
    else
        echo -e "${YELLOW}Continuing without ElevenLabs API key. Voice features will use browser fallback.${NC}"
    fi
fi

# Check if ports are available
AUDIO_PORT=5007
MAIN_PORT=5010

# Kill existing processes if needed
if ! check_port $AUDIO_PORT; then
    kill_port $AUDIO_PORT
fi

if ! check_port $MAIN_PORT; then
    kill_port $MAIN_PORT
fi

# Install required packages
echo -e "${GREEN}Checking for required packages...${NC}"
if ! pip list | grep -q "elevenlabs"; then
    echo -e "${YELLOW}Installing ElevenLabs package...${NC}"
    pip install elevenlabs requests flask
fi

# Start the audio_tools service in the background
echo -e "${GREEN}Starting ElevenLabs Audio Tools service on port $AUDIO_PORT...${NC}"
cd audio_tools
python simple_tts_test.py --port $AUDIO_PORT &
AUDIO_TOOLS_PID=$!
cd ..

# Wait a moment for the audio service to start
echo -e "${YELLOW}Waiting for audio service to initialize...${NC}"
sleep 3

# Check if audio service started successfully
if ! curl -s http://127.0.0.1:$AUDIO_PORT/ > /dev/null; then
    echo -e "${RED}Warning: Audio tools service may not have started correctly${NC}"
    echo -e "${YELLOW}You can try starting it manually with:${NC}"
    echo -e "    cd audio_tools && python simple_tts_test.py --port $AUDIO_PORT"
else
    echo -e "${GREEN}Audio tools service started successfully!${NC}"
fi

# Start the main app
echo -e "${GREEN}Starting main application on port $MAIN_PORT...${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}  Access the application at: http://127.0.0.1:$MAIN_PORT  ${NC}"
echo -e "${GREEN}  Dashboard: http://127.0.0.1:$MAIN_PORT/dashboard        ${NC}"
echo -e "${GREEN}  Interview Setup: http://127.0.0.1:$MAIN_PORT/interview_setup  ${NC}"
echo -e "${GREEN}====================================================${NC}"

python run_langchain_direct.py --port $MAIN_PORT

# If the main app exits, kill the audio tools service
echo -e "${YELLOW}Main application has exited. Cleaning up...${NC}"
kill $AUDIO_TOOLS_PID 2>/dev/null

echo -e "${GREEN}Done.${NC}" 