# DARIA Remote Interview System

The DARIA Remote Interview System is a specialized module that allows researchers to conduct remote interviews with participants using AI-powered voice capabilities.

## Architecture

The system consists of two main components:

1. **Main Application** (port 5010): Handles the interview flow, UI, session persistence, and API endpoints
2. **Audio Service** (port 5007): Provides text-to-speech and speech-to-text capabilities using the ElevenLabs API

### Files Structure

```
├── run_langchain_direct_fixed.py    # Main application entry point
├── audio_tools/                     # Audio service directory
│   └── simple_tts_test.py           # Audio service entry point
├── templates/                       # HTML templates
│   └── langchain/                   # Interview-specific templates
├── static/                          # Static assets (CSS, JS, images)
├── interviews/                      # Interview data storage
├── start_remote_interview.sh        # Script to start all services
└── stop_remote_interview.sh         # Script to stop all services
```

## Prerequisites

- Python 3.9+ installed
- ElevenLabs API key (for voice features)
- Required Python packages installed

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
cd audio_tools
pip install -r audio_test_requirements.txt
cd ..
```

### 2. Set Up ElevenLabs API Key

Create a `.env` file in the root directory:

```
ELEVENLABS_API_KEY=your_api_key_here
```

### 3. Start the System

Use the provided script to start all services:

```bash
./start_remote_interview.sh
```

This will:
- Start the audio service on port 5007
- Start the main application on port 5010
- Create necessary directories for data storage
- Save logs to the logs/ directory

### 4. Stopping the System

To stop all services:

```bash
./stop_remote_interview.sh
```

## Usage

Once the system is running, you can access it at:

- **Main URL**: http://localhost:5010/
- **Dashboard**: http://localhost:5010/dashboard
- **Interview Setup**: http://localhost:5010/interview_setup

## Key Features

1. **Text-to-Speech and Speech-to-Text**: Natural voice interactions using ElevenLabs API
2. **Persistent Storage**: Interviews are saved to disk for reliability
3. **Character Selection**: Choose from multiple researcher personas
4. **Voice Selection**: Multiple voice options for the AI interviewer
5. **Real-time Monitoring**: Watch interviews as they happen
6. **Transcript Generation**: Get complete transcripts of all interviews

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - The start script will attempt to kill processes using the required ports
   - If it fails, manually stop the processes or use different ports

2. **Audio Service Not Working**
   - Check if the ElevenLabs API key is correctly set
   - Examine logs in logs/audio_service.log

3. **Missing Interviews Data**
   - Look for the interviews/ directory, which stores all interview data
   - Each interview is stored as a separate JSON file

### Accessing Logs

- Main application logs: `logs/main_app.log`
- Audio service logs: `logs/audio_service.log`

## Database Configuration

The current implementation uses a simple file-based storage system with JSON files. Each interview is stored in a separate file in the `interviews/` directory.

In the future, this can be replaced with a proper database like PostgreSQL or MongoDB for better scalability and query capabilities. 