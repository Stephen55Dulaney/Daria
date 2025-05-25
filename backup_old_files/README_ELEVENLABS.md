# ElevenLabs Voice Integration for DARIA Interview Tool

This document explains how to use the ElevenLabs text-to-speech functionality that has been integrated into the DARIA Interview Tool.

## Setup

1. Ensure you have an ElevenLabs API key. If you don't have one, sign up at [https://elevenlabs.io](https://elevenlabs.io).

2. Add your ElevenLabs API key to the `.env` file:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ```

3. Install the required dependencies:
   ```
   pip install -r audio_tools/audio_test_requirements.txt
   ```

## Starting the Services

For the ElevenLabs voice functionality to work, both the main application and the audio_tools service need to be running. Use the provided script to start both services:

```
./start_services.sh
```

This will:
- Start the audio_tools service on port 5007
- Start the main application on port 5010

## Using ElevenLabs Voices

1. Go to the Interview Setup page at `/langchain/interview_setup`
2. In the "Interview Settings" section, select an "Interviewer Voice" from the dropdown
3. Click the "Test Voice" button to hear a sample of the selected voice
4. Complete the rest of your interview setup and click "Create Interview"

## Available Voices

The following ElevenLabs voices are available:
- Rachel (Female)
- Antoni (Male)
- Elli (Female) 
- Domi (Female)
- Fin (Male)

## Troubleshooting

If you encounter issues with the voice testing:

1. Check that the audio_tools service is running on port 5007
2. Verify your ElevenLabs API key is valid and has sufficient credits
3. Check browser console for any error messages
4. If ElevenLabs fails, the system will fall back to browser speech synthesis

## Technical Details

The implementation consists of:
- `audio_tools/simple_tts_test.py`: A Flask service that handles API calls to ElevenLabs
- `run_langchain_direct.py`: The main application that includes endpoints to proxy requests to the audio_tools service
- `templates/langchain/interview_setup.html`: Frontend UI with the "Test Voice" button and voice selection

When you click "Test Voice", the request is sent to the `/api/text_to_speech_elevenlabs` endpoint, which forwards it to the audio_tools service, which then calls the ElevenLabs API. 