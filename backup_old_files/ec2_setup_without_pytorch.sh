#!/bin/bash
# Setup script for DARIA on EC2 without PyTorch dependencies

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   DARIA EC2 Setup Without PyTorch Dependencies  ${NC}"
echo -e "${GREEN}===============================================${NC}"

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo dnf update -y
sudo dnf install -y gcc-c++ python3-devel git

# Install Docker if needed
echo -e "${YELLOW}Installing Docker...${NC}"
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
sudo curl -L "https://github.com/docker/compose/releases/download/v2.36.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Navigate to application directory
cd /home/ec2-user/DariaInterviewTool || { echo -e "${RED}DariaInterviewTool directory not found${NC}"; exit 1; }

# Create Python virtual environment
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install base dependencies
echo -e "${YELLOW}Installing base dependencies...${NC}"
pip install --upgrade pip
pip install wheel setuptools

# Install DARIA dependencies without PyTorch
echo -e "${YELLOW}Installing DARIA dependencies without PyTorch...${NC}"
pip install numpy pandas matplotlib seaborn jupyter python-dotenv flask flask-socketio openai markdown elevenlabs google-generativeai markdown2
pip install langchain langchain-community langchain-openai

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
EOF
    echo -e "${RED}Please update the .env file with your actual API keys!${NC}"
else
    echo -e "${GREEN}.env file already exists.${NC}"
fi

# Create a startup script if it doesn't exist
if [ ! -f restart_all_daria.sh ]; then
    echo -e "${YELLOW}Creating restart script...${NC}"
    cat > restart_all_daria.sh << 'EOF'
#!/bin/bash
# Script to restart all DARIA services

# Kill existing processes
pkill -f "run_interview_api.py" 2>/dev/null
pkill -f "debug_memory_api.py" 2>/dev/null
pkill -f "tts_service.py" 2>/dev/null
pkill -f "stt_service.py" 2>/dev/null
pkill -f "elevenlabs_tts.py" 2>/dev/null
sleep 2

# Start TTS service
cd audio_tools
nohup python elevenlabs_tts.py --port 5015 > ../tts_service.log 2>&1 &
cd ..

# Start STT service
cd audio_tools
nohup python stt_service.py --port 5016 > ../stt_service.log 2>&1 &
cd ..

# Start Memory Companion service
nohup python debug_memory_api.py > memory_companion.log 2>&1 &
sleep 2

# Start main Interview API with LangChain enabled
nohup python run_interview_api.py --use-langchain --port 5025 > interview_api.log 2>&1 &
sleep 3

echo "All DARIA services started"
EOF
    chmod +x restart_all_daria.sh
    echo -e "${GREEN}Restart script created and made executable.${NC}"
else
    echo -e "${GREEN}Restart script already exists.${NC}"
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}To start DARIA services, run:${NC}"
echo -e "${GREEN}./restart_all_daria.sh${NC}"
echo -e "\n${YELLOW}Important: Make sure to update your .env file with valid API keys!${NC}"

cat > test_langchain.py << 'EOF'
import os
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Check if API key is set
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")

try:
    # Initialize the LLM
    llm = ChatOpenAI(
        temperature=0.7,
        model="gpt-3.5-turbo",
    )
    
    # Create a conversation chain with memory
    conversation = ConversationChain(
        llm=llm, 
        memory=ConversationBufferMemory(),
        verbose=True
    )
    
    # Test the conversation
    response = conversation.predict(input="Hello, I'm testing if LangChain works.")
    print("\nLangChain is working correctly!")
    print(f"Response: {response}\n")
    
except Exception as e:
    print(f"Error with LangChain: {e}")
EOF 