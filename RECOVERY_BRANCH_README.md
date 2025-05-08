# Daria Interview Tool - Recovery Branch

This Recovery branch of the Daria Interview Tool includes critical stability improvements and new debugging tools to enhance system reliability and troubleshooting.

## Key Features in the Recovery Branch

### 1. New Debug Toolkit

A centralized debugging dashboard is now available at http://localhost:5025/debug that provides:

- **Real-time Service Status Monitoring**: Instantly see which services are running or failing
- **Unified Debug Interface**: Access all debugging tools from a single page
- **API Endpoint Testing**: Quickly test and verify all API endpoints
- **Monitoring Tools**: Access interview monitoring and other tools
- **Quick Links**: Direct access to key setup and configuration pages

### 2. Full End-to-End Automation

The Debug Interview Flow tool (http://localhost:5025/static/debug_interview_flow.html?port=5025) now supports complete end-to-end automation for the entire interview process:

- **Full Automation Mode**: Test complete interviews with one click
- **TTS-STT Integration**: Automated text-to-speech and speech-to-text processing
- **LangChain Response Generation**: Properly integrated with OpenAI for interview progression
- **Automatic Transcript Creation**: Correctly builds and stores interview transcripts
- **Debug Controls**: Pause, resume, and step through the interview process

### 3. User Authentication System

A new Flask-Login based authentication system has been implemented to secure the application:

- **User Registration**: New users can sign up with username, email, and password
- **Secure Login**: Password hashing with Werkzeug security
- **Role-based Access**: Support for different user roles (admin, researcher, user)
- **Protected Routes**: All sensitive routes now require authentication
- **Session Management**: Remember me functionality and session timeout settings
- **Password Reset**: Built-in workflow for password reset requests

### 4. Disaster Recovery

This branch includes robust disaster recovery capabilities:

- **Service Auto-Recovery**: Automatic restart of failed services
- **Graceful Degradation**: System continues to function even if some services are unavailable
- **Data Preservation**: Enhanced backup and restoration procedures for interview data
- **Error Logging**: Improved logging for easier troubleshooting

## Known Issues and Fixes

1. **DateTime Bug Fix**: Fixed issue in api_add_session_message where `datetime.now()` was incorrectly used instead of `datetime.datetime.now()`, causing LangChain responses to fail.

2. **Discussion Guide Handling**: Fixed issues with missing fields in discussion guides by adding default values.

3. **Interview Flow Fix**: The debug interview flow automation now properly cycles through the entire interview process with working TTS, STT, and LangChain responses.

## Getting Started

To start the Daria Interview Tool with the recovery features:

```bash
./start_daria_with_recovery.sh
```

To stop all services:

```bash
./stop_daria_services.sh
```

## Testing

The primary testing tool is the Debug Interview Flow at:
http://localhost:5025/static/debug_interview_flow.html?port=5025

This tool allows complete testing of the end-to-end interview flow, including TTS, STT, and LangChain integration.

## Migration from Previous Versions

If you're upgrading from a previous version:

1. Pull the latest code from the Recovery branch
2. Run the stop script to terminate any running services:
   ```bash
   ./stop_daria_services.sh
   ```
3. Backup your data directory:
   ```bash
   cp -r data data_backup_$(date +%Y%m%d_%H%M%S)
   ```
4. Start with the recovery script:
   ```bash
   ./start_daria_with_recovery.sh
   ```

## Known Issues Fixed in Recovery Branch

- ✅ Fixed: `InterviewService.generate_response() got an unexpected keyword argument 'session_data'` error
- ✅ Fixed: Discussion guide not loading due to missing 'options' attribute
- ✅ Fixed: TTS service not properly reading questions aloud
- ✅ Fixed: STT service cutting off sentences prematurely
- ✅ Fixed: Missing fields in JSON data causing runtime errors

## Using the Debug Toolkit

The Debug Toolkit is the central feature of the Recovery branch. To use it:

1. Start the Daria services using the recovery script
2. Navigate to http://localhost:5025/debug
3. Use the service status panel to verify all services are running
4. Select the appropriate debug tool based on what you're testing:
   - Interview Flow Debugger: Test full interview process
   - TTS Debugger: Test text-to-speech in isolation
   - STT-TTS Debugger: Test speech recognition with TTS feedback
   - API Health Check: Verify API server health and available prompts
   - Orchestration Debugger: Test interview orchestration components
   - Interview TTS Debugger: Test TTS in interview context

## Future Improvements

The Recovery branch is focused on stability and debugging. Planned improvements include:

- Database integration for more robust data storage
- AWS deployment support
- Enhanced monitoring and alerting
- Automated recovery procedures

## Feedback and Contributions

Please report any issues or suggestions for the Recovery branch via the issue tracker. Include "Debug Toolkit" in issue titles related to the new toolkit functionality.

## Recovery Procedures

If you encounter issues with the Daria Interview Tool, follow these recovery procedures:

### Quick Recovery Script

The quickest way to recover all services is to use the recovery script:

```bash
./start_daria_with_recovery.sh
```

This script will:
1. Stop all running Daria services
2. Verify environment variables
3. Start all required services in the correct order
4. Verify service health

### Manual Recovery

If the recovery script doesn't work, follow these manual steps:

1. **Stop all services**:
   ```bash
   ./stop_daria_services.sh
   ```

2. **Check environment variables**:
   Make sure the following environment variables are set:
   - `OPENAI_API_KEY`
   - `ELEVENLABS_API_KEY`

3. **Start services individually**:
   ```bash
   # Start ElevenLabs TTS service
   python services/elevenlabs_tts_direct.py --port 5015 &
   
   # Start Speech-to-Text service
   python services/speech_to_text.py --port 5016 &
   
   # Start main API server with LangChain
   python run_interview_api.py --port 5025 --debug --use-langchain &
   ```

4. **Verify services**:
   Open the Debug Toolkit at http://localhost:5025/debug to verify all services are running.

### Common Issues

#### TTS Not Working
If text-to-speech is not working:

1. Check the ElevenLabs API key is set: `echo $ELEVENLABS_API_KEY`
2. Verify the TTS service is running on port 5015
3. Restart the TTS service: `python services/elevenlabs_tts_direct.py --port 5015`

#### STT Not Working
If speech-to-text is not working:

1. Ensure microphone permissions are granted
2. Verify the STT service is running on port 5016
3. Restart the STT service: `python services/speech_to_text.py --port 5016`

#### LangChain/API Issues
If the API or LangChain is not working:

1. Check the OpenAI API key is set: `echo $OPENAI_API_KEY`
2. Make sure you're using the `--use-langchain` parameter when starting the API
3. Check for any errors in the console output
4. Look for the "datetime.now()" error which requires a quick fix in the code
5. If you see Session ID errors, make sure you're loading a valid session 