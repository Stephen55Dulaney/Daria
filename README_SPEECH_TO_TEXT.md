# Speech-to-Text Integration Guide for DARIA

This guide explains how to set up and troubleshoot speech-to-text functionality in the DARIA Interview Tool.

## Overview

The DARIA Interview Tool uses a separate audio service to handle:
1. Text-to-speech conversion (converting interviewer questions to spoken audio)
2. Speech-to-text conversion (converting interviewee's spoken responses to text)

This audio service must be running alongside the main application for the speech features to work.

## Requirements

- Python 3.7 or higher
- ElevenLabs API key (for premium speech services)
- Internet connection (for API calls to ElevenLabs)

## Quick Start

### 1. Kill any existing Python processes

If you encounter issues, first kill any existing Python processes that might be causing port conflicts:

```bash
killall Python  # On macOS/Linux
# OR
taskkill /F /IM python.exe  # On Windows
```

### 2. Start the application

Use the start_services.py script to properly start both the audio service and main application:

```bash
python start_services.py
```

This will:
- Start the audio service on port 5007
- Start the main application on port 5010

### 3. Access the application

Open your browser and navigate to:
- Main application: http://localhost:5010/dashboard
- Audio test page: http://localhost:5007/

## Troubleshooting

### 1. Speech-to-text not working

If you see "Speech-to-text error: undefined" in your browser console:

1. Make sure both services are running:
   ```bash
   ps aux | grep python  # On macOS/Linux
   # OR
   tasklist | findstr "python"  # On Windows
   ```

2. Check if the audio service is accessible:
   ```bash
   curl http://localhost:5007/  # Should return HTML
   ```

3. Test the audio service directly at http://localhost:5007/

4. Verify your microphone works with your browser

### 2. Port conflicts

If you see "Address already in use" errors:

1. Kill all Python processes as shown above
2. Choose different ports:
   ```bash
   python start_services.py --audio-port 5008 --app-port 5011
   ```

### 3. Python 3.13+ compatibility

If you're using Python 3.13 or newer, you may encounter issues with the eventlet library:

1. The application automatically sets `SKIP_EVENTLET=1` for Python 3.13+
2. This will use threading mode instead

## Important URLs

- Dashboard: http://localhost:5010/dashboard
- Interview Test: http://localhost:5010/interview_test
- Interview Setup: http://localhost:5010/interview_setup
- Audio Service Test: http://localhost:5007/

Remember that you must always run both services together using the start_services.py script. 