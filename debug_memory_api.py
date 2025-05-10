#!/usr/bin/env python3
"""
Debug script for the Memory Companion API.
This script tests the API integration by creating a simple Flask app
that just includes the Memory Companion blueprint.
"""

import os
import sys
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY is not set in environment variables")
    print("LLM functionality will not work without API keys")

# Create simple Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Try to import and register the memory companion blueprint
try:
    from api_services.memory_companion_service import memory_companion_bp
    app.register_blueprint(memory_companion_bp)
    print("Successfully registered Memory Companion blueprint")
except Exception as e:
    print(f"Error registering Memory Companion blueprint: {str(e)}")
    print(f"Exception type: {type(e).__name__}")
    print("Traceback:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Add a simple root route
@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'message': 'Memory Companion Debug Server is running',
        'endpoints': [
            '/api/memory_companion/test',
            '/api/memory_companion/project_data',
            '/api/memory_companion/chat',
            '/static/daria_memory_companion.html'
        ]
    })

if __name__ == '__main__':
    print("Starting Memory Companion Debug Server...")
    print("Available routes:")
    print("  * /api/memory_companion/test")
    print("  * /api/memory_companion/project_data")
    print("  * /api/memory_companion/chat (POST)")
    print("  * /static/daria_memory_companion.html")
    print("\nOpen http://localhost:5030/ in your browser to test the API")
    app.run(host='0.0.0.0', port=5030, debug=True) 