#!/bin/bash

echo "====== DARIA Complete Service Starter ======"
echo "This script will start all required DARIA services"

# First shut down any existing services
./shutdown_daria.sh

# Start services in the correct order
echo ""
echo "Starting Speech-to-Text service on port 5016..."
python audio_tools/simple_stt_server.py --port 5016 &
sleep 2

echo "Starting Text-to-Speech service on port 5015..."
python audio_tools/elevenlabs_tts.py --port 5015 &
sleep 2

echo "Starting Memory Companion service on port 5030..."
python py313_patch.py debug_memory_api.py --port 5030 &
sleep 2

echo "Starting Memory Companion UI on port 5035..."
python memory_companion_ui.py --port 5035 &
sleep 2

echo "Starting main DARIA service on port 5025..."
python run_without_langchain.py --port 5025 &
sleep 3

# Verify the services are running
echo ""
echo "Checking service health..."

# Check main DARIA service
if curl -s http://localhost:5025/api/health | grep -q "\"status\":\"ok\""; then
  echo "✅ Main DARIA service: RUNNING"
else
  echo "❌ Main DARIA service: FAILED"
fi

# Check TTS service
if curl -s http://localhost:5015/health | grep -q "200"; then
  echo "✅ Text-to-Speech service: RUNNING"
else
  echo "❌ Text-to-Speech service: FAILED"
fi

# Check STT service
if curl -s http://localhost:5016/health | grep -q "200"; then
  echo "✅ Speech-to-Text service: RUNNING"
else
  echo "❌ Speech-to-Text service: FAILED"
fi

# Check Memory API
if curl -s http://localhost:5030/api/memory_companion/test | grep -q "working"; then
  echo "✅ Memory API service: RUNNING"
else
  echo "❌ Memory API service: FAILED"
fi

echo ""
echo "All services have been started!"
echo "Access the main application at: http://localhost:5025/"
echo "Access the debug toolkit at: http://localhost:5025/static/debug_toolkit.html"
echo ""
echo "To stop all services, run: ./shutdown_daria.sh" 