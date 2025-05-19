#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 80
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>DARIA EC2 Instance Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .success {
            color: green;
            font-weight: bold;
        }
        .links {
            margin-top: 20px;
        }
        .links a {
            display: block;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>DARIA EC2 Instance Test</h1>
    <p class="success">✅ If you can see this page, your EC2 instance is working correctly!</p>
    
    <div class="links">
        <h2>Available Services:</h2>
        <a href="http://3.12.144.184:5030/static/daria_memory_companion.html">Memory Companion UI</a>
        <a href="http://3.12.144.184:5035/">Memory Companion Integration Tool</a>
    </div>
</body>
</html>
"""

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
        else:
            super().do_GET()

if __name__ == "__main__":
    # Create a simple text file with our HTML content
    with open(os.path.join(DIRECTORY, "test_page.html"), "w") as f:
        f.write(HTML_CONTENT)
    
    # Use the directory where this script is located
    os.chdir(DIRECTORY)
    
    Handler = MyHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving test page at port {PORT}")
            httpd.serve_forever()
    except PermissionError:
        print(f"Error: Could not bind to port {PORT}. Try running with sudo.")
        print("Trying alternative port 8080...")
        try:
            with socketserver.TCPServer(("", 8080), Handler) as httpd:
                print(f"Serving test page at port 8080")
                httpd.serve_forever()
        except Exception as e:
            print(f"Error starting server on alternative port: {e}") 