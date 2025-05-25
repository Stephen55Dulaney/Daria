#!/bin/bash

echo "====== Starting DARIA Interview Tool with LangChain and OpenAI ======"
BASE_DIR=$(pwd)
echo "Base directory: $BASE_DIR"

# Stop any existing processes
echo "Stopping any existing DARIA processes..."
pkill -f "python.*run" 2>/dev/null || true
lsof -ti:5025 | xargs kill -9 2>/dev/null || true
lsof -ti:5015 | xargs kill -9 2>/dev/null || true
lsof -ti:5016 | xargs kill -9 2>/dev/null || true
lsof -ti:5030 | xargs kill -9 2>/dev/null || true
sleep 3

# Create necessary directories
echo "Setting up required directories..."
mkdir -p data/interviews/sessions
mkdir -p logs
mkdir -p static
mkdir -p templates

# Fix syntax errors in discussion_service.py
echo "Fixing syntax errors in discussion_service.py..."
python fix_all_syntax_issues.py langchain_features/services/discussion_service.py

# Configure OpenAI API key if not set
if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY environment variable not set."
  echo "Would you like to enter your OpenAI API key now? (y/n)"
  read -r response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Enter your OpenAI API key:"
    read -r api_key
    export OPENAI_API_KEY="$api_key"
  else
    echo "Continuing without OpenAI API key. Some functionality may be limited."
  fi
fi

