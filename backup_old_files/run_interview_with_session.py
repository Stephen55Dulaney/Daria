#!/usr/bin/env python3
"""
Run Interview with Session ID

This script loads an interview configuration from a session ID and runs the
langchain_conversation_with_custom_prompts.py script with the appropriate
parameters from that session.
"""

import os
import sys
import json
import argparse
import subprocess

def load_interview_data(session_id):
    """Load interview data from the session ID"""
    try:
        data_dir = "data/interviews"
        file_path = f"{data_dir}/{session_id}.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        else:
            print(f"No interview data found for session ID: {session_id}")
            return None
    except Exception as e:
        print(f"Error loading interview data: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Run an interview with a specific session ID')
    parser.add_argument('--session_id', type=str, required=True, help='Interview session ID to load')
    parser.add_argument('--use_tts', action='store_true', help='Use text-to-speech for AI responses')
    parser.add_argument('--model', type=str, default='gpt-4o', help='OpenAI model to use')
    parser.add_argument('--max_turns', type=int, default=10, help='Maximum number of interview turns')
    parser.add_argument('--temperature', type=float, default=0.7, help='Temperature for the LLM')
    args = parser.parse_args()

    # Load interview data
    interview_data = load_interview_data(args.session_id)
    if not interview_data:
        sys.exit(1)

    # Extract the required parameters
    interview_prompt = interview_data.get('interview_prompt', '')
    analysis_prompt = interview_data.get('analysis_prompt', '')
    voice_id = interview_data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
    title = interview_data.get('title', 'Untitled Interview')

    print(f"Running interview: {title}")
    print(f"Session ID: {args.session_id}")
    print(f"Using model: {args.model}")
    print(f"Voice ID: {voice_id}")
    print(f"Max turns: {args.max_turns}")
    print(f"Temperature: {args.temperature}")
    print()

    # Build the command
    cmd = [
        'python', 'langchain_conversation_with_custom_prompts.py',
        '--session_id', args.session_id,
    ]

    # Add optional parameters if provided
    if interview_prompt:
        cmd.extend(['--interview_prompt', interview_prompt])
    
    if analysis_prompt:
        cmd.extend(['--analysis_prompt', analysis_prompt])
    
    if args.use_tts:
        cmd.append('--use_tts')
    
    if voice_id:
        cmd.extend(['--voice_id', voice_id])
    
    cmd.extend(['--model', args.model])
    cmd.extend(['--max_turns', str(args.max_turns)])
    cmd.extend(['--temperature', str(args.temperature)])

    print("Command to execute:")
    print(" ".join(cmd))
    print("\nStarting interview...\n")

    # Execute the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterview interrupted by user.")
        sys.exit(0)

if __name__ == '__main__':
    main() 