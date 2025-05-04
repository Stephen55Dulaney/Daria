#!/usr/bin/env python3
"""
LangChain Interview with Custom Prompts

This script runs a LangChain-based interview using custom prompts defined
in the interview setup form. It includes speech recognition and text-to-speech
capabilities, and generates an analysis at the end using the analysis prompt.
"""

import os
import sys
import json
import uuid
import time
import argparse
import speech_recognition as sr
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.document_loaders import TextLoader
from datetime import datetime

# Check for environment variables
try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("ERROR: OPENAI_API_KEY environment variable is not set.")
    print("Please set it with: export OPENAI_API_KEY=your_key_here")
    sys.exit(1)

# Setup argument parser
parser = argparse.ArgumentParser(description='Run an interview with LangChain using custom prompts')
parser.add_argument('--session_id', type=str, help='Interview session ID, used to load interview data')
parser.add_argument('--interview_prompt', type=str, help='Custom interview prompt')
parser.add_argument('--analysis_prompt', type=str, help='Custom analysis prompt')
parser.add_argument('--use_tts', action='store_true', help='Use text-to-speech for AI responses')
parser.add_argument('--voice_id', type=str, default="EXAVITQu4vr4xnSDxMaL", help='ElevenLabs voice ID')
parser.add_argument('--model', type=str, default="gpt-4o", help='OpenAI model to use')
parser.add_argument('--temperature', type=float, default=0.7, help='Temperature for the model')
parser.add_argument('--max_turns', type=int, default=10, help='Maximum number of interview turns')
parser.add_argument('--output_file', type=str, help='Output file for the transcript (defaults to interview_{session_id}.json)')
args = parser.parse_args()

# Initialize recognizer for speech recognition
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300

# Function to speak text using ElevenLabs API
def speak(text, voice_id=args.voice_id):
    """Speak text using ElevenLabs API"""
    import requests
    url = "http://127.0.0.1:5007/text_to_speech"
    response = requests.post(url, json={
        "text": text,
        "voice_id": voice_id
    })
    if response.status_code == 200:
        # Assuming the response is audio/mpeg
        print(f"AI: {text}")
        # In a full implementation, this would play the audio
        # For now we'll just print it
    else:
        print(f"Error with text-to-speech: {response.status_code}")
        print(f"AI: {text}")

# Function to recognize speech and convert it to text
def listen(timeout=10, phrase_time_limit=20):
    """Listen and convert speech to text"""
    with sr.Microphone() as source:
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = recognizer.recognize_google(audio)
            print(f"User said: {text}")
            return text
        except sr.UnknownValueError:
            print("Sorry, I did not understand that.")
            return ""
        except sr.RequestError:
            print("Sorry, my speech service is down.")
            return ""
        except Exception as e:
            print(f"Error in speech recognition: {str(e)}")
            return ""

# Function to load interview data from session_id
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

# Function to save conversation to a file
def save_conversation(session_id, interview_data, conversation_history):
    """Save conversation to a file"""
    try:
        data_dir = "data/interviews"
        os.makedirs(data_dir, exist_ok=True)
        
        # Update interview data with conversation history
        interview_data['conversation_history'] = conversation_history
        interview_data['last_updated'] = datetime.now().isoformat()
        interview_data['status'] = 'completed'
        
        file_path = f"{data_dir}/{session_id}.json"
        with open(file_path, 'w') as file:
            json.dump(interview_data, file, indent=2)
        
        print(f"Conversation saved to {file_path}")
        return file_path
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")
        return None

