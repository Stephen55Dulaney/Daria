# DARIA Remote Interview System - Release Candidate 1

## Overview

The DARIA Remote Interview System is a specialized module built on top of the DARIA Interview Tool that allows researchers to conduct remote interviews with participants using AI-powered voice capabilities.

## Release Candidate 1 Features

This release candidate (RC1) includes the following features:

### ElevenLabs Integration
- Text-to-speech conversion using ElevenLabs API for natural-sounding AI voices
- Support for multiple voice options (Rachel, Antoni, Elli, Domi, Fin)
- Speech-to-text functionality for transcribing participant responses
- Automatic fallback to browser-based speech synthesis when needed

### Interview Management
- Creation and configuration of interview sessions
- Character selection for different interviewer personas (Skeptica, Empathica, etc.)
- Session persistence between pages and application restarts
- Session tracking with unique IDs
- Transcript generation and storage

### User Experience
- Simple and intuitive interview setup interface
- Real-time voice capture and response
- Visual feedback during recording
- Support for both text and voice input methods

## How to Use

1. Start the services with `./start_services.sh`
2. Navigate to `http://127.0.0.1:5010/dashboard`
3. Go to the Interview Setup page to configure a new interview
4. Select a character and voice
5. Start the interview session

## Known Issues

- When the application is restarted without saving the state, session data may be lost
- Some browsers may require permission settings for microphone access
- Occasional connection issues with ElevenLabs API may occur

## Next Steps

The following features are planned for future releases:
- Enhanced database persistence for interview sessions
- Vector database for semantic search and analysis of transcripts
- Improved security measures for handling sensitive interview data

## Security Features

The system implements several security measures:

- **Tokenized Access**: Each interview link contains a unique UUID token required for access
- **Link Expiration**: Links expire after a configurable period (default: 7 days)
- **Secure Session Handling**: Participants can only access their assigned interview
- **Authorization Checks**: API endpoints verify tokens before allowing operations
- **Real-time Monitoring**: Administrators can monitor interviews as they happen
- **Data Segregation**: Each interview's data is stored in separate JSON files

## Components

### 1. Link Generation
- Generate unique interview links from `/langchain/generate_link`
- Set expiration dates, interview type, and custom prompts
- Links are in format: `http://your-domain/langchain/participate/{id}?token={token}`

### 2. Participant Interview Interface
- User-friendly interface with microphone testing
- Text or voice input options
- Secure token handling in the background
- Real-time response recording

### 3. Interview Monitoring
- View interviews in real-time at `/langchain/monitor/{id}`
- Auto-refresh transcript updates
- Notification options for new responses
- Download completed transcripts

## Running the System

1. Start the server using:
```
python run_interview_system.py
```

2. Access the dashboard at:
```
http://127.0.0.1:8000/langchain/dashboard
```

3. Generate interview links at:
```
http://127.0.0.1:8000/langchain/generate_link
```

4. Monitor ongoing interviews at:
```
http://127.0.0.1:8000/langchain/monitor/{interview_id}
```

## Production Considerations

For deploying to AWS or other production environments, consider these additional security measures:

1. **HTTPS Implementation**: Use SSL/TLS for all connections
2. **Database Storage**: Replace file-based storage with a secure database
3. **Authentication System**: Add user authentication for administrators
4. **Role-Based Access Control**: Implement RBAC for different user types
5. **Encryption**: Add end-to-end encryption for sensitive data
6. **API Rate Limiting**: Prevent abuse through rate limiting
7. **Audit Logging**: Implement comprehensive logging for security events
8. **Regular Security Scans**: Schedule automated security assessments
9. **AWS-specific Security**:
   - Use AWS IAM for access control
   - Implement AWS Web Application Firewall
   - Store sensitive data in AWS Secrets Manager
   - Use AWS CloudTrail for audit logging
   - Configure VPC and security groups properly

## Folder Structure

```
daria_interview_tool/
├── templates/
│   └── langchain/
│       ├── generate_link.html      # Link generation form
│       ├── link_generated.html     # Shows generated link
│       ├── participant_interview.html  # Participant interface
│       ├── monitor_interview.html  # Admin monitoring interface
│       └── interview_error.html    # Error handling
├── interviews/
│   └── raw/                        # Stores interview data
│       ├── {id}.json               # Interview metadata
│       └── {id}_transcript.json    # Interview transcript
└── static/
    └── images/                     # UI assets
```

## API Endpoints

- `POST /api/langchain_interview/save_response`: Save participant responses
- `POST /api/langchain_interview/complete`: Mark interview as completed
- `GET /api/langchain_interview/transcript`: Retrieve interview transcript
- `POST /api/diagnostics/microphone`: Test microphone functionality
- `POST /process_audio`: Process and transcribe audio files 