#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Daria Interview Tool - Server Restart Script${NC}"
echo -e "-------------------------------------------"

# Check for running Python processes related to the API server
echo -e "${YELLOW}Checking for running interview API processes...${NC}"

# Check for port usage first
PORT=${1:-5025}
echo -e "${YELLOW}Checking if port ${PORT} is in use...${NC}"
PORT_PID=$(lsof -i :${PORT} | grep LISTEN | awk '{print $2}')

if [ -n "$PORT_PID" ]; then
    echo -e "${RED}Found process using port ${PORT} with PID: $PORT_PID${NC}"
    echo -e "Stopping process..."
    kill -9 $PORT_PID
    sleep 2
    echo -e "${GREEN}Process stopped.${NC}"
else
    echo -e "${GREEN}No process found using port ${PORT}.${NC}"
fi

# More thorough check for any Python processes running the API server
API_PIDS=$(ps aux | grep "python run_interview_api.py" | grep -v grep | awk '{print $2}')

if [ -n "$API_PIDS" ]; then
    echo -e "${RED}Found running API processes: $API_PIDS${NC}"
    echo -e "Stopping all API processes..."
    
    for PID in $API_PIDS; do
        echo -e "Killing PID: $PID"
        kill -9 $PID
    done
    
    sleep 2
    echo -e "${GREEN}All API processes stopped.${NC}"
else
    echo -e "${GREEN}No running API processes found.${NC}"
fi

# Check for any extra socket connections
SOCKET_PIDS=$(ps aux | grep "socket.io" | grep -v grep | awk '{print $2}')

if [ -n "$SOCKET_PIDS" ]; then
    echo -e "${RED}Found running socket processes: $SOCKET_PIDS${NC}"
    echo -e "Stopping all socket processes..."
    
    for PID in $SOCKET_PIDS; do
        echo -e "Killing PID: $PID"
        kill -9 $PID
    done
    
    sleep 2
    echo -e "${GREEN}All socket processes stopped.${NC}"
else
    echo -e "${GREEN}No running socket processes found.${NC}"
fi

# Start the server with provided parameters
USE_LANGCHAIN=${2:-"false"}
if [ "$USE_LANGCHAIN" = "true" ]; then
    echo -e "${YELLOW}Starting with LangChain enabled${NC}"
    LANGCHAIN_FLAG="--use-langchain"
else
    echo -e "${YELLOW}Starting without LangChain${NC}"
    LANGCHAIN_FLAG=""
fi

echo -e "Using default port: ${PORT}"
echo -e "${GREEN}Starting interview API server...${NC}"
python run_interview_api.py ${LANGCHAIN_FLAG} --port ${PORT} &

# Give the server a moment to start
sleep 2

# Check if it started properly
if ps aux | grep "python run_interview_api.py" | grep -v grep > /dev/null; then
    echo -e "${GREEN}Server started successfully!${NC}"
    echo -e "Health check: http://127.0.0.1:${PORT}/api/health"
    echo -e "Debug tool: http://127.0.0.1:${PORT}/static/debug_interview_flow.html?port=${PORT}"
    echo -e "Interview setup: http://127.0.0.1:${PORT}/interview_setup"
    echo -e "Monitor interviews: http://127.0.0.1:${PORT}/monitor_interview"
else
    echo -e "${RED}Server failed to start. Check logs for errors.${NC}"
fi 