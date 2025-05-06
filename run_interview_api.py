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
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_cors import CORS
import yaml
import requests
import subprocess
import time
from langchain_features.services.interview_service import InterviewService
from langchain_features.services.interview_agent import InterviewAgent
from langchain_features.services.discussion_service import DiscussionService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Parse arguments
parser = argparse.ArgumentParser(description='Run DARIA Interview API')
parser.add_argument('--port', type=int, default=5010, help='Port to run the server on')
parser.add_argument('--use-langchain', action='store_true', help='Use LangChain for interviews')
args = parser.parse_args()

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

# Enable CORS with extended headers support
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
logger.info("CORS enabled for all origins with extended header support")

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

if use_langchain:
    try:
        interview_service = InterviewService(data_dir=str(DATA_DIR))
        logger.info("LangChain interview service initialized successfully")
        
        discussion_service = DiscussionService(data_dir=str(DATA_DIR))
        logger.info("Discussion service initialized successfully")
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
        # Check if audio service is running
        tts_service_running = False
        stt_service_running = False
        
        try:
            # Check if port 5015 is open (TTS service)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            tts_result = s.connect_ex(('localhost', 5015))
            s.close()
            
            # Check if port 5016 is open (STT service)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            stt_result = s.connect_ex(('localhost', 5016))
            s.close()
            
            if tts_result == 0:
                # Port is open, TTS service might be running
                tts_service_running = True
                
            if stt_result == 0:
                # Port is open, STT service might be running
                stt_service_running = True
                
            # Try to verify services by calling their health endpoints
            if tts_service_running or stt_service_running:
                if tts_service_running:
                    try:
                        tts_response = requests.get('http://localhost:5015/health', timeout=1)
                        tts_service_running = tts_response.status_code == 200
                    except:
                        pass
                        
                if stt_service_running:
                    try:
                        stt_response = requests.get('http://localhost:5016/health', timeout=1)
                        stt_service_running = stt_response.status_code == 200
                    except:
                        pass
        except:
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
                return jsonify({
                    'success': False,
                    'error': f"TTS service returned error: {response.status_code}"
                }), response.status_code
                
        except Exception as e:
            logger.error(f"Error forwarding to TTS service: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"Error in text_to_speech_elevenlabs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
                    voice_id = request.args.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
                    accepted = request.args.get('accepted', 'false').lower() == 'true'
                    
                    if not accepted:
                        # Show terms acceptance page first
                        return render_template('langchain/session_terms.html', 
                                              session_id=interview_id, 
                                              guide=guide, 
                                              name=name, 
                                              email=email,
                                              voice_id=voice_id)
                    
                    # Update participant info if provided
                    if name or email:
                        interviewee_data = session.get('interviewee', {})
                        if name:
                            interviewee_data['name'] = name
                        if email:
                            interviewee_data['email'] = email
                            
                        discussion_service.update_session(interview_id, {
                            'interviewee': interviewee_data
                        })
                    
                    # Show the participant view
                    return render_template('langchain/session_remote.html', 
                                          session=session, 
                                          guide=guide, 
                                          session_id=interview_id,
                                          voice_id=voice_id)
                
                # Otherwise show the researcher view
                return render_template('langchain/session_conduct.html', 
                                      session=session, 
                                      guide=guide, 
                                      session_id=interview_id)
        
        # If we get here, try treating it as a legacy interview
        logger.info(f"Join interview request for ID: {interview_id}")
        
        # Check if interview session exists
        interview_file = os.path.join(DATA_DIR, f"{interview_id}.json")
        
        if os.path.exists(interview_file):
            # Read the interview details
            with open(interview_file, 'r') as f:
                interview_data = json.load(f)
            
            # Check if it's a remote participant view
            remote = request.args.get('remote', 'false').lower() == 'true'
            if remote:
                # Get participant info from query parameters
                name = request.args.get('name', '')
                email = request.args.get('email', '')
                voice_id = request.args.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')
                accepted = request.args.get('accepted', 'false').lower() == 'true'
                
                if not accepted:
                    # Show terms acceptance page
                    return render_template('langchain/interview_terms.html', 
                                          interview_id=interview_id, 
                                          interview=interview_data, 
                                          name=name, 
                                          email=email,
                                          voice_id=voice_id)
                
                # Show the participant view
                return render_template('langchain/interview_session.html', 
                                      interview=interview_data, 
                                      interview_id=interview_id,
                                      voice_id=voice_id,
                                      remote=True)
            else:
                # Show the moderator/research view
                return render_template('langchain/interview_session.html', 
                                      interview=interview_data, 
                                      interview_id=interview_id,
                                      remote=False)
        else:
            logger.warning(f"Interview not found: {interview_id}")
            flash("Interview not found or has expired", "danger")
            return redirect('/dashboard')
    
    except Exception as e:
        logger.error(f"Error joining interview: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect('/dashboard')

# ------ UI Routes ------

@app.route('/')
def home():
    """Redirect to dashboard."""
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    """Render dashboard page."""
    return render_template('langchain/dashboard.html')

@app.route('/interview_setup')
def interview_setup():
    """Render interview setup page."""
    return render_template('langchain/interview_setup.html')

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
    """Monitor interviews page."""
    return render_template('langchain/monitor_interview_list.html')

@app.route('/interview_details/<session_id>')
def interview_details(session_id):
    """Show details for a specific interview."""
    interview_data = load_interview(session_id)
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
        
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'redirect_url': f"/session/{session_id}"
        })
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/<session_id>/add_message', methods=['POST'])
def add_session_message(session_id):
    """Add a message to a session."""
    if not discussion_service:
        return jsonify({'success': False, 'error': 'Discussion service not available'}), 500
    
    try:
        data = request.json
        message = data.get('message', {})
        
        if not message or 'content' not in message or 'role' not in message:
            return jsonify({'success': False, 'error': 'Invalid message data'}), 400
        
        # First, add the user's message
        success = discussion_service.add_message(session_id, message)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to add message'}), 500
        
        # If this is a user message, automatically generate an AI response
        if message['role'] == 'user':
            # Get the session
            session = discussion_service.get_session(session_id)
            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
            
            # Get the guide
            guide_id = session.get('guide_id')
            guide = discussion_service.get_guide(guide_id) if guide_id else None
            
            # Get the messages to build context
            messages = session.get('messages', [])
            
            # Generate AI response
            ai_response = ""
            if interview_service:
                try:
                    # Use the interview prompt from the guide if available
                    prompt = guide.get('interview_prompt', '') if guide else ''
                    
                    # Build conversation history
                    conversation = []
                    for msg in messages[-10:]:  # Use last 10 messages for context
                        conversation.append({
                            'role': msg.get('role', 'user'),
                            'content': msg.get('content', '')
                        })
                    
                    # Generate response using LangChain
                    ai_response = interview_service.generate_response(
                        messages=conversation,
                        prompt=prompt
                    )
                except Exception as e:
                    logger.error(f"Error generating AI response: {str(e)}")
                    ai_response = "I'm having trouble processing that. Could you please rephrase or ask another question?"
            else:
                # Fallback simple response
                ai_response = "Thank you for sharing. That's very insightful. Can you tell me more about your experiences?"
            
            # Add AI response to the session
            ai_message = {
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            discussion_service.add_message(session_id, ai_message)
            logger.info(f"Added AI response to session {session_id}")
            
            # Return success with the AI response
            return jsonify({
                'success': True,
                'message': ai_response
            })
        
        # If not a user message, just return success
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
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
            return render_template('error.html', error="Discussion guide not found"), 404
        
        sessions = discussion_service.list_guide_sessions(guide_id)
        return render_template('langchain/discussion_guide.html', guide=guide, sessions=sessions, guide_id=guide_id)
    except Exception as e:
        logger.error(f"Error loading discussion guide page: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/session/<session_id>', methods=['GET'])
def session_details(session_id):
    """Show the interview session details page."""
    try:
        if not discussion_service:
            return redirect('/interview_details/' + session_id)  # Fallback to old view if not available
        
        session = discussion_service.get_session(session_id)
        if not session:
            return render_template('error.html', error="Session not found"), 404
        
        guide_id = session.get('guide_id')
        guide = discussion_service.get_guide(guide_id) if guide_id else None
        
        return render_template('langchain/session.html', session=session, guide=guide, session_id=session_id)
    except Exception as e:
        logger.error(f"Error loading session page: {str(e)}")
        return render_template('error.html', error=str(e))

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

# Start the app
if __name__ == '__main__':
    print(f"Starting minimal DARIA Interview API on port {args.port}")
    print(f"Health check endpoint: http://127.0.0.1:{args.port}/api/health")
    print(f"Interview start endpoint: http://127.0.0.1:{args.port}/api/interview/start")
    print(f"Monitor interviews: http://127.0.0.1:{args.port}/monitor_interview")
    app.run(host='0.0.0.0', port=args.port, debug=True) 