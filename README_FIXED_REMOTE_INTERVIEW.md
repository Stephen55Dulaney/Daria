# DARIA Remote Interview System (Fixed Version)

This is the fixed version of the DARIA Remote Interview System, addressing several architectural issues that were causing problems in the original implementation.

## Key Improvements

1. **Blueprint Structure**: Proper separation between API and UI routes
2. **Template Path Resolution**: Correct template paths for all components including the Prompt Manager
3. **File-based Persistence**: Reliable file-based storage of interview data
4. **Python 3.13 Compatibility**: Works with Python 3.13 by setting SKIP_EVENTLET
5. **Improved Service Management**: Reliable scripts for starting and stopping services

## Getting Started

### Prerequisites

- Python 3.9+ (compatible with Python 3.13)
- ElevenLabs API key (for voice capabilities)

### Setup

1. **Set up your API key**:
   Create a `.env` file in the project root with:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Starting the System

Use the provided script to start all services:

```bash
./start_remote_interview.sh
```

This will:
- Start the audio service on port 5007
- Start the main application on port 5010
- Create necessary directories
- Log output to the logs/ directory

### Stopping the System

To stop all services:

```bash
./stop_remote_interview.sh
```

## Available Endpoints

- **Main Application**: http://localhost:5010/
- **Dashboard**: http://localhost:5010/dashboard
- **Interview Setup**: http://localhost:5010/interview_setup
- **Prompt Manager**: http://localhost:5010/prompts/
- **Audio Service**: http://localhost:5007/

## System Architecture

The system consists of two main components:

1. **Main Application (Flask)**:
   - API routes (`/api/...`)
   - UI routes (main URL paths)
   - Prompt Manager integration

2. **Audio Service**:
   - ElevenLabs integration for text-to-speech
   - Speech-to-text capabilities

## Troubleshooting

### Common Issues:

1. **Port in Use**:
   - The start script will attempt to kill processes using the required ports
   - If this fails, manually stop the processes or use different ports

2. **Template Not Found**:
   - Check that you're using the fixed application version (`run_langchain_direct_fixed.py`)
   - Ensure the template directories exist

3. **Audio Service Not Working**:
   - Verify the ElevenLabs API key is correctly set in the `.env` file
   - Check the audio service logs: `tail -f logs/audio_service.log`

### View Logs:

- Main application: `tail -f logs/main_app.log`
- Audio service: `tail -f logs/audio_service.log` 