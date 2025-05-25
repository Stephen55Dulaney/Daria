# DARIA Remote Interview System RC1 - Developer Guide

This guide provides instructions for developers working with the Release Candidate 1 of the DARIA Remote Interview System.

## Repository Setup

1. Clone the repository if you haven't already:
   ```
   git clone https://github.com/your-org/DariaInterviewTool.git
   cd DariaInterviewTool
   ```

2. Checkout the RC1 branch:
   ```
   git checkout remote-interview-system-rc1
   ```

## Environment Setup

1. Create and activate a Python virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   cd audio_tools
   pip install -r audio_test_requirements.txt
   cd ..
   ```

3. Set up your ElevenLabs API key:
   ```
   export ELEVENLABS_API_KEY="your-api-key-here"
   ```

## Running the Application

### Using Convenience Scripts

1. Start all services:
   ```
   ./start_rc1.sh
   ```

2. Stop all services:
   ```
   ./stop_rc1.sh
   ```

### Manual Startup

If you need to start services manually:

1. Start the audio service:
   ```
   cd audio_tools
   python simple_tts_test.py --port 5007
   ```

2. In another terminal, start the main application:
   ```
   python run_langchain_direct.py --port 5010
   ```

## Key Directories and Files

- `audio_tools/`: Contains the ElevenLabs integration for voice services
- `templates/langchain/`: HTML templates for the interview system
- `run_langchain_direct.py`: Main application runner
- `RELEASE_NOTES_RC1.md`: Detailed release notes
- `README_INTERVIEW_SYSTEM.md`: User-facing documentation

## Development Workflow

1. Always create feature branches from this RC1 branch:
   ```
   git checkout -b feature/my-new-feature remote-interview-system-rc1
   ```

2. Implement and test your changes

3. Commit changes with meaningful messages:
   ```
   git add .
   git commit -m "Descriptive message about your changes"
   ```

4. Push your branch and create a PR against the RC1 branch:
   ```
   git push -u origin feature/my-new-feature
   ```

## Testing

### Manual Testing Checklist

1. Start services using `./start_rc1.sh`
2. Navigate to `http://127.0.0.1:5010/dashboard`
3. Test interview creation flow:
   - Create a new interview
   - Select different character options
   - Test voice sample
   - Start interview
4. Test interview session:
   - Verify AI speech works
   - Test microphone input
   - Test text input if speech fails
   - Verify session persistence between page reloads
5. Test error handling:
   - Try with invalid session IDs
   - Test with ElevenLabs API key removed
   - Test microphone access denied

### Common Issues and Solutions

1. **"Port already in use" errors**
   - Run `./stop_rc1.sh` to clean up processes
   - Manually kill processes: `lsof -ti :5007 | xargs kill -9`

2. **ElevenLabs API issues**
   - Verify your API key is set correctly
   - Check API rate limits in your ElevenLabs account
   - Temporary solution: The system will fall back to browser speech synthesis

3. **Session data loss**
   - Current limitation: Sessions are stored in memory
   - Future: Database persistence will be added

## Future Development

When working on new features, please consider these planned improvements:

1. Database integration for persistent storage
2. Vector database for transcript search
3. Enhanced security for sensitive data
4. Improved error handling
5. Browser compatibility enhancements

## Getting Help

If you have any questions about this release candidate, please contact the project maintainers. 