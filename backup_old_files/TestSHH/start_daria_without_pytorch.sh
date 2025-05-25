#!/bin/bash
# Start DARIA services without PyTorch dependencies

echo "Starting DARIA services without PyTorch..."

# Kill any existing processes
pkill -f run_interview_api.py
pkill -f debug_memory_api.py
pkill -f tts_service.py
pkill -f stt_service.py
pkill -f elevenlabs_tts.py
sleep 2

# Make sure we're in the DARIA directory
cd ~/DariaInterviewTool

# Activate virtual environment
source venv/bin/activate

# Start TTS service
cd audio_tools
python elevenlabs_tts.py --port 5015 > ../tts.log 2>&1 &
cd ..

# Start STT service
cd audio_tools
python stt_service.py --port 5016 > ../stt.log 2>&1 &
cd ..

# Start Memory Companion service (required for AI Observer)
python debug_memory_api.py > memory_companion.log 2>&1 &
sleep 2

# Start main interview API
python run_interview_api.py --port 5025 --use-langchain > interview_api.log 2>&1 &

echo "All DARIA services started!"
echo "Web interface available at: http://HOSTNAME:5025"
echo "API health check: http://HOSTNAME:5025/api/health" 