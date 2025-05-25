#!/bin/bash

# Daria Interview Tool Shutdown Script
# This script stops all Daria services cleanly

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}======================================================${NC}"
echo -e "${YELLOW}        Stopping Daria Interview Tool                 ${NC}"
echo -e "${YELLOW}======================================================${NC}"

# Stop API server
echo -e "${YELLOW}Stopping API server...${NC}"
API_PIDS=$(pgrep -f "run_interview_api.py")
if [ -n "$API_PIDS" ]; then
    echo -e "${GREEN}Found API server processes: $API_PIDS${NC}"
    pkill -f "run_interview_api.py"
    echo -e "${GREEN}API server stopped.${NC}"
else
    echo -e "${YELLOW}No API server processes found.${NC}"
fi

# Stop TTS service
echo -e "${YELLOW}Stopping TTS service...${NC}"
TTS_PIDS=$(pgrep -f "audio_tools/.*tts")
if [ -n "$TTS_PIDS" ]; then
    echo -e "${GREEN}Found TTS service processes: $TTS_PIDS${NC}"
    pkill -f "audio_tools/.*tts"
    echo -e "${GREEN}TTS service stopped.${NC}"
else
    echo -e "${YELLOW}No TTS service processes found.${NC}"
fi

# Stop STT service
echo -e "${YELLOW}Stopping STT service...${NC}"
STT_PIDS=$(pgrep -f "audio_tools/.*stt")
if [ -n "$STT_PIDS" ]; then
    echo -e "${GREEN}Found STT service processes: $STT_PIDS${NC}"
    pkill -f "audio_tools/.*stt"
    echo -e "${GREEN}STT service stopped.${NC}"
else
    echo -e "${YELLOW}No STT service processes found.${NC}"
fi

# Stop Memory Companion service
echo -e "${YELLOW}Stopping Memory Companion service...${NC}"
MEMORY_PIDS=$(pgrep -f "debug_memory_api.py")
if [ -n "$MEMORY_PIDS" ]; then
    echo -e "${GREEN}Found Memory Companion processes: $MEMORY_PIDS${NC}"
    pkill -f "debug_memory_api.py"
    echo -e "${GREEN}Memory Companion service stopped.${NC}"
else
    echo -e "${YELLOW}No Memory Companion processes found.${NC}"
fi

# Check if any services are still running
sleep 2
REMAINING=$(pgrep -f "run_interview_api.py|audio_tools/.*tts|audio_tools/.*stt|debug_memory_api.py")
if [ -n "$REMAINING" ]; then
    echo -e "${RED}Some processes could not be stopped normally.${NC}"
    echo -e "${RED}Remaining processes: $REMAINING${NC}"
    echo -e "${YELLOW}Forcefully terminating remaining processes...${NC}"
    pkill -9 -f "run_interview_api.py|audio_tools/.*tts|audio_tools/.*stt|debug_memory_api.py"
    echo -e "${GREEN}All remaining processes terminated.${NC}"
else
    echo -e "${GREEN}All services stopped successfully.${NC}"
fi

# Make sure port 5030 is free
echo -e "${YELLOW}Ensuring port 5030 is free...${NC}"
lsof -i :5030 | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null || true

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}    Daria Interview Tool shutdown complete             ${NC}"
echo -e "${GREEN}======================================================${NC}" 