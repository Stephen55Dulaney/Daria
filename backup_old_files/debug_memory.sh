#!/bin/bash

# Colors for output formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Memory Companion Debug Server...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check for required packages
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install flask openai anthropic python-dotenv
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOL
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
EOL
    echo -e "${YELLOW}Please edit the .env file and add your API keys${NC}"
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check for data directory
if [ ! -d "data" ]; then
    echo -e "${YELLOW}Creating data directory...${NC}"
    mkdir -p data
fi

# Check for api_services directory
if [ ! -d "api_services" ]; then
    echo -e "${RED}Error: api_services directory not found${NC}"
    echo "Please run setup_memory_companion.sh first"
    exit 1
fi

# Run the debug server
echo -e "${GREEN}Running Memory Companion Debug Server...${NC}"
echo "Open http://localhost:5030/static/daria_memory_companion.html in your browser"

python3 debug_memory_api.py 