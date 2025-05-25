#!/bin/bash
# Comprehensive restart script for DARIA Interview Tool

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Complete System Restart Script     ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Load environment variables
if [ -f .env ]; then
  echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
  export $(cat .env | grep -v '^#' | xargs)
else
  echo -e "${RED}No .env file found. Some services may not function properly.${NC}"
fi

# Function to check if port is in use
check_port() {
  local port=$1
  lsof -i :$port >/dev/null 2>&1
  return $?
}

# Function to kill process on a specific port
kill_process_on_port() {
  local port=$1
  local pid=$(lsof -t -i :$port 2>/dev/null)
  if [ -n "$pid" ]; then
    echo -e "${YELLOW}Killing process $pid on port $port...${NC}"
    kill -9 $pid 2>/dev/null
    sleep 1
  fi
}

# Function to check and free ports
free_ports() {
  local ports=("$@")
  for port in "${ports[@]}"; do
    if check_port $port; then
      echo -e "${YELLOW}Port $port is in use. Stopping the process...${NC}"
      kill_process_on_port $port
    else
      echo -e "${GREEN}Port $port is free.${NC}"
    fi
  done
}

# Kill any Python processes that might be related to DARIA
echo -e "\n${YELLOW}Stopping any running DARIA processes...${NC}"
pkill -f "run_interview_api.py" 2>/dev/null
pkill -f "debug_memory_api.py" 2>/dev/null
pkill -f "tts_service.py" 2>/dev/null
pkill -f "stt_service.py" 2>/dev/null
pkill -f "elevenlabs_tts.py" 2>/dev/null
sleep 2

# Free up all required ports
echo -e "\n${YELLOW}Ensuring all required ports are free...${NC}"
free_ports 5015 5016 5025 5030

# Ensure virtual environment is activated
if [ -d "venv" ]; then
  echo -e "\n${YELLOW}Activating virtual environment...${NC}"
  source venv/bin/activate
elif [ -d "venv_py310" ]; then
  echo -e "\n${YELLOW}Activating Python 3.10 virtual environment...${NC}"
  source venv_py310/bin/activate
else
  echo -e "${RED}No virtual environment found. Please create one and install dependencies.${NC}"
  exit 1
fi

# Start TTS service
echo -e "\n${YELLOW}Starting TTS service on port 5015...${NC}"
cd audio_tools
python elevenlabs_tts.py --port 5015 > ../tts_service.log 2>&1 &
TTS_PID=$!
cd ..
sleep 2
if check_port 5015; then
  echo -e "${GREEN}TTS service started successfully (PID: $TTS_PID).${NC}"
else
  echo -e "${RED}Failed to start TTS service. Check tts_service.log for details.${NC}"
  exit 1
fi

# Start STT service
echo -e "\n${YELLOW}Starting STT service on port 5016...${NC}"
cd audio_tools
python stt_service.py --port 5016 > ../stt_service.log 2>&1 &
STT_PID=$!
cd ..
sleep 2
if check_port 5016; then
  echo -e "${GREEN}STT service started successfully (PID: $STT_PID).${NC}"
else
  echo -e "${RED}Failed to start STT service. Check stt_service.log for details.${NC}"
  exit 1
fi

# Start Memory Companion service
echo -e "\n${YELLOW}Starting Memory Companion service on port 5030...${NC}"
python debug_memory_api.py > memory_companion.log 2>&1 &
MEM_PID=$!
sleep 2
if check_port 5030; then
  echo -e "${GREEN}Memory Companion service started successfully (PID: $MEM_PID).${NC}"
else
  echo -e "${RED}Failed to start Memory Companion service. Check memory_companion.log for details.${NC}"
  exit 1
fi

# Start main Interview API with LangChain enabled
echo -e "\n${YELLOW}Starting Interview API with LangChain on port 5025...${NC}"
python run_interview_api.py --use-langchain --port 5025 > interview_api.log 2>&1 &
API_PID=$!
sleep 3
if check_port 5025; then
  echo -e "${GREEN}Interview API started successfully (PID: $API_PID).${NC}"
else
  echo -e "${RED}Failed to start Interview API. Check interview_api.log for details.${NC}"
  exit 1
fi

# Save process IDs for easy management
echo "$TTS_PID $STT_PID $MEM_PID $API_PID" > .daria_pids
echo -e "\n${GREEN}All process IDs saved to .daria_pids file.${NC}"

# Print service access information
echo -e "\n${GREEN}DARIA services are now running:${NC}"
echo -e "Interview API: ${YELLOW}http://localhost:5025/api/health${NC}"
echo -e "TTS Service: ${YELLOW}http://localhost:5015/${NC}"
echo -e "STT Service: ${YELLOW}http://localhost:5016/${NC}"
echo -e "Memory Companion: ${YELLOW}http://localhost:5030/${NC}"

echo -e "\n${YELLOW}To stop all services, run:${NC}"
echo -e "${GREEN}bash -c 'kill \$(cat .daria_pids)'${NC}"

echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA System Successfully Started        ${NC}"
echo -e "${GREEN}===============================================${NC}" 