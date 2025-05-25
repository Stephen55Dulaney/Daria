# AI Observer for Daria Interview Tool

This document describes the AI Observer feature added to the Daria Interview Tool, which provides real-time analysis of interview conversations.

## Overview

The AI Observer is a secondary AI agent that runs alongside the main interview AI and human researcher. It analyzes the conversation in real-time, generating semantic notes, tags, and emotional tracking to help researchers gain deeper insights during and after interviews.

## Architecture

The AI Observer consists of:

1. **Backend Components**:
   - `ObserverService` class that analyzes messages and maintains session state
   - WebSocket integration for real-time updates
   - REST API endpoints for direct interaction

2. **Frontend Components**:
   - Real-time display of observer insights in the monitoring interface
   - Mood timeline visualization
   - Tag collection and display
   - Customizable observer controls

## WebSocket Communication

The system uses Socket.IO for real-time bidirectional communication:

1. When a researcher opens a monitoring page, their client connects to a specific "room" for that session
2. As new messages are added to the session, the server:
   - Sends the raw message to all connected monitors
   - Processes the message with the AI Observer
   - Sends the AI observations to all connected monitors

This provides a much more responsive experience than polling, with insights appearing as soon as they're generated.

## AI Observer Capabilities

### 1. Semantic Note Taking

For each message in the conversation (from both participant and AI interviewer), the observer generates:
- A brief insightful note (1-2 sentences) summarizing the key point
- 1-3 semantic tags that categorize this segment (e.g., pain points, user needs, emotions)
- A mood estimate on a scale of -10 to +10

### 2. Tag Collection

Throughout the session, the observer maintains a running list of all tags it has identified. These tags help researchers identify patterns and themes in real-time.

### 3. Mood Timeline

The observer tracks the emotional state of the participant throughout the conversation, visualized as a timeline that researchers can use to identify emotional high and low points.

### 4. Session Summary

At any point (or at the end of the session), researchers can generate a comprehensive summary of the observer's insights:
- Key themes and patterns
- Important insights
- Notable participant emotions/reactions
- Primary user needs and pain points identified

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/observer/<session_id>/analyze_message` | POST | Analyze a specific message |
| `/api/observer/<session_id>/state` | GET | Get the current observer state |
| `/api/observer/<session_id>/summary` | POST | Generate a summary of observations |

## WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `join_monitor_room` | Client → Server | Join a session monitoring room |
| `new_message` | Server → Client | New message in the session |
| `new_observation` | Server → Client | New AI observation |
| `observer_data` | Server → Client | Complete observer state |
| `observer_summary` | Server → Client | Generated summary |

## Using the AI Observer

1. **View Live Observations**:
   As the interview progresses, observations appear automatically underneath each message

2. **Toggle Observations**:
   Use the "Show AI observations" toggle to show/hide the AI insights

3. **Track Emotional State**:
   Watch the mood timeline for emotional shifts during the conversation

4. **Monitor Key Topics**:
   The "Detected Topics" section shows all tags identified so far

5. **Generate Insights**:
   Click "Generate Insights" at any time to get a comprehensive summary

## Technical Implementation

The AI Observer uses:
- LangChain for orchestrating the analysis chain
- GPT-4 for generating high-quality observations
- Socket.IO for real-time communication
- Custom Flask endpoints for direct API access

## Future Enhancements

Planned enhancements include:
- More detailed mood analysis and sentiment tracking
- Customizable observation prompts
- Integration with session analysis for deeper insights
- Comparative analysis across multiple sessions
- Export observations to research note tools 