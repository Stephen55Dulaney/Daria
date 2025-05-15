# Daria Memory Companion

## Overview

The Daria Memory Companion is a feature inspired by the movie "50 First Dates" that allows Daria to maintain continuity across different user sessions by reading a "memory journal" when it starts up. This addresses the issue of losing context when chat history gets too long and Cursor crashes.

## Key Features

1. **Persistent Memory Journal**: Stores project history, current status, opportunities, and other context in a structured format
2. **LLM Integration**: Connects to real language models like GPT-4 or Claude for intelligent responses
3. **Boot Sequence**: Visually demonstrates Daria loading her memories at startup
4. **Timeline Tracking**: Maintains a chronological history of project activities
5. **Opportunity Management**: Tracks project opportunities and their priorities
6. **API-Based Architecture**: Separates frontend and backend for better maintenance

## Architecture

The Memory Companion consists of several components:

1. **Frontend UI** (`static/daria_memory_companion.html`): The user interface for interacting with Daria
2. **Backend API Service** (`api_services/memory_companion_service.py`): Handles data persistence and LLM integration
3. **Project Journal** (`data/daria_memory.json`): Stores all project memory data
4. **Flask Integration**: API endpoints for the Memory Companion integrated into the main application

## LLM Integration

The Memory Companion can connect to different LLM providers:

- **OpenAI**: Using models like GPT-4o, GPT-4o-mini
- **Anthropic**: Using models like Claude 3 Haiku, Claude 3 Sonnet

The system prompt provides Daria with context about the project, including its history, current sprint, timeline, and opportunities, allowing her to give contextually relevant responses.

## Technical Implementation - Recent Fixes

### Character Identity and Context Leakage (May 15, 2025)

#### Problem Summary
The DARIA interview tool experienced two critical issues:
1. **Character Identity Issues**: AI characters weren't maintaining consistent identity across interview sessions
2. **Context Data Leakage**: Raw internal context data was appearing in LLM responses

#### Root Causes
- **Character Identity Issues**:
  - Character information wasn't properly passed between pages (session → remote interview)
  - Custom characters like "Thomas" weren't properly registered in the system
  - Character information wasn't persisted in URL parameters when transitioning between pages
  - LangChain response generation wasn't consistently using character information
  
- **Context Data Leakage**:
  - Insufficient sanitization regex patterns couldn't detect all formats of leaked context
  - LLM responses containing raw context data (e.g., "I am {'Topic': 'General Interview'...}")
  - No fallback detection for suspicious content patterns

#### Implemented Fixes
1. **Enhanced Context Data Sanitization**:
   - Created more robust regex patterns to detect various context data formats
   - Added fallback detection for suspicious content patterns
   - Improved cleaning of responses after context removal
  
2. **Character Identity Persistence**:
   - Modified URL handling to preserve character between pages
   - Added character parameter to remote interview links
   - Updated identity response handling to be character-aware
   - Added all standard characters to direct mapping dictionaries
  
3. **Debug Tools Improvements**:
   - Added character passing between debug_character_test.html and debug_interview_flow.html
   - Enhanced character detection in debug tools
   - Added test guide with Thomas character for verification

4. **Session Handling Improvements**:
   - Modified LangChain integration to properly retrieve and use character information
   - Fixed session creation to copy character information from guides
   - Added explicit character information to system messages

#### Implementation Details
- **Key Files Modified**:
  - `langchain_features/services/interview_service.py`: Enhanced sanitization and identity response handling
  - `static/debug_character_test.html`: Added character mapping and URL parameter passing 
  - `static/debug_interview_flow.html`: Added character parameter handling
  - `templates/langchain/session.html`: Updated remote interview links to include character
  - `templates/langchain/interview_welcome.html`: Added character parameter preservation
  - `langchain_features/services/discussion_service.py`: Fixed character copying during session creation
  - `run_interview_api.py`: Updated API to pass character information to LangChain
  - `data/discussions/thomas_test_guide.json`: Created test guide for verification

#### Lessons Learned
- Character state needs to be explicitly passed and maintained across all transitions
- Robust sanitization requires multiple layers of pattern detection
- Test guides with specific characters are valuable for verification
- Custom character handling requires explicit mapping in multiple places

## Setup and Installation

1. Run the setup script: `./setup_memory_companion.sh`
2. Edit the `.env` file to add your API keys for OpenAI and/or Anthropic
3. Start Daria with memory support: `./start_daria_with_memory.sh`
4. Access the Memory Companion at: `http://localhost:5030/static/daria_memory_companion.html`

## Debug Mode

If you're having trouble with the Memory Companion, you can run it in debug mode:

1. Run the debug script: `./debug_memory.sh`
2. This starts a simplified Flask server that only includes the Memory Companion functionality
3. Access the debug interface at: `http://localhost:5030/static/daria_memory_companion.html`
4. Test the API connection by clicking the "Test API" button in the interface

The debug mode provides better error reporting and is useful for troubleshooting API connection issues.

## How to Use

1. **Start a Session**: When you open the Memory Companion, Daria will "boot up" and load her memories
2. **Ask Questions**: Ask Daria about your project status, what to work on next, or other project-related questions
3. **Select LLM Model**: Choose your preferred LLM model from the dropdown in the interface
4. **Add New Information**: The API supports adding new timeline events, opportunities, or updating sprint information
5. **Start a New Day**: Click "New Day Simulation" to simulate starting a fresh session the next day

## API Endpoints

- `GET /api/memory_companion/project_data`: Retrieves all project memory data
- `POST /api/memory_companion/chat`: Sends a message to Daria and gets her response
- `POST /api/memory_companion/timeline`: Adds a new event to the timeline
- `POST /api/memory_companion/opportunity`: Adds a new opportunity
- `PUT /api/memory_companion/sprint`: Updates the current sprint information

## Extending the Memory Companion

You can extend the Memory Companion in several ways:

1. **Additional Memory Types**: Add new types of information to track, like meeting notes or code artifacts
2. **Vector Storage**: Implement vector-based memory for more nuanced semantic retrieval
3. **Integration with Other Tools**: Connect to GitHub, JIRA, or other development tools
4. **Advanced Memory Management**: Implement forgetting curves, memory consolidation, or other cognitive-inspired features
5. **Multi-Project Support**: Expand to handle multiple projects simultaneously

## Troubleshooting

If you encounter issues:

1. **API Key Problems**: Ensure your API keys in the `.env` file are valid
2. **Connection Issues**: Check that the Flask server is running and accessible
3. **Missing Dependencies**: Run the setup script again to install any missing dependencies
4. **Data Persistence**: If the memory journal isn't updating, check permissions on the data directory

## Technical Notes

- The system uses asynchronous API calls for better performance
- The system prompt is carefully engineered to maintain Daria's personality and project context
- Memory history is limited to prevent context overflow with LLMs

## 50 First Dates Analogy

Just like Lucy in "50 First Dates" who watches a video each morning to remember her life, Daria reads her memory journal at the start of each session to recall the project's status, recent activities, and other important context. This allows her to maintain continuity despite technical limitations in chat history. 