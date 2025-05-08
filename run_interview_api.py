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
from flask import Flask, request, jsonify, render_template, redirect, Response, flash, send_file, url_for, session
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
from flask_login import login_required, current_user

# Import auth module
from auth_routes import init_auth

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

# App configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'development-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)

# Enable CORS with extended headers support
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
logger.info("CORS enabled for all origins with extended header support")

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logger.info("SocketIO initialized for real-time communication")

# Initialize authentication
init_auth(app)

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

if use_langchain:
    try:
        interview_service = InterviewService(data_dir=str(DATA_DIR))
        logger.info("LangChain interview service initialized successfully")
        
        # discussion_service is already initialized above
        
        observer_service = ObserverService(openai_api_key=os.environ.get('OPENAI_API_KEY'))
        logger.info("Observer service initialized successfully")
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
        sharing_url = f"{host_url}/interview/{new_session_id}?remote=true"
            
        return jsonify({
            'success': True,
            'session_id': new_session_id,
            'sharing_url': sharing_url
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
        
        return jsonify(interview_list)
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
                    return Response(response.content, 
                                   mimetype=content_type)
                    
                else:
                    # Default to returning raw content
                    return response.content, 200, {'Content-Type': content_type}
            else:
                logger.error(f"Error from TTS service: {response.status_code}")
                # Return a success response with a message instead of an error
                # This prevents client errors but informs that TTS failed
                return jsonify({
                    'success': True,
                    'fallback': True,
                    'message': 'TTS service unavailable, using silent mode'
                })
                
        except Exception as e:
            logger.error(f"Error forwarding to TTS service: {str(e)}")
            # Provide a fallback response instead of raising an exception
            return jsonify({
                'success': True,
                'fallback': True,
                'message': 'TTS service unavailable, using silent mode'
            })
        
    except Exception as e:
        logger.error(f"Error in text_to_speech_elevenlabs: {str(e)}")
        return jsonify({
            'success': True,
            'fallback': True,
            'message': 'TTS service error, using silent mode'
        })

@app.route('/api/speech_to_text', methods=['POST'])
def speech_to_text():
    """Process audio file and convert speech to text.
    
    Note: For simplicity, this endpoint returns a success response
    with hardcoded text. The actual speech-to-text functionality
    is implemented client-side using the Web Speech API in the browser.
    """
    try:
        # For compatibility with the API, still accept the audio file
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        # Get the audio file and save it (to simulate processing)
        audio_file = request.files['audio']
        filename = os.path.join('uploads', f"temp_audio_{uuid.uuid4()}.webm")
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        audio_file.save(filename)
        
        # Clean up the file (no need to keep it)
        try:
            os.remove(filename)
        except:
            pass
        
        # Return a success response with placeholder text
        # In reality, we're relying on the browser's Web Speech API
        # This is just to maintain API compatibility
        return jsonify({
            'success': True,
            'text': "I'm saying something important in this interview."
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
            'conversation_history': []
        }
        
        # Save the interview data
        save_interview(session_id, interview_data)
        logger.info(f"Created new interview with ID: {session_id}")
        
        # Return success response with session ID and redirect URL
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'redirect_url': f"/interview_details/{session_id}"
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
                        
                        # Show the remote session interface
                        return render_template('langchain/session_remote.html',
                                              session_id=interview_id,
                                              guide=guide,
                                              character_name=character_name,
                                              voice_id=voice_id,
                                              remote=True)
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
@login_required
def dashboard():
    """Show the dashboard."""
    return render_template('langchain/dashboard.html')

@app.route('/interview_setup')
@login_required
def interview_setup():
    """Create a new interview."""
    # Get all available prompts
    prompts = load_all_prompts()
    
    # Create prompt choices
    prompt_choices = [(name, config.get('agent_name', name)) for name, config in prompts.items()]
    
    # Get discussion guides
    discussion_guides = []
    if discussion_service:
        try:
            guides = discussion_service.get_guides()
            discussion_guides = [(guide.get('id'), guide.get('title')) for guide in guides]
        except Exception as e:
            logger.error(f"Error fetching discussion guides: {str(e)}")

    return render_template('langchain/interview_setup.html', 
                          prompts=prompt_choices,
                          guides=discussion_guides,
                          use_langchain=use_langchain)

@app.route('/interview_archive')
@login_required
def interview_archive():
    """Show all interviews."""
    try:
        # Load interviews from Discussion service
        interviews = []
        
        if discussion_service:
            session_ids = discussion_service.get_session_ids()
            logger.info(f"Loaded {len(session_ids)} interviews for archive page")
            
            for session_id in session_ids:
                try:
                    session = discussion_service.get_session(session_id)
                    if session:
                        interviews.append(session)
                except Exception as e:
                    logger.error(f"Error loading interview archive: {str(e)}")
        
        return render_template('langchain/interview_archive.html', interviews=interviews)
    except Exception as e:
        logger.error(f"Error displaying interview archive: {str(e)}")
        flash(f"Error displaying interview archive: {str(e)}", "danger")
        return redirect('/dashboard')

@app.route('/prompts/')
@login_required
def prompts_manager():
    """Show all prompts."""
    try:
        agent_names = prompt_mgr.get_available_agents()
        logger.info(f"Found {len(agent_names)} agent prompts: {agent_names}")
        
        prompts = []
        for agent_name in agent_names:
            try:
                config = prompt_mgr.load_prompt(agent_name)
                if config:
                    # Add ID to config
                    config['id'] = agent_name
                    prompts.append(config)
            except Exception as e:
                logger.error(f"Error loading prompt {agent_name}: {str(e)}")
        
        return render_template('langchain/prompts_manager.html', prompts=prompts)
    except Exception as e:
        logger.error(f"Error displaying prompts: {str(e)}")
        flash(f"Error displaying prompts: {str(e)}", "danger")
        return redirect('/dashboard')

@app.route('/prompts/view/<prompt_id>')
@login_required
def view_prompt(prompt_id):
    """View a prompt."""
    try:
        config = prompt_mgr.load_prompt(prompt_id)
        if not config:
            flash(f"Prompt {prompt_id} not found", "danger")
            return redirect('/prompts')
        
        # Add ID to config
        config['id'] = prompt_id
        
        return render_template('langchain/prompt_view.html', prompt=config)
    except Exception as e:
        logger.error(f"Error viewing prompt {prompt_id}: {str(e)}")
        flash(f"Error viewing prompt {prompt_id}: {str(e)}", "danger")
        return redirect('/prompts')

@app.route('/prompts/edit/<prompt_id>')
@login_required
def edit_prompt(prompt_id):
    """Edit a prompt."""
    try:
        config = prompt_mgr.load_prompt(prompt_id)
        if not config:
            flash(f"Prompt {prompt_id} not found", "danger")
            return redirect('/prompts')
        
        # Add ID to config
        config['id'] = prompt_id
        
        return render_template('langchain/prompt_edit.html', prompt=config)
    except Exception as e:
        logger.error(f"Error editing prompt {prompt_id}: {str(e)}")
        flash(f"Error editing prompt {prompt_id}: {str(e)}", "danger")
        return redirect('/prompts')

@app.route('/monitor_interview')
@login_required
def monitor_interview():
    """Monitor interviews in real-time."""
    try:
        # Load active sessions from Discussion service
        active_sessions = []
        
        if discussion_service:
            session_ids = discussion_service.get_session_ids()
            
            for session_id in session_ids:
                try:
                    session = discussion_service.get_session(session_id)
                    if session:
                        # Only show sessions in the last 24 hours
                        created_at = session.get('created_at')
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.datetime.fromisoformat(created_at)
                            except ValueError:
                                created_at = None
                        
                        if created_at:
                            now = datetime.datetime.now()
                            age = now - created_at
                            if age.days < 1:  # Less than 24 hours old
                                active_sessions.append(session)
                except Exception as e:
                    logger.error(f"Error loading session {session_id}: {str(e)}")
        
        return render_template('langchain/monitor_interview.html', sessions=active_sessions)
    except Exception as e:
        logger.error(f"Error displaying monitor page: {str(e)}")
        flash(f"Error displaying monitor page: {str(e)}", "danger")
        return redirect('/dashboard')

@app.route('/monitor_interview/<session_id>')
@login_required
def monitor_interview_session(session_id):
    """Monitor a specific interview session."""
    try:
        if not discussion_service:
            flash("Discussion service not available", "danger")
            return redirect('/monitor_interview')
        
        session = discussion_service.get_session(session_id)
        if not session:
            flash(f"Session {session_id} not found", "danger")
            return redirect('/monitor_interview')
        
        # Get guide details
        guide_id = session.get('guide_id')
        guide = None
        if guide_id:
            guide = discussion_service.get_guide(guide_id)
        
        # Prepare observer state if available
        observer_state = None
        if observer_service:
            try:
                observer_state = observer_service.get_state(session_id)
            except Exception as e:
                logger.error(f"Error getting observer state: {str(e)}")
        
        return render_template('langchain/monitor_session.html', 
                              session=session,
                              guide=guide,
                              observer_state=observer_state)
    except Exception as e:
        logger.error(f"Error monitoring session {session_id}: {str(e)}")
        flash(f"Error monitoring session {session_id}: {str(e)}", "danger")
        return redirect('/monitor_interview')

@app.route('/interview_details/<session_id>')
@login_required
def interview_details(session_id):
    """Show interview details."""
    return redirect(f'/session/{session_id}')

# ------ Discussion Guide Routes ------

@app.route('/discussion_guides', methods=['GET'])
@login_required
def discussion_guides_list():
    """Show all discussion guides."""
    if not discussion_service:
        flash("Discussion service not available", "danger")
        return redirect('/dashboard')
    
    # Redirect to the interview archive for now
    return redirect('/interview_archive')

@app.route('/discussion_guide/<guide_id>', methods=['GET'])
@login_required
def discussion_guide_details(guide_id):
    """Show discussion guide details."""
    if not discussion_service:
        flash("Discussion service not available", "danger")
        return redirect('/dashboard')
    
    guide = discussion_service.get_guide(guide_id)
    if not guide:
        flash(f"Discussion guide not found: {guide_id}", "danger")
        return redirect('/discussion_guides')
    
    return render_template('langchain/discussion_guide.html', guide=guide)

@app.route('/session/<session_id>', methods=['GET'])
@login_required
def session_details(session_id):
    """Show session details."""
    if not discussion_service:
        flash("Discussion service not available", "danger")
        return redirect('/dashboard')
    
    session = discussion_service.get_session(session_id)
    if not session:
        flash(f"Session not found: {session_id}", "danger")
        return redirect('/interview_archive')
    
    # Get guide details
    guide_id = session.get('guide_id')
    guide = None
    if guide_id:
        guide = discussion_service.get_guide(guide_id)
    
    return render_template('langchain/session_details.html', session=session, guide=guide)

# ------ Main Entry Point ------

if __name__ == '__main__':
    print(f"Starting DARIA Interview API on port {args.port}")
    print(f"Health check endpoint: http://127.0.0.1:{args.port}/api/health")
    print(f"Interview start endpoint: http://127.0.0.1:{args.port}/api/interview/start")
    print(f"Monitor interviews: http://127.0.0.1:{args.port}/monitor_interview")
    
    socketio.run(app, host='0.0.0.0', port=args.port, debug=args.debug) 