#!/bin/bash

# Colors for output formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Daria Memory Companion...${NC}"

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p api_services
mkdir -p logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install openai anthropic flask Flask-SQLAlchemy Flask-Cors flask-socketio

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo "Creating .env file for API keys..."
    cat > .env << EOL
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
EOL
    echo -e "${YELLOW}Please edit the .env file and add your API keys${NC}"
fi

# Create an __init__.py file in api_services
echo "Setting up Python packages..."
if [ ! -f "api_services/__init__.py" ]; then
    cat > api_services/__init__.py << EOL
# API Services package for Daria Interview Tool
EOL
fi

# Load environment variables
echo "Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Print instructions
echo -e "${GREEN}Memory Companion has been successfully installed!${NC}"
echo ""
echo -e "${YELLOW}To use Memory Companion:${NC}"
echo "1. Start your Daria application with ./start_server.sh"
echo "2. Navigate to http://localhost:5030/static/daria_memory_companion.html"
echo ""
echo -e "${YELLOW}For debugging:${NC}"
echo "1. Run ./debug_memory.sh to start the Memory Companion in debug mode"
echo "2. This will start a minimal server that only includes the Memory Companion functionality"
echo ""
echo -e "${YELLOW}Note:${NC} Make sure you have valid API keys in the .env file."
echo ""

# Make the start script executable
echo "Creating start script..."
cat > start_daria_with_memory.sh << EOL
#!/bin/bash
# Source environment variables
export \$(cat .env | grep -v '^#' | xargs)

# Start Daria with memory companion
echo "Starting Memory Companion on port 5030..."
source venv/bin/activate
python debug_memory_api.py
EOL

chmod +x start_daria_with_memory.sh

echo "Creating simple memory test script..."
cat > test_memory_api.sh << EOL
#!/bin/bash
# Simple script to test the Memory Companion API

echo "Testing Memory Companion API..."
curl -s http://localhost:5030/api/memory_companion/test | python3 -m json.tool

if [ \$? -eq 0 ]; then
    echo -e "\n✅ Memory Companion API is working!"
else
    echo -e "\n❌ Memory Companion API is not responding. Please check server logs."
fi
EOL

chmod +x test_memory_api.sh

echo "Done! You can now start Daria with ./start_daria_with_memory.sh" 