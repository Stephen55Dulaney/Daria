#!/bin/bash

echo "====== Restarting DARIA after fixes ======"
echo "Stopping all DARIA services..."

# First, run the shutdown script to ensure all services are stopped
./shutdown_daria.sh

# Wait for ports to be released
echo "Waiting for ports to be released..."
sleep 3

# Now restart the DARIA service without LangChain on the default port 5025
echo "Starting DARIA service on port 5025..."
python run_without_langchain.py --port 5025 &

# Wait for the service to initialize
echo "Waiting for service to start..."
sleep 5

# Test if the server is running
if curl -s http://localhost:5025/api/health | grep -q "\"status\":\"ok\""; then
  echo "✅ DARIA is running successfully!"
  echo "   Access the main application at: http://localhost:5025/"
  echo "   Access the discussion guide page at: http://localhost:5025/discussion_guide/9d9b0648-5f14-4a22-81df-290bbd67049d"
else
  echo "❌ Failed to start DARIA service. Check logs for errors."
fi

echo ""
echo "To stop all DARIA services, run the shutdown_daria.sh script." 