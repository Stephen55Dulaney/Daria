#!/usr/bin/env python3
"""
DARIA Interview API - A minimal API for starting interviews and handling prompts
"""

import os
import sys
import json
import logging
import argparse
import datetime
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from flask import Flask, request, jsonify, render_template, redirect, Response, flash, send_file, url_for, session, send_from_directory
from flask_cors import CORS
import yaml
import requests
import subprocess
import time
from langchain_features.services.interview_service import InterviewService
from langchain_features.services.interview_agent import InterviewAgent
from langchain_features.services.discussion_service import DiscussionService
from langchain_features.services.observer_service import ObserverService
from flask_socketio import SocketIO, emit, join_room, leave_room
import openai
from flask_login import LoginManager, current_user, login_required
from models.user import User, UserRepository
import re
import traceback

# Import user routes
from user_routes import user_bp
from auth_routes import auth_bp
from routes.issue_routes import bp as issues_bp
from langchain_features import langchain_blueprint

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run DARIA Interview API')
parser.add_argument('--port', type=int, default=5025, help='Port to run the server on')
parser.add_argument('--use-langchain', action='store_true', help='Use LangChain for interviews')
parser.add_argument('--debug', action='store_true', help='Run in debug mode')
parser.add_argument('--no-langchain', action='store_true', help='Disable LangChain features')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

# Configure secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'daria-interview-tool-secret-key')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the user repository."""
    repo = UserRepository()
    return repo.get_user_by_id(user_id)

# Enable CORS with extended headers support
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
logger.info("CORS enabled for all origins with extended header support")

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logger.info("SocketIO initialized for real-time communication")

# Define paths
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data" / "interviews"
PROMPT_DIR = BASE_DIR / "tools" / "prompt_manager" / "prompts"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROMPT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize PromptManager
from tools.prompt_manager import PromptManager
prompt_mgr = PromptManager(prompt_dir=str(PROMPT_DIR))
logger.info(f"Initialized PromptManager with prompt_dir={PROMPT_DIR}")

# Initialize LangChain service if enabled
use_langchain = args.use_langchain

# Check if --no-langchain was explicitly provided (it overrides --use-langchain)
if args.no_langchain:
    use_langchain = False
    logger.info("LangChain explicitly disabled via --no-langchain flag")

interview_service = None
discussion_service = None
observer_service = None

# Always initialize discussion service
try:
    discussion_service = DiscussionService(data_dir=str(DATA_DIR))
    logger.info("Discussion service initialized successfully")
except Exception as e:
    logger.error(f"Error initializing discussion service: {str(e)}")
    discussion_service = None

# Initialize observer service regardless of LangChain setting
# This ensures monitoring capability works even with basic mode
try:
    observer_service = ObserverService(openai_api_key=os.environ.get('OPENAI_API_KEY'))
    logger.info("Observer service initialized successfully")
except Exception as e:
    logger.error(f"Error initializing observer service: {str(e)}")
    observer_service = None

if use_langchain:
    try:
        interview_service = InterviewService(data_dir=str(DATA_DIR))
        logger.info("LangChain interview service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing LangChain services: {str(e)}")
        logger.warning("Falling back to simple response generation")
        use_langchain = False
else:
    logger.info("Using simple response generation (LangChain disabled)")

# Cache for prompt configs to avoid repeated disk access
prompt_cache = {}

# ------ Helper Functions ------

def load_all_prompts() -> Dict[str, Dict[str, Any]]:
    """Load all prompt configurations."""
    try:
        agent_names = prompt_mgr.get_available_agents()
        logger.info(f"Found {len(agent_names)} agent prompts: {agent_names}")
        
        prompts = {}
        for agent_name in agent_names:
            try:
                if agent_name in prompt_cache:
                    logger.debug(f"Using cached prompt for {agent_name}")
                    prompts[agent_name] = prompt_cache[agent_name]
                else:
                    config = prompt_mgr.load_prompt(agent_name)
                    if config:
                        # Store in cache
                        prompt_cache[agent_name] = config
                        prompts[agent_name] = config
                        logger.info(f"Loaded prompt config for {agent_name}: {config.get('agent_name')}")
                    else:
                        logger.warning(f"Failed to load prompt config for {agent_name}")
            except Exception as e:
                logger.error(f"Error loading prompt for {agent_name}: {str(e)}")
        
        return prompts
    except Exception as e:
        logger.error(f"Error loading prompts: {str(e)}")
        return {}

def save_interview(session_id: str, interview_data: Dict[str, Any]) -> bool:
    """Save interview data to file."""
    try:
        # Serialize datetime objects
        serializable_data = {}
        for key, value in interview_data.items():
            if isinstance(value, datetime.datetime):
                serializable_data[key] = value.isoformat()
            else:
                serializable_data[key] = value
        
        # Save to file
        file_path = DATA_DIR / f"{session_id}.json"
        with open(file_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error saving interview data: {str(e)}")
        return False

def load_interview(session_id: str) -> Optional[Dict[str, Any]]:
    """Load interview data from file."""
    try:
        file_path = DATA_DIR / f"{session_id}.json"
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

def load_all_interviews() -> Dict[str, Dict[str, Any]]:
    """Load all interviews from the data directory."""
    interviews = {}
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        for file_path in DATA_DIR.glob("*.json"):
            try:
                session_id = file_path.stem
                interview_data = load_interview(session_id)
                if interview_data:
                    interviews[session_id] = interview_data
            except Exception as e:
                logger.error(f"Error loading interview {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading interviews: {str(e)}")
    
    return interviews

# ------ API Routes ------

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    prompts = list(load_all_prompts().keys())
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'available_prompts': prompts,
        'langchain_enabled': use_langchain
    })

@app.route('/api/interview/start', methods=['POST'])
def start_interview():
    """Start or resume an interview session."""
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        character = data.get('character')
        voice_id = data.get('voice_id')
        
        if not session_id:
            # Create a new interview session
            logger.info(f"Creating new interview session")
            session_id = str(uuid.uuid4())
            
            # Set up new interview data
            interview_data = {
                'session_id': session_id,
                'title': data.get('title', 'Untitled Interview'),
                'character': character or "custom",
                'voice_id': voice_id,
                'status': 'active',
                'conversation_history': [],
                'created_at': datetime.datetime.now(),
                'prompt': data.get('prompt', '')
            }
            
            # Save the new interview data
            save_interview(session_id, interview_data)
            
        logger.info(f"Interview start request for session {session_id}")
        
        # Check if interview session exists
        interview_file = os.path.join(DATA_DIR, f"{session_id}.json")
        
        if not os.path.exists(interview_file):
            return jsonify({
                'success': False,
                'error': f"Interview session {session_id} not found"
            }), 404
            
        # Read the interview details
        with open(interview_file, 'r') as f:
            interview_data = json.load(f)
            
        # Check if we have a conversation history
        conversation_history = interview_data.get('conversation_history', [])
        
        # Start the interview with a greeting
        if not conversation_history:
            if interview_service:
                # Use LangChain service if available
                greeting = interview_service.start_interview(
                    session_id=session_id,
                    character=character or interview_data.get('character', 'custom'),
                    prompt=interview_data.get('prompt', '')
                )
            else:
                # Fallback to static greeting
                greeting = "Hello and welcome to this interview. How can I help you today?"
                
            # Update interview data with conversation history
            conversation_history.append({
                'role': 'assistant',
                'content': greeting
            })
            
            interview_data['conversation_history'] = conversation_history
            save_interview(session_id, interview_data)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': greeting
            })
        else:
            # Resume interview - return last assistant message
            last_message = None
            for message in reversed(conversation_history):
                if message.get('role') == 'assistant':
                    last_message = message.get('content')
                    break
                    
            if not last_message:
                last_message = "Let's continue our conversation. What would you like to discuss next?"
                
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': last_message
            })
            
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/interview/share_link', methods=['POST'])
def create_fresh_interview_link():
    """Create a fresh interview session from a template or guide and return a sharing link."""
    try:
        data = request.json or {}
        original_session_id = data.get('session_id')
        guide_id = data.get('guide_id')
        
        # We need either a session ID or a guide ID
        if not original_session_id and not guide_id:
            return jsonify({
                'success': False,
                'error': "Either session_id or guide_id is required"
            }), 400
            
        # Create a new session
        if discussion_service:
            # Option 1: Using the discussion service to create a new session from a guide
            if guide_id:
                new_session_id = discussion_service.create_session(
                    guide_id=guide_id,
                    interviewee_data=data.get('interviewee', {
                        'name': 'New Participant',
                        'email': data.get('email', '')
                    })
                )
                
                if not new_session_id:
                    return jsonify({
                        'success': False,
                        'error': f"Failed to create new session from guide {guide_id}"
                    }), 500
            
            # Option 2: Using an existing session as a template
            elif original_session_id:
                # Get the original session
                original_session = discussion_service.get_session(original_session_id)
                if not original_session:
                    return jsonify({
                        'success': False,
                        'error': f"Original session {original_session_id} not found"
                    }), 404
                    
                # Get the guide ID from the original session
                guide_id = original_session.get('guide_id')
                if not guide_id:
                    return jsonify({
                        'success': False,
                        'error': f"Original session {original_session_id} has no guide_id"
                    }), 400
                    
                # Create a new session from the same guide
                new_session_id = discussion_service.create_session(
                    guide_id=guide_id,
                    interviewee_data=data.get('interviewee', {
                        'name': 'New Participant',
                        'email': data.get('email', '')
                    })
                )
                
                if not new_session_id:
                    return jsonify({
                        'success': False,
                        'error': f"Failed to create new session from guide {guide_id}"
                    }), 500
        else:
            # Legacy approach - clone the interview
            if not original_session_id:
                return jsonify({
                    'success': False,
                    'error': "session_id is required for legacy interview sharing"
                }), 400
                
            # Read the original interview
            interview_file = os.path.join(DATA_DIR, f"{original_session_id}.json")
            if not os.path.exists(interview_file):
                return jsonify({
                    'success': False,
                    'error': f"Original interview {original_session_id} not found"
                }), 404
                
            with open(interview_file, 'r') as f:
                original_interview = json.load(f)
                
            # Create a new interview based on the original
            new_session_id = str(uuid.uuid4())
            new_interview = {
                'session_id': new_session_id,
                'title': original_interview.get('title', 'Untitled Interview'),
                'project': original_interview.get('project', ''),
                'interview_type': original_interview.get('interview_type', 'custom_interview'),
                'prompt': original_interview.get('prompt', ''),
                'interview_prompt': original_interview.get('interview_prompt', ''),
                'analysis_prompt': original_interview.get('analysis_prompt', ''),
                'character_select': original_interview.get('character_select', ''),
                'voice_id': original_interview.get('voice_id', 'EXAVITQu4vr4xnSDxMaL'),
                'interviewee': data.get('interviewee', {
                    'name': 'New Participant',
                    'email': data.get('email', '')
                }),
                'created_at': datetime.datetime.now(),
                'creation_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                'last_updated': datetime.datetime.now(),
                'expiration_date': datetime.datetime.now() + datetime.timedelta(days=30),
                'status': 'active',
                'conversation_history': []  # Start with empty conversation
            }
            
            # Save the new interview
            save_interview(new_session_id, new_interview)
            logger.info(f"Created new shared interview with ID: {new_session_id}")
            
        # Generate the sharing URL
        host_url = request.host_url.rstrip('/')
        standard_url = f"{host_url}/interview/{new_session_id}?remote=true"
        remote_url = f"{host_url}/remote_interview?session_id={new_session_id}"
            
        return jsonify({
            'success': True,
            'session_id': new_session_id,
            'sharing_url': remote_url,  # Use the new remote URL by default
            'standard_url': standard_url,
            'remote_url': remote_url
        })
            
    except Exception as e:
        logger.error(f"Error creating sharing link: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/interview/respond', methods=['POST'])
def respond_to_interview():
    """Respond to a message in an interview session."""
    try:
        data = request.json
        session_id = data.get('session_id')
        user_input = data.get('message', '')
        
        logger.info(f"Interview response request for session {session_id}")
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Missing session_id'
            }), 400
        
        if not user_input.strip():
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400
        
        # If using the dedicated LangChain interview service, delegate to it
        if use_langchain and interview_service:
            logger.info(f"Using LangChain service to respond to: {user_input[:50]}...")
            result = interview_service.handle_message(session_id, user_input)
            return jsonify(result)
        
        # Otherwise, use the built-in LangChain integration in generate_dynamic_response
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({
                'success': False,
                'error': f"Interview session {session_id} not found"
            }), 404
        
        # Add user message to conversation history
        character = interview_data.get('character', 'interviewer')
        now = datetime.datetime.now()
        
        interview_data['conversation_history'].append({
            'role': 'user',
            'content': user_input,
            'timestamp': now.isoformat()
        })
        
        # Generate response using LangChain-powered function
        response_text = generate_dynamic_response(user_input, character, interview_data['conversation_history'])
        
        # Add response to conversation history
        interview_data['conversation_history'].append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': now.isoformat()
        })
        
        # Update last_updated timestamp
        interview_data['last_updated'] = now
        
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        return jsonify({
            'success': True,
            'message': response_text
        })
    except Exception as e:
        logger.error(f"Error responding to interview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Cached LangChain conversation instances
langchain_conversations = {}

def generate_dynamic_response(user_input: str, character: str, conversation_history=None) -> str:
    """Generate a more dynamic response based on user input and character using LangChain."""
    try:
        # If conversation history is empty or invalid, return a default greeting
        if not conversation_history:
            logger.warning("No conversation history provided, returning default greeting")
            return generate_greeting(character)
            
        session_id = conversation_history[0].get('session_id', str(uuid.uuid4()))
        
        # Check if we already have a LangChain conversation for this session
        if session_id not in langchain_conversations:
            logger.info(f"Creating new LangChain conversation for session {session_id}")
            
            # Get character configuration/prompt
            system_prompt = "You are a helpful AI assistant conducting an interview."
            try:
                character_config = prompt_mgr.load_prompt(character)
                if character_config:
                    system_prompt = character_config.get('dynamic_prompt_prefix', system_prompt)
            except Exception as e:
                logger.error(f"Error loading prompt for {character}: {str(e)}")
            
            # Initialize LangChain components
            try:
                # Use langchain_community imports if available to avoid deprecation warnings
                try:
                    from langchain_community.chat_models import ChatOpenAI
                except ImportError:
                    from langchain.chat_models import ChatOpenAI
                
                from langchain.chains import LLMChain
                from langchain.memory import ConversationBufferMemory
                from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
                
                # Initialize the language model
                llm = ChatOpenAI(
                    temperature=0.7,
                    model_name="gpt-3.5-turbo",  # Use appropriate model based on your requirements
                )
                
                # Create a proper prompt template that works with the memory
                chat_prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template(system_prompt),
                    HumanMessagePromptTemplate.from_template("{input}")
                ])
                
                # Initialize conversation memory that works with the prompt
                memory = ConversationBufferMemory(input_key="input", memory_key="history")
                
                # Initialize conversation chain with compatible prompt and memory
                conversation = LLMChain(
                    llm=llm,
                    prompt=chat_prompt,
                    memory=memory,
                    verbose=False
                )
                
                # Add conversation history to memory
                for msg in conversation_history:
                    if msg['role'] == 'user':
                        # We use the predict method directly instead of adding to memory
                        # to avoid issues with memory compatibility
                        memory.chat_memory.add_user_message(msg['content'])
                    elif msg['role'] == 'assistant':
                        memory.chat_memory.add_ai_message(msg['content'])
                
                # Store in cache
                langchain_conversations[session_id] = {
                    'conversation': conversation,
                    'memory': memory,
                    'last_used': datetime.datetime.now()
                }
            except Exception as e:
                logger.error(f"Error initializing LangChain: {str(e)}")
                # Fallback to the simple response generation if LangChain initialization fails
                return _legacy_generate_response(user_input, character, conversation_history)
        else:
            logger.info(f"Using existing LangChain conversation for session {session_id}")
            # Update last used timestamp
            langchain_conversations[session_id]['last_used'] = datetime.datetime.now()
        
        # Use LangChain to generate response
        try:
            conversation = langchain_conversations[session_id]['conversation']
            prompt_suffix = "Continue the interview and ask the next question or follow-up question based on the user's response."
            input_text = f"{user_input}\n\n{prompt_suffix}"
            
            # Use the LLMChain to generate a response
            response = conversation.predict(input=input_text)
            return response
        except Exception as e:
            logger.error(f"Error generating LangChain response: {str(e)}")
            # Fallback to simple response generation
            return _legacy_generate_response(user_input, character, conversation_history)
    
    except Exception as e:
        logger.error(f"Unexpected error in generate_dynamic_response: {str(e)}")
        return "I apologize, but I encountered an error. Let's continue our conversation. What would you like to discuss next?"

