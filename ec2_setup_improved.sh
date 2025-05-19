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
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential

# Create requirements file if missing
echo "Creating requirements file..."
if [ ! -f "requirements_without_pytorch.txt" ]; then
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
langchain==0.0.267
EOF
fi

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Configure the application to use the elastic IP
echo "Configuring application to use elastic IP..."
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "Public IP: $PUBLIC_IP"

# Create necessary directories
mkdir -p instance
touch instance/config.py

# Update configuration to use 0.0.0.0 for binding
cat > instance/config.py << EOF
# Instance configuration
BIND_ADDRESS = "0.0.0.0"
PUBLIC_URL = "http://${PUBLIC_IP}"
EOF

# Initialize the database
echo "Setting up the database..."
if [ -f "init_db.py" ]; then
    python init_db.py || echo "Database initialization failed but continuing..."
fi

# Create startup script
cat > start_ec2_services.sh << EOF
#!/bin/bash

# Start all DARIA services
echo "Starting DARIA services..."

# Change to the application directory
cd \$(dirname \$0)
source venv/bin/activate

# Start the services
nohup python run_interview_api.py --host 0.0.0.0 --port 5025 > api.log 2>&1 &
echo \$! > .api_pid

# Start memory companion
nohup python -m api_services.memory_companion_service --host 0.0.0.0 --port 5030 > memory.log 2>&1 &
echo \$! > .memory_pid

# Start memory companion UI
nohup python memory_companion_ui.py --host 0.0.0.0 --port 5035 > memory_ui.log 2>&1 &
echo \$! > .memory_ui_pid

echo "Services started:"
echo "- Issue Tracker API: http://${PUBLIC_IP}:5025"
echo "- Memory Companion: http://${PUBLIC_IP}:5030"
echo "- Memory Companion UI: http://${PUBLIC_IP}:5035"
EOF

# Create stop script
cat > stop_ec2_services.sh << EOF
#!/bin/bash

# Stop all DARIA services
echo "Stopping DARIA services..."

# Change to the application directory
cd \$(dirname \$0)

# Kill processes by PID files
for pid_file in .api_pid .memory_pid .memory_ui_pid; do
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

# Make scripts executable
chmod +x start_ec2_services.sh
chmod +x stop_ec2_services.sh

# Configure security rules for the ports
echo "Make sure your EC2 security group allows inbound traffic on ports 5025, 5030, and 5035."

# Start the services
echo "Starting DARIA services..."
./start_ec2_services.sh

echo ""
echo "DARIA Interview Tool has been set up and started."
echo "Services are running on the following ports:"
echo "- Issue Tracker API: http://${PUBLIC_IP}:5025"
echo "- Memory Companion: http://${PUBLIC_IP}:5030"
echo "- Memory Companion UI: http://${PUBLIC_IP}:5035"
echo ""
echo "Use the following URLs to access the system:"
echo "- Memory Companion UI: http://${PUBLIC_IP}:5030/static/daria_memory_companion.html"
echo "- Issue Tracker: http://${PUBLIC_IP}:5025/issues/"
echo ""
echo "To stop all services, run: ./stop_ec2_services.sh" 