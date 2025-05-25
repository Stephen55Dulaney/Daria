#!/usr/bin/env python3
"""
Simple HTTP server for DARIA Interview Tool
Serves static files and proxies API requests to the main app
"""

import os
import argparse
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run a simple HTTP server')
parser.add_argument('--port', type=int, default=8889, help='Port to run the server on')
parser.add_argument('--api-url', type=str, default='http://localhost:5010', help='URL for the API server')
args = parser.parse_args()

# Define custom request handler
class DARIARequestHandler(SimpleHTTPRequestHandler):
    """
    Custom request handler that serves static files and proxies API requests
    """
    
    def do_GET(self):
        """Handle GET requests"""
        # Check if this is an API request
        parsed_path = urlparse(self.path)
        
        # Special handling for audio test page
        if parsed_path.path == '/audio_test' or parsed_path.path == '/audio_test.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            try:
                with open('audio_test.html', 'rb') as file:
                    self.wfile.write(file.read())
            except FileNotFoundError:
                self.send_error(404, 'Audio test page not found')
            return
        
        # Special handling for test interview page
        elif parsed_path.path == '/test_interview_page' or parsed_path.path == '/test_interview_page.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            try:
                with open('test_interview_page.html', 'rb') as file:
                    self.wfile.write(file.read())
            except FileNotFoundError:
                self.send_error(404, 'Test interview page not found')
            return
            
        elif parsed_path.path.startswith('/api/'):
            self.proxy_request('GET')
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        # All POST requests are proxied to the API
        self.proxy_request('POST')
    
    def proxy_request(self, method):
        """Proxy a request to the API server"""
        try:
            # Get request body for POST requests
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Copy headers
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'host'}
            
            # Log the request
            logger.info(f"Proxying {method} request to {args.api_url}{self.path}")
            
            # Make the request to the API server
            api_url = f"{args.api_url}{self.path}"
            
            if method == 'GET':
                response = requests.get(api_url, headers=headers, stream=True)
            else:  # POST
                response = requests.post(api_url, headers=headers, data=body, stream=True)
            
            # Set response status code
            self.send_response(response.status_code)
            
            # Set response headers
            for header, value in response.headers.items():
                if header.lower() not in ('content-length', 'transfer-encoding', 'connection'):
                    self.send_header(header, value)
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.content)
            
        except Exception as e:
            logger.error(f"Error proxying request: {str(e)}")
            self.send_error(500, f"Error proxying request: {str(e)}")

if __name__ == '__main__':
    # Create server
    server = HTTPServer(('', args.port), DARIARequestHandler)
    
    print(f"Starting web server on port {args.port}")
    print(f"API server URL: {args.api_url}")
    print(f"Visit: http://localhost:{args.port}")
    print(f"Audio Test Page: http://localhost:{args.port}/audio_test")
    print(f"Test Interview Page: http://localhost:{args.port}/test_interview_page")
    
    try:
        # Run server
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user")
    finally:
        server.server_close() 