def _legacy_generate_response(user_input: str, character: str, conversation_history=None) -> str:
    """Original hardcoded response generation logic as fallback."""
    # Check if we're repeating responses by examining conversation history
    if conversation_history and len(conversation_history) >= 4:  # Need at least 2 exchanges
        # Get the last two assistant responses
        assistant_responses = [msg['content'] for msg in conversation_history if msg['role'] == 'assistant']
        last_responses = assistant_responses[-2:] if len(assistant_responses) >= 2 else []
        
        # If we're repeating responses or seem stuck, use a redirect strategy
        if len(last_responses) >= 2 and any(response in last_responses[-1] for response in last_responses[:-1]):
            redirect_responses = [
                "Let's shift our discussion a bit. What aspects of your work or project are you most excited about?",
                "I notice we might be covering similar ground. Let's try a different angle. What specific outcomes are you hoping to achieve?",
                "I'd like to explore a new direction. Can you tell me about a recent challenge you've overcome and what you learned from it?",
                "Let's take a step back and look at the bigger picture. What do you see as the most significant opportunities in your current situation?",
                "I'm curious about something different. What resources or support would help you be more effective in your role?"
            ]
            import random
            return random.choice(redirect_responses)
    
    # Convert to lowercase for easier matching
    user_input_lower = user_input.lower()
    
    # Check for mentions of repetition or boring questions
    if any(phrase in user_input_lower for phrase in ['same question', 'asking the same', 'repeat', 'repetitive', 'said that already', 'said this already', 'already asked']):
        apology_responses = [
            "I apologize for being repetitive. Let's try a different approach. What would be most valuable for us to discuss?",
            "You're right, and I appreciate you pointing that out. Let's change direction. What topic would you like to explore?",
            "Thank you for the feedback. Let's shift our conversation to something more productive. What would you like to focus on?",
            "I appreciate your patience. Let's move to a more interesting question: what's a recent insight or discovery that surprised you?"
        ]
        import random
        return random.choice(apology_responses)
    
    # Check for question keywords
    if '?' in user_input:
        # User is asking a question
        if any(word in user_input_lower for word in ['what', 'how', 'why']):
            if 'you' in user_input_lower:
                # Questions about the character
                character_responses = {
                    'daria': "As Daria, Deloitte's Advanced Research & Interview Assistant, I'm designed to conduct interviews that yield valuable insights. I appreciate your interest in my role.",
                    'skeptica': "As Skeptica, my purpose is to challenge assumptions and identify potential biases. I approach every statement with healthy skepticism to uncover deeper truths.",
                    'eurekia': "As Eurekia, I help identify patterns and insights in research data. I'm particularly good at connecting seemingly unrelated concepts.",
                    'thesea': "As Thesea, I specialize in journey mapping and understanding user experiences from multiple perspectives.",
                    'askia': "As Askia, I use strategic questioning techniques to uncover insights that might otherwise remain hidden.",
                    'odessia': "As Odessia, I help analyze user experiences to create comprehensive journey maps that highlight opportunities.",
                    'synthia': "As Synthia, I specialize in drawing conclusions and synthesizing findings from complex data and conversations."
                }
                return character_responses.get(character, "I'm your interview assistant today. I'm here to help gather insights through our conversation.")
            else:
                # General questions
                return "That's an interesting question. To give you a thoughtful answer, I'd like to understand more about your perspective. Could you elaborate on why you're curious about this?"
    
    # Check for experience or opinion sharing
    if any(phrase in user_input_lower for phrase in ['i think', 'i believe', 'in my experience', 'i feel']):
        experience_responses = [
            "Thank you for sharing that perspective. It's valuable to understand your experience. Could you tell me more about how this has shaped your approach to similar situations?",
            "That's insightful. What specific events or factors led you to form this view?",
            "I appreciate your candid thoughts. How has this perspective evolved over time?"
        ]
        import random
        return random.choice(experience_responses)
    
    # Check for challenges or problems
    if any(word in user_input_lower for word in ['challenge', 'problem', 'difficult', 'issue', 'trouble']):
        challenge_responses = [
            "The challenges you've described are quite insightful. How have you attempted to address these issues so far?",
            "That sounds challenging. What resources or support would help you navigate this situation more effectively?",
            "Thank you for sharing these difficulties. What aspects of the challenge do you find most frustrating or complex?"
        ]
        import random
        return random.choice(challenge_responses)
    
    # Check for positive experiences
    if any(word in user_input_lower for word in ['good', 'great', 'excellent', 'positive', 'success']):
        positive_responses = [
            "It's great to hear about these positive aspects. What do you think were the key factors that contributed to this success?",
            "That's excellent news. What elements of this success might be replicable in other contexts?",
            "I'm glad to hear about your positive experience. What surprised you most about how well this worked out?"
        ]
        import random
        return random.choice(positive_responses)
    
    # Check for hesitation or uncertainty
    if any(word in user_input_lower for word in ['maybe', 'perhaps', 'not sure', 'might', 'possibly']):
        uncertainty_responses = [
            "I sense some uncertainty there, which is completely fine. What aspects are you most unsure about?",
            "It's natural to have some ambiguity in this area. What additional information might help clarify things for you?",
            "Your thoughtful consideration is valuable. What are the competing perspectives you're weighing?"
        ]
        import random
        return random.choice(uncertainty_responses)
    
    # Check if it's a short answer
    if len(user_input.split()) < 5:
        short_responses = [
            "I'd like to understand more about your perspective. Could you elaborate on that point?",
            "Could you share more details about what you mean?",
            "That's interesting. Could you expand on that thought?"
        ]
        import random
        return random.choice(short_responses)
    
    # Default response with follow-up
    follow_ups = [
        "That's valuable insight. How has this impacted your approach to similar situations?",
        "Thank you for sharing that. Could you tell me more about the specific examples or experiences that shaped this view?",
        "I appreciate your thoughts on this. If you could change one aspect of what you've described, what would it be and why?",
        "That's interesting. How do you think others in your field or organization might view this situation differently?",
        "Thank you for explaining that. What factors do you think have most strongly influenced your perspective on this?",
        "Building on what you've shared, what do you see as the next steps or future opportunities in this area?",
        "That's helpful context. How do you measure success or progress in this particular area?",
        "I'm curious about the broader implications of what you've described. How might this affect related aspects of your work?"
    ]
    
    import random
    return random.choice(follow_ups)

