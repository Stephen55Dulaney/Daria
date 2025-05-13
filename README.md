# Daria Interview Tool

A research interview assistant that uses AI to conduct interviews with text-to-speech (TTS) and speech-to-text (STT) capabilities.

## Recent Updates

### May 2025 Update
- Fixed critical indentation error in transcript processing code
- Created convenient server start/stop scripts (`start_server.sh`, `stop_server.sh`)
- Successfully tested and verified LangChain integration
- Improved transcript upload functionality with better speaker identification
- Added comprehensive project status documentation
- See `PROJECT_STATUS.md` for detailed status information
- See `REMAINING_TASKS.md` for pending improvements

## Overview

Daria is a comprehensive research interview tool designed to facilitate and automate the interview process. It includes:

- AI-driven interview moderation
- Text-to-speech capabilities for interviewers
- Speech-to-text for transcribing participant responses
- Discussion guides management
- Session analysis and insights

## Services Architecture

The Daria Interview Tool consists of multiple services that work together:

1. **API Server** (port 5025) - The main application server that handles API requests, renders UI pages, and coordinates between services
2. **TTS Service** (port 5015) - Text-to-speech service powered by ElevenLabs
3. **STT Service** (port 5016) - Speech-to-text mock service

## Startup Instructions

For reliable operation, always use the recovery startup script:

```bash
./start_daria_with_recovery.sh
```

This script:
- Ensures all data directories exist
- Creates default debug guide if missing
- Stops any existing services to prevent conflicts
- Starts all required services in the correct order
- Enables LangChain for full AI capabilities
- Shows URLs to access all services

## Shutdown Instructions

To properly shut down all services:

```bash
./stop_daria_services.sh
```

This script:
- Gracefully terminates all running services
- Confirms successful shutdown
- Forces termination of any stuck processes

## Accessing the Tool

After starting the services, you can access the following URLs:

- **Dashboard**: http://localhost:5025/dashboard
- **Discussion Guides**: http://localhost:5025/discussion_guides
- **Interview Setup**: http://localhost:5025/interview_setup
- **Debug Interview**: http://localhost:5025/static/debug_interview_flow.html?port=5025
- **Debug Toolkit**: http://localhost:5025/debug

## Debug Toolkit

The Debug Toolkit is a centralized dashboard for accessing all debugging tools and monitoring system health. It provides:

- Real-time service status monitoring
- Quick access to all debug interfaces
- API endpoint testing
- Monitoring tools
- Direct links to key setup pages

To access the Debug Toolkit:
- Navigate to http://localhost:5025/debug in your browser
- Or click the "Debug Toolkit" link in the sidebar of any page

## Disaster Recovery Instructions

If you encounter critical system failures, follow these recovery procedures:

### Complete System Recovery

For a full system recovery when all services are non-responsive:

1. Stop all services:
   ```bash
   ./stop_daria_services.sh
   ```

2. Clean process table (if needed):
   ```bash
   pkill -f "python.*run_.*\.py"
   ```

3. Restart with recovery options:
   ```bash
   ./start_daria_with_recovery.sh
   ```

### Data Recovery

If discussion guides or session data is corrupted:

1. Stop all services using the shutdown script
2. Make a backup of your data directory:
   ```bash
   cp -r data data_backup_$(date +%Y%m%d_%H%M%S)
   ```
3. Restore from a previous backup or initialize a fresh instance:
   ```bash
   # Option 1: Restore from backup
   cp -r data_backup_YYYYMMDD_HHMMSS/* data/
   
   # Option 2: Initialize fresh (will lose existing data)
   rm -rf data/*
   ./start_daria_with_recovery.sh
   ```

### Service-Specific Recovery

#### TTS Service Recovery

If the TTS service fails:

1. Check the TTS service log:
   ```bash
   tail -f tts_service.log
   ```
2. Verify your ElevenLabs API key:
   ```bash
   export ELEVENLABS_API_KEY=your_key_here
   ```
3. Restart just the TTS service:
   ```bash
   python run_elevenlabs_tts_direct.py --port 5015 > tts_service.log 2>&1 &
   ```

#### API Server Recovery

If the API server fails but TTS/STT services are running:

1. Check the API server log:
   ```bash
   tail -f api_server.log
   ```
2. Restart just the API server:
   ```bash
   python run_interview_api.py --port 5025 --use-langchain > api_server.log 2>&1 &
   ```

### Error Monitoring and Logs

Use the Debug Toolkit to monitor system health and identify errors:

1. Visit http://localhost:5025/debug
2. Check service status indicators
3. Click on specific debug tools based on the type of error

For more detailed error investigation:
- Check log files: `api_server.log`, `tts_service.log`, `stt_service.log`
- Use the API Health Check endpoint: http://localhost:5025/api/health
- Monitor real-time logs with:
  ```bash
  tail -f api_server.log tts_service.log stt_service.log
  ```

## Troubleshooting

### Empty Characters Dropdown

If the characters dropdown in Discussion Guide Setup is empty:
- Make sure the API server has proper access to the `tools/prompt_manager/prompts` directory
- Verify that at least one valid prompt YAML file exists in that directory
- Restart the service using `./start_daria_with_recovery.sh`

### Session Data Loss

If session data isn't persisting between restarts:
- Ensure data directories exist and have write permissions
- Check that `data/discussions` and `data/discussions/sessions` directories exist
- Use the recovery script for startup to ensure data integrity

### TTS/STT Services Not Working

If TTS or STT services aren't responding:
- Check the log files (`tts_service.log`, `stt_service.log`)
- Verify your ElevenLabs API key is set correctly (`export ELEVENLABS_API_KEY=your_key`)
- Make sure ports 5015 and 5016 are available and not blocked
- Use the Debug Toolkit's service status panel to identify which services are down

### API Errors

If you encounter API errors:
- Check for error messages in the console or network tab of your browser's dev tools
- Look for error messages in the API server log
- Try the specific API endpoint through the Debug Toolkit's quick actions section
- If you see `InterviewService.generate_response() got an unexpected keyword argument` errors, restart the API server with the recovery script

## Best Practices

1. **Always use the recovery script** to start the application
2. **Always use the stop script** to shut down services
3. **Check logs** in case of issues (`api_server.log`, `tts_service.log`, `stt_service.log`)
4. **Backup data directories** periodically
5. **Update ElevenLabs API key** when it expires
6. **Use the Debug Toolkit** to monitor and troubleshoot the system 