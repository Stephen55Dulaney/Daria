#!/bin/bash
# Script to stop all Daria services

echo "===== STOPPING ALL DARIA SERVICES ====="
echo "Cleaning up any existing processes..."
echo "Stopping all Daria services..."
lsof -ti :5025 | xargs kill -9 2>/dev/null
lsof -ti :5030 | xargs kill -9 2>/dev/null
lsof -ti :5035 | xargs kill -9 2>/dev/null
lsof -ti :5015 | xargs kill -9 2>/dev/null
lsof -ti :5016 | xargs kill -9 2>/dev/null
pkill -f run_interview_api.py
pkill -f memory_companion_ui.py
pkill -f tts_service.py
pkill -f stt_service.py
pkill -f mock_tts_service.py
pkill -f mock_stt_service.py
sleep 1
echo "All Daria services have been stopped." 