@app.route('/api/interview/end', methods=['POST'])
def end_interview():
    """End an interview session and mark it as completed."""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        logger.info(f"Request to end interview session {session_id}")
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Missing session_id'
            }), 400
            
        # Load interview data
        interview_data = load_interview(session_id)
        if not interview_data:
            return jsonify({
                'success': False,
                'error': f"Interview session {session_id} not found"
            }), 404
            
        # Mark interview as completed
        interview_data['status'] = 'completed'
        interview_data['completion_date'] = datetime.datetime.now().isoformat()
        
        # Add completion summary if using LangChain
        if use_langchain and interview_service:
            try:
                summary = interview_service.generate_summary(session_id)
                interview_data['summary'] = summary
            except Exception as e:
                logger.error(f"Error generating summary: {str(e)}")
                
        # Save updated interview data
        save_interview(session_id, interview_data)
        
        # Automatically trigger analysis after interview completion
        try:
            logger.info(f"Automatically triggering analysis for interview {session_id}")
            # Convert conversation history to transcript format
            formatted_transcript = format_transcript_for_analysis(interview_data)
            
            # Get character's analysis prompt
            character_name = interview_data.get('character', 'interviewer')
            analysis_prompt = None
            
            # Try to get character-specific analysis prompt
            if 'analysis_prompt' in interview_data and interview_data['analysis_prompt']:
                analysis_prompt = interview_data['analysis_prompt']
            else:
                try:
                    character_config = prompt_mgr.load_prompt(character_name)
                    if character_config and 'analysis_prompt' in character_config:
                        analysis_prompt = character_config['analysis_prompt']
                except Exception as e:
                    logger.warning(f"Could not load analysis prompt for {character_name}: {str(e)}")
            
            # If no specific analysis prompt found, use a generic one
            if not analysis_prompt:
                analysis_prompt = """
                Analyze this interview transcript to identify:
                
                1. User Needs: What specific needs, wants, or requirements did the user express?
                2. Goals: What short-term and long-term goals did the user mention?
                3. Pain Points: What frustrations, challenges, or obstacles did the user describe?
                4. Opportunities: What potential improvements or solutions could address the identified needs and pain points?
                5. Key Quotes: What specific quotes from the user best illustrate the above points?
                
                Structure your analysis in a clear, comprehensive way addressing each of these points.
                """
            
            # Generate analysis
            if use_langchain and interview_service:
                analysis_result = interview_service.generate_analysis(
                    transcript=formatted_transcript,
                    prompt=analysis_prompt
                )
            else:
                analysis_result = simple_analysis_generation(
                    transcript=formatted_transcript,
                    prompt=analysis_prompt
                )
            
            # Parse and structure the analysis
            structured_analysis = parse_analysis_response(analysis_result, analysis_prompt)
            
            # Update the interview with the analysis
            interview_data['analysis'] = structured_analysis
            interview_data['status'] = 'analyzed'  # Mark as analyzed
            interview_data['last_updated'] = datetime.datetime.now()
            
            # Save the updated interview data
            save_interview(session_id, interview_data)
            logger.info(f"Successfully generated and saved analysis for interview {session_id}")
        except Exception as e:
            logger.error(f"Error performing automatic analysis: {str(e)}")
            # Continue with the response even if analysis fails
        
        return jsonify({
            'success': True,
            'message': 'Interview completed successfully'
        })
    except Exception as e:
        logger.error(f"Error ending interview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/interviews', methods=['GET'])
def get_interviews():
    """Get all interviews."""
    try:
        interviews = load_all_interviews()
        
        # Convert to list for response
        interview_list = []
        for session_id, data in interviews.items():
            # Convert datetime objects to strings
            serializable_data = {}
            for key, value in data.items():
                if isinstance(value, datetime.datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            interview_list.append(serializable_data)
        
        # Return as object with success field and interviews array to match dashboard.html expectations
        return jsonify({
            'success': True,
            'interviews': interview_list
        })
    except Exception as e:
        logger.error(f"Error getting interviews: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/characters', methods=['GET'])
def get_characters():
    """Get all available character prompts."""
    try:
        prompts = load_all_prompts()
        
        characters = []
        for name, config in prompts.items():
            characters.append({
                'name': name,
                'display_name': config.get('agent_name', name.capitalize()),
                'role': config.get('role', ''),
                'description': config.get('description', '')
            })
        
        return jsonify({
            'success': True,
            'characters': characters
        })
    except Exception as e:
        logger.error(f"Error getting characters: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/character/<character_name>', methods=['GET'])
def get_character(character_name):
    """Get a specific character's prompt data."""
    try:
        character_name = character_name.lower()
        
        # Try to load from cache first
        config = None
        if character_name in prompt_cache:
            config = prompt_cache[character_name]
        else:
            # Load from disk
            config = prompt_mgr.load_prompt(character_name)
            if config:
                prompt_cache[character_name] = config
        
        if not config:
            return jsonify({
                'success': False,
                'error': f"Character '{character_name}' not found"
            }), 404
        
        return jsonify({
            'success': True,
            'name': config.get('agent_name', character_name),
            'role': config.get('role', ''),
            'description': config.get('description', ''),
            'prompt': config.get('dynamic_prompt_prefix', ''),
            'dynamic_prompt_prefix': config.get('dynamic_prompt_prefix', ''),
            'system_prompt': config.get('dynamic_prompt_prefix', ''),
            'analysis_prompt': config.get('analysis_prompt', '')
        })
    except Exception as e:
        logger.error(f"Error getting character '{character_name}': {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check_services', methods=['GET'])
def check_services():
    """Check if required services are available."""
    try:
        # Check if audio services are running
        tts_service_running = False
        stt_service_running = False
        
        try:
            # Directly check health endpoints instead of just checking socket connection
            try:
                tts_response = requests.get('http://localhost:5015/health', timeout=1)
                tts_service_running = tts_response.status_code == 200
                logging.info(f"TTS service check: {tts_service_running}, response: {tts_response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"TTS service check failed: {str(e)}")
                tts_service_running = False
                
            try:
                stt_response = requests.get('http://localhost:5016/health', timeout=1)
                stt_service_running = stt_response.status_code == 200
                logging.info(f"STT service check: {stt_service_running}, response: {stt_response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"STT service check failed: {str(e)}")
                stt_service_running = False
        except Exception as e:
            logging.error(f"Error checking service health: {str(e)}")
            pass
    
        return jsonify({
            'api_server': True,
            'tts_service': tts_service_running,
            'stt_service': stt_service_running,
            'elevenlabs': bool(os.environ.get('ELEVENLABS_API_KEY'))
        })
    except Exception as e:
        logger.error(f"Error checking services: {str(e)}")
        return jsonify({
            'api_server': True,
            'tts_service': False,
            'stt_service': False,
            'elevenlabs': False,
            'error': str(e)
        })

@app.route('/api/text_to_speech_elevenlabs', methods=['POST'])
def text_to_speech_elevenlabs():
    """Forward text-to-speech requests to ElevenLabs service."""
    try:
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
        
        if not text:
            logger.error("No text provided for text-to-speech")
            return jsonify({'error': 'No text provided'}), 400
        
        # Try to forward to audio service
        try:
            audio_service_url = 'http://localhost:5015/text_to_speech'
            
            logger.info(f"Forwarding TTS request to {audio_service_url}: {len(text)} chars, voice: {voice_id}")
            
            response = requests.post(
                audio_service_url,
                json={'text': text, 'voice_id': voice_id},
                timeout=10
            )
            
            # Return the response from the TTS service
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    # For JSON responses (e.g., mock responses)
                    return jsonify(response.json())
                    
                elif 'audio/' in content_type:
                    # For audio responses (MP3 data)
                    audio_response = Response(response.content, mimetype=content_type)
                    # Add CORS headers
                    audio_response.headers.add('Access-Control-Allow-Origin', '*')
                    audio_response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                    return audio_response
                    
                else:
                    # Default to returning raw content
                    return response.content, 200, {
                        'Content-Type': content_type,
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
            else:
                logger.error(f"Error from TTS service: {response.status_code}")
                # Return a success response with a message instead of an error
                # This prevents client errors but informs that TTS failed
                return jsonify({
                    'success': False,
                    'error': f'TTS service returned status code {response.status_code}'
                }), 500
                
        except Exception as e:
            logger.error(f"Error forwarding to TTS service: {str(e)}")
            # Provide a fallback response instead of raising an exception
            return jsonify({
                'success': False,
                'error': f'TTS service connection error: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error in text_to_speech_elevenlabs: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'TTS processing error: {str(e)}'
        }), 500

@app.route('/api/speech_to_text', methods=['POST'])
def speech_to_text():
    """Process audio file and convert speech to text.
    
    This endpoint can:
    1. Use the external audio service (if available)
    2. Return a placeholder response if audio service isn't available
    """
    try:
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        # Get session ID if provided
        session_id = request.form.get('session_id', '')
        
        # Get the audio file
        audio_file = request.files['audio']
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        
        # Save the temporary file
        filename = os.path.join('uploads', f"temp_audio_{uuid.uuid4()}.webm")
        audio_file.save(filename)
        
        # Try to forward to audio service
        try:
            audio_service_url = 'http://localhost:5015/speech_to_text'
            
            logger.info(f"Forwarding STT request to {audio_service_url}")
            
            # Create a new multipart form with the saved file
            files = {'audio': open(filename, 'rb')}
            data = {'session_id': session_id} if session_id else {}
            
            response = requests.post(
                audio_service_url,
                files=files,
                data=data,
                timeout=10
            )
            
            # Clean up the temporary file
            try:
                os.remove(filename)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")
            
            # Return the response from the STT service
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error from STT service: {response.status_code}")
                # Return a fallback response if the service fails
                return jsonify({
                    'success': True,
                    'text': "I'm saying something important in this interview.",
                    'fallback': True
                })
                
        except Exception as e:
            logger.error(f"Error forwarding to STT service: {str(e)}")
            
            # Clean up the temporary file
            try:
                os.remove(filename)
            except Exception as file_e:
                logger.error(f"Error removing temp file: {str(file_e)}")
            
            # Return a fallback response
            return jsonify({
                'success': True,
                'text': "I didn't quite catch that. Could you please repeat?",
                'fallback': True
            })
        
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add the interview/create endpoint
@app.route('/interview/create', methods=['POST'])
def create_interview():
    """Create a new interview session."""
    try:
        data = request.json or {}
        logger.info(f"Create interview request: {data}")
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Current time
        now = datetime.datetime.now()
        
        # Prepare the interview data
        interview_data = {
            'session_id': session_id,
            'title': data.get('title', 'Untitled Interview'),
            'project': data.get('project', ''),
            'interview_type': data.get('interview_type', 'custom_interview'),
            'topic': data.get('topic', 'General Interview'),
            'context': data.get('context', 'This is an interview conversation.'),
            'goals': data.get('goals', 'Gather information from the participant'),
            'prompt': data.get('prompt', ''),
            'interview_prompt': data.get('interview_prompt', ''),
            'analysis_prompt': data.get('analysis_prompt', ''),
            'character_select': data.get('character_select', ''),
            'voice_id': data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL'),
            'interviewee': {
                'name': data.get('interviewee', {}).get('name', 'Anonymous'),
                'role': data.get('interviewee', {}).get('role', ''),
                'email': data.get('interviewee', {}).get('email', '')
            },
            'created_at': now,
            'creation_date': now.strftime("%Y-%m-%d %H:%M"),
            'last_updated': now,
            'expiration_date': now + datetime.timedelta(days=30),
            'status': 'active',
            'conversation_history': [],
            'custom_questions': data.get('custom_questions', []),
            'options': data.get('options', {
                'record_transcript': True,
                'analysis': True,
                'use_tts': True
            })
        }
        
        # Save the interview data
        save_interview(session_id, interview_data)
        logger.info(f"Created new interview with ID: {session_id}")
        
        # All interview types should be treated as discussion guides for consistency
        # This provides a unified experience regardless of interview type
        redirect_url = f"/discussion_guide/{session_id}"
        
        # Return success response with session ID and redirect URL
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'redirect_url': redirect_url
        })
    except Exception as e:
        logger.error(f"Error creating interview: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Add route to handle interview sessions
@app.route('/interview/<interview_id>')
def join_interview(interview_id):
    """Join or view an interview"""
    try:
        # First, check if this is a discussion guide session
        if discussion_service:
            session = discussion_service.get_session(interview_id)
            if session:
                # This is a research session
                guide_id = session.get('guide_id')
                guide = discussion_service.get_guide(guide_id) if guide_id else None
                
                # Check if it's a remote session (participant view)
                remote = request.args.get('remote', 'false').lower() == 'true'
                if remote:
                    # Participant needs to accept terms
                    name = request.args.get('name', '')
                    email = request.args.get('email', '')
                    role = request.args.get('role', '')
                    department = request.args.get('department', '')
                    voice_id = request.args.get('voice_id', '')
                    accepted = request.args.get('accepted', 'false').lower() == 'true'
                    
                    if not accepted:
                        # Show the participant terms and consent page
                        return render_template('langchain/interview_terms.html',
                                              interview_id=interview_id,
                                              guide=guide,
                                              name=name,
                                              email=email,
                                              role=role,
                                              department=department,
                                              voice_id=voice_id)
                    else:
                        # Get character name if available
                        character_name = guide.get('character_select', '') if guide else ''
                        
                        # Check if we need to update the session with interviewee info
                        if name and email:
                            # Get current session data
                            current_session = discussion_service.get_session(interview_id)
                            if current_session:
                                # Update interviewee info if not set
                                if not current_session.get('interviewee'):
                                    current_session['interviewee'] = {
                                        'name': name,
                                        'email': email,
                                        'role': role,
                                        'department': department
                                    }
                                    discussion_service.update_session(interview_id, current_session)
                        
                        # Use the debug-based interview template for improved reliability
                        return render_template('remote_interview_fixed.html',
                                              session_id=interview_id,
                                              guide=guide,
                                              character_name=character_name,
                                              voice_id=voice_id)
                else:
                    # This is the researcher view
                    # Use a different template for a research session
                    return render_template('langchain/session_conduct.html',
                                         session_id=interview_id,
                                         session=session,
                                         guide=guide)
        
        # If we get here, treat as a legacy interview
        interview = load_interview(interview_id)
        if not interview:
            logger.warning(f"Interview not found: {interview_id}")
            return redirect(url_for('dashboard'))
        
        # Pass as much information as we have to the template
        return render_template('interview.html',
                              interview_id=interview_id,
                              interview=interview)
    except Exception as e:
        logger.error(f"Error joining interview: {str(e)}")
        # Use session.flash instead of direct flash to avoid import issues
        error_message = f"Error: {str(e)}"
        session['_flashes'] = session.get('_flashes', []) + [('danger', error_message)]
        return redirect(url_for('dashboard'))

# ------ UI Routes ------

@app.route('/')
def home():
    """Redirect to dashboard."""
    return redirect('/dashboard')

@app.route('/debug')
def debug_toolkit():
    """Redirect to the debug toolkit page."""
    return redirect('/static/debug_toolkit.html')

@app.route('/dashboard')
def dashboard():
    """Render dashboard page."""
    return render_template('langchain/dashboard.html')

@app.route('/interview_setup')
def interview_setup():
    """Render discussion guide setup page with proper title and character data."""
    try:
        # Load available characters/prompts
        characters = []
        prompts = load_all_prompts()
        for name, config in prompts.items():
            characters.append({
                'name': name,
                'display_name': config.get('agent_name', name.capitalize()),
                'role': config.get('role', ''),
                'description': config.get('description', '')
            })
        
        # Set default interview prompt
        interview_prompt = "You are an AI assistant conducting a research interview. Ask open-ended questions, follow up on interesting points, and help the participant share their experiences and perspectives."
        
        # Set default analysis prompt
        analysis_prompt = "Based on the interview transcript, please provide:\n1. Key insights\n2. Pain points and frustrations\n3. Opportunities for improvement"
        
        # Render the template with data
        return render_template(
            'langchain/interview_setup.html', 
            title="Create New Discussion Guide",
            characters=characters,
            interview_prompt=interview_prompt,
            analysis_prompt=analysis_prompt
        )
    except Exception as e:
        logger.error(f"Error loading interview setup page: {str(e)}")
        return render_template('langchain/interview_setup.html', characters=[])

@app.route('/interview_archive')
def interview_archive():
    """Render interview archive page."""
    try:
        # Load all interviews
        interviews = load_all_interviews()
        
        # Convert to list for the template
        interview_list = []
        for session_id, data in interviews.items():
            # Convert datetime objects to strings if needed
            serializable_data = {}
            for key, value in data.items():
                if isinstance(value, datetime.datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            # Add session_id to the data
            serializable_data['session_id'] = session_id
            interview_list.append(serializable_data)
        
        logger.info(f"Loaded {len(interview_list)} interviews for archive page")
        
        return render_template('langchain/interview_archive.html', interviews=interview_list)
    except Exception as e:
        logger.error(f"Error loading interview archive: {str(e)}")
        return render_template('langchain/interview_archive.html', interviews=[], error=str(e))

@app.route('/prompts/')
def prompts_manager():
    """Render prompts manager page."""
    try:
        prompts = load_all_prompts()
        
        prompt_list = []
        for name, config in prompts.items():
            prompt_list.append({
                'id': name,
                'name': config.get('agent_name', name.capitalize()),
                'description': config.get('description', ''),
                'role': config.get('role', ''),
                'version': config.get('version', 'v1.0')
            })
        
        # Sort prompts by name
        prompt_list.sort(key=lambda x: x['name'])
        
        return render_template(
            'langchain/prompt_manager.html',
            prompts=prompt_list,
            title="Prompt Manager",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error loading prompts page: {str(e)}")
        return render_template(
            'langchain/prompt_manager.html',
            prompts=[],
            title="Prompt Manager",
            section="prompts",
            error=str(e)
        )

@app.route('/prompts/view/<prompt_id>')
def view_prompt(prompt_id):
    """View a specific prompt."""
    try:
        prompt_id = prompt_id.lower()
        
        # Load prompt config
        config = None
        if prompt_id in prompt_cache:
            config = prompt_cache[prompt_id]
        else:
            config = prompt_mgr.load_prompt(prompt_id)
            if config:
                prompt_cache[prompt_id] = config
        
        if not config:
            return redirect('/prompts/')
        
        return render_template(
            'langchain/view_prompt.html',
            prompt_id=prompt_id,
            agent=config.get('agent_name', prompt_id),
            config=config,
            title=f"View Prompt: {config.get('agent_name', prompt_id)}",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error viewing prompt {prompt_id}: {str(e)}")
        return redirect('/prompts/')

@app.route('/prompts/edit/<prompt_id>')
def edit_prompt(prompt_id):
    """Edit a specific prompt."""
    try:
        prompt_id = prompt_id.lower()
        
        # Load prompt config
        config = None
        if prompt_id in prompt_cache:
            config = prompt_cache[prompt_id]
        else:
            config = prompt_mgr.load_prompt(prompt_id)
            if config:
                prompt_cache[prompt_id] = config
        
        if not config:
            return redirect('/prompts/')
        
        return render_template(
            'langchain/edit_prompt.html',
            prompt_id=prompt_id,
            agent=config.get('agent_name', prompt_id),
            config=config,
            title=f"Edit Prompt: {config.get('agent_name', prompt_id)}",
            section="prompts"
        )
    except Exception as e:
        logger.error(f"Error editing prompt {prompt_id}: {str(e)}")
        return redirect('/prompts/')

@app.route('/monitor_interview')
def monitor_interview():
    """Render monitoring dashboard for live sessions."""
    try:
        if not discussion_service:
            return render_template('langchain/error.html', 
                                error="Discussion service not available")
        
        # Get all active sessions
        try:
            active_sessions = discussion_service.get_all_sessions()
            
            # Sort sessions by last activity (most recent first)
            active_sessions = sorted(
                active_sessions, 
                key=lambda s: s.get('last_updated', s.get('created_at', '')),
                reverse=True
            )
        except AttributeError as e:
            logger.error(f"Error calling get_all_sessions: {str(e)}")
            # Fall back to using list_guide_sessions from all available guides
            active_sessions = []
            try:
                guides = discussion_service.list_guides()
                for guide in guides:
                    guide_id = guide.get('id')
                    if guide_id:
                        guide_sessions = discussion_service.get_guide_sessions(guide_id)
                        active_sessions.extend(guide_sessions)
                
                # Sort sessions by last activity (most recent first)
                active_sessions = sorted(
                    active_sessions, 
                    key=lambda s: s.get('last_updated', s.get('created_at', '')),
                    reverse=True
                )
            except Exception as inner_e:
                logger.error(f"Error in fallback method for retrieving sessions: {str(inner_e)}")
                # If all else fails, return an empty list
                active_sessions = []
        
        return render_template('langchain/monitor_dashboard.html', 
                            sessions=active_sessions)
    except Exception as e:
        logger.error(f"Error loading monitor page: {str(e)}")
        return render_template('langchain/error.html', 
                            error=f"Error loading monitor page: {str(e)}")

@app.route('/monitor_interview/<session_id>')
def monitor_interview_session(session_id):
    """Monitor a specific interview session."""
    try:
        if not discussion_service:
            logger.warning(f"Discussion service not available for monitoring session {session_id}")
            return redirect(url_for('interview_details', session_id=session_id))
        
        # Get the session details
        session = discussion_service.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for monitoring")
            return render_template('langchain/error.html', 
                                error=f"Session {session_id} not found")
        
        # Get the discussion guide if available
        guide = None
        if 'guide_id' in session and session.get('guide_id'):
            try:
                guide = discussion_service.get_guide(session.get('guide_id'))
            except Exception as e:
                logger.warning(f"Error loading guide for session {session_id}: {str(e)}")
        
        # Make sure session has a title
        if 'title' not in session or not session.get('title'):
            session['title'] = f"Session {session_id[:8]}"
        
        # Ensure messages list exists for JavaScript usage
        if 'messages' not in session:
            session['messages'] = []
            
        # Ensure session_id is in the session data for JavaScript to use
        session['session_id'] = session_id
            
        # Log connection to monitor page
        logger.info(f"Rendering monitoring page for session {session_id}")
        
        # Return the monitor page
        return render_template('langchain/monitor_session.html', 
                            session=session,
                            guide=guide,
                            session_id=session_id,
                            observer_enabled=(observer_service is not None))
    except Exception as e:
        logger.error(f"Error loading monitoring session {session_id}: {str(e)}")
        return render_template('langchain/error.html', 
                            error=f"Error loading monitoring page: {str(e)}")

@app.route('/interview_details/<session_id>')
def interview_details(session_id):
    """Show details for a specific interview."""
    # First try to load from the file-based storage
    interview_data = load_interview(session_id)
    
    # If not found in file storage, try to get it from the LangChain discussion service
    if not interview_data and discussion_service:
        try:
            langchain_session = discussion_service.get_session(session_id)
            if langchain_session:
                # Convert LangChain session to the format expected by the template
                interview_data = langchain_session
                # Ensure all necessary fields exist
                if 'title' not in interview_data:
                    interview_data['title'] = f"Session {session_id[:8]}"
        except Exception as e:
            logger.error(f"Error loading LangChain session {session_id}: {str(e)}")
    
    if not interview_data:
        return render_template('langchain/interview_error.html',
                               error=f"No interview found for session: {session_id}")
    
    return render_template('langchain/interview_details.html',
                           interview=interview_data,
                           session_id=session_id)

@app.route('/api/interview/analyze/<interview_id>', methods=['POST'])
def analyze_interview(interview_id):
    """Analyze an interview and generate insights."""
    try:
        # Load the interview data
        interview_data = load_interview(interview_id)
        if not interview_data:
            return jsonify({
                'success': False,
                'error': f"Interview with ID {interview_id} not found."
            }), 404
        
        # Check if interview is completed
        if interview_data.get('status') != 'completed':
            return jsonify({
                'success': False,
                'error': "Only completed interviews can be analyzed."
            }), 400
        
        # Check if interview already has analysis
        if 'analysis' in interview_data and interview_data['analysis']:
            # If force parameter is not provided or false, return existing analysis
            if not request.json or not request.json.get('force', False):
                return jsonify({
                    'success': True,
                    'message': "Analysis already exists for this interview.",
                    'interview_id': interview_id,
                    'analysis': interview_data['analysis']
                })
            # Otherwise continue with new analysis (force=true)
        
        # Get the character's analysis prompt
        character_name = interview_data.get('character', 'interviewer')
        
        # Try to get character-specific analysis prompt
        analysis_prompt = None
        
        # First check if there's a specific analysis_prompt in the interview data
        if 'analysis_prompt' in interview_data and interview_data['analysis_prompt']:
            analysis_prompt = interview_data['analysis_prompt']
        # Then try to get it from the prompt manager
        else:
            try:
                character_config = prompt_mgr.load_prompt(character_name)
                if character_config and 'analysis_prompt' in character_config:
                    analysis_prompt = character_config['analysis_prompt']
            except Exception as e:
                logger.warning(f"Could not load analysis prompt for {character_name}: {str(e)}")
        
        # If no specific analysis prompt found, use a generic one
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this interview transcript to identify:
            
            1. User Needs: What specific needs, wants, or requirements did the user express?
            2. Goals: What short-term and long-term goals did the user mention?
            3. Pain Points: What frustrations, challenges, or obstacles did the user describe?
            4. Opportunities: What potential improvements or solutions could address the identified needs and pain points?
            5. Key Quotes: What specific quotes from the user best illustrate the above points?
            
            Structure your analysis in a clear, comprehensive way addressing each of these points.
            """
        
        # Prepare the transcript in a format suitable for analysis
        formatted_transcript = format_transcript_for_analysis(interview_data)
        
        # Send to LLM for analysis
        # If using LangChain
        if use_langchain and interview_service:
            logger.info(f"Using LangChain for interview analysis: {interview_id}")
            analysis_result = interview_service.generate_analysis(
                transcript=formatted_transcript,
                prompt=analysis_prompt
            )
        # Otherwise use simple implementation
        else:
            logger.info(f"Using simple implementation for interview analysis: {interview_id}")
            analysis_result = simple_analysis_generation(
                transcript=formatted_transcript,
                prompt=analysis_prompt
            )
        
        # Parse and structure the analysis
        structured_analysis = parse_analysis_response(analysis_result, analysis_prompt)
        
        # Update the interview with the analysis
        interview_data['analysis'] = structured_analysis
        interview_data['status'] = 'analyzed'  # Mark as analyzed
        interview_data['last_updated'] = datetime.datetime.now()
        
        # Save the updated interview
        success = save_interview(interview_id, interview_data)
        if not success:
            return jsonify({
                'success': False,
                'error': "Failed to save analysis results."
            }), 500
        
        return jsonify({
            'success': True,
            'message': "Analysis completed successfully.",
            'interview_id': interview_id,
            'analysis': structured_analysis
        })
    
    except Exception as e:
        logger.error(f"Error analyzing interview {interview_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Failed to analyze interview: {str(e)}"
        }), 500


def format_transcript_for_analysis(interview_data):
    """Format interview transcript for analysis."""
    formatted = ""
    
    # Check if there's conversation_history
    if 'conversation_history' in interview_data and interview_data['conversation_history']:
        # Add basic metadata
        formatted += f"Interview Title: {interview_data.get('title', 'Untitled Interview')}\n"
        formatted += f"Date: {interview_data.get('created_at', '')}\n"
        formatted += f"Character: {interview_data.get('character', 'Interviewer')}\n\n"
        formatted += "TRANSCRIPT:\n\n"
        
        # Add conversation history
        for message in interview_data['conversation_history']:
            speaker = "Interviewer" if message.get('role') == 'assistant' else "Participant"
            formatted += f"{speaker}: {message.get('content', '')}\n\n"
    
    # If there's a transcript field in the new format
    elif 'transcript' in interview_data and isinstance(interview_data['transcript'], list):
        # Add basic metadata
        formatted += f"Interview Title: {interview_data.get('title', 'Untitled Interview')}\n"
        formatted += f"Date: {interview_data.get('created_at', '')}\n"
        formatted += f"Character: {interview_data.get('character', 'Interviewer')}\n\n"
        formatted += "TRANSCRIPT:\n\n"
        
        # Add transcript entries
        for entry in interview_data['transcript']:
            formatted += f"{entry.get('speaker_name', 'Unknown')}: {entry.get('content', '')}\n\n"
    
    return formatted


def simple_analysis_generation(transcript, prompt):
    """Generate analysis using a simple OpenAI API call."""
    try:
        import os
        import openai
        
        # Check for API key
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
        
        client = openai.OpenAI(api_key=api_key)
        
        # Send request to OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        # Return the analysis
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error generating analysis: {str(e)}")
        return f"Error generating analysis: {str(e)}"


def parse_analysis_response(response, prompt_used):
    """Parse the LLM response into a structured analysis format."""
    # This implementation does basic parsing of common sections
    # A more sophisticated implementation could use structured output from GPT
    
    # Initialize the structure
    analysis = {
        "performed_at": datetime.datetime.now().isoformat(),
        "analysis_prompt_used": prompt_used,
        "raw_analysis": response,  # Keep the original for reference
        "summary": "",
        "user_needs": [],
        "goals": [],
        "pain_points": [],
        "opportunities": [],
        "recommendations": [],
        "key_quotes": []
    }
    
    # Extract summary (first paragraph often contains summary)
    paragraphs = response.split('\n\n')
    if paragraphs:
        analysis["summary"] = paragraphs[0].strip()
    
    # Look for section headers in the response
    sections = {
        "user needs": "user_needs",
        "needs": "user_needs",
        "goals": "goals",
        "pain points": "pain_points",
        "challenges": "pain_points",
        "opportunities": "opportunities",
        "recommendations": "recommendations",
        "key quotes": "key_quotes",
        "quotes": "key_quotes"
    }
    
    current_section = None
    section_content = []
    
    for line in response.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check if this line is a section header
        is_header = False
        for header, section_name in sections.items():
            # Look for section headers (e.g., "User Needs:", "Goals:", etc.)
            if line.lower().startswith(header.lower() + ':') or line.lower() == header.lower():
                # If we were building a previous section, add it
                if current_section and section_content:
                    analysis[current_section].append(' '.join(section_content))
                    section_content = []
                
                # Start new section
                current_section = section_name
                # Remove the header from the content
                content = line.split(':', 1)[-1].strip() if ':' in line else ""
                if content:
                    section_content.append(content)
                is_header = True
                break
        
        # If not a header and we're in a section, add to current section
        if not is_header and current_section:
            # Check if this is a bullet point
            if line.startswith('- ') or line.startswith('• '):
                # If we have accumulated content, add it as an item
                if section_content:
                    analysis[current_section].append(' '.join(section_content))
                    section_content = []
                # Start a new item
                section_content.append(line[2:].strip())
            else:
                # Continue with current item
                section_content.append(line)
    
    # Add the last section if there is one
    if current_section and section_content:
        analysis[current_section].append(' '.join(section_content))
    
    return analysis

# ------ Discussion Guide and Session API Routes ------

@app.route('/discussion_guide/create', methods=['POST'])
def create_discussion_guide():
    """Create a new discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        data = request.json
        logger.info(f"Create discussion guide request: {data}")
        
        # Generate a unique ID
        guide_id = str(uuid.uuid4())
        
        # Current time
        now = datetime.datetime.now()
        
        # Prepare the guide data
        guide_data = {
            'id': guide_id,
            'title': data.get('title', 'Untitled Guide'),
            'project': data.get('project', ''),
            'interview_type': data.get('interview_type', 'custom_interview'),
            'prompt': data.get('prompt', ''),
            'interview_prompt': data.get('interview_prompt', ''),
            'analysis_prompt': data.get('analysis_prompt', ''),
            'character_select': data.get('character_select', ''),
            'voice_id': data.get('voice_id', 'EXAVITQu4vr4xnSDxMaL'),
            'target_audience': data.get('interviewee', {}),  # Map interviewee to target_audience
            'created_at': now,
            'updated_at': now,
            'status': 'active',
            'sessions': [],
            'custom_questions': data.get('custom_questions', []),
            'time_per_question': data.get('time_per_question', 3),
            'options': data.get('options', {})
        }
        
        # Save the guide
        created_id = discussion_service.create_guide(guide_data)
        logger.info(f"Created new discussion guide with ID: {created_id}")
        
        # Return success response with guide ID and redirect URL
        return jsonify({
            'status': 'success',
            'guide_id': created_id,
            'redirect_url': f"/discussion_guide/{created_id}"
        })
    except Exception as e:
        logger.error(f"Error creating discussion guide: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guides', methods=['GET'])
def get_discussion_guides():
    """Get all discussion guides."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        guides = discussion_service.list_guides(active_only=active_only)
        return jsonify({'success': True, 'guides': guides})
    except Exception as e:
        logger.error(f"Error getting discussion guides: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>', methods=['GET'])
def get_discussion_guide(guide_id):
    """Get a discussion guide by ID."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        guide = discussion_service.get_guide(guide_id)
        if not guide:
            return jsonify({'success': False, 'error': 'Guide not found'}), 404
        
        return jsonify({'success': True, 'guide': guide})
    except Exception as e:
        logger.error(f"Error getting discussion guide: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>/sessions', methods=['GET'])
def get_guide_sessions(guide_id):
    """Get all sessions for a discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        sessions = discussion_service.list_guide_sessions(guide_id)
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        logger.error(f"Error getting guide sessions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a session by ID."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        session = discussion_service.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        return jsonify({'success': True, 'session': session})
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new session for a discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        data = request.json
        guide_id = data.get('guide_id')
        interviewee = data.get('interviewee', {})
        
        if not guide_id:
            return jsonify({'success': False, 'error': 'Missing guide_id'}), 400
        
        session_id = discussion_service.create_session(guide_id, interviewee)
        if not session_id:
            return jsonify({'success': False, 'error': 'Failed to create session'}), 500
            
        # If character was provided in the request, update it in the session
        if 'character' in data:
            character = data.get('character')
            session = discussion_service.get_session(session_id)
            if session:
                session['character'] = character
                session['character_select'] = character
                discussion_service.update_session(session_id, session)
                logger.info(f"Updated character for new session {session_id} to {character}")
        
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'redirect_url': f"/session/{session_id}"
        })
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>/add_message', methods=['POST'])
def api_add_session_message(session_id):
    """Add a message to a session."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Service not available'}), 500
    
    try:
        data = request.json
        if not data or 'content' not in data or 'role' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        content = data['content']
        role = data['role']
        message_id = data.get('id', str(uuid.uuid4()))
        
        logger.info(f"Session message request for {session_id}: {data}")
        
        # Add message to the session
        discussion_service.add_message_to_session(session_id, content, role, message_id)
        
        # Notify all clients monitoring this session
        message_data = {
            'id': message_id,
            'content': content,
            'role': role,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Emit to all clients in the monitoring room
        socketio.emit('new_message', {
            'session_id': session_id,
            'message': message_data
        }, room=f"monitor_{session_id}")
        
        logger.info(f"Added message {message_id} to session {session_id} via WebSocket: True")
        
        # Process the message with AI Observer if available
        if observer_service:
            try:
                # Get context from the session
                context = []
                session = discussion_service.get_session(session_id)
                if session:
                    messages = session.get('messages', [])
                    # Get the last few messages for context
                    context = messages[-5:] if len(messages) > 5 else messages
                
                # Analyze the message
                observation = observer_service.analyze_message(session_id, message_data, context)
                
                # Emit the observation to the monitoring room
                socketio.emit('new_observation', {
                    'session_id': session_id,
                    'observation': observation
                }, room=f"monitor_{session_id}")
                
                logger.info(f"Emitted AI Observer analysis for message {message_id}")
            except Exception as e:
                logger.error(f"Error processing message with AI Observer: {str(e)}")
        
        # If LangChain is enabled, generate response for user messages
        if role == 'user' and use_langchain:
            # Generate AI response
            logger.info(f"Generating AI response for session {session_id}")
            
            try:
                # Get the session to check if it has guide information
                session = discussion_service.get_session(session_id)
                
                if not session:
                    logger.error(f"Session {session_id} not found")
                    raise ValueError(f"Session {session_id} not found")
                
                # We need the guide ID to get the context
                guide_id = session.get('guide_id')
                if not guide_id:
                    logger.error(f"No guide_id found for session {session_id}")
                    raise ValueError("No guide_id found for session")
                
                # Get the guide to get context information
                guide = discussion_service.get_guide(guide_id)
                if not guide:
                    logger.error(f"Guide {guide_id} not found for session {session_id}")
                    raise ValueError(f"Guide {guide_id} not found")

                # Prepare required context for LangChain interview
                context = guide.get('context', '')
                topic = guide.get('name', 'General Interview')
                goals = guide.get('goals', [])
                
                if not context or not goals:
                    logger.warning(f"Missing context or goals in guide {guide_id} for session {session_id}")
                    # Default values if missing
                    if not context:
                        context = "This is an interview conversation."
                    if not goals:
                        goals = ["Gather information from the participant"]

                # Log key information before calling generate_response
                logger.info(f"Using topic: {topic}, context length: {len(context)}, goals: {len(goals)} items")
                
                # Generate response with all required context information
                try:
                    # Get character from session data if available
                    session_data = discussion_service.get_session(session_id)
                    character = session_data.get('character', 'interviewer') if session_data else 'interviewer'
                    
                    # Pass all required information to the interview service
                    response_text = interview_service.generate_response(
                        session_id, 
                        content,
                        character,
                        {
                            'topic': topic,
                            'context': context,
                            'goals': goals
                        }
                    )
                    
                    # Add AI response to the session
                    ai_message_id = str(uuid.uuid4())
                    discussion_service.add_message_to_session(session_id, response_text, 'assistant', ai_message_id)
                    
                    # Create message data for websocket
                    ai_message = {
                        'id': ai_message_id,
                        'content': response_text,
                        'role': 'assistant',
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    
                    # Emit AI message to all clients
                    socketio.emit('new_message', {
                        'session_id': session_id,
                        'message': ai_message
                    }, room=f"monitor_{session_id}")
                    
                    logger.info(f"Added AI response ({len(response_text)} chars) to session {session_id}")
                except Exception as e:
                    logger.error(f"Error generating response: {str(e)}")
                    error_message = f"Sorry, I encountered an error while processing your response. {str(e)}"
                    
                    # Add an error message as the AI response
                    ai_message_id = str(uuid.uuid4())
                    discussion_service.add_message_to_session(
                        session_id, 
                        error_message, 
                        'assistant', 
                        ai_message_id
                    )
                    
                    # Emit error message to clients
                    socketio.emit('new_message', {
                        'session_id': session_id,
                        'message': {
                            'id': ai_message_id,
                            'content': error_message,
                            'role': 'assistant',
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                    }, room=f"monitor_{session_id}")
            except Exception as e:
                logger.error(f"Error in LangChain response generation: {str(e)}")
                ai_message_id = str(uuid.uuid4())
                error_message = f"I apologize for the confusion, but it seems like there might have been an error in the conversation retrieval. Could you please provide me with the latest response from the participant so that I can continue the interview or introduce a new relevant topic? Thank you for your understanding."
                
                discussion_service.add_message_to_session(
                    session_id, 
                    error_message, 
                    'assistant', 
                    ai_message_id
                )
                
                socketio.emit('new_message', {
                    'session_id': session_id,
                    'message': {
                        'id': ai_message_id,
                        'content': error_message,
                        'role': 'assistant',
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                }, room=f"monitor_{session_id}")
        
        return jsonify({'success': True, 'message_id': message_id})
        
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>/messages', methods=['GET'])
def api_get_session_messages(session_id):
    """Get all messages for a session."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        # Check if session exists
        try:
            session = discussion_service.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found in get_messages")
                return jsonify({'success': False, 'error': f'Session {session_id} not found'}), 404
        except Exception as e:
            logger.error(f"Error checking session {session_id} in get_messages: {str(e)}")
            return jsonify({'success': False, 'error': 'Error checking session'}), 500
            
        # Get all messages for the session
        messages = discussion_service.get_messages(session_id)
        return jsonify({'success': True, 'messages': messages})
        
    except Exception as e:
        logger.error(f"Error in api_get_session_messages for session {session_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>/complete', methods=['POST'])
def complete_session(session_id):
    """Mark a session as completed."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        # Get additional data if provided
        data = request.json or {}
        
        # Update session with additional information before marking as complete
        if data:
            # Get the current session
            session = discussion_service.get_session(session_id)
            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
                
            # Add researcher notes if provided
            if 'researcher_notes' in data:
                session['researcher_notes'] = data['researcher_notes']
                
            # Add session quality if provided
            if 'session_quality' in data:
                session['session_quality'] = data['session_quality']
                
            # Add end reason if provided
            if 'end_reason' in data:
                session['end_reason'] = data['end_reason']
                
            # Add final message if provided
            if 'final_message' in data:
                session['final_message'] = data['final_message']
                
            # Update participant information if provided
            if 'additional_participant_info' in data and data['additional_participant_info']:
                # Get current interviewee data or create empty dict
                interviewee = session.get('interviewee', {})
                
                # Update with additional information
                additional_info = data['additional_participant_info']
                if 'role_details' in additional_info and additional_info['role_details']:
                    interviewee['role_details'] = additional_info['role_details']
                    
                if 'experience_level' in additional_info and additional_info['experience_level']:
                    interviewee['experience_level'] = additional_info['experience_level']
                    
                if 'additional_context' in additional_info and additional_info['additional_context']:
                    interviewee['additional_context'] = additional_info['additional_context']
                
                # Update the session with enriched interviewee data
                session['interviewee'] = interviewee
                
            # Save the updated session data
            discussion_service.update_session(session_id, session)
        
        # Mark the session as complete
        success = discussion_service.complete_session(session_id)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to complete session'}), 500
        
        # Notify researchers via WebSocket that the session has been completed
        try:
            socketio.emit('session_completed', {
                'session_id': session_id,
                'timestamp': datetime.datetime.now().isoformat(),
                'message': "The interview session has been completed."
            }, room=f"monitor_{session_id}")
            logger.info(f"Emitted session_completed event for session {session_id}")
        except Exception as e:
            logger.error(f"Error emitting session_completed event: {str(e)}")
        
        # Check if auto-analysis should be run based on request data
        should_analyze = data.get('should_analyze', True)
        
        # If auto-analysis is enabled, generate analysis
        if should_analyze:
            session = discussion_service.get_session(session_id)
            guide_id = session.get('guide_id')
            guide = discussion_service.get_guide(guide_id)
            
            if guide and guide.get('options', {}).get('analysis', True):
                try:
                    # Get the transcript
                    transcript = session.get('transcript', '')
                    
                    # Get analysis prompt
                    analysis_prompt = guide.get('analysis_prompt', 'Analyze the transcript')
                    
                    # Generate analysis using LangChain
                    if interview_service:
                        logger.info(f"Automatically generating analysis for session {session_id}")
                        analysis = interview_service.generate_analysis(transcript, analysis_prompt)
                        
                        # Save the analysis
                        discussion_service.analyze_session(session_id, {
                            'content': analysis,
                            'generated_at': datetime.datetime.now().isoformat()
                        })
                        
                        # Notify researchers via WebSocket that the analysis is ready
                        try:
                            socketio.emit('analysis_complete', {
                                'session_id': session_id,
                                'timestamp': datetime.datetime.now().isoformat(),
                                'message': "The interview analysis is now ready."
                            }, room=f"monitor_{session_id}")
                            logger.info(f"Emitted analysis_complete event for session {session_id}")
                        except Exception as e:
                            logger.error(f"Error emitting analysis_complete event: {str(e)}")
                except Exception as ae:
                    logger.error(f"Error generating automatic analysis: {str(ae)}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error completing session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>/analyze', methods=['POST'])
def analyze_session(session_id):
    """Generate analysis for a session."""
    if not discussion_service or not interview_service:
        return jsonify({'success': False, 'error': 'Required services not available'}), 500
    
    try:
        # Get the session
        session = discussion_service.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Get the transcript
        transcript = session.get('transcript', '')
        if not transcript:
            return jsonify({'success': False, 'error': 'No transcript available for analysis'}), 400
        
        # Get the guide
        guide_id = session.get('guide_id')
        guide = discussion_service.get_guide(guide_id)
        
        # Get analysis prompt
        analysis_prompt = guide.get('analysis_prompt', 'Analyze the transcript') if guide else 'Analyze the transcript'
        
        # Generate analysis
        analysis = interview_service.generate_analysis(transcript, analysis_prompt)
        
        # Save the analysis
        success = discussion_service.analyze_session(session_id, {
            'content': analysis,
            'generated_at': datetime.datetime.now().isoformat()
        })
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to save analysis'}), 500
        
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        logger.error(f"Error analyzing session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>/archive', methods=['POST'])
def archive_discussion_guide(guide_id):
    """Archive a discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        success = discussion_service.archive_guide(guide_id)
        if not success:
            return jsonify({'success': False, 'error': 'Guide not found or could not be archived'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error archiving guide {guide_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>/delete', methods=['POST'])
def delete_discussion_guide(guide_id):
    """Permanently delete a discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        success = discussion_service.delete_guide(guide_id)
        if not success:
            return jsonify({'success': False, 'error': 'Guide not found or could not be deleted'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting guide {guide_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/discussion_guide/<guide_id>/duplicate', methods=['POST'])
def duplicate_discussion_guide(guide_id):
    """Duplicate a discussion guide."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        data = request.json
        title = data.get('title')
        
        if not title:
            return jsonify({'success': False, 'error': 'Missing title'}), 400
        
        # Get the source guide
        source_guide = discussion_service.get_guide(guide_id)
        if not source_guide:
            return jsonify({'success': False, 'error': 'Guide not found'}), 404
        
        # Create a copy with a new ID
        new_guide = source_guide.copy()
        new_guide.pop('id', None)
        new_guide['title'] = title
        new_guide['created_at'] = datetime.datetime.now()
        new_guide['updated_at'] = datetime.datetime.now()
        new_guide['sessions'] = []
        new_guide['status'] = 'active'
        
        # Save the new guide
        new_guide_id = discussion_service.create_guide(new_guide)
        
        return jsonify({
            'success': True,
            'guide_id': new_guide_id
        })
    except Exception as e:
        logger.error(f"Error duplicating guide {guide_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ------ Frontend Routes for Discussion Guides and Sessions ------

@app.route('/discussion_guides', methods=['GET'])
def discussion_guides_list():
    """Show the discussion guides list page."""
    try:
        if not discussion_service:
            return redirect('/interview_archive')  # Fallback to old view if not available
        
        guides = discussion_service.list_guides()
        return render_template('langchain/discussion_guides.html', guides=guides)
    except Exception as e:
        logger.error(f"Error loading discussion guides page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/discussion_guide/<guide_id>', methods=['GET'])
def discussion_guide_details(guide_id):
    """Show the discussion guide details page."""
    try:
        if not discussion_service:
            return redirect('/interview_details/' + guide_id)  # Fallback to old view if not available
        
        guide = discussion_service.get_guide(guide_id)
        if not guide:
            return render_template('langchain/error.html', error="Discussion guide not found"), 404
        
        sessions = discussion_service.list_guide_sessions(guide_id)
        return render_template('langchain/discussion_guide_details.html', guide=guide, sessions=sessions, guide_id=guide_id)
    except Exception as e:
        logger.error(f"Error loading discussion guide page: {str(e)}")
        return render_template('langchain/error.html', error=str(e))

@app.route('/session/<session_id>', methods=['GET'])
def session_details(session_id):
    """Show the interview session details page."""
    try:
        if not discussion_service:
            return redirect('/interview_details/' + session_id)  # Fallback to old view if not available
        
        session = discussion_service.get_session(session_id)
        if not session:
            return render_template('langchain/error.html', error="Session not found"), 404
        
        guide_id = session.get('guide_id')
        guide = discussion_service.get_guide(guide_id) if guide_id else None
        
        return render_template('langchain/session.html', session=session, guide=guide, session_id=session_id)
    except Exception as e:
        logger.error(f"Error loading session page: {str(e)}")
        return render_template('langchain/error.html', error=str(e))

@app.route('/api/session/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get all messages for a session."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        # Get the session
        session = discussion_service.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Return the messages
        messages = session.get('messages', [])
        
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'messages': messages
        })
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ------ AI Observer API Routes ------

@app.route('/api/observer/<session_id>/analyze_message', methods=['POST'])
def analyze_session_message(session_id):
    """Analyze a session message using the AI observer."""
    if not observer_service:
        return jsonify({'success': False, 'error': 'Observer service not available'}), 500
    
    try:
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({'success': False, 'error': 'Missing message data'}), 400
        
        # Get context from the session
        context = []
        if discussion_service:
            session = discussion_service.get_session(session_id)
            if session:
                messages = session.get('messages', [])
                # Get the last few messages for context
                context = messages[-5:] if len(messages) > 5 else messages
        
        # Analyze the message
        observation = observer_service.analyze_message(session_id, message, context)
        
        # Emit the observation to the monitoring room
        socketio.emit('new_observation', {
            'session_id': session_id,
            'observation': observation
        }, room=f"monitor_{session_id}")
        
        logger.info(f"Emitted new observation for message {message.get('id')}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'observation': observation
        })
    except Exception as e:
        logger.error(f"Error analyzing message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/observer/<session_id>/state', methods=['GET'])
def get_observer_state(session_id):
    """Get the current observer state for a session."""
    if not observer_service:
        return jsonify({'success': False, 'error': 'Observer service not available'}), 500
    
    try:
        # Get the observer state
        state = observer_service.get_observer_state(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'observer_state': state
        })
    except Exception as e:
        logger.error(f"Error getting observer state: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/observer/<session_id>/summary', methods=['POST'])
def generate_observer_summary(session_id):
    """Generate a summary of the observer notes for a session."""
    if not observer_service:
        return jsonify({'success': False, 'error': 'Observer service not available'}), 500
    
    try:
        # Generate the summary
        summary = observer_service.generate_summary(session_id)
        
        # Emit the summary to the monitoring room
        socketio.emit('observer_summary', {
            'session_id': session_id,
            'summary': summary
        }, room=f"monitor_{session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'summary': summary
        })
    except Exception as e:
        logger.error(f"Error generating observer summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ------ SocketIO Event Handlers ------

@socketio.on('connect')
def handle_connect():
    """Handle client connection event."""
    logger.info(f"Client connected: {request.sid}")
    emit('welcome', {'message': 'Connected to DARIA interview server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect event."""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_monitor_room')
def handle_join_monitor(data):
    """Handle a client joining a monitoring room for an interview."""
    try:
        session_id = data.get('session_id')
        if not session_id:
            logger.warning(f"Client {request.sid} tried to join monitoring room without session_id")
            # Return error response via callback
            return {'success': False, 'error': 'No session_id provided'}
        
        # Join the socket room for this monitoring session
        room = f"monitor_{session_id}"
        join_room(room)
        logger.info(f"Client {request.sid} joined monitoring room for session {session_id}")
        
        # Immediately trigger question generation and insights on join
        if observer_service:
            # Request suggested questions
            questions = observer_service.get_suggested_questions(session_id)
            socketio.emit('suggested_questions', {
                'session_id': session_id,
                'questions': questions
            }, room=request.sid)
            logger.info(f"Sent initial suggested questions to new monitor client for session {session_id}")
            
            # Also generate insights if available
            try:
                insights = observer_service.get_key_insights(session_id)
                socketio.emit('insights_update', {
                    'session_id': session_id,
                    'insights': insights
                }, room=request.sid)
                logger.info(f"Sent initial insights to new monitor client for session {session_id}")
            except Exception as insight_error:
                logger.error(f"Error getting initial insights: {str(insight_error)}")
        
        # Emit connection confirmation
        emit('monitor_joined', {'session_id': session_id, 'joined_at': datetime.datetime.now().isoformat()})
        
        # Return success response via callback
        return {'success': True, 'message': f'Joined monitor room for {session_id}'}
        
    except Exception as e:
        logger.error(f"Error in join_monitor_room: {str(e)}")
        # Return error response via callback
        return {'success': False, 'error': str(e)}

@socketio.on('join_session')
def handle_join_session(data):
    """Handle interview client joining its session room."""
    try:
        session_id = data.get('session_id')
        if not session_id:
            return {'success': False, 'error': 'No session_id provided'}
        
        # Join the specific room for this interview session
        room = f"session_{session_id}"
        join_room(room)
        
        logger.info(f"Client {request.sid} joined session room for session {session_id}")
        return {'success': True}
    except Exception as e:
        logger.error(f"Error in join_session: {str(e)}")
        return {'success': False, 'error': str(e)}

@socketio.on('new_message')
def handle_new_message(data):
    """Event handler when a new message is received from a client."""
    if not data or 'session_id' not in data or 'message' not in data:
        return {'success': False, 'error': 'Invalid message data'}
    
    session_id = data['session_id']
    message = data['message']
    
    # Save the message to the session
    try:
        # Add to session via the API
        discussion_service.add_message_to_session(session_id, message['content'], message['role'], message.get('id'))
        
        # Emit to all clients in both rooms
        # First to the session room (remote interview client)
        emit('new_message', {'message': message}, room=f"session_{session_id}", include_self=False)
        
        # Then to the monitor room
        emit('new_message', {'message': message}, room=f"monitor_{session_id}", include_self=False)
        
        # Update that it was emitted via WebSocket
        logger.info(f"Added message {message.get('id')} to session {session_id} via WebSocket: True")
        
        # Process the message with AI Observer if available
        if observer_service:
            try:
                # Get context from the session
                context = []
                session = discussion_service.get_session(session_id)
                if session:
                    messages = session.get('messages', [])
                    # Get the last few messages for context
                    context = messages[-5:] if len(messages) > 5 else messages
                
                # Analyze the message
                observation = observer_service.analyze_message(session_id, message, context)
                
                # Emit the observation to the monitoring room
                emit('new_observation', {
                    'session_id': session_id,
                    'observation': observation
                }, room=f"monitor_{session_id}")
                
                logger.info(f"Emitted AI Observer analysis for message {message.get('id')}")
            except Exception as e:
                logger.error(f"Error processing message with AI Observer: {str(e)}")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error adding message to session: {str(e)}")
        return {'success': False, 'error': str(e)}

@socketio.on('send_suggestion')
def handle_send_suggestion(data):
    """Handle suggestion from monitor."""
    session_id = data.get('session_id')
    suggestion = data.get('suggestion')
    
    if not session_id or not suggestion:
        emit('error', {'message': 'Missing session_id or suggestion'})
        return
        
    try:
        # Create a formatted message for the suggestion
        message = {
            'id': str(uuid.uuid4()),
            'role': 'system',
            'content': suggestion,
            'type': 'suggestion',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Only notify the monitor - don't send to the remote interview UI
        # This prevents popups from appearing to the interviewee
        socketio.emit('suggestion_sent', {
            'session_id': session_id,
            'suggestion': message
        }, room=f"monitor_{session_id}")
        
        logger.info(f"Suggestion sent to monitor for session {session_id}: {suggestion}")
        
        # Store the suggestion in the session for later reference
        if discussion_service:
            try:
                # Add as a special type of message that won't be shown to participants
                message['visible_to_participant'] = False
                discussion_service.add_message_to_session(
                    session_id, 
                    message['content'], 
                    'system', 
                    message.get('id'),
                    metadata={'type': 'monitor_suggestion'}
                )
            except Exception as e:
                logger.warning(f"Could not store suggestion in session history: {str(e)}")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error sending suggestion: {str(e)}")
        return {'success': False, 'error': str(e)}

@socketio.on('request_suggested_questions')
def handle_request_suggested_questions(data):
    """Handle a request for AI-suggested interview questions."""
    session_id = data.get('session_id')
    if not session_id:
        logger.warning("No session_id provided to request_suggested_questions")
        emit('error', {'message': 'No session_id provided'})
        return
        
    logger.info(f"Received request for suggested questions for session {session_id}")
        
    try:
        if observer_service:
            # Get suggested questions from observer service
            logger.info(f"Requesting suggested questions from observer service for session {session_id}")
            questions = observer_service.get_suggested_questions(session_id)
            
            # Ensure questions are properly formatted
            formatted_questions = []
            for q in questions:
                # Make sure each question has the expected format
                if isinstance(q, dict) and 'text' in q:
                    formatted_questions.append(q)
                elif isinstance(q, str):
                    # If it's just a string, convert to proper format
                    formatted_questions.append({
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.datetime.now().isoformat(),
                        'text': q
                    })
            
            logger.info(f"Sending {len(formatted_questions)} suggested questions for session {session_id}")
            
            # Debug the questions we're sending
            for q in formatted_questions[:3]:  # Log first 3 for brevity
                q_text = q.get('text', 'NO TEXT FOUND')
                logger.info(f"Question being sent: {q_text[:50]}...")
            
            # Send back to client
            emit('suggested_questions', {
                'session_id': session_id,
                'questions': formatted_questions
            })
            
            logger.info(f"Sent suggested questions for session {session_id}")
        else:
            logger.warning("Observer service not available for generating questions")
            # Generate some static fallback questions if observer is not available
            fallback_questions = [
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Could you tell me more about that?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "How did that make you feel?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Can you provide a specific example?"
                }
            ]
            
            logger.info(f"Sending {len(fallback_questions)} fallback questions for session {session_id}")
            
            # Send fallback questions
            emit('suggested_questions', {
                'session_id': session_id,
                'questions': fallback_questions
            })
            
            logger.info(f"Sent fallback questions for session {session_id}")
    except Exception as e:
        logger.error(f"Error getting suggested questions: {str(e)}", exc_info=True)
        # Try to send some emergency fallback questions even after error
        try:
            emergency_questions = [
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Can you explain more about your experience?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "What else would you like to share?"
                }
            ]
            
            emit('suggested_questions', {
                'session_id': session_id,
                'questions': emergency_questions
            })
            
            logger.info(f"Sent emergency questions after error for session {session_id}")
        except Exception as inner_e:
            logger.error(f"Failed to send emergency questions: {str(inner_e)}", exc_info=True)
            
        emit('error', {'message': f"Error getting suggested questions: {str(e)}"})

@socketio.on('leave_monitor_room')
def handle_leave_room(data):
    """Handle client leaving a monitoring room."""
    try:
        session_id = data.get('session_id')
        if not session_id:
            return
        
        room = f"monitor_{session_id}"
        leave_room(room)
        logger.info(f"Client {request.sid} left monitoring room for session {session_id}")
    except Exception as e:
        logger.error(f"Error in leave_monitor_room: {str(e)}")

@socketio.on('researcher_message')
def handle_researcher_message(data):
    """Handle system message from researcher to participant."""
    try:
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message or not discussion_service:
            return
        
        # Add message ID and timestamp if not provided
        if 'id' not in message:
            message['id'] = str(uuid.uuid4())
        
        if 'timestamp' not in message:
            message['timestamp'] = datetime.datetime.now().isoformat()
        
        # Process different message types
        message_type = message.get('type', 'suggestion')
        
        # For direct questions, we need to add them directly as an AI message
        if message_type == 'direct_question':
            # Create an AI message with the researcher's question
            ai_message = {
                'role': 'assistant',
                'content': message['content'],
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'researcher_generated': True
            }
            
            # Add the message to the session
            discussion_service.add_message(session_id, ai_message)
            
            # Emit to all clients in the monitoring room
            socketio.emit('new_message', {
                'session_id': session_id,
                'message': ai_message
            }, room=f"monitor_{session_id}")
            
            logger.info(f"Direct researcher question sent to session {session_id}")
            
        # For custom questions to add to the AI prompt
        elif message_type == 'custom_question':
            # Add the custom question to the session's custom_questions list
            session = discussion_service.get_session(session_id)
            if session:
                # Create or update the custom_questions list
                if 'custom_questions' not in session:
                    session['custom_questions'] = []
                
                # Add the new question
                session['custom_questions'].append({
                    'text': message['content'],
                    'priority': message.get('priority', 'normal'),
                    'added_at': datetime.datetime.now().isoformat(),
                    'asked': False
                })
                
                # Update the session
                discussion_service.update_session(session_id, session)
                
                # Log and emit confirmation
                logger.info(f"Custom question added to session {session_id}")
                socketio.emit('custom_question_added', {
                    'session_id': session_id,
                    'question': message['content']
                }, room=f"monitor_{session_id}")
            
        # Regular suggestions and notes
        else:
            # Add message to the session as a system message
            discussion_service.add_message(session_id, message)
            
            # Emit to all clients in the monitoring room
            socketio.emit('new_message', {
                'session_id': session_id,
                'message': message
            }, room=f"monitor_{session_id}")
            
            logger.info(f"Researcher {message_type} sent to session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in researcher_message: {str(e)}")
        socketio.emit('error', {
            'message': f"Error processing researcher message: {str(e)}"
        }, room=request.sid)

@app.route('/api/prompts/edit/<prompt_id>', methods=['POST'])
def api_edit_prompt(prompt_id):
    """API endpoint to save prompt edits."""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        logger.info(f"Editing prompt {prompt_id} with data: {data}")
        
        # Load current prompt to preserve structure
        try:
            config = prompt_mgr.load_prompt(prompt_id)
            if not config:
                config = {}
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Error loading prompt: {str(e)}"}), 500
        
        # Update fields from request data
        for key, value in data.items():
            config[key] = value
        
        # Save the updated config
        try:
            success = prompt_mgr.save_prompt(prompt_id, config)
            if not success:
                return jsonify({'success': False, 'error': 'Failed to save prompt'}), 500
            
            # Clear cache for this prompt
            if prompt_id in prompt_cache:
                del prompt_cache[prompt_id]
                
            return jsonify({'success': True, 'message': f"Prompt {prompt_id} updated successfully"})
        except Exception as e:
            logger.error(f"Error saving prompt {prompt_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Error saving prompt: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error in api_edit_prompt for {prompt_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('request_insights')
def handle_request_insights(data):
    """Handle a request for AI insights on the interview."""
    session_id = data.get('session_id')
    if not session_id:
        emit('error', {'message': 'No session_id provided'})
        return
        
    try:
        if observer_service:
            # Get insights from observer service
            insights = observer_service.get_key_insights(session_id)
            
            # Send back to client
            emit('insights_update', {
                'session_id': session_id,
                'insights': insights
            })
            
            logger.info(f"Sent insights update for session {session_id}")
        else:
            # Send empty list if observer service not available
            emit('insights_update', {
                'session_id': session_id,
                'insights': []
            })
    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        emit('error', {'message': f"Error getting insights: {str(e)}"})

@socketio.on('ping')
def handle_ping(data):
    """Handle ping from client and respond with pong to confirm connection."""
    try:
        logger.debug(f"Received ping from client {request.sid}: {data}")
        emit('pong', {
            'server_time': datetime.datetime.now().isoformat(),
            'client_time': data.get('time'),
            'session_id': data.get('session_id')
        })
    except Exception as e:
        logger.error(f"Error in ping handler: {str(e)}")
        emit('error', {'error': f'Ping error: {str(e)}'})

@socketio.on('intervention')
def handle_intervention(data):
    """Handle direct intervention request from monitor."""
    session_id = data.get('session_id')
    intervention_type = data.get('type')
    
    if not session_id or not intervention_type:
        emit('error', {'message': 'Missing session_id or intervention type'})
        return
        
    try:
        # Forward the intervention to the interview session
        socketio.emit('intervention', {
            'session_id': session_id,
            'type': intervention_type,
            'timestamp': datetime.datetime.now().isoformat()
        }, room=f"session_{session_id}")
        
        # Log the intervention for the monitor too
        socketio.emit('intervention', {
            'session_id': session_id,
            'type': intervention_type,
            'timestamp': datetime.datetime.now().isoformat()
        }, room=f"monitor_{session_id}")
        
        logger.info(f"Applied intervention: {intervention_type} to session {session_id}")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error applying intervention: {str(e)}")
        return {'success': False, 'error': str(e)}

@socketio.on('send_suggestion')
def handle_send_suggestion(data):
    """Handle suggestion from monitor."""
    session_id = data.get('session_id')
    suggestion = data.get('suggestion')
    
    if not session_id or not suggestion:
        emit('error', {'message': 'Missing session_id or suggestion'})
        return
        
    try:
        # Create a formatted message for the suggestion
        message = {
            'id': str(uuid.uuid4()),
            'role': 'system',
            'content': suggestion,
            'type': 'suggestion',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Only notify the monitor - don't send to the remote interview UI
        # This prevents popups from appearing to the interviewee
        socketio.emit('suggestion_sent', {
            'session_id': session_id,
            'suggestion': message
        }, room=f"monitor_{session_id}")
        
        logger.info(f"Suggestion sent to monitor for session {session_id}: {suggestion}")
        
        # Store the suggestion in the session for later reference
        if discussion_service:
            try:
                # Add as a special type of message that won't be shown to participants
                message['visible_to_participant'] = False
                discussion_service.add_message_to_session(
                    session_id, 
                    message['content'], 
                    'system', 
                    message.get('id'),
                    metadata={'type': 'monitor_suggestion'}
                )
            except Exception as e:
                logger.warning(f"Could not store suggestion in session history: {str(e)}")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error sending suggestion: {str(e)}")
        return {'success': False, 'error': str(e)}

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(issues_bp, url_prefix='/issues')
app.register_blueprint(langchain_blueprint)

# ------ Upload Transcript Routes ------

@app.route('/api/upload_transcript', methods=['POST'])
def api_upload_transcript():
    """Handle transcript upload and conversion to interview format."""
    try:
        # Ensure files were uploaded
        if 'transcript_file' not in request.files:
            return jsonify({'success': False, 'error': 'No transcript file provided'}), 400
        
        transcript_file = request.files['transcript_file']
        if transcript_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get metadata from form
        title = request.form.get('title', 'Untitled Interview')
        project = request.form.get('project', '')
        interview_type = request.form.get('interview_type', 'custom_interview')
        researcher_name = request.form.get('researcher_name', '')
        researcher_email = request.form.get('researcher_email', '')
        participant_name = request.form.get('participant_name', 'Anonymous')
        participant_role = request.form.get('participant_role', '')
        participant_email = request.form.get('participant_email', '')
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Read and process the transcript content
        try:
            transcript_content = transcript_file.read().decode('utf-8')
        except UnicodeDecodeError:
            # Try another common encoding if utf-8 fails
            transcript_file.seek(0)
            transcript_content = transcript_file.read().decode('latin-1')
            
        # Debug: Log the first 10 lines to understand format
        preview_lines = transcript_content.strip().split('\n')[:10]
        logger.info(f"Transcript preview (first 10 lines):\n{''.join([line + '\n' for line in preview_lines])}")
        
        # Process transcript into conversation chunks
        lines = transcript_content.strip().split('\n')
        transcript_chunks = []
        current_speaker = None
        current_timestamp = None
        current_content = []
        
        # Detect format patterns
        zoom_bracket_pattern = r'^\s*\[(.*?)\]\s*(\d{1,2}:\d{1,2}:\d{1,2})'  # [Name] 00:00:00
        simple_bracket_pattern = r'^\s*\[(.*?)\]'  # [Name]
        colon_pattern = r'^([^:]+):\s*(.*)'  # Name: text
        time_pattern = r'^(\d{1,2}:\d{1,2}:\d{1,2})\s+(.+)'  # 00:00:00 text
        
        format_type = None
        
        # Check first few lines to determine format
        for line in [l for l in lines[:15] if l.strip()][:5]:
            if re.match(zoom_bracket_pattern, line):
                format_type = "zoom_bracket"
                break
            elif re.match(simple_bracket_pattern, line):
                format_type = "simple_bracket"
                break
            elif re.match(colon_pattern, line):
                format_type = "colon"
                break
            elif re.match(time_pattern, line):
                format_type = "time_prefixed"
                break
        
        logger.info(f"Detected transcript format: {format_type or 'unknown'}")
        
        # Process transcript based on detected format
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if format_type == "zoom_bracket":
                # Try to match [Speaker] 00:00:00 pattern (Zoom format)
                match = re.match(zoom_bracket_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker and timestamp
                    current_speaker = match.group(1).strip()
                    current_timestamp = match.group(2)
                    
                    # Get content after timestamp
                    timestamp_start = line.find(current_timestamp)
                    if timestamp_start > 0:
                        content_start = timestamp_start + len(current_timestamp)
                        content = line[content_start:].strip()
                        if content:
                            current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "simple_bracket":
                # Try to match [Speaker] pattern (without timestamp)
                match = re.match(simple_bracket_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker
                    current_speaker = match.group(1).strip()
                    
                    # Get content after bracket
                    bracket_end = line.find(']')
                    if bracket_end > 0:
                        content = line[bracket_end+1:].strip()
                        if content:
                            current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "colon":
                # Try to match Name: Content pattern
                match = re.match(colon_pattern, line)
                if match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker and content
                    current_speaker = match.group(1).strip()
                    content = match.group(2).strip()
                    if content:
                        current_content.append(content)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            elif format_type == "time_prefixed":
                # Try to match 00:00:00 Content pattern
                match = re.match(time_pattern, line)
                if match:
                    timestamp = match.group(1)
                    remaining_text = match.group(2).strip()
                    
                    # Check if remaining text has speaker designation
                    speaker_match = re.match(colon_pattern, remaining_text)
                    if speaker_match:
                        # This is a new speaker entry
                        if current_speaker and current_content:
                            transcript_chunks.append({
                                'speaker': current_speaker,
                                'speaker_name': current_speaker,
                                'content': ' '.join(current_content),
                                'timestamp': current_timestamp or ''
                            })
                            current_content = []
                        
                        current_speaker = speaker_match.group(1).strip()
                        current_timestamp = timestamp
                        content = speaker_match.group(2).strip()
                        if content:
                            current_content.append(content)
                    else:
                        # No speaker designation, continue with current speaker
                        current_timestamp = timestamp
                        if current_speaker:
                            current_content.append(remaining_text)
                        else:
                            # No current speaker, create a generic one
                            current_speaker = "Speaker"
                            current_content.append(remaining_text)
                else:
                    # If no match, treat as continuation of current speaker
                    if current_speaker:
                        current_content.append(line)
            
            else:
                # Fallback processing for unknown formats
                # Try bracket format first (most common in Zoom transcripts)
                bracket_match = re.match(simple_bracket_pattern, line)
                if bracket_match:
                    # Save previous speaker's content if we're switching speakers
                    if current_speaker and current_content:
                        transcript_chunks.append({
                            'speaker': current_speaker,
                            'speaker_name': current_speaker,
                            'content': ' '.join(current_content),
                            'timestamp': current_timestamp or ''
                        })
                        current_content = []
                    
                    # Extract new speaker
                    current_speaker = bracket_match.group(1).strip()
                    
                    # Get content after bracket
                    bracket_end = line.find(']')
                    if bracket_end > 0:
                        content = line[bracket_end+1:].strip()
                        if content:
                            current_content.append(content)
                else:
                    # Try colon pattern
                    colon_match = re.match(colon_pattern, line)
                    if colon_match:
                        # Save previous speaker's content if we're switching speakers
                        if current_speaker and current_content:
                            transcript_chunks.append({
                                'speaker': current_speaker,
                                'speaker_name': current_speaker,
                                'content': ' '.join(current_content),
                                'timestamp': current_timestamp or ''
                            })
                            current_content = []
                        
                        # Extract new speaker and content
                        current_speaker = colon_match.group(1).strip()
                        content = colon_match.group(2).strip()
                        if content:
                            current_content.append(content)
                    elif current_speaker:
                        # If no pattern match, treat as continuation
                        current_content.append(line)
                    else:
                        # No current speaker, create a generic one
                        current_speaker = "Speaker"
                        current_content.append(line)
        
        # Add the last speaker's content
        if current_speaker and current_content:
            transcript_chunks.append({
                'speaker': current_speaker,
                'speaker_name': current_speaker,
                'content': ' '.join(current_content),
                'timestamp': current_timestamp or ''
            })
        
        # Log the extracted chunks for debugging
        logger.info(f"Extracted {len(transcript_chunks)} chunks from transcript")
        if transcript_chunks:
            logger.info(f"First chunk: {transcript_chunks[0]}")
        
        # Auto-identify researcher and participant based on names in transcript
        researcher_speakers = []
        participant_speakers = []
        
        # Extract unique speaker names from transcript
        all_speakers = list(set(chunk['speaker'] for chunk in transcript_chunks))
        logger.info(f"Detected speakers: {all_speakers}")
        
        # If researcher_name is provided, try to identify their messages
        if researcher_name:
            researcher_speakers = [s for s in all_speakers if researcher_name.lower() in s.lower()]
        
        # If participant_name is provided, try to identify their messages
        if participant_name and participant_name != 'Anonymous':
            participant_speakers = [s for s in all_speakers if participant_name.lower() in s.lower()]
        
        # If not found by name, look for typical interviewer/interviewee patterns
        if not researcher_speakers:
            researcher_patterns = ['interviewer', 'researcher', 'moderator', 'dulaney', 'stephen']
            researcher_speakers = [s for s in all_speakers if any(p in s.lower() for p in researcher_patterns)]
        
        if not participant_speakers:
            participant_patterns = ['participant', 'interviewee', 'respondent', 'stark', 'ted', 'theodore']
            participant_speakers = [s for s in all_speakers if any(p in s.lower() for p in participant_patterns)]
        
        logger.info(f"Identified researcher speakers: {researcher_speakers}")
        logger.info(f"Identified participant speakers: {participant_speakers}")
        
        # Map transcript chunks to conversation history format
        conversation_history = []
        for chunk in transcript_chunks:
            # Determine role based on speaker name
            speaker = chunk['speaker']
            # Default to 'user' unless explicitly identified as researcher
            role = 'assistant' if speaker in researcher_speakers else 'user'
            
            conversation_history.append({
                'role': role,
                'content': chunk['content'],
                'timestamp': chunk['timestamp'] or datetime.datetime.now().isoformat()
            })
        
        # Create interview data
        now = datetime.datetime.now()
        interview_data = {
            'session_id': session_id,
            'title': title,
            'project': project,
            'interview_type': interview_type,
            'created_at': now,
            'creation_date': now.strftime("%Y-%m-%d %H:%M"),
            'last_updated': now,
            'expiration_date': now + datetime.timedelta(days=30),
            'status': 'completed',  # Mark as completed since we have the full transcript
            'conversation_history': conversation_history,
            'transcript': transcript_chunks,
            'character': 'interviewer',
            'interviewee': {
                'name': participant_name,
                'role': participant_role,
                'email': participant_email
            },
            'researcher': {
                'name': researcher_name or (researcher_speakers[0] if researcher_speakers else 'Researcher'),
                'email': researcher_email
            },
            'analysis': None  # Will be generated later if needed
        }
        
        # Save the interview data
        save_interview(session_id, interview_data)
        
        # Return success with the session ID
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Transcript uploaded successfully',
            'redirect_url': f"/interview_details/{session_id}"
        })
        
    except Exception as e:
        logger.error(f"Error uploading transcript: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f"Error processing transcript: {str(e)}"
        }), 500

@app.route('/upload_transcript', methods=['GET'])
def upload_transcript_page():
    """Render the upload transcript page."""
    return render_template('langchain/upload_transcript.html', title="Upload Transcript")

# Add a route to test WebSocket connection on monitor
@app.route('/api/test_monitor_ws/<session_id>', methods=['GET'])
def test_monitor_websocket(session_id):
    """Test WebSocket connection to monitor interface."""
    try:
        # Send a test message to the monitor room
        socketio.emit('new_message', {
            'session_id': session_id,
            'message': {
                'id': str(uuid.uuid4()),
                'role': 'system',
                'content': 'This is a test message from the server. WebSocket connection is working!',
                'type': 'system_message',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }, room=f"monitor_{session_id}")
        
        # Also send a test observation
        socketio.emit('new_observation', {
            'session_id': session_id,
            'observation': {
                'id': str(uuid.uuid4()),
                'message_id': str(uuid.uuid4()),
                'content': 'Test observation from the server',
                'tags': ['test', 'observation'],
                'timestamp': datetime.datetime.now().isoformat()
            }
        }, room=f"monitor_{session_id}")
        
        # Send test suggested questions
        socketio.emit('suggested_questions', {
            'session_id': session_id,
            'questions': [
                'Test question 1 from server?',
                'Test question 2 from server?',
                'Test question 3 from server?'
            ]
        }, room=f"monitor_{session_id}")
        
        return jsonify({'success': True, 'message': 'Test events sent to WebSocket'})
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_message_add/<session_id>', methods=['GET'])
def test_add_message(session_id):
    """Test adding a message to a session using the add_message_to_session method."""
    try:
        if not discussion_service:
            return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
        
        # Test message content
        test_content = "This is a test message for debugging the add_message_to_session method"
        
        # Try to add the message to the session
        message_id = discussion_service.add_message_to_session(
            session_id,
            test_content,
            'user'
        )
        
        logger.info(f"Test message added with ID {message_id} to session {session_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Test message added successfully',
            'message_id': message_id
        })
    except Exception as e:
        logger.error(f"Error in test_add_message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add this after the API route for analyzing interviews or in the API routes section

@app.route('/api/interview/delete/<interview_id>', methods=['POST'])
def delete_interview_api(interview_id):
    """Delete an interview by ID."""
    try:
        # Check if the interview exists
        interview_file = os.path.join(DATA_DIR, f"{interview_id}.json")
        if not os.path.exists(interview_file):
            return jsonify({
                'success': False,
                'error': f"Interview with ID {interview_id} not found."
            }), 404
        
        # Delete the interview file
        try:
            os.remove(interview_file)
            logger.info(f"Deleted interview file for {interview_id}")
            
            # If using discussion service, try to delete the session there too
            if discussion_service:
                try:
                    discussion_service.delete_session(interview_id)
                    logger.info(f"Deleted session {interview_id} from discussion service")
                except Exception as e:
                    logger.warning(f"Could not delete session from discussion service: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': "Interview deleted successfully."
            })
        except Exception as e:
            logger.error(f"Error deleting interview file: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error deleting interview file: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"Error deleting interview {interview_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error deleting interview: {str(e)}"
        }), 500

@app.route('/api/session/<session_id>/intervention', methods=['POST'])
def handle_intervention(session_id):
    """Handle an intervention request from the researcher."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Service not available'}), 500
    
    try:
        # Get intervention data
        data = request.json
        if not data or 'type' not in data:
            return jsonify({'success': False, 'error': 'No intervention type provided'}), 400
        
        intervention_type = data['type']
        
        # Log the intervention
        logger.info(f"Intervention requested for session {session_id}: {intervention_type}")
        
        # Different actions based on intervention type
        if intervention_type == 'change-topic':
            # Create a system message
            message = {
                'role': 'system',
                'content': 'The researcher has suggested changing the topic. Please transition to a new relevant area.',
                'timestamp': datetime.datetime.now().isoformat(),
                'id': str(uuid.uuid4()),
                'intervention': 'change-topic'
            }
            discussion_service.add_message(session_id, message)
            
        elif intervention_type == 'pause':
            # Create a system message
            message = {
                'role': 'system',
                'content': 'The researcher has suggested a brief pause. Take a moment before continuing.',
                'timestamp': datetime.datetime.now().isoformat(),
                'id': str(uuid.uuid4()),
                'intervention': 'pause'
            }
            discussion_service.add_message(session_id, message)
            
        elif intervention_type == 'go-deeper':
            # Create a system message
            message = {
                'role': 'system',
                'content': 'The researcher suggests exploring this topic in more depth. Ask follow-up questions to get more details.',
                'timestamp': datetime.datetime.now().isoformat(),
                'id': str(uuid.uuid4()),
                'intervention': 'go-deeper'
            }
            discussion_service.add_message(session_id, message)
            
        elif intervention_type == 'summarize':
            # Create a system message
            message = {
                'role': 'system',
                'content': 'The researcher suggests summarizing what has been discussed so far.',
                'timestamp': datetime.datetime.now().isoformat(),
                'id': str(uuid.uuid4()),
                'intervention': 'summarize'
            }
            discussion_service.add_message(session_id, message)
        
        # Notify all clients in the room about the intervention
        if socketio:
            socketio.emit('intervention', {
                'session_id': session_id,
                'type': intervention_type,
                'timestamp': datetime.datetime.now().isoformat()
            }, room=f"monitor_{session_id}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error handling intervention: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_message_send/<session_id>', methods=['GET'])
def test_send_message(session_id):
    """Test the message sending endpoint directly."""
    try:
        # A simple test message
        test_message = "This is a test message from the diagnostic endpoint"
        
        # Log the test 
        logger.info(f"Test message endpoint called for session {session_id}")
        
        # Add the message to the session
        if discussion_service:
            # This should match the logic in the add_message endpoint
            message_id = discussion_service.add_message_to_session(
                session_id, 
                test_message, 
                'user'
            )
            
            # If successful, return message details
            if message_id:
                # Emit the message via WebSocket if enabled
                if socketio:
                    try:
                        room = f"session_{session_id}"
                        socketio.emit('new_message', {
                            'session_id': session_id,
                            'message': {
                                'content': test_message,
                                'role': 'user',
                                'id': message_id
                            }
                        }, room=room)
                        socketio.emit('new_message', {
                            'session_id': session_id,
                            'message': {
                                'content': test_message,
                                'role': 'user',
                                'id': message_id
                            }
                        }, room=f"monitor_{session_id}")
                        
                        logger.info(f"Added message {message_id} to session {session_id} via WebSocket: {True}")
                    except Exception as e:
                        logger.error(f"Error emitting message via WebSocket: {str(e)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Test message sent successfully',
                    'message_id': message_id
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to add message to session'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Discussion service not available'
            }), 503
    except Exception as e:
        logger.error(f"Error in test message endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Exception: {str(e)}"
        }), 500

@app.route('/remote_interview')
def remote_interview():
    """
    Render the simplified remote interview page
    """
    try:
        # Get session ID from query parameter
        session_id = request.args.get('session_id')
        accepted = request.args.get('accepted', 'false').lower() == 'true'
        character = request.args.get('character')  # Get character parameter from URL
        
        if not session_id:
            error_msg = "No session ID provided"
            logger.error(error_msg)
            return render_template('error.html', message=error_msg)
            
        # Verify session exists
        session_info = discussion_service.get_session(session_id)
        
        if not session_info:
            error_msg = f"Session {session_id} not found"
            logger.error(error_msg)
            return render_template('error.html', message=error_msg)
        
        # If character parameter is provided, set it on the session immediately
        if character and accepted:
            try:
                logger.info(f"Setting character for session {session_id} to {character} from URL parameter")
                session_info['character'] = character
                discussion_service.update_session(session_id, session_info)
                
                # Add system message to reinforce character identity
                system_msg = f"IMPORTANT: You are {character}. Always respond as {character}. When asked about your name, say 'I am {character}'."
                discussion_service.add_message_to_session(session_id, system_msg, "system")
                logger.info(f"Character {character} set for session {session_id} from URL parameter")
                
                # Check if there are any existing assistant messages
                messages = discussion_service.get_session_messages(session_id)
                has_assistant_msg = any(msg.get('role') == 'assistant' for msg in messages if isinstance(msg, dict))
                
                # If no assistant messages yet, add a welcome message
                if not has_assistant_msg:
                    logger.info(f"Adding welcome message for remote session {session_id} as character {character}")
                    # Choose appropriate welcome message based on character
                    welcome_msg = f"Hello! I'm {character}, your interview assistant. Thank you for joining me today to talk about {session_info.get('topic', 'this topic')}. I'd love to hear more about your interest in this activity. Can you share with me what initially drew you to {session_info.get('topic', 'this')}?"
                    
                    # Use character-specific welcome messages for better engagement
                    if character.lower() == 'odessia':
                        welcome_msg = f"Welcome! I'm Odessia, your journey guide for this interview. I believe every conversation is a unique journey of discovery. I'd love to hear more about your interest in {session_info.get('topic', 'this topic')}. Can you share with me what initially drew you to it?"
                    
                    # Add the welcome message
                    discussion_service.add_message_to_session(session_id, welcome_msg, "assistant")
                    logger.info(f"Welcome message added for session {session_id}")
            except Exception as e:
                logger.error(f"Error setting character from URL parameter: {str(e)}")
            
        # If not accepted, show welcome page first
        if not accepted:
            # Get guide info for context
            guide_id = session_info.get('guide_id')
            guide_info = discussion_service.get_guide(guide_id) if guide_id else None
            guide_name = guide_info.get('name', 'Research Session') if guide_info else 'Research Session'
            
            return render_template('welcome.html', 
                                 session_id=session_id,
                                 guide_name=guide_name,
                                 port=request.host.split(':')[-1] if ':' in request.host else '5025',
                                 character=character)  # Pass character to template
        
        # Render the interview page
        return render_template('remote_interview_fixed.html',
                             session_id=session_id,
                             port=request.host.split(':')[-1] if ':' in request.host else '5025')
    except Exception as e:
        logger.exception(f"Error rendering remote interview: {str(e)}")
        return render_template('error.html', message=f"Error rendering interview: {str(e)}")

@app.route('/api/session/<session_id>/set_character', methods=['POST'])
def set_session_character(session_id):
    """Set or update the character for a session."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        data = request.json
        if not data or 'character' not in data:
            return jsonify({'success': False, 'error': 'Missing character parameter'}), 400
        
        character = data['character']
        logger.info(f"Setting character for session {session_id} to {character}")
        print(f"Debug: API call to set_character for session {session_id} with character {character}")
        
        # Get current session data
        session = discussion_service.get_session(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
            
        # Update session with new character
        session['character'] = character
        session['character_select'] = character  # Update both fields for consistency
        
        # Add system message to reinforce character identity
        system_msg = f"""SYSTEM: Character set to {character}. 
        IMPORTANT: You are {character}. Your name is {character}.
        You MUST always respond as {character}. Never break character or reveal you are an AI.
        When asked "who are you" or "what is your name", you MUST respond with "I am {character}."
        If character is Thomas, always respond to identity questions with "My name is Thomas."
        """
        
        # Use add_message_to_session instead of add_message with incorrect parameters
        discussion_service.add_message_to_session(session_id, system_msg, "system")
        
        # Save session
        discussion_service.update_session(session_id, session)
        
        return jsonify({'success': True, 'character': character})
    except Exception as e:
        logger.error(f"Error setting character: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/debug_suggestion')
def debug_suggestion_tool():
    """Debug page for testing suggestions between monitor and remote interview pages."""
    return render_template('debug_suggestion_tool.html')

# Add the API endpoint for suggestions as a fallback method
@app.route('/api/session/<session_id>/suggestion', methods=['POST'])
def handle_api_suggestion(session_id):
    """API endpoint for handling suggestions (fallback method)."""
    if not request.json:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        suggestion = request.json
        logger.info(f"Handling API suggestion for session {session_id}: {suggestion}")
        
        # Emit to all clients in the room
        socketio.emit('new_suggestion', {
            'session_id': session_id,
            'suggestion': suggestion
        }, room=f"session_{session_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error handling API suggestion: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add a test endpoint for WebSocket connections
@app.route('/api/test_monitor_suggestion/<session_id>', methods=['GET'])
def test_monitor_suggestion(session_id):
    """Test endpoint to send a suggestion to a session via Socket.IO."""
    try:
        test_suggestion = {
            'content': 'This is a test suggestion from the API',
            'type': 'suggestion'
        }
        
        # Emit to the session room
        socketio.emit('new_suggestion', {
            'session_id': session_id,
            'suggestion': test_suggestion
        }, room=f"session_{session_id}")
        
        return jsonify({
            'success': True,
            'message': f'Test suggestion sent to session {session_id}',
            'details': 'If the remote interview page is open and connected to the socket, it should receive this suggestion.'
        })
    except Exception as e:
        logger.error(f"Error in test_monitor_suggestion: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# New endpoint to explicitly generate questions
@app.route('/api/observer/<session_id>/generate_questions', methods=['POST'])
def generate_observer_questions(session_id):
    """
    Force generation of question suggestions for a session.
    """
    try:
        # Make sure we have observer service
        if not observer_service:
            return jsonify({
                'success': False,
                'error': 'Observer service not available'
            }), 500
        
        logger.info(f"Manually generating questions for session {session_id}")
        
        # Get the latest messages for context
        if discussion_service:
            messages = discussion_service.get_session_messages(session_id, limit=10)
            logger.info(f"Found {len(messages)} messages for question generation")
        else:
            logger.warning("No discussion service available for fetching messages")
            messages = []
        
        # Call the internal method to generate questions
        observer_service._generate_question_suggestions(session_id, messages)
        
        # Get the newly generated questions
        questions = observer_service.get_suggested_questions(session_id)
        
        # Log what's been generated
        logger.info(f"Generated {len(questions)} questions for session {session_id}")
        
        # Emit to all clients watching this session
        if len(questions) > 0:
            socketio.emit('suggested_questions', {
                'session_id': session_id,
                'questions': questions
            }, room=f"monitor_{session_id}")
            logger.info(f"Emitted {len(questions)} questions to monitor room")
        
        return jsonify({
            'success': True,
            'count': len(questions),
            'message': f"Generated {len(questions)} questions"
        })
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------ Static Debug Routes ------

@app.route('/static/debug_character_test.html')
def debug_character_test():
    """Serve the debug character test page."""
    return send_from_directory('static', 'debug_character_test.html')

@app.route('/static/debug_ai_observer.html')
def debug_ai_observer():
    """Serve the AI Observer debug tool page."""
    return send_from_directory('static', 'debug_ai_observer.html')

@app.route('/api/session/<session_id>/send_confirmed_suggestion', methods=['POST'])
def send_confirmed_suggestion(session_id):
    """API endpoint for sending a confirmed suggestion to the remote interview."""
    try:
        if not request.json or 'suggestion' not in request.json:
            return jsonify({'success': False, 'error': 'Missing suggestion content'}), 400
        
        suggestion = request.json['suggestion']
        logger.info(f"Sending confirmed suggestion to session {session_id}: {suggestion}")
        
        # Create a formatted message for the suggestion
        message = {
            'id': str(uuid.uuid4()),
            'role': 'system',
            'content': suggestion,
            'type': 'suggestion',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Emit to the remote interview session
        socketio.emit('new_suggestion', {'suggestion': message}, room=f"session_{session_id}")
        
        # Also notify the monitor session
        socketio.emit('suggestion_sent', {
            'session_id': session_id,
            'suggestion': message
        }, room=f"monitor_{session_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error sending confirmed suggestion: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/observer/<session_id>/state', methods=['GET'])
def debug_observer_state(session_id):
    """
    Debug endpoint to return the raw observer state for a session.
    This is helpful for troubleshooting observer issues.
    """
    try:
        if not observer_service:
            return jsonify({
                'success': False,
                'error': 'Observer service not available'
            }), 500
        
        # Get the raw observer state
        state = observer_service.get_observer_state(session_id)
        
        # Log what we're returning
        logger.info(f"Debug: Returning observer state for session {session_id}")
        
        # Extract the suggested_questions specifically for easier debugging
        questions = state.get('suggested_questions', [])
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'state': state,
            'suggested_questions': questions
        })
    except Exception as e:
        logger.error(f"Error getting observer state: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add the API endpoint for suggested questions
@app.route('/api/session/<session_id>/suggested_questions', methods=['GET'])
def get_suggested_questions_api(session_id):
    """API endpoint for getting AI-suggested interview questions."""
    try:
        # Make sure we have observer service
        if not observer_service:
            # Return fallback questions if observer service is not available
            fallback_questions = [
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Could you tell me more about that?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "How did that make you feel?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Can you provide a specific example?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "What would you change or improve about that?"
                },
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': "Why do you think that happened?"
                }
            ]
            
            logger.warning(f"Observer service not available - returning fallback questions for session {session_id}")
            return jsonify({
                'session_id': session_id,
                'questions': fallback_questions
            })
        
        logger.info(f"Getting suggested questions for session {session_id}")
        questions = observer_service.get_suggested_questions(session_id)
        
        # Ensure questions are properly formatted
        formatted_questions = []
        for q in questions:
            # Make sure each question has the expected format
            if isinstance(q, dict) and 'text' in q:
                formatted_questions.append(q)
            elif isinstance(q, str):
                # If it's just a string, convert to proper format
                formatted_questions.append({
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'text': q
                })
        
        logger.info(f"Returning {len(formatted_questions)} suggested questions for session {session_id}")
        return jsonify({
            'session_id': session_id,
            'questions': formatted_questions
        })
        
    except Exception as e:
        logger.error(f"Error getting suggested questions via API: {str(e)}", exc_info=True)
        # Return emergency fallback questions on error
        emergency_questions = [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'text': "Can you explain more about your experience?"
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'text': "What else would you like to share?"
            }
        ]
        
        return jsonify({
            'session_id': session_id,
            'questions': emergency_questions
        })

# Start the app
if __name__ == '__main__':
    debug_mode = False
    if '--debug' in sys.argv:
        debug_mode = True
    
    # Check if a custom port is specified
    port = 5025
    port_index = -1
    if '--port' in sys.argv:
        port_index = sys.argv.index('--port')
        if port_index >= 0 and port_index + 1 < len(sys.argv):
            port = int(sys.argv[port_index + 1])
            
    print(f"Starting DARIA Interview API on port {port}")
    print(f"Health check endpoint: http://127.0.0.1:{port}/api/health")
    print(f"Interview start endpoint: http://127.0.0.1:{port}/api/interview/start")
    print(f"Monitor interviews: http://127.0.0.1:{port}/monitor_interview")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode, allow_unsafe_werkzeug=True) 