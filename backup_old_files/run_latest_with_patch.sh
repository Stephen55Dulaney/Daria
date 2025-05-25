#!/bin/bash

# DARIA Interview Tool with Python 3.13 Compatibility Patch
# Latest version with all features

# Get the directory where this script resides
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Use port 5025 as required by EC2 security group
DARIA_PORT=5025
MEMORY_PORT=5030

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  DARIA Latest with Python 3.13 Patch ${NC}"
echo -e "${GREEN}===========================================${NC}"

# Stop any existing processes
echo -e "${YELLOW}Stopping any existing processes...${NC}"
pkill -f "python.*run_interview_api.py" || true
pkill -f "elevenlabs_tts.py" || true
pkill -f "stt_service.py" || true
pkill -f "simple_stt_server.py" || true
pkill -f "debug_memory_api.py" || true
lsof -i :$DARIA_PORT | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null || true
lsof -i :$MEMORY_PORT | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null || true
sleep 1

# Make scripts executable
chmod +x "${SCRIPT_DIR}/py313_patch.py"

# Check if simple_stt_server.py exists
if [ -f "${SCRIPT_DIR}/audio_tools/simple_stt_server.py" ]; then
    STT_SCRIPT="simple_stt_server.py"
else
    STT_SCRIPT="stt_service.py"
fi

# Start TTS service (in background)
echo -e "${YELLOW}Starting TTS service...${NC}"
cd "${SCRIPT_DIR}/audio_tools" && python elevenlabs_tts.py --port 5015 > "${SCRIPT_DIR}/tts.log" 2>&1 &
TTS_PID=$!
echo -e "${GREEN}TTS service started (PID: $TTS_PID)${NC}"

# Start STT service (in background)
echo -e "${YELLOW}Starting STT service...${NC}"
cd "${SCRIPT_DIR}/audio_tools" && python $STT_SCRIPT --port 5016 > "${SCRIPT_DIR}/stt.log" 2>&1 &
STT_PID=$!
echo -e "${GREEN}STT service started (PID: $STT_PID)${NC}"

# Wait for services to initialize
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 2

# Run the main application with our patch
echo -e "${YELLOW}Starting DARIA API server with Python 3.13 compatibility patch...${NC}"
cd "${SCRIPT_DIR}" && python py313_patch.py run_interview_api.py --port $DARIA_PORT --use-langchain > "${SCRIPT_DIR}/daria.log" 2>&1 &
DARIA_PID=$!
echo -e "${GREEN}DARIA API server started (PID: $DARIA_PID)${NC}"

# Start Memory Companion service
echo -e "${YELLOW}Starting Memory Companion service...${NC}"
cd "${SCRIPT_DIR}" && python py313_patch.py debug_memory_api.py --port $MEMORY_PORT > "${SCRIPT_DIR}/memory_companion.log" 2>&1 &
MEMORY_PID=$!
echo -e "${GREEN}Memory Companion service started (PID: $MEMORY_PID)${NC}"

# Wait a moment
sleep 2

# Check if processes are still running
echo -e "${YELLOW}Checking service status...${NC}"
if ps -p $TTS_PID > /dev/null; then
    echo -e "${GREEN}TTS service is running${NC}"
else
    echo -e "${RED}TTS service failed to start - check tts.log${NC}"
    echo -e "${YELLOW}Last 10 lines of tts.log:${NC}"
    tail -n 10 "${SCRIPT_DIR}/tts.log"
fi

if ps -p $STT_PID > /dev/null; then
    echo -e "${GREEN}STT service is running${NC}"
else
    echo -e "${RED}STT service failed to start - check stt.log${NC}"
    echo -e "${YELLOW}Last 10 lines of stt.log:${NC}"
    tail -n 10 "${SCRIPT_DIR}/stt.log"
fi

if ps -p $DARIA_PID > /dev/null; then
    echo -e "${GREEN}DARIA API server is running${NC}"
else
    echo -e "${RED}DARIA API server failed to start - check daria.log${NC}"
    echo -e "${YELLOW}Last 10 lines of daria.log:${NC}"
    tail -n 10 "${SCRIPT_DIR}/daria.log"
fi

if ps -p $MEMORY_PID > /dev/null; then
    echo -e "${GREEN}Memory Companion service is running${NC}"
else
    echo -e "${RED}Memory Companion service failed to start - check memory_companion.log${NC}"
    echo -e "${YELLOW}Last 10 lines of memory_companion.log:${NC}"
    tail -n 10 "${SCRIPT_DIR}/memory_companion.log"
fi

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Services:${NC}"
echo -e "${GREEN}  TTS Service:    ${NC}http://localhost:5015"
echo -e "${GREEN}  STT Service:    ${NC}http://localhost:5016"
echo -e "${GREEN}  DARIA API:      ${NC}http://localhost:$DARIA_PORT"
echo -e "${GREEN}  DARIA Dashboard:${NC}http://localhost:$DARIA_PORT/dashboard"
echo -e "${GREEN}  AI Observer:    ${NC}http://localhost:$DARIA_PORT/static/debug_ai_observer_with_controls.html"
echo -e "${GREEN}  Memory Companion:${NC}http://localhost:$MEMORY_PORT/static/daria_memory_companion.html"
echo -e "${GREEN}===========================================${NC}"
echo -e "${YELLOW}Log files: tts.log, stt.log, daria.log, memory_companion.log${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running until user presses Ctrl+C
wait $DARIA_PID 