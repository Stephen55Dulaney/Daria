#!/bin/bash

# DARIA Interview Tool with Python 3.13 Compatibility Fix
# This script runs the DARIA interview tool with patches for Python 3.13

# Get the directory where this script resides
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make script executable
chmod +x "${SCRIPT_DIR}/patch_typing.py"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  DARIA Interview Tool with Python 3.13 Fix ${NC}"
echo -e "${GREEN}===========================================${NC}"

# Stop any existing processes
echo -e "${YELLOW}Stopping any existing processes...${NC}"
pkill -f "python.*run_interview_api.py" || true
pkill -f "elevenlabs_tts.py" || true
pkill -f "simple_stt_server.py" || true

# Create a simple wrapper script
echo -e "${YELLOW}Creating wrapper script...${NC}"
cat > "${SCRIPT_DIR}/run_daria_wrapper.py" <<EOF
#!/usr/bin/env python3
# Import and apply the patch
import patch_typing
patch_typing.apply_patch()

# Now run the main script
import sys
import os
import argparse

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run DARIA with Python 3.13 compatibility patch')
    parser.add_argument('--port', type=int, default=5025, help='Port to run the API server on')
    parser.add_argument('--use-langchain', action='store_true', help='Use LangChain features')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Parse the command line arguments
    args = parser.parse_args()
    
    # Modify sys.argv to match what run_interview_api.py expects
    sys.argv = ['run_interview_api.py']
    if args.port:
        sys.argv.extend(['--port', str(args.port)])
    if args.use_langchain:
        sys.argv.append('--use-langchain')
    if args.debug:
        sys.argv.append('--debug')
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the interview API script
    main_script = os.path.join(current_dir, 'run_interview_api.py')
    with open(main_script) as f:
        code = compile(f.read(), main_script, 'exec')
        exec(code, {'__name__': '__main__', '__file__': main_script})

if __name__ == '__main__':
    main()
EOF
chmod +x "${SCRIPT_DIR}/run_daria_wrapper.py"

# Start TTS service (in background)
echo -e "${YELLOW}Starting TTS service...${NC}"
cd "${SCRIPT_DIR}/audio_tools" && python elevenlabs_tts.py --port 5015 > "${SCRIPT_DIR}/tts.log" 2>&1 &
TTS_PID=$!
echo -e "${GREEN}TTS service started (PID: $TTS_PID)${NC}"

# Start STT service (in background)
echo -e "${YELLOW}Starting STT service...${NC}"
cd "${SCRIPT_DIR}/audio_tools" && python simple_stt_server.py --port 5016 > "${SCRIPT_DIR}/stt.log" 2>&1 &
STT_PID=$!
echo -e "${GREEN}STT service started (PID: $STT_PID)${NC}"

# Wait for services to initialize
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 2

# Run the main application with our patch
echo -e "${YELLOW}Starting DARIA API server with Python 3.13 compatibility patch...${NC}"
cd "${SCRIPT_DIR}" && python "${SCRIPT_DIR}/run_daria_wrapper.py" --port=5025 --use-langchain > "${SCRIPT_DIR}/daria.log" 2>&1 &
DARIA_PID=$!
echo -e "${GREEN}DARIA API server started (PID: $DARIA_PID)${NC}"

# Wait a moment
sleep 2

# Check if processes are still running
echo -e "${YELLOW}Checking service status...${NC}"
if ps -p $TTS_PID > /dev/null; then
    echo -e "${GREEN}TTS service is running${NC}"
else
    echo -e "${RED}TTS service failed to start - check tts.log${NC}"
fi

if ps -p $STT_PID > /dev/null; then
    echo -e "${GREEN}STT service is running${NC}"
else
    echo -e "${RED}STT service failed to start - check stt.log${NC}"
fi

if ps -p $DARIA_PID > /dev/null; then
    echo -e "${GREEN}DARIA API server is running${NC}"
else
    echo -e "${RED}DARIA API server failed to start - check daria.log${NC}"
    echo -e "${YELLOW}Last 10 lines of daria.log:${NC}"
    tail -n 10 "${SCRIPT_DIR}/daria.log"
fi

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Services:${NC}"
echo -e "${GREEN}  TTS Service:    ${NC}http://localhost:5015"
echo -e "${GREEN}  STT Service:    ${NC}http://localhost:5016"
echo -e "${GREEN}  DARIA API:      ${NC}http://localhost:5025"
echo -e "${GREEN}  DARIA Dashboard:${NC}http://localhost:5025/dashboard"
echo -e "${GREEN}===========================================${NC}"
echo -e "${YELLOW}Log files: tts.log, stt.log, daria.log${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running until user presses Ctrl+C
wait $DARIA_PID 