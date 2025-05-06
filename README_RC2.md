# Daria Interview Tool - Release Candidate 2

## Release Overview

Release Candidate 2 (RC2) addresses several critical issues in the Daria Interview Tool's LangChain integration, particularly focusing on conversation context handling, speech processing, and analysis functionality.

## Key Fixes

### 1. LangChain Conversation Compatibility

- Fixed prompt template and memory configuration in the LangChain integration
- Resolved validation errors related to input variable mismatches between prompt templates and memory components
- Updated the conversations to properly maintain context during interviews
- Improved handling of follow-up questions by adding specific prompting to the conversation chain

### 2. Text-to-Speech Functionality

- Fixed integration between the interview system and TTS services
- Ensured proper voice ID handling during interviews
- Resolved errors that prevented spoken responses from being generated

### 3. Analysis Capabilities

- Implemented missing generate_analysis method in InterviewService
- Added generate_summary and format_transcript helper methods
- Ensured automatic analysis at the end of interviews
- Improved analysis prompt handling for different character types

### 4. Template Improvements

- Fixed interview_details.html template to handle missing interviewee information
- Improved error handling and robustness in template rendering

## Installation and Usage

1. Clone the repository and checkout the RC2 branch:
   ```
   git clone https://github.com/your-org/DariaInterviewTool.git
   cd DariaInterviewTool
   git checkout release-candidate-2
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   export OPENAI_API_KEY=your_api_key
   export ELEVENLABS_API_KEY=your_elevenlabs_key
   ```

4. Start the services:
   ```
   ./setup_services.sh
   ./start_services.sh
   ```

5. Access the application at http://localhost:5010

## Testing Notes

The application has been tested with:
- Multiple interview sessions with different character types
- Speech-to-text and text-to-speech functionality
- Analysis generation after interview completion
- Edge cases such as missing interviewee information

## Known Issues

- Monitor Interview link still leads to a 404 page
- Some deprecated LangChain imports generate warnings that should be addressed in future releases

## Contributors

- Stephen Dulaney (@sdulaney)

# Daria Interview Tool - RC2 Technical Guide

## Overview

Release Candidate 2 (RC2) of the Daria Interview Tool represents a stable version with all core functionality working. This document provides a technical overview of the system architecture, key improvements, and guidance for developers.

## Architecture

The Daria Interview Tool consists of the following core components:

1. **Main API Server (`run_interview_api.py`)**: 
   - Flask-based API server running on port 5010
   - Handles interview session management and API endpoints
   - Integrates with prompt management system

2. **Text-to-Speech Service (`audio_tools/simple_tts_service.py`)**:
   - Standalone service running on port 5015
   - Integrates with ElevenLabs API for high-quality voice synthesis
   - Simple REST API for text-to-speech conversion

3. **Client-Side Speech Recognition**:
   - Uses Web Speech API in the browser
   - Replaces previous server-side speech-to-text implementation
   - Provides more reliable speech recognition

4. **Character System**:
   - YAML-based character definition in `tools/prompt_manager/prompts/`
   - Configurable prompts, evaluation metrics, and analysis templates
   - Supports multiple interview personas (Daria, Skeptica, etc.)

5. **Web UI**:
   - HTML/JavaScript-based interfaces for interview setup and execution
   - Remote interview capabilities with real-time transcription
   - Debug information panel for troubleshooting

## Key Improvements in RC2

1. **Web Speech API Integration**:
   - Replaced server-side speech-to-text with browser-based implementation
   - Improved reliability and reduced API dependencies
   - Simplified processing pipeline

2. **Character Selection Fix**:
   - Resolved issue with dropdown not displaying available characters
   - Improved character parameter passing through URL
   - Fixed default character assignment in interview sessions

3. **Interview Termination**:
   - Added detection for phrases like "end interview"
   - Implemented proper API endpoints (`/api/interview/end`)
   - Added graceful session cleanup and summary generation

4. **Auto-Close Feature**:
   - Added countdown timer for browser windows at interview end
   - Improved user experience with clear session termination
   - Displays thank you message after completion

5. **Debug Information**:
   - Added panel for troubleshooting character and prompt issues
   - Displays loaded prompt information and system state
   - Helps identify configuration problems in real-time

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health check and version information |
| `/api/interview/start` | POST | Start a new interview session |
| `/api/interview/respond` | POST | Process user input and generate response |
| `/api/interview/end` | POST | End an interview session |
| `/api/text_to_speech_elevenlabs` | POST | Convert text to speech using ElevenLabs |
| `/api/speech_to_text` | POST | Process speech (now passthrough to browser API) |
| `/api/characters` | GET | List available character personas |
| `/api/character/<name>` | GET | Get specific character information |
| `/api/check_services` | GET | Check if required services are running |

## Configuration

The system uses the following configuration:

- **Environment Variables**: 
  - `ELEVENLABS_API_KEY`: Required for text-to-speech functionality
  - `OPENAI_API_KEY`: Required for AI responses (when LangChain is enabled)

- **Character Prompts**:
  - Located in `tools/prompt_manager/prompts/`
  - YAML format with standardized fields
  - Configurable system prompts and evaluation metrics

## Developer Guide

### Starting the Services

```bash
./start_services.sh
```

This starts:
- Main API server on port 5010
- TTS service on port 5015

### Clean Shutdown

```bash
./cleanup_services.sh
```

### Testing Character Prompts

```bash
python3 test_prompt_loading.py
```

This validates all character prompt files and checks for format issues.

### Fixing Character Prompts

If you encounter issues with character prompts:

1. Ensure `evaluation_metrics` is formatted as a dictionary, not a list
2. Verify all required fields are present
3. Use the test script to validate changes

## Known Issues and Limitations

1. **Prompt Manager Display Issues**:
   - Some complexity with YAML parsing and display
   - Fixed Synthia prompt to use dictionary format instead of list

2. **Missing Favicon**:
   - Created placeholder in `static/favicon.ico`
   - Should be replaced with proper binary .ico file

3. **ElevenLabs STT API**:
   - Server-side implementation is incomplete
   - Currently using browser-based Web Speech API instead

4. **Flask Development Server**:
   - Current implementation uses Flask development server
   - Not suitable for production deployment
   - Would need to be deployed with WSGI server like Gunicorn

## Next Steps

1. Fix remaining issues in the Prompt Manager
2. Create production deployment configuration
3. Implement comprehensive test suite
4. Add persistent storage for interview transcripts
5. Implement proper authentication system

---

Daria Interview Tool - RC2  
Copyright © 2025 Deloitte 