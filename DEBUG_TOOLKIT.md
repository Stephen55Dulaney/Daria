# DARIA Interview Tool Debugging Toolkit

This toolkit provides specialized debugging tools for the DARIA Interview Tool, focusing on isolating and testing specific components such as LangChain conversation, TTS (Text-to-Speech), and STT (Speech-to-Text).

## Components

1. **Isolated Interview Testing** (`debug_interview_isolated.sh`)
   - Runs the API server with LangChain enabled but without audio services
   - Creates a debug discussion guide and session automatically
   - Allows testing of the conversation flow without TTS/STT interference

2. **STT/TTS Isolation Testing** (`static/debug_stt_tts.html`)
   - Separate interface for testing STT and TTS components in isolation
   - Prevents audio feedback loops between TTS output and STT input
   - Detailed logging of all STT/TTS operations

3. **TTS-STT Orchestration Testing** (`static/debug_orchestration.html`)
   - Tests proper coordination between TTS and STT components
   - Fine-grained control over timing between TTS end and STT start
   - Helps solve "InvalidStateError" and race condition issues
   - Prevents STT from capturing AI's TTS output

4. **Full Interview Flow Testing** (`static/debug_interview_flow.html`)
   - Complete end-to-end testing of the entire interview process
   - Combines LangChain, TTS, and STT in one controlled environment
   - Configurable port for connecting to any running API server
   - Interactive sliders for precise timing control:
     - TTS-STT Transition Delay (300ms default)
     - STT to Submit Delay (500ms default)
     - STT Timeout and Restart Delay
   - Full automation mode for hands-free testing of the complete interview cycle
   - Supports both automatic and manual TTS/STT operations
   - Detailed logging of each step in the conversation flow

5. **Interview TTS Testing** (`static/debug_interview_tts.html`)
   - Simulates the interview environment with jQuery properly included
   - Tests TTS during the interview flow without STT interference
   - Supports manual and automatic TTS for assistant messages

6. **Conversation History Debugging** (`debug_conversation.py`)
   - Visualizes message flow and timing
   - Provides formatted output of conversation history
   - Can save conversation data to files for further analysis

7. **TTS Debug Interface** (`debug_tts.html`)
   - Tests ElevenLabs TTS integration
   - Works independently of the interview flow

## Usage Instructions

### Isolated LangChain Interview Testing

```bash
# Start the isolated debug environment
./debug_interview_isolated.sh

# Stop the isolated debug environment
./stop_isolated_debug.sh
```

The script will:
1. Start the API server with LangChain enabled on port 5050
2. Create a test discussion guide and session
3. Open the dashboard in your browser
4. Tail the logs

### Conversation History Debugging

```bash
# View conversation history from a session
python debug_conversation.py --session-id YOUR_SESSION_ID

# Use the most recent debug session
python debug_conversation.py

# Save conversation to a file
python debug_conversation.py --output conversation.json

# Format options: table (default), json, raw
python debug_conversation.py --format json
```

### STT/TTS Isolation Testing

1. Start the API server (if not already running)
2. Open `http://localhost:PORT/static/debug_stt_tts.html` in your browser
3. Use the interface to test STT and TTS separately

### TTS-STT Orchestration Testing

1. Start the API server with LangChain enabled:
   ```bash
   python run_interview_api.py --port 5010 --use-langchain
   ```
2. Open `http://localhost:5010/static/debug_orchestration.html` in your browser
3. Configure timing parameters to avoid race conditions
4. Test different TTS-STT flow combinations:
   - Full orchestration test (TTS followed by auto-STT)
   - TTS only
   - STT only
   - TTS then manual STT
5. Monitor the debug logs to identify issues with coordination

### Full Interview Flow Testing

1. Start the API server with LangChain enabled (if not already running):
   ```bash
   python run_interview_api.py --port 5010 --use-langchain
   ```
2. Open `http://localhost:5010/static/debug_interview_flow.html` in your browser
3. Enter the API port (default: 5010) and click "Connect"
4. Optionally provide a session ID to continue an existing interview
5. Use the sliders to fine-tune timing parameters:
   - TTS-STT Transition Delay (300ms default)
   - STT to Submit Delay (500ms default)
   - STT Timeout and Restart Delay
6. Test different automation modes:
   - Manual mode: Control each step of the process individually
   - Semi-automated: Enable auto-TTS and auto-STT features
   - Full automation: Click "Start Full Automation" for hands-free testing
7. Monitor the debug logs for detailed information
8. Can also use URL parameters: `?port=5010&session_id=your_session_id`

### Interview TTS Testing

1. Start the API server with LangChain enabled:
   ```bash
   python run_interview_api.py --port 5010 --use-langchain
   ```
2. Open `http://localhost:5010/static/debug_interview_tts.html` in your browser
3. Create a new conversation or load an existing session ID
4. Test TTS during the interview flow (supports auto TTS or manual playback)

## Troubleshooting

### LangChain Issues

If LangChain fails to initialize:

1. Check that all required packages are installed:
   ```bash
   pip install langchain langchain-community langchain-openai
   ```

2. Verify your OpenAI API key is set:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. Check the logs:
   ```bash
   cat logs/isolated_api.log | grep -i "error"
   ```

### TTS/STT Issues

1. For TTS issues, check ElevenLabs API key:
   ```bash
   export ELEVENLABS_API_KEY=your_api_key_here
   ```

2. For STT issues, make sure your browser has microphone permissions

3. Check browser console for JavaScript errors

### Common STT-TTS Orchestration Issues

1. **"InvalidStateError: recognition has already started"**
   - This happens when the code tries to start STT that's already running
   - Use the orchestration debug tool to add proper delays and checks
   - Ensure STT is properly stopped before restarting it

2. **STT capturing TTS audio output**
   - Add a delay between TTS ending and STT starting (300-500ms recommended)
   - Use the "TTS-STT Delay" setting in the orchestration tool

3. **Premature message submission**
   - If the system submits messages before the user finishes speaking
   - Increase the "STT to Submit Delay" (500-1000ms recommended)
   - This gives time for the final STT result to be processed

4. **Continual "no-speech" errors**
   - Increase the STT timeout
   - Add a delay between restart attempts
   - Test with the orchestration tool to find optimal parameters

## Advanced Testing

### Simulating Interview Sessions

The isolated debug environment creates a discussion guide and session that you can use to test the API endpoints directly:

```bash
# Send a user message
curl -X POST -H "Content-Type: application/json" \
  -d '{"message": {"role": "user", "content": "Hello, this is a test message"}}' \
  http://localhost:5050/api/session/YOUR_SESSION_ID/add_message
```

### API Endpoint Testing

Check key API endpoints:
- Health: `http://localhost:5010/api/health`
- Discussion guides: `http://localhost:5010/api/discussion_guides`
- Session messages: `http://localhost:5010/api/session/YOUR_SESSION_ID/messages`

## Known Issues

1. Browser TTS may not work consistently across all browsers
2. Speech recognition requires HTTPS in some browsers (works in localhost development)
3. Long interview sessions might cause performance issues 
4. jQuery missing in the original interview interface - fixed in `debug_interview_tts.html`
5. Race conditions between TTS ending and STT starting - addressed in `debug_orchestration.html`
6. "Failed to fetch" errors - make sure to use the correct port (5010 not 5050) 