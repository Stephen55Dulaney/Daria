#!/bin/bash
# Source environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start Daria with memory companion
echo "Starting Memory Companion on port 5030..."
source venv/bin/activate
python debug_memory_api.py
