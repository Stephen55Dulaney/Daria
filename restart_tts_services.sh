#!/bin/bash

# Enhanced script to restart all TTS and audio services with better error handling

echo "====================== TTS Service Restart Tool ======================"
echo "This script will restart all TTS-related services to fix audio issues."
echo "===================================================================="

# Function to check if a process is running
check_process() {
    local process_name=$1
    local pid=$(pgrep -f "$process_name")
    if [ -n "$pid" ]; then
        echo "✅ $process_name is running (PID: $pid)"
        return 0
    else
        echo "❌ $process_name is NOT running"
        return 1
    fi
}

# Function to stop a process
stop_process() {
    local process_name=$1
    local pid=$(pgrep -f "$process_name")
    if [ -n "$pid" ]; then
        echo "Stopping $process_name (PID: $pid)..."
        kill -15 $pid
        sleep 1
        # Check if it's still running and force kill if needed
        if pgrep -f "$process_name" > /dev/null; then
            echo "Process didn't stop gracefully, force killing..."
            kill -9 $(pgrep -f "$process_name")
        fi
        echo "Process stopped."
    else
        echo "$process_name is not running."
    fi
}

# Stop all TTS-related services
echo "Stopping all TTS and audio services..."
stop_process "python.*audio_tools/elevenlabs_tts.py"
stop_process "python.*audio_tools/debug_tts_service.py"
stop_process "python.*audio_tools/tts_service.py"
stop_process "python.*run_audio_services.py"

# Ensure service PID files are removed/reset
echo "Cleaning up PID files..."
if [ -f ".service_pids" ]; then
    rm .service_pids
    echo "Removed .service_pids file"
fi

# Check for port conflicts
check_port() {
    local port=$1
    if lsof -i:$port -t &> /dev/null; then
        echo "⚠️ Warning: Port $port is already in use by PID $(lsof -i:$port -t)"
        read -p "Would you like to kill the process using port $port? (y/n): " kill_port
        if [[ $kill_port == "y" || $kill_port == "Y" ]]; then
            kill -9 $(lsof -i:$port -t) &> /dev/null
            echo "Process killed. Port $port is now available."
        else
            echo "Please free up port $port manually before continuing."
            return 1
        fi
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

# Check TTS-related ports
echo "Checking TTS service ports..."
check_port 5007 # Main TTS service
check_port 5015 # Elevenlabs TTS service

# Start the TTS services
echo "Starting TTS services..."

# Start ElevenLabs TTS service
echo "Starting ElevenLabs TTS service..."
python audio_tools/elevenlabs_tts.py --port 5015 > tts_service.log 2>&1 &
echo $! >> .service_pids
echo "ElevenLabs TTS service started on port 5015 (PID: $!)"

# Wait for service to initialize
sleep 2

# Test the TTS service
echo "Testing ElevenLabs TTS service..."
if curl -s "http://localhost:5015/health" | grep -q "ok"; then
    echo "✅ ElevenLabs TTS service is working"
else
    echo "❌ ElevenLabs TTS service health check failed"
fi

# Start main TTS service
echo "Starting main TTS service..."
python audio_tools/tts_service.py --port 5007 > audio_service.log 2>&1 &
echo $! >> .service_pids
echo "Main TTS service started on port 5007 (PID: $!)"

# Wait for service to initialize
sleep 2

# Check the services are running
echo "Checking service status..."
check_process "python.*elevenlabs_tts.py"
check_process "python.*tts_service.py"

echo "===================================================================="
echo "TTS services restarted. To test TTS, open the minimal_remote_interview.html"
echo "If issues persist, check the logs in tts_service.log and audio_service.log"
echo "====================================================================" 