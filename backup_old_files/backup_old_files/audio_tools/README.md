# ElevenLabs Audio Testing Tools

This directory contains utilities to test the ElevenLabs text-to-speech and speech-to-text functionality for the DARIA Interview Tool.

## Directory Structure

```
audio_tools/
├── templates/              # HTML templates
│   └── test_audio_endpoints.html  # Test page UI
├── simple_tts_test.py      # Flask server with API endpoints
├── audio_test_requirements.txt  # Required packages
├── .gitignore              # Git ignore rules for this directory
└── README.md               # This file
```

## Setup

1. Make sure you have the required dependencies installed:
   ```
   pip install -r audio_test_requirements.txt
   ```

2. Create a `.env` file in the audio_tools directory with your ElevenLabs API key:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ```

   You can get an API key by signing up at [ElevenLabs](https://elevenlabs.io/).

## Running the Test Server

Start the testing server by running:

```bash
cd audio_tools
python simple_tts_test.py
```

This will start a Flask server on port 5007 (by default).

## Accessing the Test Page

Open your browser and navigate to:

```
http://localhost:5007/
```

## Features

The test page provides:

1. **Text-to-Speech Testing** - Enter any text and select from different ElevenLabs voices to test text-to-speech functionality.
2. **Speech-to-Text Testing** - Record your voice and have it transcribed using ElevenLabs API.
3. **Microphone Testing** - Test your microphone to ensure it's working correctly for interview recording.

## Troubleshooting

- If you see an error about ElevenLabs API key not being configured, make sure your `.env` file is correctly set up with a valid API key.
- If you encounter a "port already in use" error, you can change the port by setting the `PORT` environment variable:
  ```bash
  PORT=5008 python simple_tts_test.py
  ```

## Integration with DARIA Interview Tool

This is a standalone testing tool. To integrate the ElevenLabs functionality with the main DARIA application, you'll need to:

1. Install the required packages in your main environment
2. Set up the appropriate environment variables 
3. Implement the text-to-speech and speech-to-text endpoints in your main Flask application

The code in `simple_tts_test.py` can be used as a reference for implementation. 