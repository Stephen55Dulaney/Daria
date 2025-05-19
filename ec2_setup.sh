#!/bin/bash

# EC2 Setup Script for DARIA Interview Tool
# This script extracts and sets up the application on an EC2 instance

ELASTIC_IP="3.12.144.184"
echo "Setting up DARIA Interview Tool on EC2 with Elastic IP: $ELASTIC_IP"

# Extract the uploaded tarball
mkdir -p DariaInterviewTool_new
tar -xzf DariaInterviewTool.tar.gz -C DariaInterviewTool_new
cd DariaInterviewTool_new

# Install required packages
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements_without_pytorch.txt

# Set up the database
echo "Setting up the database..."
python3 init_db.py

# Start the services
echo "Starting DARIA services..."

# Start the Issue Tracker API service with explicit host binding
nohup python3 run_interview_api.py --use-langchain --port 5025 --host 0.0.0.0 > interview_api.log 2>&1 &
echo $! > .issue_tracker_pid

# Start the Memory Companion service
nohup python3 api_services/memory_companion_service.py --port 5030 --host 0.0.0.0 > memory_companion.log 2>&1 &
echo $! > .memory_companion_pid

# Start the Memory Companion UI
nohup python3 memory_companion_ui.py --port 5035 --host 0.0.0.0 > memory_companion_ui.log 2>&1 &
echo $! > .memory_companion_ui_pid

# Start the Issue to Memory Sync service
nohup python3 issue_to_memory_sync.py --interval 10 > issue_memory_sync.log 2>&1 &
echo $! > .issue_memory_sync_pid

# Create a stop script
cat > stop_services.sh << 'STOPEOF'
#!/bin/bash

# Stop DARIA Interview Tool services
echo "Stopping DARIA services..."

# Stop Issue Tracker API
if [ -f .issue_tracker_pid ]; then
    PID=$(cat .issue_tracker_pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Issue Tracker API stopped."
    fi
    rm .issue_tracker_pid
fi

# Stop Memory Companion service
if [ -f .memory_companion_pid ]; then
    PID=$(cat .memory_companion_pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Memory Companion service stopped."
    fi
    rm .memory_companion_pid
fi

# Stop Memory Companion UI
if [ -f .memory_companion_ui_pid ]; then
    PID=$(cat .memory_companion_ui_pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Memory Companion UI stopped."
    fi
    rm .memory_companion_ui_pid
fi

# Stop Issue to Memory Sync service
if [ -f .issue_memory_sync_pid ]; then
    PID=$(cat .issue_memory_sync_pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Issue to Memory Sync service stopped."
    fi
    rm .issue_memory_sync_pid
fi

echo "All DARIA services have been stopped."
STOPEOF

chmod +x stop_services.sh

echo "DARIA Interview Tool has been set up and started."
echo "Services are running on the following ports:"
echo "- Issue Tracker API: http://$ELASTIC_IP:5025"
echo "- Memory Companion: http://$ELASTIC_IP:5030"
echo "- Memory Companion UI: http://$ELASTIC_IP:5035"
echo ""
echo "Use the following URLs to access the system:"
echo "- Memory Companion UI: http://$ELASTIC_IP:5030/static/daria_memory_companion.html"
echo "- Issue Tracker: http://$ELASTIC_IP:5025/issues/"
echo ""
echo "To stop all services, run: ./stop_services.sh"
