#!/usr/bin/env python3
"""
Simplified Speech-to-Text service with reliable health check
"""

import argparse
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import random
import logging
import threading
import time
import socketserver

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run Simple STT Service')
parser.add_argument('--port', type=int, default=5016, help='Port to run the server on')
args = parser.parse_args()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class STTRequestHandler(BaseHTTPRequestHandler):
    """Request handler for the STT service"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'status': 'ok', 'service': 'stt'})
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'error': 'Not found'})
            self.wfile.write(response.encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/speech_to_text':
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Generate mock response
            mock_responses = [
                "I'm interested in learning more about this topic.",
                "Could you explain that in more detail?",
                "That's an interesting perspective. I'd like to know more.",
                "I've been thinking about this issue for some time now.",
                "How would this approach work in practice?",
                "What are the implications of this decision?",
                "I'm not sure I fully understand. Could you clarify?",
                "That makes sense. I'd like to build on that idea.",
                "I have some concerns about the implementation details.",
                "How does this compare to alternative approaches?"
            ]
            
            selected_response = random.choice(mock_responses)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({
                'success': True,
                'text': selected_response,
                'source': 'mock'
            })
            
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'error': 'Not found'})
            self.wfile.write(response.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override log_message to use our logger"""
        logger.info("%s - %s" % (self.address_string(), format % args))

def run_server():
    """Run the STT server"""
    server_address = ('', args.port)
    httpd = ThreadedHTTPServer(server_address, STTRequestHandler)
    logger.info(f"Starting STT service on port {args.port}")
    logger.info(f"Health check: http://localhost:{args.port}/health")
    logger.info(f"Speech-to-text endpoint: http://localhost:{args.port}/speech_to_text")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        httpd.server_close()

if __name__ == '__main__':
    run_server() 