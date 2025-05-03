#!/bin/bash
# Start both the main application and the audio service

# Check if ELEVENLABS_API_KEY is set
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "Warning: ELEVENLABS_API_KEY environment variable is not set."
    echo "Speech-to-text functionality will be limited."
    echo "Please set it before running this script with:"
    echo "export ELEVENLABS_API_KEY=your_api_key_here"
    read -p "Do you want to continue without the API key? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start the audio service in the background
echo "Starting audio service on port 5007..."
python audio_tools/simple_tts_test.py &
AUDIO_PID=$!

# Wait a moment to ensure audio service starts
sleep 2

# Check if audio service started successfully
if ! curl -s http://localhost:5007/ > /dev/null; then
    echo "Warning: Audio service did not start properly."
    echo "Speech-to-text functionality may not work."
    read -p "Do you want to continue without the audio service? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        # Kill audio service if it's running
        kill $AUDIO_PID 2>/dev/null
        exit 1
    fi
else
    echo "Audio service started successfully."
fi

# Start the main application
echo "Starting main application on port 5010..."
python run_langchain_direct_fixed.py --port 5010

# When the main app exits, also kill the audio service
echo "Shutting down audio service..."
kill $AUDIO_PID 2>/dev/null 