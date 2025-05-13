#!/usr/bin/env python3
"""
DARIA Interview Tool - Demo Script

This script demonstrates how to run a LangChain interview with custom
interview_prompt and analysis_prompt. It creates a new interview session
and runs a simple interview, then generates an analysis.
"""

import os
import sys
import json
import uuid
from datetime import datetime
import argparse
import subprocess

# Check for OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please set it with: export OPENAI_API_KEY=your_key_here")
    sys.exit(1)

def create_interview_session(title, interview_prompt, analysis_prompt):
    """Create a new interview session with custom prompts"""
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Create the data directory if it doesn't exist
    data_dir = "data/interviews"
    os.makedirs(data_dir, exist_ok=True)
    
    # Create interview data
    interview_data = {
        'session_id': session_id,
        'title': title,
        'project': 'Demo Project',
        'interview_type': 'custom_interview',
        'interview_prompt': interview_prompt,
        'analysis_prompt': analysis_prompt,
        'character_select': 'daria',  # Default character
        'voice_id': 'EXAVITQu4vr4xnSDxMaL',  # Rachel voice
        'created_at': datetime.now().isoformat(),
        'status': 'active',
        'conversation_history': []
    }
    
    # Save the interview data
    file_path = f"{data_dir}/{session_id}.json"
    with open(file_path, 'w') as f:
        json.dump(interview_data, f, indent=2)
    
    print(f"Created interview session: {session_id}")
    print(f"Saved to: {file_path}")
    
    return session_id

def run_interview(session_id, use_tts=False, model="gpt-4o-mini"):
    """Run the interview using the langchain_conversation_with_custom_prompts.py script"""
    cmd = [
        'python', 'langchain_conversation_with_custom_prompts.py',
        '--session_id', session_id,
        '--model', model,
        '--max_turns', '5'  # Limit to 5 turns for the demo
    ]
    
    if use_tts:
        cmd.append('--use_tts')
    
    print(f"\nRunning interview with command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running interview: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterview interrupted by user.")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Run a demo interview with custom prompts')
    parser.add_argument('--use_tts', action='store_true', help='Use text-to-speech')
    parser.add_argument('--model', type=str, default="gpt-4o-mini", help='OpenAI model to use')
    args = parser.parse_args()
    
    # Demo interview prompt
    interview_prompt = """
You are an expert UX researcher conducting an interview about the user's experience with mobile banking apps.
Ask open-ended questions to understand:
1. How they currently manage their finances using mobile apps
2. Pain points and frustrations with existing banking apps
3. Features they wish existed but don't currently have
4. Security and privacy concerns

Be conversational and empathetic. Each question should build on the previous response.
Start with a friendly introduction and general question about their banking app usage.
    """
    
    # Demo analysis prompt
    analysis_prompt = """
Analyze this interview transcript about mobile banking apps to identify:

1. User Needs and Goals:
   - Primary financial management tasks
   - Frequency and context of banking app usage
   - Key motivations for using banking apps

2. Pain Points:
   - Usability issues and friction points
   - Missing features or functionality
   - Emotional frustrations

3. Behavioral Patterns:
   - How users currently work around limitations
   - Decision-making processes for financial management
   - Integration with other tools or services

4. Security Considerations:
   - Attitudes toward security features
   - Balance between security and convenience
   - Trust factors influencing app usage

Include specific quotes from the user to support your findings.
Conclude with 3-5 actionable recommendations for improving mobile banking app experiences.
    """
    
    print("===============================================")
    print("DARIA Interview Tool - Demo Script")
    print("===============================================")
    print("This demo will create a new interview session with custom prompts")
    print("and run a sample interview about mobile banking apps.\n")
    
    # Create the interview session
    session_id = create_interview_session(
        "Mobile Banking UX Research Demo",
        interview_prompt,
        analysis_prompt
    )
    
    print("\nPress Enter to start the interview, or Ctrl+C to exit.")
    input()
    
    # Run the interview
    run_interview(session_id, args.use_tts, args.model)
    
    print("\n===============================================")
    print("Demo completed!")
    print("===============================================")
    print(f"Interview session ID: {session_id}")
    print(f"The full interview transcript and analysis are saved in data/interviews/{session_id}.json")
    print("\nYou can view the results in the web interface or run:")
    print(f"python -c \"import json; print(json.load(open('data/interviews/{session_id}.json'))['analysis'])\"")
    
if __name__ == "__main__":
    main() 