#!/bin/bash
# Setup and start Daria Interview Tool services

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool Service Setup     ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Check for ElevenLabs API key
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating one now...${NC}"
    echo -e "${YELLOW}Enter your ElevenLabs API key (or press Enter to skip):${NC}"
    read API_KEY
    
    if [ -z "$API_KEY" ]; then
        echo -e "${RED}No API key provided. TTS service will not work properly.${NC}"
        echo "ELEVENLABS_API_KEY=" > .env
    else
        echo "ELEVENLABS_API_KEY=$API_KEY" > .env
        echo -e "${GREEN}API key saved to .env file${NC}"
    fi
else
    echo -e "${GREEN}Found existing .env file${NC}"
    # Check if ELEVENLABS_API_KEY is set in .env
    if ! grep -q "ELEVENLABS_API_KEY=" .env || grep -q "ELEVENLABS_API_KEY=$" .env; then
        echo -e "${YELLOW}ELEVENLABS_API_KEY not set in .env file${NC}"
        echo -e "${YELLOW}Enter your ElevenLabs API key (or press Enter to skip):${NC}"
        read API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo -e "${RED}No API key provided. TTS service will not work properly.${NC}"
        else
            # Replace the line if it exists, otherwise append
            if grep -q "ELEVENLABS_API_KEY=" .env; then
                sed -i.bak "s/ELEVENLABS_API_KEY=.*/ELEVENLABS_API_KEY=$API_KEY/" .env
            else
                echo "ELEVENLABS_API_KEY=$API_KEY" >> .env
            fi
            echo -e "${GREEN}API key saved to .env file${NC}"
        fi
    else
        echo -e "${GREEN}ELEVENLABS_API_KEY is set in .env file${NC}"
    fi
fi

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p logs uploads data/interviews tools/prompt_manager/prompts

# Check if any ports are in use
API_PORT=5010
AUDIO_PORT=5015

PORT_STATUS=0
lsof -i :$API_PORT > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${RED}Port $API_PORT is already in use. Please stop the process first.${NC}"
    echo -e "${YELLOW}Run: lsof -i :$API_PORT${NC}"
    PORT_STATUS=1
fi

lsof -i :$AUDIO_PORT > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${RED}Port $AUDIO_PORT is already in use. Please stop the process first.${NC}"
    echo -e "${YELLOW}Run: lsof -i :$AUDIO_PORT${NC}"
    PORT_STATUS=1
fi

if [ $PORT_STATUS -eq 1 ]; then
    echo -e "${RED}Please stop the processes using the ports and try again.${NC}"
    echo -e "${YELLOW}You can use: ./stop_services.sh${NC}"
    exit 1
fi

# Start the services
echo -e "${YELLOW}Starting services...${NC}"
./start_services.sh

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}===============================================${NC}" 