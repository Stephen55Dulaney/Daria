#!/bin/bash

# Daria Interview Tool Startup Script with Disaster Recovery
# This script starts all necessary services and ensures data persistence

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}    Starting Daria Interview Tool with Recovery       ${NC}"
echo -e "${GREEN}======================================================${NC}"

# Ensure data directories exist
echo -e "${YELLOW}Ensuring data directories exist...${NC}"
mkdir -p data/discussions
mkdir -p data/discussions/sessions
mkdir -p data/interviews

# Check for debug guide
if [ ! -f "data/discussions/debug_guide.json" ]; then
    echo -e "${YELLOW}Creating default debug guide...${NC}"
    cat > data/discussions/debug_guide.json << 'EOF'
{
  "id": "debug_guide_001",
  "title": "Debug Interview Guide",
  "project": "Debug Testing",
  "interview_type": "debug_test",
  "prompt": "This is a debug guide for testing the interview flow.",
  "interview_prompt": "You are a helpful AI assistant conducting an interview to debug the system. Ask simple questions and provide clear responses.",
  "analysis_prompt": "Analyze the conversation for any technical issues or anomalies.",
  "character_select": "interviewer",
  "voice_id": "EXAVITQu4vr4xnSDxMaL",
  "target_audience": {
    "name": "Debug User",
    "role": "Tester",
    "department": "QA"
  },
  "created_at": "2023-05-07T16:00:00.000Z",
  "updated_at": "2023-05-07T16:00:00.000Z",
  "status": "active",
  "sessions": [],
  "custom_questions": [
    "How is the system working for you?",
    "Are you experiencing any technical issues?",
    "Is the audio quality acceptable?",
    "How responsive is the interface?",
    "Are the AI responses relevant and helpful?"
  ],
  "time_per_question": 2,
  "options": {
    "show_transcript": true,
    "auto_advance": false,
    "record_audio": true
  }
}
EOF
    echo -e "${GREEN}Default debug guide created.${NC}"
fi

# Stop any existing services
echo -e "${YELLOW}Stopping existing services...${NC}"
pkill -f "run_interview_api.py" || true
pkill -f "audio_tools/.*tts" || true
pkill -f "audio_tools/.*stt" || true

# Start TTS service
echo -e "${YELLOW}Starting TTS service...${NC}"
if [ -f "audio_tools/elevenlabs_tts_direct.py" ]; then
    python audio_tools/elevenlabs_tts_direct.py --port 5015 > tts_service.log 2>&1 &
    TTS_PID=$!
    echo -e "${GREEN}TTS service started (PID: $TTS_PID).${NC}"
else
    echo -e "${RED}TTS service file not found. Using elevenlabs_tts.py instead.${NC}"
    python audio_tools/elevenlabs_tts.py --port 5015 > tts_service.log 2>&1 &
    TTS_PID=$!
    echo -e "${GREEN}Legacy TTS service started (PID: $TTS_PID).${NC}"
fi

# Start STT service
echo -e "${YELLOW}Starting STT service...${NC}"
if [ -f "audio_tools/mock_stt.py" ]; then
    python audio_tools/mock_stt.py --port 5016 > stt_service.log 2>&1 &
    STT_PID=$!
    echo -e "${GREEN}STT service started (PID: $STT_PID).${NC}"
else
    echo -e "${RED}Mock STT service file not found. Please install it.${NC}"
fi

# Wait a moment for services to initialize
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 2

# Start the main API server with LangChain enabled for full functionality
echo -e "${YELLOW}Starting API server with LangChain enabled...${NC}"
python run_interview_api.py --port 5025 --debug --use-langchain > api_server.log 2>&1 &
API_PID=$!
echo -e "${GREEN}API server started (PID: $API_PID).${NC}"

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}    All services started successfully                 ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}TTS Service:       ${NC}http://localhost:5015"
echo -e "${GREEN}STT Service:       ${NC}http://localhost:5016"
echo -e "${GREEN}API Server:        ${NC}http://localhost:5025"
echo -e "${GREEN}Dashboard:         ${NC}http://localhost:5025/dashboard"
echo -e "${GREEN}Discussion Guides: ${NC}http://localhost:5025/discussion_guides"
echo -e "${GREEN}Debug Interview:   ${NC}http://localhost:5025/static/debug_interview_flow.html?port=5025"
echo -e "${GREEN}======================================================${NC}"

# Keep script running to allow easy stopping with Ctrl+C
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
wait $API_PID 