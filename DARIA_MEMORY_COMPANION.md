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