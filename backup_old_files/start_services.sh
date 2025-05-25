#!/bin/bash
# Script to start all services for DARIA Interview Tool

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}     DARIA Interview Tool Service Launcher     ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        return 0 # Port is in use
    else
        return 1 # Port is free
    fi
}

echo "Starting DARIA services..."

# First stop any existing services
./stop_services.sh

# Ensure we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start memory service
echo "Starting memory service..."
python mock_memory_service.py --port 5030 &> memory_companion.log &

# Start STT service
echo "Starting STT service..."
python mock_stt_service.py --port 5015 &> stt_service.log &

# Start TTS service
echo "Starting TTS service..."
python mock_tts_service.py --port 5016 &> tts_service.log &

# Start main application
echo "Starting main application..."
python app.py &> app.log &

# Wait a moment for services to start
sleep 2

# Check if services are running
echo "Checking services..."
curl -s http://127.0.0.1:5030/health || echo "Memory service not responding"
curl -s http://127.0.0.1:5015/health || echo "STT service not responding"
curl -s http://127.0.0.1:5016/health || echo "TTS service not responding"
curl -s http://127.0.0.1:5025/health || echo "Main application not responding"

echo "All services started. Check logs for details:"
echo "- memory_companion.log"
echo "- stt_service.log"
echo "- tts_service.log"
echo "- app.log"

# Print access information
echo -e "\n${GREEN}Services should now be running:${NC}"
echo -e "Main application: ${YELLOW}http://localhost:5010${NC}"
echo -e "Audio service: ${YELLOW}http://localhost:5007${NC}"

echo -e "\n${GREEN}You can access the following pages:${NC}"
echo -e "Dashboard: ${YELLOW}http://localhost:5010/dashboard${NC}"
echo -e "Interview Setup: ${YELLOW}http://localhost:5010/interview_setup${NC}"
echo -e "Prompt Manager: ${YELLOW}http://localhost:5010/prompts/${NC}"

echo -e "\n${YELLOW}To stop the services, run:${NC}"
echo -e "kill $AUDIO_PID $APP_PID"

# Save PIDs to a file for easy cleanup
echo -e "$AUDIO_PID $APP_PID" > .service_pids

echo -e "\n${GREEN}Service PIDs saved to .service_pids file${NC}"
echo -e "You can stop all services with: ${YELLOW}kill \$(cat .service_pids)${NC}"

echo -e "\n${GREEN}===============================================${NC}" 