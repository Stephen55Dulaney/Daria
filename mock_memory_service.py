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
