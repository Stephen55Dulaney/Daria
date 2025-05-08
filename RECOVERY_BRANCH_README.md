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

The Debug Interview Flow tool at http://localhost:5025/static/debug_interview_flow.html?port=5025 now supports:

- **Fully Automated Interview Flow**: Complete TTS → STT → LangChain response cycle works end-to-end
- **LangChain Integration**: AI responses are properly generated and added to the session
- **Customizable Timing**: Adjustable delays between TTS and STT for optimal performance
- **Robust Error Handling**: Prevents common issues that previously broke the interview flow

### 3. Disaster Recovery

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