def main():
    # Generate a session ID if not provided
    session_id = args.session_id or str(uuid.uuid4())
    output_file = args.output_file or f"interview_{session_id}.json"
    
    # Interview data structure
    interview_data = None
    
    # Try to load existing interview data if session_id was provided
    if args.session_id:
        interview_data = load_interview_data(args.session_id)
    
    # If no data loaded, create new interview data
    if not interview_data:
        interview_data = {
            'session_id': session_id,
            'title': 'Custom LangChain Interview',
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'interview_prompt': args.interview_prompt,
            'analysis_prompt': args.analysis_prompt,
            'conversation_history': []
        }
    
    # Extract prompts from interview data
    interview_prompt = interview_data.get('interview_prompt', args.interview_prompt)
    analysis_prompt = interview_data.get('analysis_prompt', args.analysis_prompt)
    
    # Ensure we have a prompt
    if not interview_prompt:
        interview_prompt = ("You are an expert UX researcher conducting a user interview. "
                           "Ask open-ended questions to understand the user's needs, goals, and pain points. "
                           "Be conversational, empathetic, and curious.")
    
    if not analysis_prompt:
        analysis_prompt = ("Analyze the interview transcript to identify key insights, themes, and opportunities. "
                          "Highlight important quotes, pain points, user needs, and suggestions for improvement.")
    
    # Initialize LangChain components
    llm = ChatOpenAI(model=args.model, temperature=args.temperature)
    memory = ConversationBufferMemory()
    conversation = ConversationChain(llm=llm, memory=memory, verbose=True)
    
    # Create a file to save the transcript
    transcript_file = "transcript.txt"
    f = open(transcript_file, "w")
    
    # Conversation history to save
    conversation_history = []
    
    # Add the system prompt to conversation history
    conversation_history.append({
        "role": "system",
        "content": interview_prompt
    })
    
    # Begin the interview
    print("\n======== STARTING INTERVIEW ========\n")
    print(f"Using interview prompt: {interview_prompt[:100]}...\n")
    
    # Initial greeting from the assistant
    initial_prompt = f"{interview_prompt}\n\nStart the interview with a friendly greeting and your first question."
    greeting = conversation.predict(input=initial_prompt)
    
    # Add to conversation history
    conversation_history.append({
        "role": "assistant",
        "content": greeting
    })
    
    # Speak or print the greeting
    if args.use_tts:
        speak(greeting)
    else:
        print(f"AI: {greeting}")
    
    # Write to transcript
    f.write(f"AI: {greeting}\n")
    
    # Main interview loop
    for i in range(args.max_turns):
        # Get user input
        if args.use_tts:
            user_input = listen()
        else:
            user_input = input("You: ").strip()
        
        # Check for exit conditions
        if not user_input or user_input.lower() in ['exit', 'quit', 'end interview', 'end the interview']:
            break
        
        # Add to conversation history
        conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Write to transcript
        f.write(f"User: {user_input}\n")
        
        # Get AI response
        prompt = "Continue the interview and ask the next question or follow-up question based on the user's response."
        ai_response = conversation.predict(input=prompt)
        
        # Add to conversation history
        conversation_history.append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Speak or print the response
        if args.use_tts:
            speak(ai_response)
        else:
            print(f"AI: {ai_response}")
        
        # Write to transcript
        f.write(f"AI: {ai_response}\n")
    
    # Close the transcript file
    f.close()
    
    # Generate analysis using the analysis_prompt
    print("\n======== GENERATING ANALYSIS ========\n")
    print(f"Using analysis prompt: {analysis_prompt[:100]}...\n")
    
    # Load the interview transcript
    loader = TextLoader(transcript_file)
    documents = loader.load()
    context = " ".join([doc.page_content for doc in documents])
    
    # Construct the prompt template for analysis
    prompt_template = ChatPromptTemplate.from_template(
        f"{analysis_prompt}\n\nHere is the interview transcript:\n{{context}}\n\nGenerate a detailed analysis:"
    )
    
    # Create the LLM chain for analysis
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt_template
    )
    
    # Generate the analysis
    analysis = llm_chain.run({"context": context})
    
    # Print the analysis
    print("\n======== INTERVIEW ANALYSIS ========\n")
    print(analysis)
    
    # Add the analysis to conversation history and interview data
    conversation_history.append({
        "role": "system",
        "content": "Generated analysis"
    })
    conversation_history.append({
        "role": "assistant",
        "content": analysis
    })
    
    interview_data['analysis'] = analysis
    
    # Save the complete conversation
    save_path = save_conversation(session_id, interview_data, conversation_history)
    
    # Clean up
    if os.path.exists(transcript_file):
        os.remove(transcript_file)
    
    print(f"\nInterview completed and saved to {save_path}")
    print("\n======== INTERVIEW COMPLETED ========\n")

if __name__ == '__main__':
    main() 