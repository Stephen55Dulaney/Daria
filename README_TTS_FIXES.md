# TTS Troubleshooting for Remote Interview Tool

This document provides solutions for text-to-speech (TTS) issues in the remote interview tool.

## Common Issues

1. **TTS not working in remote interviews:**
   - Messages appear in UI but aren't read aloud
   - Microphone permission modals blocking TTS playback
   - JavaScript errors like "addSpeakingIndicator is not defined"
   - Server instability and frequent terminations

## Quick Solutions

### Solution 1: Use the Minimal Remote Interview Interface

We've created a simpler version of the interview interface with:
- No microphone permission dialogs
- Simplified, dependency-free JavaScript
- Better error handling
- Built-in visual TTS status indicators
- CORS headers to prevent browser blocking

To use the minimal interface, simply append `&minimal=true` to your interview URL:
```
http://yourserver:5000/interview/[session_id]?voice_id=[voice_id]&remote=true&minimal=true
```

### Solution 2: Restart TTS Services

If TTS isn't working, try restarting the TTS services:

```bash
./restart_tts_services.sh
```

This script will:
- Stop all running TTS/audio services
- Clear any port conflicts
- Start ElevenLabs TTS service
- Start main TTS service
- Test that services are responding correctly

### Solution 3: Manual Testing

To manually test TTS:

1. Test the TTS service directly:
   ```bash
   curl -X POST http://localhost:5015/text_to_speech \
     -H "Content-Type: application/json" \
     -d '{"text":"This is a test","voice_id":"EXAVITQu4vr4xnSDxMaL"}'
   ```

2. Check TTS service health:
   ```bash
   curl http://localhost:5015/health
   ```

3. Open the debug TTS page:
   ```
   http://yourserver:5000/debug/tts
   ```

## Technical Improvements Made

The following improvements were made to fix TTS issues:

1. **Removed Modal Dependencies**: The minimal interface has no modals that could block audio playback

2. **Enhanced TTS Implementation**:
   - Added robust error handling
   - Implemented proper cleanup of audio elements
   - Added CORS headers to prevent permission issues
   - Created visual indicators for TTS status

3. **Backend Improvements**:
   - Fixed CORS issues in TTS API endpoints
   - Added detailed logging
   - Created direct fallback to ElevenLabs API when service forwarding fails
   - Fixed content-type issues that could cause audio playback problems

4. **Error Recovery**:
   - Added browser TTS fallback when ElevenLabs fails
   - Improved status reporting to help troubleshoot issues

## Configuration Requirements

For TTS to work properly, ensure:

1. `ELEVENLABS_API_KEY` is set in your environment
2. ElevenLabs TTS service (port 5015) is running
3. Main TTS service (port 5007) is running
4. No browser extensions are blocking audio playback

## Log Files to Check

If issues persist, check these log files:
- `tts_service.log` - ElevenLabs TTS service logs
- `audio_service.log` - Main TTS service logs
- `web_server.log` - Web server logs for API errors

## Browser Compatibility

The enhanced TTS implementation has been tested and works in:
- Chrome
- Firefox
- Safari
- Edge

## Last Resort Solution

If everything else fails, you can create a completely isolated minimal HTML file that doesn't depend on any server-side components. See `templates/isolated_minimal_tts.html` for reference. 