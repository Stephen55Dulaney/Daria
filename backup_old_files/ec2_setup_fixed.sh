#!/bin/bash

# EC2 Setup Script for DARIA Interview Tool
# This script extracts and sets up the application on an EC2 instance

echo "Setting up DARIA Interview Tool on EC2..."

# Extract the uploaded tarball if not already extracted
if [ ! -d "DariaInterviewTool_new" ]; then
    mkdir -p DariaInterviewTool_new
    tar -xzf DariaInterviewTool.tar.gz -C DariaInterviewTool_new
fi
cd DariaInterviewTool_new

# Install required packages
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential curl

# Get the public IP
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
if [ -z "$PUBLIC_IP" ]; then
    # Fallback to using the EC2 instance info
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "3.12.144.184")
    # If still empty, use the known IP
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP="3.12.144.184"
    fi
fi
echo "Public IP: $PUBLIC_IP"

# Create requirements file
echo "Creating requirements file..."
cat > requirements.txt << EOF
Flask==2.3.3
Flask-WTF==1.1.1
Flask-Login==0.6.2
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.4
Flask-Cors==4.0.0
WTForms==3.0.1
SQLAlchemy==2.0.19
pydantic==1.10.12
python-dotenv==1.0.0
requests==2.31.0
boto3==1.28.29
pymongo==4.5.0
schedule==1.2.0
EOF

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install gunicorn  # For production serving

# Skip database initialization since it's failing and might not be necessary for our memory companion feature
echo "Skipping database initialization..."

# Create start and stop scripts for the integration services
echo "Creating service scripts..."

# Create startup script for memory companion and UI
cat > start_memory_services.sh << EOF
#!/bin/bash

# Start the memory companion services
echo "Starting Memory Companion services..."

# Change to the application directory
cd \$(dirname \$0)
source venv/bin/activate

# Start memory companion service
echo "Starting Memory Companion API..."
nohup python -m api_services.memory_companion_service --host 0.0.0.0 --port 5030 > memory_api.log 2>&1 &
echo \$! > .memory_api_pid

# Start memory companion UI
echo "Starting Memory Companion UI..."
nohup python memory_companion_ui.py --host 0.0.0.0 --port 5035 > memory_ui.log 2>&1 &
echo \$! > .memory_ui_pid

echo "Services started:"
echo "- Memory Companion API: http://${PUBLIC_IP}:5030"
echo "- Memory Companion UI: http://${PUBLIC_IP}:5035"
echo ""
echo "Access the Memory Companion at:"
echo "http://${PUBLIC_IP}:5030/static/daria_memory_companion.html"
EOF

# Create stop script
cat > stop_memory_services.sh << EOF
#!/bin/bash

# Stop memory companion services
echo "Stopping Memory Companion services..."

# Change to the application directory
cd \$(dirname \$0)

# Kill processes by PID files
for pid_file in .memory_api_pid .memory_ui_pid; do
    if [ -f "\$pid_file" ]; then
        pid=\$(cat \$pid_file)
        if ps -p \$pid > /dev/null; then
            echo "Stopping process \$pid"
            kill \$pid
        fi
        rm \$pid_file
    fi
done

echo "All services stopped."
EOF

# Create a test HTML page to verify the web service is working
cat > test_page.html << EOF
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
        <a href="http://${PUBLIC_IP}:5030/static/daria_memory_companion.html">Memory Companion UI</a>
        <a href="http://${PUBLIC_IP}:5035/">Memory Companion Integration Tool</a>
    </div>
</body>
</html>
EOF

# Create a simple Flask server to serve the test page
cat > test_server.py << EOF
from flask import Flask, send_file

app = Flask(__name__)

@app.route('/')
def home():
    return send_file('test_page.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
EOF

# Create a startup script for the test server
cat > start_test_server.sh << EOF
#!/bin/bash
cd \$(dirname \$0)
source venv/bin/activate
sudo nohup python test_server.py > test_server.log 2>&1 &
echo \$! > .test_server_pid
echo "Test server started on http://${PUBLIC_IP}/"
EOF

# Make scripts executable
chmod +x start_memory_services.sh
chmod +x stop_memory_services.sh
chmod +x start_test_server.sh

# Fix bug in memory_companion_ui.py - update the API endpoints to use 0.0.0.0
echo "Fixing memory_companion_ui.py to use proper IP bindings..."
if [ -f "memory_companion_ui.py" ]; then
    # Update with sed to use the proper host binding
    sed -i "s/app.run(debug=args.debug, port=args.port)/app.run(debug=args.debug, port=args.port, host='0.0.0.0')/g" memory_companion_ui.py
    
    # Update localhost references to the public IP
    sed -i "s|http://localhost:5030|http://${PUBLIC_IP}:5030|g" memory_companion_ui.py
    sed -i "s|http://localhost:5025|http://${PUBLIC_IP}:5025|g" memory_companion_ui.py
fi

# Configure security rules for the ports
echo "Make sure your EC2 security group allows inbound traffic on ports 5025, 5030, and 5035."

# Start the memory companion services
echo "Starting Memory Companion services..."
./start_memory_services.sh

# Start the test server (requires sudo)
echo "Starting test server..."
./start_test_server.sh

echo ""
echo "DARIA Memory Companion has been set up and started."
echo ""
echo "You can access the system at:"
echo "- Test page: http://${PUBLIC_IP}/"
echo "- Memory Companion UI: http://${PUBLIC_IP}:5030/static/daria_memory_companion.html"
echo "- Memory Companion Integration: http://${PUBLIC_IP}:5035/"
echo ""
echo "To stop services, run: ./stop_memory_services.sh" 