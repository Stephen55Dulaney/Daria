#!/bin/bash
# Script to launch the DARIA Interview Tool with AI Observer enabled

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   DARIA Interview Tool with AI Observer   ${NC}"
echo -e "${GREEN}================================================${NC}"

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY not found in environment${NC}"
    echo -e "${YELLOW}Set the key with: export OPENAI_API_KEY=your_key_here${NC}"
    exit 1
fi

# Define the port
PORT=5025

# Kill any existing services
echo -e "\n${YELLOW}Stopping any existing services...${NC}"
pkill -f "run_interview_api.py" || true

# Start the DARIA Interview API with LangChain and AI Observer
echo -e "\n${YELLOW}Starting DARIA Interview API with AI Observer...${NC}"
python run_interview_api.py --port $PORT --use-langchain

# Open the AI Observer Debug Tool
echo -e "\n${YELLOW}Opening AI Observer Debug Tool...${NC}"
echo -e "${GREEN}Access the debug tool at: http://localhost:$PORT/static/debug_ai_observer.html${NC}"

# For macOS, attempt to open the debug page automatically
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:$PORT/static/debug_ai_observer.html"
fi

echo -e "\n${GREEN}DARIA Interview Tool is running!${NC}"
echo -e "Health check endpoint: http://localhost:$PORT/api/health"
echo -e "Monitor interviews: http://localhost:$PORT/monitor_interview"
echo -e "\nPress Ctrl+C to stop the server" 