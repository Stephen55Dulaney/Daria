"""
Interview Service for managing LangChain interview agents
"""

import os
import logging
from typing import Dict, Any, Optional, List
import json
import datetime
import uuid
from pathlib import Path

from .interview_agent import InterviewAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterviewService:
    """Service for managing LangChain interview agents and sessions"""
    
    def __init__(self, data_dir: str = "data/interviews"):
        """
        Initialize the Interview Service
        
        Args:
            data_dir: Directory for storing interview data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Active interview agents
        self.active_agents: Dict[str, InterviewAgent] = {}
        
        logger.info(f"Initialized InterviewService with data_dir={data_dir}")
    
    def start_interview(
        self,
        character_name: str,
        system_prompt: str,
        title: str = "Untitled Interview",
        description: str = "",
        session_id: str = None,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Start a new interview session
        
        Args:
            character_name: Name of the character/persona
            system_prompt: System prompt for the LLM
            title: Interview title
            description: Interview description
            session_id: Optional session ID (generated if not provided)
            model_name: LLM model to use
            temperature: Temperature setting for LLM response generation
            
        Returns:
            Dict with session information including session_id and greeting message
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create interview agent
        agent = InterviewAgent(
            character_name=character_name,
            system_prompt=system_prompt,
            session_id=session_id,
            model_name=model_name,
            temperature=temperature
        )
        
        # Store agent in active sessions
        self.active_agents[session_id] = agent
        
        # Create interview metadata
        now = datetime.datetime.now()
        interview_data = {
            'session_id': session_id,
            'character': character_name,
            'title': title,
            'description': description,
            'status': 'active',
            'created_at': now,
            'last_updated': now,
            'expiration_date': now + datetime.timedelta(days=7),
            'conversation_history': []
        }
        
        # Generate greeting
        greeting = self._generate_greeting(character_name)
        
        # Add greeting to conversation history
        interview_data['conversation_history'].append({
            'role': 'assistant',
            'content': greeting,
            'timestamp': now.isoformat()
        })
        
        # Save interview data
        self._save_interview(session_id, interview_data)
        
        return {
            'success': True,
            'session_id': session_id,
            'message': greeting
        }
    
    def handle_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Handle a message in an interview session
        
        Args:
            session_id: Interview session ID
            message: User message
            
        Returns:
            Dict with response message
        """
        # Check if session exists
        if session_id not in self.active_agents:
            # Try to load session from disk
            interview_data = self._load_interview(session_id)
            if interview_data:
                character_name = interview_data.get('character', 'interviewer')
                system_prompt = interview_data.get('system_prompt', "You are a helpful interview assistant.")
                
                # Create agent
                agent = InterviewAgent(
                    character_name=character_name,
                    system_prompt=system_prompt,
                    session_id=session_id
                )
                
                # Restore conversation history
                for msg in interview_data.get('conversation_history', []):
                    if msg['role'] == 'user':
                        # Add user messages to memory
                        agent.memory.chat_memory.add_user_message(msg['content'])
                    elif msg['role'] == 'assistant':
                        # Add assistant messages to memory
                        agent.memory.chat_memory.add_ai_message(msg['content'])
                
                # Store agent in active sessions
                self.active_agents[session_id] = agent
            else:
                return {
                    'success': False,
                    'error': f"Session {session_id} not found"
                }
        
        # Get agent
        agent = self.active_agents[session_id]
        
        # Add user message to conversation history
        interview_data = self._load_interview(session_id)
        if interview_data:
            interview_data['conversation_history'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.datetime.now().isoformat()
            })
            interview_data['last_updated'] = datetime.datetime.now()
            self._save_interview(session_id, interview_data)
        
        # Generate response
        response = agent.generate_response(message)
        
        # Add response to conversation history
        if interview_data:
            interview_data['conversation_history'].append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.datetime.now().isoformat()
            })
            self._save_interview(session_id, interview_data)
        
        return {
            'success': True,
            'message': response
        }
    
    def end_interview(self, session_id: str) -> Dict[str, Any]:
        """
        End an interview session
        
        Args:
            session_id: Interview session ID
            
        Returns:
            Dict with success status
        """
        # Check if session exists
        if session_id not in self.active_agents:
            return {
                'success': False,
                'error': f"Session {session_id} not found"
            }
        
        # Remove agent from active sessions
        agent = self.active_agents.pop(session_id)
        
        # Update interview data
        interview_data = self._load_interview(session_id)
        if interview_data:
            interview_data['status'] = 'completed'
            interview_data['last_updated'] = datetime.datetime.now()
            self._save_interview(session_id, interview_data)
        
        return {
            'success': True,
            'message': f"Interview session {session_id} ended"
        }
    
    def _generate_greeting(self, character_name: str) -> str:
        """Generate a greeting message based on character"""
        character_greetings = {
            'daria': "Hello, I'm Daria, Deloitte's Advanced Research & Interview Assistant. I'll be conducting this interview today. How are you doing?",
            'skeptica': "Hi there, I'm Skeptica. My role is to ask thoughtful questions and challenge assumptions. Let's begin our conversation.",
            'eurekia': "Welcome! I'm Eurekia, and I'm here to help uncover insights through our conversation. I'm looking forward to our discussion.",
            'thesea': "Hello! I'm Thesea, and I'll be mapping your journey today through a series of questions. Ready to get started?",
            'askia': "Greetings! I'm Askia, your interview assistant. I'm designed to ask strategic questions to uncover valuable insights. Shall we begin?",
            'odessia': "Welcome! I'm Odessia, your journey mapping assistant. Let's explore your experiences together."
        }
        
        return character_greetings.get(
            character_name.lower(), 
            f"Hello, I'm your interview assistant. I'll be asking you some questions today. Let's get started!"
        )
    
    def _save_interview(self, session_id: str, interview_data: Dict[str, Any]) -> bool:
        """Save interview data to file"""
        try:
            # Convert datetime objects to ISO format
            serializable_data = {}
            for key, value in interview_data.items():
                if isinstance(value, datetime.datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            # Save to file
            file_path = self.data_dir / f"{session_id}.json"
            with open(file_path, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving interview data: {str(e)}")
            return False
    
    def _load_interview(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load interview data from file"""
        try:
            file_path = self.data_dir / f"{session_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert ISO dates back to datetime
            for key, value in data.items():
                if key in ['created_at', 'last_updated', 'expiration_date'] and isinstance(value, str):
                    try:
                        data[key] = datetime.datetime.fromisoformat(value)
                    except ValueError:
                        pass
            
            return data
        except Exception as e:
            logger.error(f"Error loading interview data: {str(e)}")
            return None
            
    def generate_analysis(self, transcript: str, prompt: str) -> str:
        """
        Generate analysis of an interview transcript
        
        Args:
            transcript: The formatted interview transcript
            prompt: The analysis prompt to use
            
        Returns:
            The generated analysis text
        """
        try:
            # Import the necessary LangChain components
            try:
                from langchain_community.chat_models import ChatOpenAI
            except ImportError:
                from langchain.chat_models import ChatOpenAI
                
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate
            
            # Initialize the language model
            llm = ChatOpenAI(
                temperature=0.3,  # Lower temperature for more focused/analytical responses
                model_name="gpt-4" if os.environ.get("USE_GPT4", "").lower() == "true" else "gpt-3.5-turbo-16k",
            )
            
            # Create a prompt template for analysis
            template = """
            {analysis_prompt}
            
            INTERVIEW TRANSCRIPT:
            {transcript}
            
            ANALYSIS:
            """
            
            prompt_template = PromptTemplate(
                input_variables=["analysis_prompt", "transcript"],
                template=template
            )
            
            # Create the LLM chain
            chain = LLMChain(llm=llm, prompt=prompt_template)
            
            # Generate the analysis
            analysis = chain.run(analysis_prompt=prompt, transcript=transcript)
            
            logger.info(f"Successfully generated analysis of {len(transcript)} characters")
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating analysis: {str(e)}")
            return f"Error generating analysis: {str(e)}"
            
    def generate_summary(self, session_id: str) -> str:
        """
        Generate a summary of an interview
        
        Args:
            session_id: The interview session ID
            
        Returns:
            A summary of the interview
        """
        try:
            # Load the interview data
            interview_data = self._load_interview(session_id)
            if not interview_data:
                return "Interview data not found"
                
            # Format the transcript
            transcript = self._format_transcript(interview_data)
            
            # Generate a summary using a simple prompt
            summary_prompt = """
            Provide a concise summary of this interview, highlighting:
            1. Key topics discussed
            2. Main insights
            3. Notable points made by the interviewee
            
            Keep the summary brief and focused on the most important information.
            """
            
            # Use the analysis method with a summary prompt
            return self.generate_analysis(transcript, summary_prompt)
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
            
    def generate_response(self, session_id_or_messages, prompt: str = "", character: str = None, context_data: dict = None) -> str:
        """
        Generate a response based on a session or a set of messages
        
        Args:
            session_id_or_messages: Session ID or list of messages
            prompt: Optional explicit prompt for the LLM
            character: Character name (optional)
            context_data: Dictionary containing topic, context, and goals
            
        Returns:
            Generated response string
        """
        try:
            if context_data is None:
                context_data = {}
            
            # Set default values for required parameters
            topic = context_data.get('topic', 'General Interview')
            context = context_data.get('context', 'This is an interview conversation.')
            goals = context_data.get('goals', ['Gather relevant information from the participant'])
            
            # Ensure goals is a list
            if isinstance(goals, str):
                goals = [goals]
            
            # Log the context being used
            logger.info(f"generate_response: Using topic: {topic}, context length: {len(context)}, goals: {len(goals)} items")
            
            # Prepare input data
            if isinstance(session_id_or_messages, str):
                # It's a session ID, try to load the session
                logger.info(f"generate_response: Loading session with ID {session_id_or_messages}")
                session_data = self._load_interview(session_id_or_messages)
                
                if not session_data:
                    logger.warning(f"No conversation history found for session {session_id_or_messages}")
                    
                conversation_history = []
                
                if session_data and 'conversation_history' in session_data:
                    conversation_history = session_data['conversation_history']
                    logger.info(f"generate_response: Loaded {len(conversation_history)} messages from session")
                
                # Use dedicated character from session if not provided
                if not character and session_data:
                    character = session_data.get('character', 'interviewer')
                    logger.info(f"generate_response: Using character '{character}' from session")
            else:
                # It's already a list of messages
                conversation_history = session_id_or_messages
                logger.info(f"generate_response: Using provided list of {len(conversation_history)} messages")
            
            # Prepare the prompt
            if not prompt:
                # Use most recent user message as prompt
                if conversation_history:
                    for msg in reversed(conversation_history):
                        if msg.get('role') == 'user':
                            prompt = msg.get('content', '')
                            break
                
                if not prompt:
                    prompt = "Hello, can you help me with this interview?"
                    logger.warning("generate_response: No prompt found in conversation history, using default")
            
            # Set a default character if not provided
            if not character:
                character = "interviewer"
                logger.info(f"generate_response: Using default character '{character}'")
            
            # Build the complete system prompt
            system_prompt = f"""You are conducting an interview on the topic of '{topic}'. 

Context: {context}

Your goals are:
"""
            # Add goals to prompt
            for goal in goals:
                system_prompt += f"- {goal}\n"
            
            system_prompt += """
Maintain a professional, empathetic tone throughout the conversation.
Ask follow-up questions based on the participant's responses.
Keep your responses concise and focused on the interview topic.
"""
            
            # Create messages list for the API call
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history (limited to last 10 messages to avoid token limits)
            history_limit = min(len(conversation_history), 10)
            for msg in conversation_history[-history_limit:]:
                role = msg.get('role')
                content = msg.get('content')
                
                # Only include user and assistant messages
                if role in ['user', 'assistant'] and content:
                    messages.append({"role": role, "content": content})
            
            # Use GPT model to generate response
            try:
                openai_api_key = os.environ.get('OPENAI_API_KEY')
                if not openai_api_key:
                    logger.error("Missing OPENAI_API_KEY environment variable")
                    return "I'm sorry, I'm having trouble accessing my reasoning capabilities at the moment."
                
                # Add user's current message if it's not already in the history
                if prompt and (not messages or messages[-1]["role"] != "user"):
                    messages.append({"role": "user", "content": prompt})
                
                from openai import OpenAI
                
                client = OpenAI(api_key=openai_api_key)
                logger.info(f"generate_response: Sending request to OpenAI with {len(messages)} messages")
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                
                response_text = response.choices[0].message.content.strip()
                logger.info(f"generate_response: Generated response of {len(response_text)} characters")
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                return f"I apologize, but I'm having trouble processing your response at the moment. Could you please rephrase your question?"
                
        except Exception as e:
            logger.error(f"Error in generate_response method: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Let's continue our conversation from a different angle. Could you tell me more about your thoughts on this topic?"
            
    def _format_transcript(self, interview_data: Dict[str, Any]) -> str:
        """Format interview data into a readable transcript for analysis"""
        formatted = ""
        
        # Add basic metadata
        formatted += f"Interview Title: {interview_data.get('title', 'Untitled Interview')}\n"
        formatted += f"Date: {interview_data.get('created_at', '')}\n"
        formatted += f"Character: {interview_data.get('character', 'Interviewer')}\n\n"
        formatted += "TRANSCRIPT:\n\n"
        
        # Add conversation history
        if 'conversation_history' in interview_data and interview_data['conversation_history']:
            for message in interview_data['conversation_history']:
                speaker = "Interviewer" if message.get('role') == 'assistant' else "Participant"
                formatted += f"{speaker}: {message.get('content', '')}\n\n"
        
        return formatted 