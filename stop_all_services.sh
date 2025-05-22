#!/bin/bash
# Script to stop all Daria services

echo "===== STOPPING ALL DARIA SERVICES ====="
echo "Cleaning up any existing processes..."
pkill -f "mock_tts|debug_memory|memory_companion_ui|integration_ui_fix|py313_patch"
sleep 1
echo "All Daria services have been stopped." 