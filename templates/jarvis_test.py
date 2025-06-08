"""
Jarvis Interview Test Script with TTS/STT Support

This script provides a command-line interface for testing the Jarvis interview system
with text-to-speech and speech-to-text capabilities, and multi-agent conversations.
"""

import sys
import time
import logging
import json
import requests
from typing import Dict, List, Optional
import pyttsx3
import speech_recognition as sr

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JarvisInterview:
    def __init__(self):
        self.interview_started = False
        self.current_question = 0
        self.agents = {
            'jarvis': {
                'name': 'Jarvis',
                'role': 'UX Research Assistant',
                'expertise': ['User Interviews', 'Contextual Inquiry', 'UX Research'],
                'prompt': """You are Jarvis, a UX Research Assistant specializing in user interviews and contextual inquiry.
Your role is to conduct insightful interviews about user experiences with software systems.
You should be friendly, professional, and focused on understanding user needs and pain points.
When you detect topics related to discovery research or project planning, you should acknowledge that
Synthia or Daria would be better suited to help with those aspects."""
            },
            'daria': {
                'name': 'Daria',
                'role': 'Research Project Manager',
                'expertise': ['Project Planning', 'Research Strategy', 'Team Coordination'],
                'prompt': """You are Daria, a Research Project Manager with expertise in coordinating research efforts
and managing research projects. You help teams plan and execute research initiatives effectively.
You should focus on project timelines, resource allocation, and research strategy."""
            },
            'synthia': {
                'name': 'Synthia',
                'role': 'Discovery Research Specialist',
                'expertise': ['Discovery Research', 'User Research', 'Research Planning'],
                'prompt': """You are Synthia, a Discovery Research Specialist focused on helping teams plan
and execute discovery research. You excel at creating research plans, identifying research questions,
and structuring discovery efforts. You should be proactive in offering guidance on research methodology
and planning."""
            }
        }
        self.active_agents = ['jarvis']
        self.conversation_history = []
        self.current_agent = 'jarvis'
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Load agent voices
        self.voices = self.tts_engine.getProperty('voices')
        self.tts_engine.setProperty('voice', self.voices[0].id)  # Default voice

    def speak(self, text: str, agent: str = None):
        """Convert text to speech."""
        if agent is None:
            agent = self.current_agent
        print(f"\n{self.agents[agent]['name']}: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen(self) -> str:
        """Listen for user input using speech recognition."""
        with sr.Microphone() as source:
            print("\nListening...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except sr.WaitTimeoutError:
                print("No speech detected")
                return ""
            except sr.UnknownValueError:
                print("Could not understand audio")
                return ""
            except sr.RequestError as e:
                print(f"Error with speech recognition service: {e}")
                return ""

    def start_interview(self):
        """Initialize the interview session."""
        welcome_message = """Welcome! I'm Jarvis, a UX Research Assistant.
I can help you with user interviews and research. I'm joined by my colleagues:
- Daria, our Research Project Manager
- Synthia, our Discovery Research Specialist

Type 'Start' to begin the interview.
Type 'help' for available commands.
Type 'exit' to end the session.
Type 'voice' to toggle voice input/output."""

        self.speak(welcome_message)

    def switch_agent(self, new_agent: str):
        """Switch the current active agent."""
        if new_agent in self.agents and new_agent not in self.active_agents:
            self.active_agents.append(new_agent)
            self.current_agent = new_agent
            intro = f"Hello! I'm {self.agents[new_agent]['name']}, {self.agents[new_agent]['role']}. I'd be happy to help you with {', '.join(self.agents[new_agent]['expertise'])}. What specific aspects would you like to explore?"
            self.speak(intro, new_agent)
            return True
        return False

    def process_input(self, user_input: str) -> str:
        """Process user input and generate appropriate response."""
        user_input = user_input.lower().strip()
        
        if user_input == 'exit':
            return "Thank you for participating in this interview. Goodbye!"
            
        if user_input == 'help':
            return self.get_help_text()
            
        if user_input == 'voice':
            return "Voice mode toggled. You can now speak your responses."
            
        if not self.interview_started:
            if user_input == 'start':
                self.interview_started = True
                return "Tell me about your role and how often you use the ordering portal."
            return "Please type 'Start' to begin the interview."
        
        # Add user input to conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Check for topics that might require additional agents
        if any(keyword in user_input.lower() for keyword in ['discovery', 'research plan', 'methodology', 'planning']):
            if self.switch_agent('synthia'):
                return "I'll let Synthia help you with the discovery planning. What specific aspects would you like to explore?"
        
        if any(keyword in user_input.lower() for keyword in ['project', 'timeline', 'resources', 'team', 'coordination']):
            if self.switch_agent('daria'):
                return "I'll let Daria help you with the project management aspects. What would you like to discuss?"
        
        # Get next question based on conversation state
        response = self.get_next_question()
        
        # Add response to conversation history
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
        return response

    def get_next_question(self) -> str:
        """Get the next question based on the current state."""
        self.current_question += 1
        
        questions = [
            "What aspects of the ordering system work well for you, and what challenges do you face?",
            "That's helpful to know. How do you currently handle backordered items? What would make this process better?",
            "Can you describe a specific instance where you had difficulty with a backordered item?",
            "When you need to find a substitute for a backordered item, what information is most important to you?",
            "How does the backorder situation affect your relationship with customers or other departments?",
            "If you could make one improvement to the ordering system, what would it be and why?",
            "This has been very insightful. Is there anything else about the ordering portal that you'd like to share before we conclude?"
        ]
        
        if self.current_question <= len(questions):
            return questions[self.current_question - 1]
        else:
            return "Thank you for your valuable feedback. This interview has provided important insights about the ordering portal experience and potential areas for improvement."

    def get_help_text(self) -> str:
        """Return help text for available commands."""
        return """
Available commands:
- 'start': Begin the interview
- 'help': Show this help message
- 'exit': End the interview session
- 'voice': Toggle voice input/output
- 'agents': Show active research assistants

You can also ask about:
- Discovery research planning (brings in Synthia)
- Project management (brings in Daria)
- User research methods
- Team coordination
"""

def main():
    """Main function to run the interview."""
    interview = JarvisInterview()
    interview.start_interview()
    
    use_voice = False
    
    while True:
        try:
            if use_voice:
                user_input = interview.listen()
            else:
                user_input = input("> ")
                
            if user_input.lower() == 'voice':
                use_voice = not use_voice
                print(f"Voice mode {'enabled' if use_voice else 'disabled'}")
                continue
                
            response = interview.process_input(user_input)
            interview.speak(response)
            
            if user_input.lower() == 'exit':
                break
                
        except KeyboardInterrupt:
            print("\nInterview ended by user.")
            break
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            print("I apologize, but I encountered an error. Please try again.")

if __name__ == "__main__":
    main() 