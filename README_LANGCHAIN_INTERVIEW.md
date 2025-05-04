# DARIA Interview Tool - LangChain Integration

This documentation describes how to use the LangChain-based interview system with custom prompts in the DARIA Interview Tool.

## Overview

The LangChain integration enables:

1. Creating interview templates with custom interview prompts and analysis prompts
2. Running interviews using voice recognition and text-to-speech
3. Generating automatic analysis of interview transcripts based on custom analysis prompts

## Setup

### Requirements

- Python 3.9+ with required packages (install with `pip install -r requirements.txt`)
- OpenAI API key (for GPT-4/GPT-3.5 access)
- ElevenLabs API key (optional, for high-quality text-to-speech)

### Environment Variables

Set up the following environment variables:

```bash
export OPENAI_API_KEY=your_openai_key_here
export ELEVENLABS_API_KEY=your_elevenlabs_key_here  # Optional
```

## Usage

### 1. Creating Interview Templates

1. Navigate to http://localhost:5010/interview_setup
2. Fill in the interview details:
   - Title and project name
   - Select a character (optional)
   - Enter a custom interview prompt
   - Enter a custom analysis prompt
   - Select a voice for text-to-speech (optional)
3. Submit the form to create the interview template

The interview prompt is used to guide the AI in how to conduct the interview. The analysis prompt is used to analyze the interview transcript after completion.

### 2. Running Interviews

You can run interviews using several methods:

#### Method 1: Web Interface

1. Run the interview launcher UI:
   ```bash
   python launch_interview_ui.py
   ```
2. Open http://localhost:5050 in your browser
3. Select an interview from the list and click "Start Interview"
4. Choose whether to use text-to-speech and select an AI model
5. The interview will run in a terminal window

#### Method 2: Command Line

Run an interview directly from the command line:

```bash
python run_interview_with_session.py --session_id <session_id> --use_tts
```

Options:
- `--session_id`: ID of the interview session (required)
- `--use_tts`: Enable text-to-speech (optional)
- `--model`: OpenAI model to use (default: gpt-4o)
- `--max_turns`: Maximum number of interview turns (default: 10)
- `--temperature`: Temperature for LLM responses (default: 0.7)

#### Method 3: Direct API Calls

The system exposes several API endpoints:

- `POST /interview/create`: Create a new interview
- `POST /interview/start`: Start an interview session
- `POST /interview/respond`: Get AI response to user input
- `POST /interview/end`: End an interview and generate analysis

### 3. Viewing Results

After an interview is completed:

1. The conversation transcript is saved in data/interviews/<session_id>.json
2. If an analysis prompt was provided, the analysis is included in the saved data
3. Visit http://localhost:5010/interview_details/<session_id> to view the interview details and analysis

## Scripts

- `langchain_conversation_with_custom_prompts.py`: Main script for running interviews
- `run_interview_with_session.py`: Helper to run interviews with existing session IDs
- `launch_interview_ui.py`: Web UI for managing and launching interviews

## Custom Prompts

### Interview Prompt

The interview prompt tells the AI how to conduct the interview. Example:

```
You are an expert UX researcher conducting a user interview about a new mobile app. 
Ask open-ended questions that explore the user's needs, goals, pain points, and daily habits.
Be conversational and empathetic. Avoid leading questions.
Focus on understanding the user's context rather than suggesting solutions.
```

### Analysis Prompt

The analysis prompt tells the AI how to analyze the interview transcript. Example:

```
Analyze this interview transcript to identify:
1. Key user needs and goals
2. Pain points and frustrations
3. Behavioral patterns and habits
4. Opportunities for product improvement
5. Unexpected insights

Structure your analysis with clear headings and include specific quotes from the user.
Conclude with 3-5 actionable recommendations.
```

## Integration with Main System

The LangChain interview functionality is integrated with the main DARIA system. You can:

1. Create interviews via the standard interface
2. Run interviews using either the built-in system or via command line
3. View and analyze results in the main dashboard

## Troubleshooting

- **Missing API keys**: Make sure OPENAI_API_KEY is set
- **Text-to-speech issues**: Ensure the audio service is running (check with `curl http://localhost:5007`)
- **Port conflicts**: If ports are in use, restart the services with different ports

## Adding New Features

To extend the system:
- Add new character templates in `/langchain_features/prompt_manager/prompts/`
- Add custom analysis prompts for different use cases
- Modify the frontend to expose additional options 