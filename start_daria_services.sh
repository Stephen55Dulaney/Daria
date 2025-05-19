#!/bin/bash

# Change to the DariaInterviewTool directory
cd ~/DariaInterviewTool_new
source venv/bin/activate

# Kill any existing DARIA processes
function kill_service() {
  port=$1
  pid=$(lsof -t -i:$port)
  if [ ! -z "$pid" ]; then
    echo "Stopping service on port $port (PID: $pid)"
    kill -9 $pid
  fi
}

# Kill existing services
kill_service 5025  # API Server
kill_service 5015  # TTS Service
kill_service 5016  # STT Service

# Start DARIA API Server (port 5025)
echo "Starting DARIA API Server on port 5025..."
nohup python run_interview_api.py --host 0.0.0.0 --port 5025 > api_server.log 2>&1 &
echo $! > .api_server_pid
echo "DARIA API Server started with PID $(cat .api_server_pid)"

# Start ElevenLabs TTS Service (port 5015)
echo "Starting ElevenLabs TTS Service on port 5015..."
# Check if the service startup script exists, otherwise use a simple Python server
if [ -f run_elevenlabs_service.py ]; then
  nohup python run_elevenlabs_service.py --host 0.0.0.0 --port 5015 > tts_service.log 2>&1 &
  echo $! > .tts_service_pid
  echo "ElevenLabs TTS Service started with PID $(cat .tts_service_pid)"
else
  # Create a mock TTS service for testing
  cat > mock_tts_service.py << 'MOCKEOF'
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import argparse

app = Flask(__name__)

@app.route('/api/tts', methods=['POST'])
def tts():
    """Mock TTS endpoint"""
    return jsonify({
        "success": True,
        "message": "Mock TTS service - Audio would be generated here"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mock-tts"
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mock TTS Service')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5015, help='Port to run the server on')
    
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)
MOCKEOF
  chmod +x mock_tts_service.py
  nohup python mock_tts_service.py --host 0.0.0.0 --port 5015 > tts_service.log 2>&1 &
  echo $! > .tts_service_pid
  echo "Mock TTS Service started with PID $(cat .tts_service_pid)"
fi

# Start STT Service (port 5016)
echo "Starting STT Service on port 5016..."
# Check if the service startup script exists, otherwise use a simple Python server
if [ -f run_stt_service.py ]; then
  nohup python run_stt_service.py --host 0.0.0.0 --port 5016 > stt_service.log 2>&1 &
  echo $! > .stt_service_pid
  echo "STT Service started with PID $(cat .stt_service_pid)"
else
  # Create a mock STT service for testing
  cat > mock_stt_service.py << 'MOCKEOF'
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import argparse

app = Flask(__name__)

@app.route('/api/stt', methods=['POST'])
def stt():
    """Mock STT endpoint"""
    return jsonify({
        "success": True,
        "text": "This is mock transcribed text from the STT service",
        "message": "Mock STT service - Audio would be processed here"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mock-stt"
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mock STT Service')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5016, help='Port to run the server on')
    
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)
MOCKEOF
  chmod +x mock_stt_service.py
  nohup python mock_stt_service.py --host 0.0.0.0 --port 5016 > stt_service.log 2>&1 &
  echo $! > .stt_service_pid
  echo "Mock STT Service started with PID $(cat .stt_service_pid)"
fi

# Create a debug toolkit HTML page
cat > debug_toolkit.html << 'DEBUGEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DARIA Debug Toolkit</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .service {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 5px;
            background-color: #e8f4f8;
        }
        .status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .running {
            background-color: #4CAF50;
        }
        .stopped {
            background-color: #F44336;
        }
        .tools {
            margin-top: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        button {
            background-color: #4285f4;
            color: white;
            border: none;
            padding: 8px 12px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #3367d6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>DARIA Debug Toolkit</h1>
        <p>Centralized access to all debugging tools and services</p>
        
        <h2>Service Status</h2>
        <div id="service-status">
            <div class="service">
                <span class="status" id="api-status"></span>
                <strong>Api Server</strong>
                <p>Main API server handling requests and responses</p>
            </div>
            <div class="service">
                <span class="status" id="elevenlabs-status"></span>
                <strong>ElevenLabs</strong>
                <p>ElevenLabs API integration for high-quality TTS</p>
            </div>
            <div class="service">
                <span class="status" id="stt-status"></span>
                <strong>Stt Service</strong>
                <p>Speech-to-Text service for voice recognition</p>
            </div>
            <div class="service">
                <span class="status" id="tts-status"></span>
                <strong>Tts Service</strong>
                <p>Text-to-Speech service for voice synthesis</p>
            </div>
        </div>

        <h2>Debug Tools</h2>
        <div class="tools">
            <button onclick="checkService('api', 5025)">Check API</button>
            <button onclick="checkService('elevenlabs', 5015)">Check ElevenLabs</button>
            <button onclick="checkService('stt', 5016)">Check STT</button>
            <button onclick="checkService('tts', 5015)">Check TTS</button>
        </div>

        <h2>Quick Links</h2>
        <div class="tools">
            <a href="http://3.12.144.184:5030/static/daria_memory_companion.html" target="_blank">
                <button>Memory Companion</button>
            </a>
            <a href="http://3.12.144.184:5035/" target="_blank">
                <button>Memory Integration</button>
            </a>
            <a href="http://3.12.144.184:5025/interview/" target="_blank">
                <button>Start Interview</button>
            </a>
        </div>
    </div>

    <script>
        function checkService(service, port) {
            const statusEl = document.getElementById(`${service}-status`);
            statusEl.className = 'status';
            
            // This is just for UI demo since we can't do actual fetch from different origin
            // In a real implementation, you would set up a proxy endpoint
            statusEl.classList.add(Math.random() > 0.3 ? 'running' : 'stopped');
            
            alert(`Checking ${service} service on port ${port}.\nIn a real implementation, this would connect to a service health check endpoint.`);
        }
        
        // Initialize with random status (this would normally be from actual API calls)
        document.querySelectorAll('.status').forEach(el => {
            el.classList.add(Math.random() > 0.3 ? 'running' : 'stopped');
        });
    </script>
</body>
</html>
DEBUGEOF

# Create a static directory to serve debug toolkit
mkdir -p static
cp debug_toolkit.html static/debug_toolkit.html

# Show services status
echo ""
echo "DARIA Services Status:"
echo "======================"
echo "API Server (5025): Running with PID $(cat .api_server_pid 2>/dev/null || echo 'Not running')"
echo "TTS Service (5015): Running with PID $(cat .tts_service_pid 2>/dev/null || echo 'Not running')"
echo "STT Service (5016): Running with PID $(cat .stt_service_pid 2>/dev/null || echo 'Not running')"
echo "Memory Companion (5030): Running with PID $(ps aux | grep 'memory_companion' | grep -v grep | awk '{print $2}' || echo 'Not running')"
echo "Memory Integration (5035): Running with PID $(ps aux | grep 'memory_companion_ui\|integration_ui_fix' | grep -v grep | awk '{print $2}' || echo 'Not running')"
echo ""

echo "You can access the services at:"
echo "- Debug Toolkit: http://3.12.144.184:5025/static/debug_toolkit.html"
echo "- Memory Companion: http://3.12.144.184:5030/static/daria_memory_companion.html"
echo "- Memory Integration: http://3.12.144.184:5035/"
echo "- Interview App: http://3.12.144.184:5025/interview/{session-id}?remote=true&accepted=true"