# Create a simple mock OpenAI provider if needed
echo "Creating mock OpenAI provider for compatibility..."
cat > mock_openai_provider.py << 'EOF'
"""Mock OpenAI Provider for DARIA compatibility"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class MockOpenAIProvider:
    """A mock OpenAI provider that returns predefined responses"""
    
    def __init__(self):
        self.model = "gpt-4"
        logger.info("Initialized MockOpenAIProvider with model=gpt-4")
    
    def complete(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return a mock completion response"""
        logger.info(f"Mock completion for prompt: {prompt[:50]}...")
        return {
            "choices": [
                {
                    "text": "I am a mock response from the interview AI.",
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 10,
                "total_tokens": len(prompt.split()) + 10
            }
        }
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Return a mock chat response"""
        logger.info(f"Mock chat with {len(messages)} messages")
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I am a mock response from the interview AI."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                "completion_tokens": 10,
                "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + 10
            }
        }

# Create a singleton instance
provider = MockOpenAIProvider()
EOF

# Create a simple OpenAI adapter for LangChain
echo "Creating OpenAI adapter for LangChain..."
cat > openai_langchain_adapter.py << 'EOF'
"""OpenAI adapter for LangChain compatibility"""

import os
import logging
from typing import Any, Dict, List, Optional

# Try to import OpenAI or use the mock provider
try:
    from openai import OpenAI
    USING_OPENAI = True
except ImportError:
    from mock_openai_provider import provider
    USING_OPENAI = False

# LangChain imports
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import LLMResult

logger = logging.getLogger(__name__)

class OpenAILangChainAdapter(LLM):
    """Adapter to use OpenAI with LangChain"""
    
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 500
    
    @property
    def _llm_type(self) -> str:
        return "openai-adapter"
    
    def _call(
        self, 
        prompt: str, 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Call the OpenAI API or mock provider"""
        try:
            if USING_OPENAI:
                client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                response = client.completions.create(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stop=stop
                )
                return response.choices[0].text.strip()
            else:
                response = provider.complete(prompt)
                return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Error calling OpenAI: {str(e)}")
            return "I'm sorry, I encountered an error processing that request."
    
    def generate(
        self, 
        prompts: List[str], 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Generate text from multiple prompts"""
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop, run_manager, **kwargs)
            generations.append([{"text": text}])
        return LLMResult(generations=generations)
EOF

# Create a quick fix for the interview agent
echo "Creating fix for interview agent initialization..."
cat > fix_interview_agent.py << 'EOF'
"""Fix script for the interview agent"""

import sys
import re

def fix_interview_agent():
    """Fix the interview agent to use our adapter"""
    try:
        with open('langchain_features/services/interview_agent.py', 'r') as f:
            content = f.read()
        
        # Add import for our adapter
        if "from openai_langchain_adapter import OpenAILangChainAdapter" not in content:
            content = re.sub(
                r'from langchain.prompts import',
                'from openai_langchain_adapter import OpenAILangChainAdapter\nfrom langchain.prompts import',
                content
            )
        
        # Replace the LLM initialization
        content = re.sub(
            r'self\.llm = .*',
            'self.llm = OpenAILangChainAdapter(model_name="gpt-4", temperature=0.7)',
            content
        )
        
        with open('langchain_features/services/interview_agent.py', 'w') as f:
            f.write(content)
        
        print("Successfully fixed interview_agent.py")
        return True
    except Exception as e:
        print(f"Error fixing interview_agent.py: {str(e)}")
        return False

if __name__ == "__main__":
    fix_interview_agent()
EOF

# Execute the fix
echo "Running fixes for interview agent..."
python fix_interview_agent.py

# Make scripts executable
chmod +x fix_pydantic_forward_refs.py

# Start the services
echo "Starting all DARIA services with LangChain enabled..."

# 1. Start the TTS service on port 5015
echo "Starting TTS service on port 5015..."
if [ -f "elevenlabs_tts.py" ]; then
    python fix_pydantic_forward_refs.py elevenlabs_tts.py --port 5015 > logs/tts.log 2>&1 &
    TTS_PID=$!
    echo "TTS service started with PID: $TTS_PID"
else
    echo "Creating mock TTS service..."
    cat > mock_tts_service.py << 'EOF'
#!/usr/bin/env python3
"""Mock TTS service for DARIA"""

import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """Mock synthesis endpoint"""
    data = request.json
    text = data.get('text', '')
    voice_id = data.get('voice_id', 'default')
    
    # Return a mock audio URL
    return jsonify({
        "status": "success",
        "audio_url": f"mock_audio_{int(time.time())}.mp3",
        "text": text,
        "voice_id": voice_id
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5015))
    app.run(host='0.0.0.0', port=port)
EOF
    chmod +x mock_tts_service.py
    python mock_tts_service.py > logs/tts.log 2>&1 &
    TTS_PID=$!
    echo "Mock TTS service started with PID: $TTS_PID"
fi

# 2. Start the STT service on port 5016
echo "Starting STT service on port 5016..."
if [ -f "stt_service.py" ]; then
    python fix_pydantic_forward_refs.py stt_service.py --port 5016 > logs/stt.log 2>&1 &
    STT_PID=$!
    echo "STT service started with PID: $STT_PID"
else
    echo "Creating mock STT service..."
    cat > mock_stt_service.py << 'EOF'
#!/usr/bin/env python3
"""Mock STT service for DARIA"""

import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Mock transcribe endpoint"""
    # Return a mock transcript
    return jsonify({
        "status": "success",
        "transcript": "This is a mock transcript generated by the STT service.",
        "confidence": 0.95
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5016))
    app.run(host='0.0.0.0', port=port)
EOF
    chmod +x mock_stt_service.py
    python mock_stt_service.py > logs/stt.log 2>&1 &
    STT_PID=$!
    echo "Mock STT service started with PID: $STT_PID"
fi

# Wait for audio services to initialize
echo "Waiting for audio services to initialize..."
sleep 5

# 3. Start the Memory Companion service on port 5030
echo "Starting Memory Companion service on port 5030..."
if [ -f "memory_companion.py" ]; then
    python fix_pydantic_forward_refs.py memory_companion.py --port 5030 > logs/memory.log 2>&1 &
    MEMORY_PID=$!
    echo "Memory Companion service started with PID: $MEMORY_PID"
else
    echo "Creating mock Memory Companion service..."
    cat > mock_memory_service.py << 'EOF'
#!/usr/bin/env python3
"""Mock Memory Companion service for DARIA"""

import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Mock memory retrieval endpoint"""
    return jsonify({
        "status": "success",
        "memories": [
            {"id": "1", "content": "Mock memory 1", "timestamp": time.time()},
            {"id": "2", "content": "Mock memory 2", "timestamp": time.time()},
        ]
    })

@app.route('/api/memory', methods=['POST'])
def store_memory():
    """Mock memory storage endpoint"""
    return jsonify({
        "status": "success",
        "message": "Memory stored successfully"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5030))
    app.run(host='0.0.0.0', port=port)
EOF
    chmod +x mock_memory_service.py
    python mock_memory_service.py > logs/memory.log 2>&1 &
    MEMORY_PID=$!
    echo "Mock Memory Companion service started with PID: $MEMORY_PID"
fi

# Wait for memory service to initialize
echo "Waiting for memory service to initialize..."
sleep 3

# 4. Start the main DARIA API service
echo "Starting main DARIA API on port 5025 with LangChain enabled..."
python fix_pydantic_forward_refs.py run_interview_api.py --use-langchain --port 5025 > logs/daria.log 2>&1 &
DARIA_PID=$!
echo "DARIA started with PID: $DARIA_PID"

# Wait for all services to initialize
echo "Waiting for all services to initialize..."
sleep 10

# Verify all services are running
echo "Testing all services..."

# Check main DARIA service
if curl -s "http://localhost:5025/api/health" > /dev/null; then
    echo "✅ DARIA API service is running successfully!"
    DARIA_RUNNING=true
else
    echo "❌ DARIA API service failed to start. Check logs/daria.log for errors."
    DARIA_RUNNING=false
fi

# Check TTS service
if curl -s "http://localhost:5015/health" > /dev/null; then
    echo "✅ TTS service is running successfully!"
    TTS_RUNNING=true
else
    echo "❌ TTS service failed to start. Check logs/tts.log for errors."
    TTS_RUNNING=false
fi

# Check STT service
if curl -s "http://localhost:5016/health" > /dev/null; then
    echo "✅ STT service is running successfully!"
    STT_RUNNING=true
else
    echo "❌ STT service failed to start. Check logs/stt.log for errors."
    STT_RUNNING=false
fi

# Check Memory Companion service
if curl -s "http://localhost:5030/health" > /dev/null; then
    echo "✅ Memory Companion service is running successfully!"
    MEMORY_RUNNING=true
else
    echo "❌ Memory Companion service failed to start. Check logs/memory.log for errors."
    MEMORY_RUNNING=false
fi

echo ""
echo "====== DARIA Services Status ======="
echo "📁 Main DARIA API (port 5025): ${DARIA_RUNNING}"
echo "🔊 TTS Service (port 5015): ${TTS_RUNNING}"
echo "🎤 STT Service (port 5016): ${STT_RUNNING}"
echo "🧠 Memory Service (port 5030): ${MEMORY_RUNNING}"
echo ""

if [ "$DARIA_RUNNING" = true ] && [ "$TTS_RUNNING" = true ] && [ "$STT_RUNNING" = true ] && [ "$MEMORY_RUNNING" = true ]; then
    echo "✅ All required services are running!"
    echo ""
    echo "📱 Access the main application at: http://localhost:5025/"
    echo "🧪 Access the interview debug page at: http://localhost:5025/static/debug_interview_flow.html?port=5025"
    echo "🛠️ Access the debug toolkit at: http://localhost:5025/static/debug_toolkit.html"
else
    echo "❌ Some services failed to start. Please check the logs for more information."
fi

echo ""
echo "Press Ctrl+C to stop all services when done."

# Keep the script running until user interrupts
wait $DARIA_PID 