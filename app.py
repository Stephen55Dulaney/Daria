import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, current_app
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv
import tempfile
from io import BytesIO
import wave
import numpy as np
import uuid
import json
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime, timedelta
from pathlib import Path
from daria_interview_tool.vector_store import InterviewVectorStore
import traceback
import logging
from markupsafe import Markup
from openai import OpenAI
import markdown  # Added this import since it's used in the markdown filter
from daria_interview_tool.google_ai import GeminiPersonaGenerator
from daria_interview_tool.daria_resources import get_interview_prompt, BASE_SYSTEM_PROMPT, INTERVIEWER_BEST_PRACTICES
from langchain.schema import SystemMessage, HumanMessage
from langchain.vectorstores import VectorStore
import MySQLdb
from werkzeug.utils import secure_filename
import re
import markdown2
from daria_interview_tool.semantic_analysis import SemanticAnalyzer
from sklearn.metrics.pairwise import cosine_similarity
from daria_interview_tool.processed_interview_store import ProcessedInterviewStore
import sys
from daria_interview_tool.discovery_gpt import DiscoveryGPT
from asgiref.sync import async_to_sync
from daria_interview_tool.persona_gpt import generate_persona_from_interviews
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont
import random

# Import the jarvis_wrapper module
import templates.jarvis_wrapper as jarvis_wrapper

# Configure logging with a more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

# Global variables
vector_store = None

# Initialize Flask app
app = Flask(__name__, static_url_path='')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['INTERVIEWS_DIR'] = 'interviews/raw'
app.config['VECTOR_STORE_PATH'] = 'vector_store'
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')  # Add OpenAI API key configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import and register the memory companion blueprint
try:
    from api_services.memory_companion_service import memory_companion_bp
    app.register_blueprint(memory_companion_bp)
    print("Successfully registered Memory Companion blueprint")
except Exception as e:
    print(f"Failed to register Memory Companion blueprint: {str(e)}")
    # Continue without the memory companion functionality

# Global directories
interview_dirs = ['interviews', 'interviews/raw', 'interviews/processed']

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database models for the research survey functionality
class ResearchSurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)

# Create database tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://localhost:5175"],  # React dev server ports
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    },
    r"/annotated-transcript/*": {
        "origins": ["http://localhost:5174", "http://localhost:5175"],
        "methods": ["GET"],
        "allow_headers": ["Content-Type"]
    },
    r"/text_to_speech": {"origins": ["http://localhost:5174", "http://localhost:5175"]},
    r"/process_audio": {"origins": ["http://localhost:5174", "http://localhost:5175"]},
    r"/*": {"origins": ["http://localhost:5175"]}  # Allow all routes for the new frontend port
})

# Configure SocketIO with CORS
socketio = SocketIO(app, 
    cors_allowed_origins=["http://localhost:5173", "http://localhost:5175"],
    async_mode='eventlet',
    logger=True,
    engineio_logger=True
)

load_dotenv()

# Add markdown filter
@app.template_filter('markdown')
def markdown_filter(text):
    return Markup(markdown.markdown(text))

# Load environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Store audio responses temporarily
TEMP_DIR = tempfile.mkdtemp()
AUDIO_RESPONSES = {}

# Available voices
AVAILABLE_VOICES = {
    "rachel": "EXAVITQu4vr4xnSDxMaL",  # Rachel - Professional Female
    "antoni": "ErXwobaYiN019PkySvjV",  # Antoni - Female
    "elli": "MF3mGyEYCl7XYWbV9V6O",   # Elli - Female
    "domi": "AZnzlk1XvdvUeBnXmlld",    # Domi - Female
}

# Store interview prompts and conversations
interview_prompts = {}
conversations = {}

# Initialize TestProject for audio testing
interview_prompts['TestProject'] = {
    'prompt': 'This is a test project prompt for audio recording and transcription tests.',
    'form_data': {'interviewee': {'name': 'Test User'}}
}
conversations['TestProject'] = {
    'messages': [
        {"role": "system", "content": "You are conducting an interview about TestProject."},
        {"role": "assistant", "content": "Daria: Hello, this is Daria. How can I help you today?"}
    ]
}

# Initialize GreenEggsAndHam project
interview_prompts['GreenEggsAndHam'] = {
    'prompt': 'This is an interview about the GreenEggsAndHam project, focusing on the user experience of reading Dr. Seuss books.',
    'form_data': {'interviewee': {'name': 'Sam I Am'}}
}
conversations['GreenEggsAndHam'] = {
    'messages': [
        {"role": "system", "content": "You are conducting an interview about the GreenEggsAndHam project, focusing on user preferences for breakfast foods."},
        {"role": "assistant", "content": "Daria: Hello, I'm Daria. I'd like to ask you some questions about your experience with Green Eggs and Ham. Let's begin our interview when you're ready."}
    ]
}

# Add after the existing configuration
INTERVIEWS_DIR = Path('interviews/raw')
INTERVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# Add after INTERVIEWS_DIR definition
PERSONAS_DIR = Path('personas')
PERSONAS_DIR.mkdir(exist_ok=True)

# Add maximum rounds constant
MAX_ROUNDS = 3

# Initialize vector store
app.vector_store = None

# Initialize semantic analyzer
semantic_analyzer = SemanticAnalyzer()

# Add emotion icon filter
@app.template_filter('emotion_icon')
def emotion_icon_filter(emotion):
    """Convert emotion name to emoji icon."""
    emotion_icons = {
        'happy': '😊',
        'sad': '😢',
        'angry': '😠',
        'neutral': '😐',
        'excited': '🤩',
        'frustrated': '😤',
        'confused': '😕',
        'anxious': '😰',
        'satisfied': '😌',
        'disappointed': '😞'
    }
    return emotion_icons.get(emotion.lower(), '😐')

# Helper functions
def list_interviews():
    """List all saved interviews."""
    try:
        logger.info("Listing saved interviews...")
        interviews_dir = os.path.join(app.root_path, 'interviews', 'raw')
        
        # Create directory if it doesn't exist
        if not os.path.exists(interviews_dir):
            os.makedirs(interviews_dir)
            logger.info("Created interviews directory")
            return []
        
        interviews = []
        for filename in os.listdir(interviews_dir):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(interviews_dir, filename)
            try:
                with open(file_path, 'r') as f:
                    interview = json.load(f)
                    
                # Extract interview ID from filename
                interview_id = os.path.splitext(filename)[0]
                
                # Create summary dictionary using transcript_name directly
                summary = {
                    'id': interview_id,
                    'title': interview.get('title', 'Untitled Interview'),
                    'type': interview.get('interview_type', 'Interview'),
                    'created_at': interview.get('created_at', datetime.now().isoformat()),
                    'participant_name': interview.get('transcript_name', 'Untitled Interview'),
                    'project_name': interview.get('project_name', 'Unassigned'),
                    'transcript_name': interview.get('transcript_name', ''),
                    'metadata': interview.get('metadata', {}),
                    'has_analysis': bool(interview.get('analysis')),
                    'content_preview': _get_content_preview(interview)
                }
                
                interviews.append(summary)
                logger.info(f"Added interview: {interview_id} - {summary['participant_name']}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {filename}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue
        
        # Sort by date, most recent first
        interviews.sort(key=lambda x: x['created_at'], reverse=True)
        return interviews
        
    except Exception as e:
        logger.error(f"Error listing interviews: {str(e)}")
        return []

def _get_content_preview(interview: dict, max_length: int = 200) -> str:
    """Get a preview of the interview content, showing only participant responses."""
    try:
        # Try to get content from chunks first
        chunks = interview.get('chunks', [])
        if chunks:
            # Get the first few non-empty participant chunks
            preview_texts = []
            for chunk in chunks:
                # Skip if no text or if speaker is interviewer/researcher
                text = chunk.get('text', '').strip()
                speaker = chunk.get('speaker', '').lower()
                if not text or 'interviewer' in speaker or 'researcher' in speaker:
                    continue
                    
                preview_texts.append(text)
                if len(' '.join(preview_texts)) >= max_length:
                    break
            
            if preview_texts:
                preview = ' '.join(preview_texts)
                if len(preview) > max_length:
                    preview = preview[:max_length] + '...'
                return preview
        
        # Fallback to transcript field
        transcript = interview.get('transcript', '').strip()
        if transcript:
            # Try to filter out interviewer lines from transcript
            lines = transcript.split('\n')
            participant_lines = []
            for line in lines:
                if ': ' in line:
                    speaker, text = line.split(': ', 1)
                    if not any(role in speaker.lower() for role in ['interviewer', 'researcher']):
                        participant_lines.append(text.strip())
                elif line.strip():  # If no speaker prefix, include the line
                    participant_lines.append(line.strip())
                    
            if participant_lines:
                preview = ' '.join(participant_lines)
                if len(preview) > max_length:
                    return preview[:max_length] + '...'
                return preview
            
        return 'No participant responses available'
        
    except Exception as e:
        logger.error(f"Error getting content preview: {str(e)}")
        return 'Error getting preview'

def get_emotion_icon(emotion):
    """Get the appropriate emoji icon for an emotion."""
    emotion_icons = {
        'Happy': '😊',
        'Sad': '😢',
        'Angry': '😠',
        'Neutral': '😐',
        'Excited': '🤩',
        'Frustrated': '😤',
        'Confused': '😕'
    }
    return emotion_icons.get(emotion, '😐')

def load_interview(interview_id):
    """Load interview data from JSON file."""
    file_path = INTERVIEWS_DIR / f"{interview_id}.json"
    if not file_path.exists():
        return None
    with open(file_path) as f:
        return json.load(f)

def delete_interview(interview_id):
    """Delete an interview from the system."""
    try:
        # Delete the JSON file
        file_path = INTERVIEWS_DIR / f"{interview_id}.json"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted interview file: {file_path}")
        
        # Remove from vector store if available
        if vector_store:
            try:
                vector_store.remove_interview(interview_id)
                vector_store.save_vector_store()
                logger.info(f"Removed interview {interview_id} from vector store")
            except Exception as e:
                logger.error(f"Error removing interview from vector store: {str(e)}")
                logger.error(traceback.format_exc())
        
        return True
    except Exception as e:
        logger.error(f"Error deleting interview: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def save_interview_data(project_name, interview_type, transcript, analysis=None, form_data=None):
    """Save interview data to a JSON file using the new schema."""
    try:
        # Generate unique interview ID if not provided
        interview_id = str(uuid.uuid4())
        
        # Process transcript into chunks if it's a string
        transcript_chunks = []
        if isinstance(transcript, str):
            # Split transcript into chunks by speaker
            lines = transcript.split('\n')
            current_chunk = {
                'text': '', 
                'speaker': '', 
                'start_time': None, 
                'end_time': None,
                'metadata': {
                    'emotion': None,
                    'theme': [],
                    'insightTag': []
                }
            }
            
            for line in lines:
                if ': ' in line:  # New speaker
                    if current_chunk['text']:  # Save previous chunk
                        # Process semantic data for the chunk before saving
                        semantic_data = analyze_chunk_semantics(current_chunk['text'])
                        current_chunk['metadata'].update(semantic_data)
                        transcript_chunks.append(current_chunk)
                        current_chunk = {
                            'text': '', 
                            'speaker': '', 
                            'start_time': None, 
                            'end_time': None,
                            'metadata': {
                                'emotion': None,
                                'theme': [],
                                'insightTag': []
                            }
                        }
                    
                    speaker, text = line.split(': ', 1)
                    current_chunk['speaker'] = speaker
                    current_chunk['text'] = text
                else:  # Continuation of previous speaker
                    current_chunk['text'] += f"\n{line}"
            
            if current_chunk['text']:  # Save last chunk
                # Process semantic data for the final chunk
                semantic_data = analyze_chunk_semantics(current_chunk['text'])
                current_chunk['metadata'].update(semantic_data)
                transcript_chunks.append(current_chunk)
        else:
            transcript_chunks = transcript  # Assume pre-chunked format

        # Generate title based on participant name and first response
        title = None
        participant_name = None
        first_response = None

        # Try to get participant name from form data first
        if form_data and form_data.get('interviewee', {}).get('name'):
            participant_name = form_data['interviewee']['name']
        
        # If no name in form data, try to extract from transcript
        if not participant_name:
            for chunk in transcript_chunks:
                speaker = chunk.get('speaker', '').strip()
                # Skip system messages or empty speakers
                if not speaker or speaker.lower() in ['system', 'assistant', 'interviewer', 'daria']:
                    continue
                # Extract name from common formats like "[Name]" or "Name:"
                if '[' in speaker and ']' in speaker:
                    participant_name = speaker[speaker.find('[')+1:speaker.find(']')]
                    break
                elif speaker.endswith(':'):
                    participant_name = speaker[:-1].strip()
                    break
                else:
                    participant_name = speaker
                    break
        
        # If still no name, use "Anonymous"
        if not participant_name:
            participant_name = "Anonymous"

        # Get interview date
        interview_date = None
        if form_data and form_data.get('metadata', {}).get('interviewDate'):
            interview_date = form_data['metadata']['interviewDate']
        else:
            interview_date = datetime.now().strftime('%Y-%m-%d')

        # Format the title
        if interview_type.lower() != 'interview':
            title = f"{interview_type} with {participant_name} - {interview_date}"
        else:
            title = f"Interview with {participant_name} - {interview_date}"

        # Process metadata
        metadata = {
            'participant': {
                'name': participant_name,
                'role': form_data.get('role', '') if form_data else '',
                'department': form_data.get('department', '') if form_data else '',
                'experience_level': form_data.get('experience_level', '') if form_data else ''
            },
            'researcher': {
                'name': form_data.get('author', 'system') if form_data else 'system',
                'email': form_data.get('researcher_email', '') if form_data else ''
            },
            'session': {
                'date': interview_date,
                'duration': None,  # Will be calculated from chunks if available
                'format': 'text',
                'language': 'en'
            }
        }

        # Calculate duration if timestamps are available
        if transcript_chunks and all(chunk.get('start_time') and chunk.get('end_time') for chunk in transcript_chunks):
            try:
                start = min(float(chunk['start_time']) for chunk in transcript_chunks)
                end = max(float(chunk['end_time']) for chunk in transcript_chunks)
                metadata['session']['duration'] = end - start
            except (ValueError, TypeError):
                pass

        # Prepare interview data according to new schema
        interview_data = {
            'id': interview_id,
            'type': interview_type,
            'project_id': None,  # To be set when project system is implemented
            'project_name': project_name or 'Unassigned',
            'title': title,
            'created_at': datetime.now().isoformat(),
            'created_by': metadata['researcher'].get('email', 'system'),
            'status': 'draft',
            'metadata': metadata,
            'chunks': transcript_chunks,
            'analysis': analysis,
            'tags': form_data.get('tags', []) if form_data else []
        }
        
        # Save to JSON file
        filename = f'interviews/{interview_id}.json'
        os.makedirs('interviews', exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        logger.info(f"Saved interview data to {filename}")
        logger.debug(f"Interview data: {interview_data}")
        
        return interview_id
        
    except Exception as e:
        logger.error(f"Error saving interview data: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def analyze_chunk_semantics(text):
    """Analyze the semantic content of a chunk using our semantic analyzer."""
    try:
        # Use semantic analyzer to get analysis
        analysis = semantic_analyzer.analyze_chunk(text)
        metadata = analysis['metadata']
        
        # Map the emotion and sentiment to our simplified categories
        emotion_label = metadata['emotion']['primary']['label']
        sentiment_label = metadata['sentiment']['label']
        
        # Determine overall sentiment category
        if sentiment_label == 'POS':
            sentiment = 'positive'
        elif sentiment_label == 'NEG':
            sentiment = 'negative'
        elif emotion_label in ['anger', 'annoyance', 'disappointment']:
            sentiment = 'frustration'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'themes': metadata['themes'],
            'insightTag': metadata['insight_tags'],
            'relatedFeature': metadata['related_feature'],
            'emotion': {
                'primary': metadata['emotion']['primary'],
                'secondary': metadata['emotion']['secondary'],
                'confidence': metadata['emotion_confidence']
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing chunk semantics: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'sentiment': 'neutral',
            'themes': [],
            'insightTag': [],
            'relatedFeature': None,
            'emotion': {
                'primary': {'label': 'neutral', 'score': 0.0},
                'secondary': [],
                'confidence': 0.0
            }
        }

def create_openai_client():
    """Create and configure OpenAI client."""
    try:
        logger.info("Creating OpenAI client")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not found in environment")
            return None
            
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        logger.info("Successfully created OpenAI client")
        return client
        
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def extract_value(prompt, field_name, context):
    """Extract a value from the interview prompt based on the field name and context."""
    try:
        # Find the appropriate section based on context
        if context == 'researcher':
            section_start = prompt.find('#Researcher Information:')
        elif context == 'interviewee':
            section_start = prompt.find('#Interviewee Information:')
        elif context == 'technology':
            section_start = prompt.find('#Technology Usage:')
        else:
            return ''

        if section_start == -1:
            return ''

        # Find the end of the section
        section_end = prompt.find('#', section_start + 1)
        if section_end == -1:
            section_end = len(prompt)

        # Extract the section
        section = prompt[section_start:section_end]

        # Find the field in the section
        field_start = section.find(field_name)
        if field_start == -1:
            return ''

        # Find the end of the line
        line_end = section.find('\n', field_start)
        if line_end == -1:
            line_end = len(section)

        # Extract the value
        value = section[field_start + len(field_name):line_end].strip()
        return value
    except Exception as e:
        logger.error(f"Error extracting value for {field_name}: {str(e)}")
        return ''

# Initialize vector store
try:
    logger.info("Initializing vector store...")
    vector_store = InterviewVectorStore(openai_api_key=OPENAI_API_KEY)
    # Load all existing interviews into the vector store
    interviews = []
    raw_interviews_dir = os.path.join('interviews', 'raw')
    if os.path.exists(raw_interviews_dir):
        logger.info("Loading existing interviews into vector store...")
        for filename in os.listdir(raw_interviews_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(raw_interviews_dir, filename)) as f:
                        interview = json.load(f)
                        # Ensure all required fields are present
                        interview.setdefault('date', datetime.now().isoformat())
                        interview.setdefault('project_name', 'Unknown Project')
                        interview.setdefault('interview_type', 'Unknown Type')
                        interviews.append(interview)
                except Exception as e:
                    logger.error(f"Error loading interview {filename}: {str(e)}")
                    continue
        
        if interviews:
            logger.info(f"Adding {len(interviews)} interviews to vector store...")
            vector_store.add_interviews(interviews)
            vector_store.save_vector_store()
            logger.info("Vector store initialized successfully")
        else:
            logger.warning("No interviews found to load into vector store")
    else:
        logger.warning("Raw interviews directory not found")
except Exception as e:
    logger.error(f"Error initializing vector store: {str(e)}")
    logger.error(traceback.format_exc())
    vector_store = None

def save_persona(project_name, content, selected_elements):
    """
    Save a generated persona to disk
    
    Args:
        project_name (str): Name of the project
        content (str): JSON string containing persona data
        selected_elements (list): List of selected persona elements
        
    Returns:
        dict: Saved persona data
    """
    try:
        # Create personas directory if it doesn't exist
        os.makedirs('personas', exist_ok=True)
        
        # Generate unique ID for persona
        persona_id = str(uuid.uuid4())
        
        # Parse content back to dict if it's a JSON string
        if isinstance(content, str):
            content = json.loads(content)
            
        # Create persona data structure
        persona_data = {
            'id': persona_id,
            'project_name': project_name,
            'content': content,
            'selected_elements': selected_elements,
            'created_at': datetime.now().isoformat()
        }
        
        # Save to file
        filename = f'personas/{project_name}_{persona_id}.json'
        with open(filename, 'w') as f:
            json.dump(persona_data, f, indent=2)
            
        return persona_data
        
    except Exception as e:
        logger.error(f"Error saving persona: {str(e)}")
        raise Exception(f"Failed to save persona: {str(e)}")

def list_personas(limit=None):
    """List all saved personas, optionally limited to a specific number."""
    personas = []
    if PERSONAS_DIR.exists():
        for file_path in PERSONAS_DIR.glob('*.json'):
            with open(file_path) as f:
                persona = json.load(f)
                # Use date as last_modified if last_modified is not present
                if 'last_modified' not in persona:
                    persona['last_modified'] = persona.get('date', datetime.now().isoformat())
                personas.append(persona)
    
    # Sort personas by creation date, most recent first
    personas.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    
    if limit:
        personas = personas[:limit]
    
    return personas

def load_persona(persona_id: str) -> dict:
    """Load a specific persona by ID."""
    file_path = PERSONAS_DIR / f"{persona_id}.json"
    if not file_path.exists():
        return None
    with open(file_path) as f:
        return json.load(f)

def load_interviews(project_name):
    """Load all interviews for a specific project."""
    interviews = []
    if INTERVIEWS_DIR.exists():
        for file_path in INTERVIEWS_DIR.glob('*.json'):
            try:
                with open(file_path) as f:
                    interview = json.load(f)
                    if interview.get('project_name') == project_name:
                        # Ensure all required fields are present
                        interview.setdefault('date', datetime.now().isoformat())
                        interview.setdefault('transcript', '')
                        interview.setdefault('analysis', '')
                        interviews.append(interview)
            except Exception as e:
                logger.error(f"Error loading interview {file_path}: {str(e)}")
                continue
    return sorted(interviews, key=lambda x: x.get('date', ''), reverse=True)

@app.route('/chat')
def chat_page():
    """Chat page route"""
    project_name = request.args.get('project_name', '')
    prompt = interview_prompts.get(project_name, '') if project_name else ''
    return render_template('interview.html', project_name=project_name, prompt=prompt)

def list_projects():
    """List all active projects."""
    try:
        projects = []
        PROJECTS_DIR = Path('projects')
        if PROJECTS_DIR.exists():
            for file in sorted(PROJECTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if all(key in data for key in ['id', 'name', 'description', 'status']):
                            # Only include active projects
                            if data.get('status', '').lower() == 'active':
                                projects.append(data)
                except Exception as e:
                    logger.error(f"Error loading project {file}: {str(e)}")
                    continue
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return []

@app.route('/')
def home():
    """Home page."""
    try:
        # Get projects
        projects = list_projects()
        
        # Get recent interviews
        recent_interviews = []
        INTERVIEWS_DIR = Path('interviews')
        if INTERVIEWS_DIR.exists():
            for file in sorted(INTERVIEWS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if all(key in data for key in ['id', 'project_name', 'interview_type', 'date']):
                            recent_interviews.append(data)
                except Exception as e:
                    logger.error(f"Error loading interview {file}: {str(e)}")
                    continue
        
        # Get recent personas
        recent_personas = []
        PERSONAS_DIR = Path('personas')
        if PERSONAS_DIR.exists():
            for file in sorted(PERSONAS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        # Ensure all required fields are present
                        if 'id' not in data:
                            data['id'] = str(uuid.uuid4())
                        if 'created_at' not in data:
                            data['created_at'] = datetime.now().isoformat()
                        if 'project_name' not in data:
                            data['project_name'] = 'Unknown Project'
                            # For Unknown Project items, set the ID to match the project name
                            # This helps with deletion
                            data['id'] = 'Unknown Project'
                        recent_personas.append(data)
                        logger.info(f"Loaded persona: {data.get('project_name')} with ID: {data.get('id')}")
                except Exception as e:
                    logger.error(f"Error loading persona {file}: {str(e)}")
                    continue
        
        # Get recent journey maps
        recent_journey_maps = []
        JOURNEY_MAPS_DIR = Path('journey_maps')
        if JOURNEY_MAPS_DIR.exists():
            for file in sorted(JOURNEY_MAPS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        # Ensure the data has all required fields
                        if 'id' not in data:
                            data['id'] = str(uuid.uuid4())
                        if 'created_at' not in data:
                            data['created_at'] = datetime.now().isoformat()
                        if 'project_name' not in data:
                            data['project_name'] = 'Unknown Project'
                            # For Unknown Project items, set the ID to match the project name
                            # This helps with deletion
                            data['id'] = 'Unknown Project'
                        recent_journey_maps.append(data)
                        logger.info(f"Loaded journey map: {data.get('project_name')} with ID: {data.get('id')}")
                except Exception as e:
                    logger.error(f"Error loading journey map {file}: {str(e)}")
                    continue
        
        return render_template('home.html',
                             projects=projects,
                             recent_interviews=recent_interviews,
                             recent_personas=recent_personas,
                             recent_journey_maps=recent_journey_maps)
    except Exception as e:
        logger.error(f"Error loading home page: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading home page', 'error')
        return render_template('home.html',
                             projects=[],
                             recent_interviews=[],
                             recent_personas=[],
                             recent_journey_maps=[])

@app.route('/new_interview')
def new_interview():
    """New interview page"""
    return render_template('config.html')

@app.route('/persona')
def persona():
    """Persona creation page"""
    try:
        # Get list of projects for dropdown
        projects = []
        project_names = set()

        # Check both interviews and interviews/raw directories
        interview_dirs = ['interviews', 'interviews/raw']
        
        for dir_path in interview_dirs:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(dir_path, filename)) as f:
                                interview = json.load(f)
                                project_name = interview.get('project_name')
                                if project_name:
                                    project_names.add(project_name)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding JSON from {filename}: {str(e)}")
                            continue
                        except Exception as e:
                            logger.error(f"Error reading file {filename}: {str(e)}")
                            continue
        
        # Convert to list of project objects
        projects = [{'id': name, 'name': name} for name in sorted(project_names) if name]
        
        logger.info(f"Found {len(projects)} projects for persona creation")
        return render_template('persona.html', projects=projects)
        
    except Exception as e:
        logger.error(f"Error in persona route: {str(e)}")
        logger.error(traceback.format_exc())
        # Return empty projects list if there's an error
        return render_template('persona.html', projects=[])

@app.route('/journey_map')
def journey_map():
    """Journey map creation page"""
    try:
        # Get list of projects with their IDs and names
        projects = []
        project_dict = {}
        
        # Check both raw and processed interview directories
        interview_dirs = ['interviews/raw', 'interviews/processed']
        
        for dir_path in interview_dirs:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(dir_path, filename)) as f:
                                interview = json.load(f)
                                project_name = interview.get('project_name')
                                if project_name and project_name not in project_dict:
                                    project_dict[project_name] = {
                                        'id': project_name,  # Use project name as ID for consistency
                                        'name': project_name
                                    }
                        except Exception as e:
                            logger.error(f"Error reading interview file {filename}: {str(e)}")
                            continue
        
        projects = list(project_dict.values())
        logger.info(f"Found {len(projects)} projects for journey map")
        
        return render_template('journey_map.html', 
                             projects=sorted(projects, key=lambda x: x['name']),
                             current_project=request.args.get('project', ''))
    except Exception as e:
        logger.error(f"Error in journey_map route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('journey_map.html', projects=[], current_project='')

@app.route('/save_interview', methods=['POST'])
def save_interview():
    """Save new interview configuration and generate prompt."""
    try:
        logger.info("=== save_interview endpoint called ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Log detailed information about the request
        if request.content_type and 'application/json' in request.content_type:
            logger.info("Request has correct JSON content type")
        else:
            logger.warning(f"Unexpected content type: {request.content_type}")
        
        # Get and log the raw data
        raw_data = request.get_data(as_text=True)
        logger.info(f"Raw request data: {raw_data[:200]}...")
        
        data = request.get_json()
        if data is None:
            logger.error("Failed to parse JSON data from request")
            return jsonify({'error': 'Invalid JSON data or content-type'}), 400
            
        logger.info(f"Parsed JSON data: {data}")
        
        # Required fields
        project_name = data.get('project_name')
        interview_type = data.get('interview_type')
        project_description = data.get('project_description')
        
        logger.info(f"Project name: {project_name}")
        logger.info(f"Interview type: {interview_type}")
        logger.info(f"Project description: {project_description[:50]}...")
        
        # Validate required fields
        missing_fields = []
        if not project_name:
            missing_fields.append('project_name')
        if not interview_type:
            missing_fields.append('interview_type')
        if not project_description:
            missing_fields.append('project_description')
            
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        # Get all the metadata fields
        metadata = {
            'participant': {
                'name': data.get('participant_name', 'Anonymous'),
                'role': data.get('role', ''),
                'experience_level': data.get('experience_level', ''),
                'department': data.get('department', '')
            },
            'session': {
                'date': datetime.now().isoformat(),
                'status': data.get('status', 'Draft')
            },
            'tags': data.get('tags', []),
            'emotion': data.get('emotion', 'Neutral'),
            'researcher': {
                'name': data.get('author', 'Unknown')
            }
        }

        logger.info(f"Prepared metadata: {metadata}")

        # Generate the interview prompt
        try:
            logger.info("Generating interview prompt...")
            interview_prompt = get_interview_prompt(interview_type, project_name, project_description)
            logger.info("Interview prompt generated successfully")
        except Exception as e:
            logger.error(f"Error generating interview prompt: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Failed to generate interview prompt'}), 500

        # Store the interview configuration
        interview_prompts[project_name] = {
            'prompt': interview_prompt,
            'metadata': metadata,
            'project_description': project_description,
            'type': interview_type
        }
        
        logger.info(f"Successfully stored interview configuration for project: {project_name}")
        
        # Create response with redirect URL
        redirect_url = url_for('interview', project_name=project_name)
        logger.info(f"Generated redirect URL: {redirect_url}")
        
        response_data = {
            'status': 'success',
            'message': 'Interview configuration saved successfully',
            'project_name': project_name,
            'redirect_url': redirect_url
        }
        
        logger.info(f"Returning success response: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error occurred: {str(e)}'}), 500

@app.route('/interview/<project_name>', methods=['GET', 'POST'])
def interview(project_name):
    try:
        if request.method == 'GET':
            # Check if the project exists in interview_prompts
            if project_name not in interview_prompts:
                logger.warning(f"Project {project_name} not found in interview_prompts")
                return redirect(url_for('new_interview'))
            
            # Get the prompt for this project
            prompt = interview_prompts[project_name]
            logger.info(f"Retrieved prompt for project: {project_name}")
            
            # Render the interview template
            return render_template('interview.html', project_name=project_name, prompt=prompt)
        else:  # POST request
            data = request.get_json()
            user_input = data.get('user_input', '')
            question_count = data.get('question_count', 0)
            is_follow_up = data.get('is_follow_up', False)
            
            logger.info(f"Processing interview POST for project: {project_name}")
            logger.info(f"Question count: {question_count}, Is follow-up: {is_follow_up}")
            logger.info(f"User input: {user_input[:50]}..." if len(user_input) > 50 else f"User input: {user_input}")
            
            # Create OpenAI client
            llm = create_openai_client()
            
            # Get the interview prompt
            prompt = interview_prompts.get(project_name)
            if not prompt:
                logger.error(f"Interview prompt not found for project: {project_name}")
                return jsonify({'error': 'Interview prompt not found'}), 404
            
            # Get the interview type and project description
            interview_type = prompt.get('type', 'Application Interview')
            project_description = prompt.get('project_description', '')
            
            # Check if we're near the end of the interview (after 3 main questions)
            # We add +1 because we're currently processing question_count, not the next one
            is_final_round = (question_count >= 3 and not is_follow_up)
            
            # Initialize conversation if it doesn't exist
            if project_name not in conversations:
                logger.info(f"Initializing new conversation for project: {project_name}")
                conversations[project_name] = {'messages': []}
            
            # Add the user's message to the conversation
            conversations[project_name]['messages'].append({"role": "user", "content": user_input})
            
            # Create an enhanced system prompt based on the original prompt
            # but with additional instruction for improved interview quality
            base_system_message = prompt.get('prompt', '')
            
            if is_final_round:
                # For the final round, use a concluding prompt
                system_message = f"""You are conducting a {interview_type} about {project_name}.

This is the FINAL question of the interview. Create a thoughtful concluding question that:
1. Asks the participant if there's anything else they'd like to share
2. Gently signals that the interview is coming to an end
3. Encourages any final thoughts or feedback
4. Maintains a professional and appreciative tone

Project context: {project_description}

DO NOT thank the participant for their time yet - this is just the final question."""

            else:
                # Add specific instruction based on question count and if it's a follow-up
                if is_follow_up:
                    system_message = f"""{base_system_message}

You are FOLLOWING UP on the previous question about {project_name}.
1. Ask ONE specific follow-up question based on their previous response
2. Dig deeper into an interesting point they mentioned
3. Do NOT change the topic - stay focused on what they just discussed
4. Keep your follow-up question concise and clear
5. NEVER repeat a question that has already been asked

Current question count: {question_count} of 3
Project context: {project_description}"""
                else:
                    system_message = f"""{base_system_message}

You are now asking question #{question_count + 1} of 3 about {project_name}.
1. Ask ONE specific, open-ended question related to {project_name}
2. NEVER repeat a question that has already been asked
3. Move to a new topic - don't ask about the same aspects covered in previous questions
4. Keep your question concise and clear (1-2 sentences maximum)
5. Do not include unnecessary preambles or explanations
6. Format as a direct question only

Current question count: {question_count + 1} of 3
Project context: {project_description}"""
            
            # Generate response
            response = llm.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    *conversations[project_name]['messages']
                ],
                temperature=0.7
            )
            
            # Add the assistant's response to the conversation
            assistant_response = response.choices[0].message.content
            conversations[project_name]['messages'].append({"role": "assistant", "content": assistant_response})
            
            # Check if this response contains a follow-up question
            # Look for key phrases that suggest it's a follow-up
            response_lower = assistant_response.lower()
            contains_follow_up = any(phrase in response_lower for phrase in [
                "could you expand", "tell me more", "can you elaborate", 
                "what specifically", "why did you", "how did you", 
                "can you provide", "would you mind", "follow up", "follow-up"
            ])
            
            # Check if we've reached the end of the interview
            should_end_interview = False
            if is_final_round:
                # This was the final question
                should_end_interview = True
            
            return jsonify({
                'response': assistant_response,
                'question_count': question_count + (0 if contains_follow_up or is_follow_up else 1),
                'is_follow_up': contains_follow_up,
                'should_stop_interview': should_end_interview
            })
            
    except Exception as e:
        logger.error(f"Error in interview route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        project_name = request.args.get('project_name')
        if not project_name:
            logger.error("Project name is required for process_audio")
            return jsonify({'error': 'Project name is required'}), 400

        if 'audio' not in request.files:
            logger.error("No audio file provided in request")
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        if not audio_file:
            logger.error("Empty audio file provided")
            return jsonify({'error': 'Empty audio file'}), 400

        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)
            logger.info(f"Audio saved to temporary file: {temp_audio.name}")
            
            # Process the audio file with OpenAI's Whisper API
            try:
                client = OpenAI()
                with open(temp_audio.name, 'rb') as audio:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio
                    )
                logger.info(f"Audio transcribed successfully: {transcription.text[:30]}...")
            except Exception as whisper_error:
                logger.error(f"Error transcribing audio with Whisper API: {str(whisper_error)}")
                return jsonify({'error': f'Transcription error: {str(whisper_error)}'}), 500

        # Clean up the temporary file
        os.unlink(temp_audio.name)
        logger.info("Temporary audio file deleted")

        # Get the saved interview prompt
        interview_prompt_data = interview_prompts.get(project_name)
        if not interview_prompt_data:
            logger.warning(f"Interview prompt not found for project: {project_name}. Using default prompt.")
            interview_prompt_data = {
                'prompt': f"You are conducting an interview about {project_name}. Ask relevant questions to understand the user's experience.",
                'form_data': {'interviewee': {'name': 'Anonymous'}}
            }

        # Extract form data for context
        form_data = interview_prompt_data.get('form_data', {})
        
        # Extract interview type from prompt or form data
        interview_type = form_data.get('interview_type', 'User Interview')
        if not interview_type:
            # Try to infer from the prompt text
            prompt_text = interview_prompt_data.get('prompt', '')
            if "Persona Interview" in prompt_text:
                interview_type = "Persona Interview"
            elif "Journey Map Interview" in prompt_text:
                interview_type = "Journey Map Interview"
            else:
                interview_type = "Application Interview"
        
        # Extract project description
        project_description = form_data.get('project_description', f"Project about {project_name}")
        
        # Extract participant details
        interviewee = form_data.get('interviewee', {})
        participant_name = interviewee.get('name', 'Anonymous')
        participant_role = interviewee.get('role', '')
        
        # Create a rich system message with all available context
        system_message = f"""You are Daria, an experienced UX researcher conducting a {interview_type} about {project_name}.
        
Project Description: {project_description}

Participant: {participant_name}{f", {participant_role}" if participant_role else ""}

Your goal is to gather meaningful insights about the user's experience, pain points, and needs.
Ask follow-up questions based on their responses to dig deeper into important topics.
Keep the conversation natural and conversational while guiding it towards valuable research outcomes.
Focus on specific examples and stories rather than general opinions.
"""

        # Initialize the conversation if it doesn't exist
        if project_name not in conversations:
            logger.info(f"Initializing new conversation for project: {project_name}")
            conversations[project_name] = {
                'messages': [
                    {"role": "system", "content": system_message},
                    {"role": "assistant", "content": f"Daria: Hello, I'm Daria, and I'm conducting research about {project_name}. Thank you for participating."}
                ]
            }

        # Get the current conversation
        conversation = conversations[project_name]
        current_round = len(conversation['messages']) // 2
        
        # Update the system message with the enhanced context
        conversation['messages'][0]['content'] = system_message

        # Add the transcription to the conversation history
        conversation['messages'].append({"role": "user", "content": f"You: {transcription.text}\n\n"})

        # Get AI response using OpenAI client
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=conversation['messages'],
                temperature=0.7
            )

            ai_response = response.choices[0].message.content
            conversation['messages'].append({"role": "assistant", "content": f"Daria: {ai_response}\n\n"})
            logger.info(f"Generated AI response: {ai_response[:30]}...")
        except Exception as openai_error:
            logger.error(f"Error generating AI response: {str(openai_error)}")
            ai_response = "I'm sorry, I couldn't process your request at the moment."
            conversation['messages'].append({"role": "assistant", "content": f"Daria: {ai_response}\n\n"})

        # Only set should_stop_interview if we've reached max rounds and have meaningful conversation
        should_stop = False
        if current_round > 0 and len(transcription.text.split()) > 2 and current_round >= MAX_ROUNDS:
            should_stop = False  # Don't stop the interview automatically

        # Add CORS headers to the response
        response = jsonify({
            'transcription': transcription.text,
            'response': ai_response,
            'should_stop_interview': should_stop
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    try:
        text = request.json.get('text')
        voice_id = request.json.get('voice_id', AVAILABLE_VOICES['rachel'])  # Default to Rachel if not specified
        
        if not text:
            logger.error("No text provided for text-to-speech")
            return jsonify({'error': 'No text provided'}), 400
        
        logger.info(f"Text-to-speech request received: {text[:30]}...")
        
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not found in environment")
            return jsonify({'error': 'ElevenLabs API key is not configured'}), 500
        
        # Convert text to speech using ElevenLabs
        try:
            audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            
            # Convert stream to bytes
            audio_data = BytesIO()
            for chunk in audio_stream:
                audio_data.write(chunk)
            audio_data.seek(0)
            
            logger.info(f"Text-to-speech conversion successful, size: {audio_data.getbuffer().nbytes} bytes")
            
            response = send_file(
                audio_data,
                mimetype='audio/wav',
                as_attachment=False
            )
            
            # Add CORS headers explicitly
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as elevenlabs_error:
            logger.error(f"ElevenLabs API error: {str(elevenlabs_error)}")
            return jsonify({'error': f'ElevenLabs API error: {str(elevenlabs_error)}'}), 500
        
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        project_name = request.args.get('project_name', '').strip()
        if not project_name:
            return jsonify({'error': 'Project name is required'}), 400
        
        if project_name not in conversations:
            return jsonify({'error': 'Invalid project'}), 400
        
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        
        if not user_input:
            return jsonify({'error': 'No input provided'}), 400
        
        # Format the user input
        formatted_user_input = f"You: {user_input}\n\n"
        
        # Get the saved interview prompt
        interview_prompt = interview_prompts.get(project_name)
        if not interview_prompt:
            return jsonify({'error': 'Interview prompt not found'}), 400
            
        # Safely extract interview type from prompt
        interview_type = "Application Interview"  # Default
        if "Persona Interview" in interview_prompt:
            interview_type = "Persona Interview"
        elif "Journey Map Interview" in interview_prompt:
            interview_type = "Journey Map Interview"
        
        # Get the current conversation
        conversation = conversations[project_name]
        
        # Calculate current round (each round has a user message and an assistant message)
        current_round = len(conversation['messages']) // 2
        
        # Add the user's message to the conversation
        conversation['messages'].append({"role": "user", "content": formatted_user_input})
        
        # Check if this is a response to the conclusion question
        if conversation['messages'][-2]['content'].startswith("Thank you for participating"):
            if "yes" in user_input.lower() or "complete" in user_input.lower() or "generate" in user_input.lower():
                return jsonify({
                    'response': "Great! I'll now analyze our conversation and generate a report.",
                    'should_stop_interview': True,
                    'generate_report': True
                })
            else:
                return jsonify({
                    'response': "I understand you'd like to continue. Let's proceed with the interview.",
                    'should_stop_interview': False
                })
        
        # Only check for max rounds if we're past the first round and the input isn't too short
        if current_round > 0 and len(user_input.split()) > 2 and current_round >= MAX_ROUNDS:
            # Only ask to conclude if we haven't already asked
            if not any(msg['content'].startswith("Thank you for participating") for msg in conversation['messages']):
                return jsonify({
                    'response': "Thank you for participating in this interview. I've gathered enough information for now. Would you like to conclude the interview?",
                    'should_stop_interview': False  # Don't stop until user confirms
                })
        
        # Create the system message for this turn
        system_message = f"""You are conducting a {interview_type} about {project_name}.

Based on the user's responses so far, ask the next relevant question. Remember to:
1. Stay focused on {project_name}
2. Ask follow-up questions only if clarification is needed
3. Move to a new topic when appropriate
4. Never repeat questions
5. Keep questions concise and direct
6. Maintain a professional tone without unnecessary acknowledgments
7. Focus on gathering specific, actionable insights
8. This is round {current_round + 1} of {MAX_ROUNDS}, so manage time accordingly"""

        # Special handling for the first response
        if current_round == 0:
            system_message = f"""You are conducting a {interview_type} about {project_name}.
The user has just given permission to proceed with the interview.

Based on this, ask the first question about {project_name}. Remember to:
1. Stay focused on {project_name}
2. Keep questions concise and direct
3. Maintain a professional tone
4. Focus on gathering specific, actionable insights"""
        
        # Update the system message
        conversation['messages'][0]['content'] = system_message
        
        # Get AI response using OpenAI client
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation['messages'],
            temperature=0.7
        )
        
        # Format the AI response
        ai_response = response.choices[0].message.content
        formatted_response = f"Daria: {ai_response}\n\n"
        
        # Add the AI response to the conversation
        conversation['messages'].append({"role": "assistant", "content": formatted_response})
        
        return jsonify({
            'response': ai_response,
            'should_stop_interview': False  # Only stop when user confirms
        })
        
    except Exception as e:
        logger.error(f"Error in chat route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def update_interview_data(interview_id, analysis):
    """Update an existing interview with new analysis."""
    try:
        file_path = INTERVIEWS_DIR / f"{interview_id}.json"
        if not file_path.exists():
            return None
            
        # Read existing interview
        with open(file_path, 'r') as f:
            interview_data = json.load(f)
            
        # Update analysis
        interview_data['analysis'] = analysis
        
        # Save updated interview
        with open(file_path, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        logger.info(f"Interview {interview_id} updated successfully")
        return interview_id
        
    except Exception as e:
        logger.error(f"Error updating interview: {str(e)}")
        logger.error(traceback.format_exc())
        return None

@app.route('/final_analysis', methods=['POST'])
def final_analysis():
    try:
        project_name = request.args.get('project_name')
        if not project_name:
            return jsonify({'status': 'error', 'error': 'Project name is required'}), 400

        data = request.get_json()
        transcript = data.get('transcript', '')
        report_prompt = data.get('report_prompt', '')

        # Get the saved interview prompt and form data
        interview_data = interview_prompts.get(project_name)
        if not interview_data:
            logger.warning(f"Interview data not found for project: {project_name}. Using default context.")
            # Create default context instead of failing
            interview_data = {
                'prompt': f"An interview about {project_name}",
                'form_data': {
                    'project_name': project_name,
                    'project_description': f"A project about {project_name}",
                    'interview_type': "Application Interview", 
                    'interviewee': {'name': 'Anonymous'}
                }
            }

        # Load all configuration data
        interview_prompt = interview_data.get('prompt', '')
        form_data = interview_data.get('form_data', {})
        
        # Extract critical context information
        project_description = form_data.get('project_description', '')
        interview_type = form_data.get('interview_type', '')
        
        # Extract participant information
        interviewee = form_data.get('interviewee', {})
        participant_name = interviewee.get('name', 'Anonymous')
        participant_role = interviewee.get('role', '')
        participant_experience = interviewee.get('experience_level', '')
        participant_department = interviewee.get('department', '')
        
        # Create rich participant context
        participant_context = f"{participant_name}"
        if participant_role:
            participant_context += f", {participant_role}"
        if participant_experience:
            participant_context += f", with {participant_experience} experience"
        if participant_department:
            participant_context += f" in the {participant_department} department"

        # Determine interview type from the prompt if not explicitly provided
        if not interview_type:
            if "Persona Interview" in interview_prompt:
                interview_type = "Persona Interview"
            elif "Journey Map Interview" in interview_prompt:
                interview_type = "Journey Map Interview"
            else:
                interview_type = "Application Interview"

        # Create context-rich analysis prompt
        if interview_type == "Application Interview":
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher analyzing an Application Evaluation interview.
#Project: {project_name}
#Project Description: {project_description}
#Participant: {participant_context}

#Objective: Evaluate the participant's experience with {project_name}

#Instructions: Analyze the interview transcript and provide a comprehensive evaluation report.

Your analysis should include:
1. User Role and Experience: How the participant uses the system and their relevant background
2. Key Tasks and Workflows: Main activities and processes they perform
3. Pain Points and Challenges: Specific frustrations and obstacles they encounter
4. Positive Aspects: Features or elements they find valuable or effective
5. Suggestions and Ideas: Improvements they mentioned or implied
6. Overall Assessment: Evaluation of their experience and critical needs
7. Key Quotes: Include meaningful direct quotes from the transcript

Format your response with clear section headers and concise, actionable insights. Support your analysis with evidence from the transcript."""
        elif interview_type == "Persona Interview":
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher analyzing a Persona Interview.
#Project: {project_name}
#Project Description: {project_description}
#Participant: {participant_context}

#Objective: Generate a detailed persona based on the interview

#Instructions: Analyze the interview transcript and create a robust user persona.

Your analysis should include:
1. Persona Demographics: Age, role, experience level, and other relevant characteristics
2. Behaviors and Usage Patterns: How they interact with the system, their workflow, and habits
3. Goals and Motivations: What they're trying to achieve, both functionally and emotionally
4. Challenges and Frustrations: Specific pain points they experience
5. Needs and Preferences: Their requirements and what they value in a solution
6. Mental Models: How they think about and approach the system or problem space
7. Key Quotes: Include meaningful direct quotes that illuminate their perspective

Format your response with clear section headers, and make the persona specific and actionable. Base all insights directly on evidence from the transcript."""
        else:  # Journey Map Interview
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher analyzing a Journey Map Interview.
#Project: {project_name}
#Project Description: {project_description}
#Participant: {participant_context}

#Objective: Create a detailed journey map based on the participant's experience

#Instructions: Analyze the interview transcript and develop a comprehensive journey map.

Your analysis should include:
1. Journey Stages: Identify and name each key phase of the user journey
2. User Actions: What the participant does at each stage
3. Touchpoints: All interactions with the system, people, or other elements
4. Emotions and Thoughts: How they feel and what they think at each stage
5. Pain Points: Specific challenges, frustrations, or obstacles encountered
6. Opportunities: Potential improvements or solutions at each stage
7. Key Quotes: Include meaningful direct quotes for each journey stage

For each stage, provide a clear analysis of what works well and what needs improvement.
Format your response with clear section headers and ensure insights are specific and actionable.
Structure the journey chronologically and highlight critical moments that impact the overall experience."""

        # Create a new instance of the OpenAI client
        client = OpenAI()
        
        # Generate the analysis using the enhanced prompt
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": f"Here is the interview transcript to analyze:\n\n{transcript}"}
                ],
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
        except Exception as api_error:
            logger.error(f"Error with OpenAI API: {str(api_error)}")
            return jsonify({'status': 'error', 'error': f'API error: {str(api_error)}'}), 500

        # Save the interview data with the transcript and analysis
        save_interview_data(project_name, interview_type, transcript, analysis, form_data)

        return jsonify({
            'status': 'success',
            'message': 'Interview analysis completed successfully',
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"Error in final_analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Add new routes
@app.route('/archive')
def archive():
    """Display the archive page with all interviews."""
    try:
        logger.info("Loading interviews for archive page...")
        interviews = list_interviews()
        logger.info(f"Found {len(interviews)} interviews")
        
        # Format interviews for display
        for interview in interviews:
            logger.info(f"Processing interview: {interview.get('id')}")
            
            # Set type and status
            interview['type'] = interview.get('type', 'Interview').title()
            interview['status'] = interview.get('status', 'draft').title()
            
            # Set preview text
            interview['preview'] = interview.get('content_preview', 'No preview available')
            
            # Set project info
            interview['project_name'] = interview.get('project_name', 'Unassigned')
            
            # Debug logging for participant name extraction
            logger.info(f"Interview metadata: {interview.get('metadata', {})}")
            logger.info(f"Direct participant_name: {interview.get('participant_name')}")
            logger.info(f"Transcript name: {interview.get('transcript_name')}")
            
            # Standardized name extraction
            participant_name = None
            
            # Try metadata.interviewee first (new format)
            if interview.get('metadata', {}).get('interviewee', {}).get('name'):
                participant_name = interview['metadata']['interviewee']['name']
                logger.info(f"Found name in metadata.interviewee: {participant_name}")
            
            # Try metadata.participant next (alternate format)
            elif interview.get('metadata', {}).get('participant', {}).get('name'):
                participant_name = interview['metadata']['participant']['name']
                logger.info(f"Found name in metadata.participant: {participant_name}")
            
            # Try direct participant_name
            elif interview.get('participant_name'):
                participant_name = interview['participant_name']
                logger.info(f"Found direct participant_name: {participant_name}")
            
            # Try transcript_name (remove "'s Interview" if present)
            elif interview.get('transcript_name'):
                name = interview['transcript_name']
                if "'s Interview" in name:
                    participant_name = name.split("'s Interview")[0]
                else:
                    participant_name = name
                logger.info(f"Found name in transcript_name: {participant_name}")
            
            # Default to Anonymous if no name found
            if not participant_name:
                logger.info("No participant name found, defaulting to Anonymous")
                participant_name = 'Anonymous'
            
            interview['participant_name'] = participant_name
            logger.info(f"Final participant_name set to: {participant_name}")
            
            # Extract themes and insights if available
            themes = set()
            insights = set()
            emotions = {}
            
            if interview.get('chunks'):
                for chunk in interview['chunks']:
                    if chunk.get('metadata'):
                        # Collect themes
                        if chunk['metadata'].get('themes'):
                            themes.update(chunk['metadata']['themes'])
                        
                        # Collect insights
                        if chunk['metadata'].get('insight_tags'):
                            insights.update(chunk['metadata']['insight_tags'])
                        
                        # Track emotions and their intensities
                        if chunk['metadata'].get('emotion'):
                            emotion = chunk['metadata']['emotion'].lower()
                            intensity = chunk['metadata'].get('emotion_intensity', 3)
                            if emotion in emotions:
                                emotions[emotion]['count'] += 1
                                emotions[emotion]['total_intensity'] += intensity
                            else:
                                emotions[emotion] = {
                                    'count': 1,
                                    'total_intensity': intensity
                                }
            
            # Convert sets to lists for JSON serialization
            interview['themes'] = list(themes)
            interview['insights'] = list(insights)
            
            # Calculate average emotion intensities
            interview['emotions'] = [
                {
                    'name': emotion,
                    'count': data['count'],
                    'avg_intensity': round(data['total_intensity'] / data['count'], 1)
                }
                for emotion, data in emotions.items()
            ]
            
            # Sort emotions by count
            interview['emotions'].sort(key=lambda x: x['count'], reverse=True)
            
            logger.info(f"Processed interview: {interview.get('id')} - {interview['participant_name']}")
        
        logger.info("Rendering archive template...")
        return render_template('archive.html', interviews=interviews)
        
    except Exception as e:
        logger.error(f"Error in archive route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', 
                             error="Failed to load interviews archive",
                             details=str(e))

# Add search endpoints
@app.route('/api/search/exact', methods=['GET'])
def search_exact():
    """Exact match search for interviews."""
    try:
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({'success': True, 'interviews': []})
        
        interviews = list_interviews()
        results = []
        
        for interview in interviews:
            # Get the full interview data to search in transcript
            interview_file = Path('interviews/raw') / f"{interview['id']}.json"
            try:
                with open(interview_file, 'r') as f:
                    full_interview = json.load(f)
                    transcript = full_interview.get('transcript', '')
            except:
                transcript = ''
            
            # Search in participant name
            if query in interview.get('participant_name', '').lower():
                results.append(interview)
                continue
            
            # Search in project name
            if query in interview.get('project_name', '').lower():
                results.append(interview)
                continue
            
            # Search in themes
            if any(query in theme.lower() for theme in interview.get('themes', [])):
                results.append(interview)
                continue
            
            # Search in insights
            if any(query in insight.lower() for insight in interview.get('insights', [])):
                results.append(interview)
                continue
            
            # Search in transcript preview
            if query in interview.get('preview', '').lower():
                results.append(interview)
                continue
                
            # Search in full transcript
            if transcript and query in transcript.lower():
                # Generate a preview around the match
                match_start = transcript.lower().find(query)
                preview_start = max(0, match_start - 100)
                preview_end = min(len(transcript), match_start + len(query) + 100)
                preview = transcript[preview_start:preview_end]
                if preview_start > 0:
                    preview = '...' + preview
                if preview_end < len(transcript):
                    preview = preview + '...'
                    
                interview['preview'] = preview
                results.append(interview)
                continue
        
        return jsonify({'success': True, 'interviews': results})
        
    except Exception as e:
        logger.error(f"Error in exact search: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/search/fuzzy', methods=['GET'])
def search_fuzzy():
    """Fuzzy match search for interviews using semantic similarity."""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': True, 'interviews': []})
        
        # Get semantic analyzer instance
        analyzer = SemanticAnalyzer()
        query_embedding = np.array(analyzer.get_embedding(query)).reshape(1, -1)  # Reshape to 2D
        
        interviews = list_interviews()
        results = []
        
        # Process interviews in smaller batches
        batch_size = 5
        for i in range(0, len(interviews), batch_size):
            batch = interviews[i:i + batch_size]
            batch_results = []
            
            for interview in batch:
                similarity_score = 0
                preview_text = None
                
                # Get the full interview data
                interview_file = Path('interviews/raw') / f"{interview['id']}.json"
                try:
                    with open(interview_file, 'r') as f:
                        full_interview = json.load(f)
                        transcript = full_interview.get('transcript', '')
                        # Get default preview
                        preview_text = _get_content_preview(full_interview)
                except:
                    transcript = ''
                    preview_text = 'No preview available'
                
                # Compare with participant name and project name together
                metadata_text = ' '.join(filter(None, [
                    interview.get('participant_name', ''),
                    interview.get('project_name', '')
                ]))
                if metadata_text:
                    metadata_embedding = np.array(analyzer.get_embedding(metadata_text)).reshape(1, -1)
                    similarity_score = max(similarity_score, 
                                        cosine_similarity(query_embedding, metadata_embedding)[0][0])
                
                # Compare with themes and insights together
                tags_text = ' '.join(filter(None, 
                    interview.get('themes', []) + interview.get('insights', [])
                ))
                if tags_text:
                    tags_embedding = np.array(analyzer.get_embedding(tags_text)).reshape(1, -1)
                    similarity_score = max(similarity_score, 
                                        cosine_similarity(query_embedding, tags_embedding)[0][0])
                
                # Compare with transcript content
                if transcript:
                    # Use larger chunks to reduce number of embeddings
                    chunk_size = 1000
                    for i in range(0, len(transcript), chunk_size):
                        chunk = transcript[i:i + chunk_size]
                        chunk_embedding = np.array(analyzer.get_embedding(chunk)).reshape(1, -1)
                        chunk_similarity = cosine_similarity(query_embedding, chunk_embedding)[0][0]
                        
                        if chunk_similarity > similarity_score:
                            similarity_score = chunk_similarity
                            # Update preview if this is the best matching chunk
                            preview_start = max(0, i - 100)
                            preview_end = min(len(transcript), i + chunk_size + 100)
                            preview_text = transcript[preview_start:preview_end]
                            if preview_start > 0:
                                preview_text = '...' + preview_text
                            if preview_end < len(transcript):
                                preview_text = preview_text + '...'
                
                # Add to results if similarity is above threshold
                if similarity_score > 0.3:  # Lowered threshold to catch more matches
                    interview['similarity_score'] = float(similarity_score)
                    interview['preview'] = preview_text
                    batch_results.append(interview)
            
            # Add batch results to main results
            results.extend(batch_results)
            
            # Sort current results by similarity score
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Return current batch as a response
            response = jsonify({
                'success': True,
                'interviews': results,
                'is_partial': i + batch_size < len(interviews)
            })
            response.headers['Content-Type'] = 'application/json'
            return response
        
        # Log for debugging
        logger.info(f"Fuzzy search for '{query}' found {len(results)} results")
        for result in results[:3]:  # Log top 3 results
            logger.info(f"Score: {result['similarity_score']:.3f}, Preview: {result.get('preview', '')[:100]}")
        
        # Return final results
        return jsonify({
            'success': True,
            'interviews': results,
            'is_partial': False
        })
        
    except Exception as e:
        logger.error(f"Error in fuzzy search: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/transcript/<interview_id>')
def view_transcript(interview_id):
    """View interview transcript."""
    try:
        # Load interview from raw directory
        interview_file = Path('interviews/raw') / f"{interview_id}.json"
        if not interview_file.exists():
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        with open(interview_file, 'r') as f:
            interview = json.load(f)
        
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        return render_template('transcript.html', 
                             interview=interview,
                             transcript=interview.get('transcript', ''))
    except Exception as e:
        logger.error(f"Error viewing transcript: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading transcript', 'error')
        return redirect(url_for('archive'))

@app.route('/analysis/<interview_id>')
def view_analysis(interview_id):
    """View interview analysis. If analysis doesn't exist, generate it."""
    try:
        # Try to load interview from processed directory first
        processed_file = Path('interviews/processed') / f"{interview_id}.json"
        raw_file = Path('interviews/raw') / f"{interview_id}.json"
        
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                interview = json.load(f)
        elif raw_file.exists():
            with open(raw_file, 'r') as f:
                interview = json.load(f)
        else:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        # Check if we need to generate semantic chunks
        if not interview.get('chunks'):
            try:
                # Process transcript into semantic chunks
                transcript = interview.get('transcript', '')
                if not transcript:
                    flash('No transcript found', 'error')
                    return redirect(url_for('archive'))
                    
                chunks = process_semantic_chunks(transcript)
                
                # Analyze each chunk for sentiment and themes
                for chunk in chunks:
                    semantic_data = analyze_chunk_semantics(chunk['combined_text'])
                    chunk['analysis'] = semantic_data
                
                # Update interview with chunks
                interview['chunks'] = chunks
                
                # Save the updated interview to processed directory
                processed_file.parent.mkdir(parents=True, exist_ok=True)
                with open(processed_file, 'w') as f:
                    json.dump(interview, f, indent=2)
                
            except Exception as e:
                logger.error(f"Error generating semantic chunks: {str(e)}")
                logger.error(traceback.format_exc())
                flash('Error generating analysis', 'error')
                return redirect(url_for('archive'))
        
        return render_template('analysis.html', interview=interview)
        
    except Exception as e:
        logger.error(f"Error viewing analysis: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading analysis', 'error')
        return redirect(url_for('archive'))

@app.route('/metadata/<interview_id>')
def view_metadata(interview_id):
    """View interview metadata (old format)."""
    try:
        # Load interview from raw directory
        interview_file = Path('interviews/raw') / f"{interview_id}.json"
        if not interview_file.exists():
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        with open(interview_file, 'r') as f:
            interview = json.load(f)
        
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        return render_template('metadata.html', 
                             interview=interview)
    except Exception as e:
        logger.error(f"Error viewing metadata: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading metadata', 'error')
        return redirect(url_for('archive'))

@app.route('/demographics/<interview_id>')
def view_demographics(interview_id):
    """View interview demographics (new format)."""
    try:
        # Load interview from raw directory
        interview_file = Path('interviews/raw') / f"{interview_id}.json"
        if not interview_file.exists():
            logger.error(f"Interview file not found: {interview_file}")
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        with open(interview_file, 'r') as f:
            interview = json.load(f)
            
        if not interview:
            logger.error("Interview data is empty")
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
            
        # Log the structure we're looking for
        logger.info(f"Looking for demographics in metadata.interviewee: {interview.get('metadata', {}).get('interviewee')}")
        logger.info(f"Looking for demographics in metadata.participant: {interview.get('metadata', {}).get('participant')}")
        logger.info(f"Looking for demographics in participant: {interview.get('participant')}")
        
        # Create a processed directory if it doesn't exist
        processed_dir = Path('interviews/processed')
        processed_dir.mkdir(exist_ok=True)
        
        # Save a processed version of the interview with cleaned up structure
        processed_interview = {
            'id': interview.get('id'),
            'metadata': {
                'participant': interview.get('metadata', {}).get('interviewee') or 
                             interview.get('metadata', {}).get('participant') or 
                             interview.get('participant', {}),
                'researcher': interview.get('metadata', {}).get('researcher', {}),
                'interview_details': interview.get('metadata', {}).get('interview_details', {})
            }
        }
        
        processed_file = processed_dir / f"{interview_id}.json"
        with open(processed_file, 'w') as f:
            json.dump(processed_interview, f, indent=2)
            
        logger.info(f"Saved processed interview data to: {processed_file}")
        
        return render_template('demographics.html', 
                             interview=processed_interview)
    except Exception as e:
        logger.error(f"Error viewing demographics: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading demographics', 'error')
        return redirect(url_for('archive'))

@app.route('/analyze_interviews', methods=['POST'])
def analyze_interviews():
    """Analyze multiple interviews together."""
    data = request.get_json()
    interview_ids = data.get('interview_ids', [])
    
    # Load all selected interviews
    interviews = [load_interview(id) for id in interview_ids]
    if not all(interviews):
        return jsonify({'error': 'One or more interviews not found'}), 404
    
    # Combine transcripts for analysis
    combined_data = "\n\n".join([
        f"Interview {i+1} - {interview['project_name']} ({interview['date']})\n"
        f"Type: {interview['interview_type']}\n"
        f"Transcript:\n{interview['transcript']}\n"
        f"Individual Analysis:\n{interview['analysis']}"
        for i, interview in enumerate(interviews)
    ])
    
    # Create analysis prompt
    analysis_prompt = f"""Analyze the following {len(interviews)} interviews collectively:

{combined_data}

Please provide a comprehensive cross-interview analysis that includes:
1. Common Themes: Identify patterns and recurring topics across interviews
2. Key Differences: Note significant variations in experiences or perspectives
3. Aggregate Insights: Synthesize the main findings from all interviews
4. Recommendations: Suggest actionable items based on the collective feedback

Format your response with clear sections and bullet points where appropriate."""
    
    try:
        # Use the conversation chain for analysis
        analysis_chain = ConversationChain(
            llm=ChatOpenAI(
                temperature=0.7,
                openai_api_key=OPENAI_API_KEY,
                model_name="gpt-4"
            ),
            memory=ConversationBufferMemory()
        )
        
        cross_analysis = analysis_chain.predict(input=analysis_prompt)
        return jsonify({'analysis': cross_analysis})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_interviews', methods=['GET', 'POST'])
def search_interviews():
    """Search interviews based on query and filters."""
    try:
        # Get query and filters
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('query', '').strip()
            filters = data.get('filters', {})
        else:
            query = request.args.get('q', '').strip()
            filters = {
                'project_name': request.args.get('project'),
                'date_from': request.args.get('from'),
                'date_to': request.args.get('to')
            }
        
        # Get all interviews
        interviews = list_interviews()
        
        # Filter interviews
        filtered_interviews = []
        for interview in interviews:
            if not interview:
                continue
                
            # Apply filters
            if filters.get('project_name') and interview.get('project_name') != filters['project_name']:
                continue
                
            if filters.get('date_from') and interview.get('created_at', '') < filters['date_from']:
                continue
                
            if filters.get('date_to') and interview.get('created_at', '') > filters['date_to']:
                continue
                
            # Apply text search if query exists
            if query:
                # Search in multiple fields
                searchable_text = ' '.join([
                    str(interview.get('title', '')),
                    str(interview.get('participant_name', '')),
                    str(interview.get('project_name', '')),
                    str(interview.get('preview', '')),
                    str(interview.get('content_preview', ''))
                ]).lower()
                
                if query.lower() not in searchable_text:
                    continue
                    
            filtered_interviews.append(interview)
            
        return jsonify({
            'success': True,
            'interviews': filtered_interviews
        })
        
    except Exception as e:
        logger.error(f"Error in search_interviews: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Failed to search interviews'
        }), 500

def get_match_preview(text, query, window=100):
    """Get a preview of text around the search query match."""
    if not text or not query:
        return ""
    
    text = text.lower()
    index = text.find(query)
    if index == -1:
        # If exact query not found, return start of text
        return text[:window] + "..." if len(text) > window else text
        
    # Calculate preview window
    start = max(0, index - window // 2)
    end = min(len(text), index + len(query) + window // 2)
    
    # Add ellipsis if necessary
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    
    return prefix + text[start:end] + suffix

@app.route('/similar_interviews/<interview_id>')
def similar_interviews(interview_id):
    """Find interviews similar to a given interview."""
    k = int(request.args.get('k', 3))
    results = vector_store.find_similar_interviews(interview_id, k=k)
    return jsonify({'results': results})

@app.route('/delete_interview/<interview_id>', methods=['POST'])
def delete_interview_route(interview_id):
    """Delete a specific interview."""
    try:
        if delete_interview(interview_id):
            return jsonify({'status': 'success', 'message': 'Interview deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete interview'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_personas/<project_name>')
def create_personas(project_name):
    """Display the persona creation page for a specific project."""
    return render_template('create_personas.html', project_name=project_name)

@app.route('/save_persona', methods=['POST'])
def save_persona_route():
    """Save a persona configuration."""
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        persona_data = data.get('persona_data')
        
        # Create personas directory if it doesn't exist
        personas_dir = Path('personas')
        personas_dir.mkdir(exist_ok=True)
        
        # Save persona data
        file_path = personas_dir / f"{project_name}_{persona_data['name'].lower().replace(' ', '_')}.json"
        with open(file_path, 'w') as f:
            json.dump(persona_data, f, indent=2)
            
        return jsonify({'status': 'success', 'message': 'Persona saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_persona', methods=['POST'])
def generate_persona():
    """Generate a persona based on selected interviews."""
    try:
        data = request.get_json()
        logger.info(f"Received persona generation request: {json.dumps(data, indent=2)}")
        
        if not data or 'interviews' not in data:
            logger.error("No interviews provided in request")
            return jsonify({'error': 'No interviews provided'}), 400
            
        interviews = data['interviews']
        project_name = data.get('project_name', '')
        model = data.get('model', 'gpt-4')
        selected_elements = data.get('selected_elements', [])

        # Load interview data
        interview_data = []
        for interview_id in interviews:
            interview = get_interview(interview_id)
            if not interview:
                logger.warning(f"Could not load interview data for ID {interview_id}")
                continue
            interview_data.append(interview)
        
        if not interview_data:
            logger.error("No valid interviews found")
            return jsonify({'error': 'No valid interviews found'}), 400

        # Extract full transcripts for persona synthesis
        interview_texts = []
        for interview in interview_data:
            transcript = interview.get('transcript', '')
            # If transcript is a list of messages, join them
            if isinstance(transcript, list):
                transcript = ' '.join([msg.get('text', '') for msg in transcript])
            interview_texts.append(transcript)

        # Use the robust persona synthesis function
        from daria_interview_tool.persona_gpt import generate_persona_from_interviews
        try:
            persona_data = generate_persona_from_interviews(
                interview_texts=interview_texts,
                project_name=project_name,
                model=model
            )
        except Exception as e:
            logger.error(f"Error generating persona: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Failed to generate persona: {str(e)}'}), 500

        # Generate HTML from persona data
        try:
            persona_html = generate_persona_html(persona_data)
            logger.info("Successfully generated persona HTML")
            return jsonify({'persona': persona_html})
        except Exception as e:
            logger.error(f"Error generating persona HTML: {str(e)}")
            return jsonify({'error': 'Failed to generate persona HTML'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in generate_persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def generate_persona_html(persona_data):
    """Generate HTML representation of the persona data."""
    try:
        # Basic validation
        if not isinstance(persona_data, dict):
            logger.error(f"persona_data is not a dictionary: {type(persona_data)}")
            return '<div class="error">Invalid persona data format</div>'
            
        logger.info(f"Generating HTML for persona data: {json.dumps(persona_data, indent=2)}")
        
        # Get required fields with defaults
        name = persona_data.get('name', 'Unnamed Persona')
        summary = persona_data.get('summary', 'No summary available')
        demographics = persona_data.get('demographics', {})
        background = persona_data.get('background', 'No background information available')
        goals = persona_data.get('goals', [])
        pain_points = persona_data.get('pain_points', [])
        
        # Build HTML
        html = f"""
        <div class="persona-container space-y-8">
            <div class="header-section bg-indigo-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-indigo-800 mb-2">{name}</h2>
                <p class="text-gray-700">{summary}</p>
            </div>"""
            
        # Add demographics if available
        if demographics:
            demo_fields = {
                'age_range': 'Age Range',
                'gender': 'Gender',
                'occupation': 'Occupation',
                'location': 'Location',
                'education': 'Education'
            }
            
            html += """
            <div class="demographics-section bg-blue-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-blue-800 mb-4">Demographics</h2>
                <div class="grid grid-cols-2 gap-4">"""
                
            for field_key, field_label in demo_fields.items():
                value = demographics.get(field_key, 'Not specified')
                html += f"""
                    <div>
                        <p class="text-sm font-medium text-blue-700">{field_label}</p>
                        <p class="text-gray-600">{value}</p>
                    </div>"""
                    
            html += """
                </div>
            </div>"""
            
        # Add background section
        html += f"""
            <div class="background-section bg-gray-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">Background & Context</h2>
                <p class="text-gray-700">{background}</p>
            </div>"""
            
        # Add goals section if available
        if goals:
            html += """
            <div class="goals-section bg-green-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-green-800 mb-4">Goals & Motivations</h2>
                <div class="space-y-4">"""
                
            for goal in goals:
                if isinstance(goal, dict):
                    goal_text = goal.get('goal', '')
                    motivation = goal.get('motivation', '')
                    quotes = goal.get('supporting_quotes', [])
                    
                    if goal_text:
                        html += f"""
                        <div class="goal-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-green-700 mb-2">{goal_text}</h3>"""
                        
                        if motivation:
                            html += f'<p class="text-gray-600 mb-2">{motivation}</p>'
                            
                        if quotes:
                            html += """
                            <div class="mt-2">
                                <p class="text-sm font-medium text-green-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">"""
                            for quote in quotes:
                                html += f'<li>{quote}</li>'
                            html += """
                                </ul>
                            </div>"""
                            
                        html += """
                        </div>"""
                elif isinstance(goal, str):
                    html += f"""
                    <div class="goal-card bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-green-700 mb-2">{goal}</h3>
                    </div>"""
                    
            html += """
                </div>
            </div>"""
            
        # Add pain points section if available
        if pain_points:
            html += """
            <div class="pain-points-section bg-red-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-red-800 mb-4">Pain Points & Challenges</h2>
                <div class="space-y-4">"""
                
            for pain_point in pain_points:
                if isinstance(pain_point, dict):
                    point_text = pain_point.get('pain_point', '')
                    impact = pain_point.get('impact', '')
                    quotes = pain_point.get('supporting_quotes', [])
                    
                    if point_text:
                        html += f"""
                        <div class="pain-point-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-red-700 mb-2">{point_text}</h3>"""
                            
                        if impact:
                            html += f'<p class="text-gray-600 mb-2">Impact: {impact}</p>'
                            
                        if quotes:
                            html += """
                            <div class="mt-2">
                                <p class="text-sm font-medium text-red-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">"""
                            for quote in quotes:
                                html += f'<li>{quote}</li>'
                            html += """
                                </ul>
                            </div>"""
                            
                        html += """
                        </div>"""
                elif isinstance(pain_point, str):
                    html += f"""
                    <div class="pain-point-card bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-red-700 mb-2">{pain_point}</h3>
                    </div>"""
                    
            html += """
                </div>
            </div>"""
            
        html += """
        </div>"""
        
        return html
        
    except Exception as e:
        logger.error(f"Error generating persona HTML: {str(e)}")
        logger.error(f"Persona data: {json.dumps(persona_data, indent=2)}")
        logger.error(traceback.format_exc())
        return '<div class="error">Error generating persona display</div>'

@app.route('/api/save-persona', methods=['POST'])
def save_persona_api():
    """Save a generated persona."""
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        persona_data = data.get('persona_data')
        
        if not project_name or not persona_data:
            return jsonify({'error': 'Project name and persona data are required'}), 400
        
        # Create personas directory if it doesn't exist
        PERSONAS_DIR = Path('personas')
        PERSONAS_DIR.mkdir(exist_ok=True)
        
        # Generate a unique filename based on project name and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{project_name}_{timestamp}.json"
        file_path = PERSONAS_DIR / filename
        
        # Save the persona data with metadata
        persona_data_with_metadata = {
            'id': str(uuid.uuid4()),
            'project_name': project_name,
            'created_at': datetime.now().isoformat(),
            'persona_data': persona_data
        }
        
        with open(file_path, 'w') as f:
            json.dump(persona_data_with_metadata, f, indent=2)
        
        logger.info(f"Saved persona to {file_path}")
        return jsonify({'message': 'Persona saved successfully', 'filename': filename})
        
    except Exception as e:
        logger.error(f"Error saving persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/personas')
def list_personas():
    """List all saved personas."""
    try:
        PERSONAS_DIR = Path('personas')
        if not PERSONAS_DIR.exists():
            return jsonify([])
        
        personas = []
        for file in PERSONAS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    personas.append({
                        'id': data.get('id'),
                        'project_name': data.get('project_name'),
                        'created_at': data.get('created_at'),
                        'filename': file.name
                    })
            except Exception as e:
                logger.error(f"Error reading persona file {file}: {str(e)}")
                continue
        
        # Sort personas by creation date, most recent first
        personas.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        return jsonify(personas)
        
    except Exception as e:
        logger.error(f"Error listing personas: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/personas/<persona_id>')
def get_persona(persona_id):
    """Get a specific persona by ID."""
    try:
        PERSONAS_DIR = Path('personas')
        if not PERSONAS_DIR.exists():
            return jsonify({'error': 'Persona not found'}), 404
        
        for file in PERSONAS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == persona_id:
                        return jsonify(data)
            except Exception as e:
                logger.error(f"Error reading persona file {file}: {str(e)}")
                continue
        
        return jsonify({'error': 'Persona not found'}), 404
        
    except Exception as e:
        logger.error(f"Error getting persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/view-persona/<persona_id>')
def view_persona(persona_id):
    """View a saved persona."""
    try:
        PERSONAS_DIR = Path('personas')
        if not PERSONAS_DIR.exists():
            flash('Persona not found', 'error')
            return redirect(url_for('home'))
        
        # Find the file with the matching ID
        for file in PERSONAS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == persona_id:
                        # If download parameter is present, return the JSON file
                        if request.args.get('download'):
                            return send_file(
                                file,
                                as_attachment=True,
                                download_name=f"{data.get('project_name', 'persona')}.json"
                            )
                        return render_template('view_persona.html', 
                                             persona=data)
            except Exception as e:
                logger.error(f"Error reading persona {file}: {str(e)}")
                continue
        
        flash('Persona not found', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error viewing persona: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error viewing persona', 'error')
        return redirect(url_for('home'))

@app.route('/generate_journey_map', methods=['POST'])
def generate_journey_map():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        project_name = data.get('project_name')
        focus_areas = data.get('focus_areas', [])

        if not project_name:
            return jsonify({'error': 'Project name is required'}), 400

        if not focus_areas:
            return jsonify({'error': 'At least one focus area is required'}), 400

        # Get interviews for the project
        interviews = load_interviews(project_name)
        if not interviews:
            return jsonify({
                'error': 'No interviews found',
                'details': f'No interviews found for project: {project_name}'
            }), 404

        # Combine all interview transcripts
        combined_transcript = "\n\n".join([interview['transcript'] for interview in interviews])

        # Create the analysis prompt
        focus_areas_str = ", ".join(focus_areas)
        prompt = f"""Based on the following interview transcripts, create a detailed customer journey map focusing on {focus_areas_str}.

Interview Transcripts:
{combined_transcript}

Please create a comprehensive customer journey map that includes:
1. Key stages of the customer journey
2. Customer touchpoints at each stage
3. Customer emotions and pain points
4. Opportunities for improvement

Format the journey map in markdown with clear sections and bullet points."""

        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Generate the journey map using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a UX research expert specializing in customer journey mapping."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        journey_map = response.choices[0].message.content

        return jsonify({
            'journey_map': journey_map,
            'project_name': project_name
        })

    except Exception as e:
        logger.error(f"Error generating journey map: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to generate journey map',
            'details': str(e)
        }), 500

@app.route('/save_transcript', methods=['POST'])
def save_transcript():
    """Save a transcript during the interview."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        project_name = data.get('project_name')
        interview_type = data.get('interview_type')
        transcript = data.get('transcript')

        if not all([project_name, interview_type, transcript]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Save the interview data
        interview_id = save_interview_data(
            project_name=project_name,
            interview_type=interview_type,
            transcript=transcript
        )

        return jsonify({
            'status': 'success',
            'interview_id': interview_id,
            'message': 'Interview saved successfully'
        })

    except Exception as e:
        logger.error(f"Error in save_transcript: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to save transcript',
            'details': str(e)
        }), 500

@app.route('/api/projects/<project_id>/interviews')
def get_project_interviews(project_id):
    """Get all interviews for a specific project."""
    try:
        interviews = []
        project_name = None
        
        # Check both interviews and interviews/raw directories
        interview_dirs = ['interviews', 'interviews/raw']
        
        # First, find the project name from any interview with this project ID
        for dir_path in interview_dirs:
            if os.path.exists(dir_path):
                for file in Path(dir_path).glob('*.json'):
                    try:
                        with open(file) as f:
                            interview_data = json.load(f)
                            if interview_data.get('project_id') == project_id:
                                project_name = interview_data.get('project_name')
                                break
                            # If we're using project name as ID
                            elif interview_data.get('project_name') == project_id:
                                project_name = project_id
                                break
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"Error reading file {file}: {str(e)}")
                        continue
                if project_name:
                    break
        
        if project_name:
            # Now get all interviews for this project from both directories
            for dir_path in interview_dirs:
                if os.path.exists(dir_path):
                    for file in Path(dir_path).glob('*.json'):
                        try:
                            with open(file) as f:
                                interview_data = json.load(f)
                                if interview_data.get('project_name') == project_name:
                                    # Format date for display
                                    date = interview_data.get('date', '')
                                    if date:
                                        try:
                                            date = datetime.fromisoformat(date)
                                            formatted_date = date.strftime('%B %d, %Y')
                                        except ValueError:
                                            formatted_date = date
                                    else:
                                        formatted_date = 'No date'
                                    
                                    interviews.append({
                                        'id': interview_data.get('id'),
                                        'title': interview_data.get('title', 'Untitled Interview'),
                                        'date': formatted_date,
                                        'interview_type': interview_data.get('interview_type', 'Unknown Type')
                                    })
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"Error reading file {file}: {str(e)}")
                            continue
        
        logger.info(f"Found {len(interviews)} interviews for project {project_name}")
        return jsonify(interviews)
    except Exception as e:
        logger.error(f"Error getting project interviews: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/interviews/<interview_id>/<content_type>')
def get_interview_content(interview_id, content_type):
    """Get specific content (transcript, analysis, or metadata) for an interview."""
    try:
        # Check multiple directories for the interview file
        interview_dirs = ['interviews', 'interviews/raw', 'interviews/processed']
        interview_data = None
        
        for dir_path in interview_dirs:
            interview_file = Path(dir_path) / f"{interview_id}.json"
            if interview_file.exists():
                with open(interview_file) as f:
                    interview_data = json.load(f)
                break
        
        if not interview_data:
            return jsonify({'error': 'Interview not found'}), 404
            
        if content_type == 'transcript':
            content = interview_data.get('transcript', '')
        elif content_type == 'analysis':
            content = interview_data.get('analysis', '')
        elif content_type == 'metadata':
            # Include all metadata fields
            metadata = {
                'project_name': interview_data.get('project_name'),
                'interview_type': interview_data.get('interview_type'),
                'date': interview_data.get('date'),
                'researcher': interview_data.get('metadata', {}).get('researcher', {}),
                'interviewee': interview_data.get('metadata', {}).get('interviewee', {}),
                'technology': interview_data.get('metadata', {}).get('technology', {})
            }
            content = json.dumps(metadata, indent=2)
        else:
            return jsonify({'error': 'Invalid content type'}), 400
            
        return jsonify({'content': content})
    except Exception as e:
        logger.error(f"Error getting interview content: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/journey-map', methods=['POST'])
def create_journey_map():
    """Create a journey map from selected interviews."""
    try:
        data = request.get_json()
        logger.info(f"Received journey map request with data: {data}")
        
        interview_ids = data.get('interview_ids', [])
        # Get model preference (default to gpt-4 if not provided)
        model = data.get('model', 'gpt-4')
        
        logger.info(f"Processing {len(interview_ids)} interview IDs: {interview_ids}")
        logger.info(f"Using model: {model}")
        
        if not interview_ids:
            logger.error("No interviews selected")
            return jsonify({'error': 'No interviews selected'}), 400
            
        # Load all selected interviews
        interviews = []
        interview_dirs = ['interviews', 'interviews/raw', 'interviews/processed']
        
        for interview_id in interview_ids:
            interview_data = None
            
            # Try each directory
            for dir_path in interview_dirs:
                interview_file = Path(dir_path) / f"{interview_id}.json"
                logger.info(f"Checking for interview file: {interview_file}")
                
                if interview_file.exists():
                    with open(interview_file) as f:
                        interview_data = json.load(f)
                        interviews.append(interview_data)
                        logger.info(f"Successfully loaded interview {interview_id} from {dir_path}")
                        break
            
            if not interview_data:
                logger.warning(f"Interview file not found for ID: {interview_id}")
        
        if not interviews:
            logger.error("No valid interviews found")
            return jsonify({'error': 'No valid interviews found'}), 404
            
        logger.info(f"Successfully loaded {len(interviews)} interviews")
        
        # Get project name from first interview or use default
        project_name = interviews[0].get('project_name', 'Journey Map Project')
        
        # Generate journey map JSON using our function, passing the model parameter
        from daria_interview_tool.journey_map import generate_journey_map_json
        journey_map_json = generate_journey_map_json(interviews, project_name, model)
        logger.info(f"Generated journey map JSON for {project_name} using {model}")
        
        # Extract model info for debugging if available
        model_info = journey_map_json.get('model_info', {})
        
        # Save the journey map to file if needed
        journey_map_id = journey_map_json.get('id')
        journey_maps_dir = Path('journey_maps')
        journey_maps_dir.mkdir(exist_ok=True)
        
        file_path = journey_maps_dir / f"{journey_map_id}.json"
        with open(file_path, 'w') as f:
            json.dump(journey_map_json, f, indent=2)
        logger.info(f"Saved journey map to {file_path}")
        
        # Create HTML from JSON for display
        from daria_interview_tool.journey_map_renderer import render_journey_map_html
        journey_map_html = render_journey_map_html(journey_map_json)
        
        # Add HTML to the response
        response_data = journey_map_json.copy()
        response_data['html'] = journey_map_html
        response_data['model_info'] = model_info
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error creating journey map: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        report_prompt = data.get('report_prompt')
        
        logger.info(f"Generating report for project: {project_name}")
        logger.info(f"Report prompt: {report_prompt}")
        
        if not project_name or not report_prompt:
            logger.error("Missing project_name or report_prompt")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Get the conversation history
        conversation = conversations.get(project_name)
        if not conversation:
            logger.error(f"No conversation found for project: {project_name}")
            return jsonify({'error': 'No conversation found'}), 404
        
        # Format the conversation for analysis
        transcript = "\n".join([msg['content'] for msg in conversation['messages']])
        logger.info(f"Conversation transcript: {transcript}")
        
        # Create a new instance of ChatOpenAI for analysis
        analysis_llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4",
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Generate analysis prompt based on interview type
        if "Journey Map Interview" in report_prompt:
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher conducting Creating a Journey Map interviews.
#Objective: Generate a comprehensive Journey Map based on the interviewee's responses about {project_name}
#Instructions: Evaluate the interview transcript and generate a Journey Map based on the interviewee's responses.

Your analysis should include:
1. User Journey Stages: Break down the experience into key stages or phases
2. Touchpoints:
   - For each stage, identify:
     * Key interactions with the system
     * Tools or features used
     * Communication channels
     * Support mechanisms
   - Include specific examples from the interviews

3. User Emotions:
   - Track emotional changes throughout the journey
   - Identify:
     * High points and low points
     * Specific triggers for emotional responses
     * Patterns in emotional experiences
   - Include emotional quotes from users

4. Pain Points:
   - For each stage, identify:
     * Specific challenges users face
     * Technical difficulties
     * Process inefficiencies
     * Communication gaps
   - Include specific examples and quotes

5. Moments of Delight:
   - Identify positive experiences
   - Note what worked well
   - Highlight successful interactions
   - Include specific examples and quotes

Format your response with clear sections using headers and include relevant quotes from the transcript.

Here is the interview transcript:
{transcript}"""
        
        logger.info("Sending request to OpenAI for report generation")
        response = analysis_llm.predict(analysis_prompt)
        logger.info("Received response from OpenAI")
        
        return jsonify({'report': response})
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add new routes for journey maps
@app.route('/api/save-journey-map', methods=['POST'])
def save_journey_map():
    """Save a journey map to JSON file."""
    try:
        data = request.json
        project_name = data.get('project_name')
        journey_map_data = data.get('journey_map_data')
        
        if not project_name or not journey_map_data:
            return jsonify({'error': 'Missing project name or journey map data'}), 400
        
        # Create journey maps directory if it doesn't exist
        JOURNEY_MAPS_DIR = Path('journey_maps')
        JOURNEY_MAPS_DIR.mkdir(exist_ok=True)
        
        # Generate a unique ID
        journey_map_id = str(uuid.uuid4())
        
        # Generate a unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{project_name}_{timestamp}.json"
        filepath = JOURNEY_MAPS_DIR / filename
        
        # Save the journey map data
        with open(filepath, 'w') as f:
            json.dump({
                'id': journey_map_id,
                'project_name': project_name,
                'journey_map_data': journey_map_data,
                'created_at': datetime.now().isoformat()
            }, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Journey map saved successfully',
            'id': journey_map_id
        })
    except Exception as e:
        logger.error(f"Error saving journey map: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/journey-maps', methods=['GET'])
def list_journey_maps():
    """List all saved journey maps."""
    try:
        JOURNEY_MAPS_DIR = Path('journey_maps')
        if not JOURNEY_MAPS_DIR.exists():
            return jsonify([])
        
        journey_maps = []
        for file in JOURNEY_MAPS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    journey_maps.append({
                        'id': data.get('id', str(uuid.uuid4())),
                        'project_name': data.get('project_name', 'Unknown Project'),
                        'created_at': data.get('created_at', ''),
                        'filename': file.name
                    })
            except Exception as e:
                logger.error(f"Error reading journey map {file}: {str(e)}")
                continue
        
        # Sort by creation date, newest first
        journey_maps.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify(journey_maps)
    except Exception as e:
        logger.error(f"Error listing journey maps: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/journey-maps/<journey_map_id>', methods=['GET'])
def get_journey_map(journey_map_id):
    """Get a specific journey map by ID."""
    try:
        JOURNEY_MAPS_DIR = Path('journey_maps')
        if not JOURNEY_MAPS_DIR.exists():
            return jsonify({'error': 'Journey map not found'}), 404
        
        # Find the file with the matching ID
        for file in JOURNEY_MAPS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == journey_map_id:
                        return jsonify(data)
            except Exception as e:
                logger.error(f"Error reading journey map {file}: {str(e)}")
                continue
        
        return jsonify({'error': 'Journey map not found'}), 404
    except Exception as e:
        logger.error(f"Error getting journey map: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/view-journey-map/<journey_map_id>')
def view_journey_map(journey_map_id):
    """View a saved journey map."""
    try:
        JOURNEY_MAPS_DIR = Path('journey_maps')
        if not JOURNEY_MAPS_DIR.exists():
            flash('Journey map not found', 'error')
            return redirect(url_for('home'))
        
        # Find the file with the matching ID
        for file in JOURNEY_MAPS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == journey_map_id:
                        # If download parameter is present, return the JSON file
                        if request.args.get('download'):
                            return send_file(
                                file,
                                as_attachment=True,
                                download_name=f"{data.get('project_name', 'journey_map')}.json"
                            )
                        return render_template('view_journey_map.html', 
                                             journey_map=data)
            except Exception as e:
                logger.error(f"Error reading journey map {file}: {str(e)}")
                continue
        
        flash('Journey map not found', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error viewing journey map: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading journey map', 'error')
        return redirect(url_for('home'))

@app.route('/delete_persona/<persona_id>', methods=['POST'])
def delete_persona_route(persona_id):
    """Delete a persona."""
    try:
        # Check if personas directory exists
        PERSONAS_DIR = Path('personas')
        if not PERSONAS_DIR.exists():
            return jsonify({'error': 'Personas directory not found'}), 404
        
        # If the persona_id is "Unknown Project", find and delete the most recent persona with that project name
        if persona_id == "Unknown Project":
            persona_files = sorted(PERSONAS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            for file in persona_files:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if data.get('project_name') == 'Unknown Project':
                            os.remove(file)
                            logger.info(f"Deleted persona file: {file}")
                            return jsonify({'message': 'Persona deleted successfully'})
                except Exception as e:
                    logger.error(f"Error reading persona file {file}: {str(e)}")
                    continue
            return jsonify({'error': 'Persona not found'}), 404
        
        # For regular persona IDs, find and delete the specific file
        for file in PERSONAS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == persona_id:
                        os.remove(file)
                        logger.info(f"Deleted persona file: {file}")
                        return jsonify({'message': 'Persona deleted successfully'})
            except Exception as e:
                logger.error(f"Error reading persona file {file}: {str(e)}")
                continue
        
        return jsonify({'error': 'Persona not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting persona: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_journey_map/<journey_map_id>', methods=['POST'])
def delete_journey_map_route(journey_map_id):
    """Delete a journey map."""
    try:
        # Check if journey_maps directory exists
        JOURNEY_MAPS_DIR = Path('journey_maps')
        if not JOURNEY_MAPS_DIR.exists():
            return jsonify({'error': 'Journey maps directory not found'}), 404
        
        # If the journey_map_id is "Unknown Project", find and delete the most recent journey map with that project name
        if journey_map_id == "Unknown Project":
            journey_map_files = sorted(JOURNEY_MAPS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            for file in journey_map_files:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if data.get('project_name') == 'Unknown Project':
                            os.remove(file)
                            logger.info(f"Deleted journey map file: {file}")
                            return jsonify({'message': 'Journey map deleted successfully'})
                except Exception as e:
                    logger.error(f"Error reading journey map file {file}: {str(e)}")
                    continue
            return jsonify({'error': 'Journey map not found'}), 404
        
        # For regular journey map IDs, find and delete the specific file
        for file in JOURNEY_MAPS_DIR.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('id') == journey_map_id:
                        os.remove(file)
                        logger.info(f"Deleted journey map file: {file}")
                        return jsonify({'message': 'Journey map deleted successfully'})
            except Exception as e:
                logger.error(f"Error reading journey map file {file}: {str(e)}")
                continue
        
        return jsonify({'error': 'Journey map not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting journey map: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test_interview')
def test_interview():
    """Create a test interview with sample data."""
    try:
        # Pre-configured test data
        project_name = "Login Redesign"
        interview_type = "Application Interview"
        transcript = """
Interviewer: Can you walk me through your experience with the login process?

You: I hate having to go through this screen just to reset my password. The process is really frustrating. First, I have to click through multiple pages, then wait for an email, and sometimes the email never arrives.

Interviewer: How often do you need to reset your password?

You: At least once a month because the system requires password changes. It's particularly annoying on mobile because the interface is clunky.

Interviewer: What would make this process better for you?

You: I wish there was a simpler way, maybe using biometrics or a one-click reset option. Also, the mobile interface needs serious improvement.
"""
        analysis = """
# Interview Analysis

## Key Pain Points
- Frustrating password reset process
- Multiple pages to navigate
- Email delivery issues
- Frequent mandatory password changes
- Poor mobile interface

## User Needs
- Simpler authentication process
- Better mobile experience
- More reliable password reset system

## Recommendations
1. Implement biometric authentication
2. Streamline password reset flow
3. Optimize mobile interface
4. Review password expiration policy
"""
        
        # Sample form data with all card fields
        form_data = {
            'participant_name': 'Sam P.',
            'tags': ['frustration', 'mobile', 'authentication'],
            'status': 'Validated',
            'emotion': 'Angry',
            'author': 'M. Li',
            'role': 'Product Manager',
            'experience_level': 'Senior',
            'department': 'Engineering'
        }
        
        # Save the test interview
        interview_id = save_interview_data(
            project_name=project_name,
            interview_type=interview_type,
            transcript=transcript,
            analysis=analysis,
            form_data=form_data
        )
        
        flash('Test interview created successfully', 'success')
        return redirect(url_for('archive'))
        
    except Exception as e:
        logger.error(f"Error creating test interview: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error creating test interview', 'error')
        return redirect(url_for('archive'))

@app.route('/start_interview', methods=['POST'])
def start_interview():
    data = request.get_json()
    interview_type = data.get('interview_type')
    project_name = data.get('project_name')
    project_description = data.get('project_description')
    
    if not all([interview_type, project_name, project_description]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        # Get the appropriate interview prompt based on type
        interview_prompt = get_interview_prompt(interview_type, project_name, project_description)
        
        # Initialize the conversation with the system prompt
        conversation = [
            {"role": "system", "content": BASE_SYSTEM_PROMPT},
            {"role": "system", "content": interview_prompt}
        ]
        
        # Store the conversation in the session
        session['conversation'] = conversation
        session['interview_type'] = interview_type
        session['project_name'] = project_name
        session['project_description'] = project_description
        
        return jsonify({
            'status': 'success',
            'message': 'Interview started successfully',
            'interview_type': interview_type,
            'project_name': project_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload_transcript', methods=['GET', 'POST'])
def upload_transcript():
    if request.method == 'GET':
        return render_template('upload_transcript.html')
        
    try:
        # Extract form data
        researcher = json.loads(request.form.get('researcher', '{}'))
        project = json.loads(request.form.get('project', '{}'))
        interviewee = json.loads(request.form.get('interviewee', '{}'))
        technology = json.loads(request.form.get('technology', '{}'))
        transcript_name = request.form.get('transcriptName')
        consent = request.form.get('consent') == 'true'
        
        if not all([researcher, project, transcript_name, consent]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get the transcript file
        transcript_file = request.files.get('transcriptFile')
        if not transcript_file:
            return jsonify({'error': 'No transcript file provided'}), 400
            
        # Read and process the transcript
        transcript_text = transcript_file.read().decode('utf-8')
        
        # Process transcript into chunks
        chunks = []
        current_chunk = {
            'text': '',
            'speaker': '',
            'start_time': None,
            'end_time': None,
            'metadata': {
                'emotion': None,
                'emotion_intensity': 0,
                'theme': [],
                'insightTag': [],
                'sentiment_score': 0
            }
        }
        
        # Split transcript into chunks by speaker
        lines = transcript_text.split('\n')
        for line in lines:
            if ': ' in line:  # New speaker
                if current_chunk['text']:  # Save previous chunk
                    # Analyze chunk semantics
                    semantic_data = analyze_chunk_semantics(current_chunk['text'])
                    current_chunk['metadata'].update(semantic_data)
                    chunks.append(current_chunk.copy())
                    
                    # Reset current chunk
                    current_chunk = {
                        'text': '',
                        'speaker': '',
                        'start_time': None,
                        'end_time': None,
                        'metadata': {
                            'emotion': None,
                            'emotion_intensity': 0,
                            'theme': [],
                            'insightTag': [],
                            'sentiment_score': 0
                        }
                    }
                
                # Process new line
                speaker, text = line.split(': ', 1)
                current_chunk['speaker'] = speaker
                current_chunk['text'] = text
            else:  # Continuation of previous speaker
                current_chunk['text'] += f" {line.strip()}"
        
        # Don't forget to process the last chunk
        if current_chunk['text']:
            semantic_data = analyze_chunk_semantics(current_chunk['text'])
            current_chunk['metadata'].update(semantic_data)
            chunks.append(current_chunk)
        
        # Generate a unique ID for the transcript
        transcript_id = str(uuid.uuid4())
        
        # Create the transcript data structure
        transcript_data = {
            'id': transcript_id,
            'transcript_name': transcript_name,
            'project_name': project.get('name'),
            'interview_type': project.get('type'),
            'project_description': project.get('description'),
            'date': datetime.now().isoformat(),
            'transcript': transcript_text,
            'chunks': chunks,  # Add the processed chunks
            'metadata': {
                'researcher': researcher,
                'interviewee': interviewee,
                'technology': technology,
                'interview_details': json.loads(request.form.get('metadata', '{}')),
                'consent': consent
            }
        }
        
        # Create interviews directory if it doesn't exist
        INTERVIEWS_DIR.mkdir(exist_ok=True)
        
        # Save the transcript to the interviews directory
        transcript_path = INTERVIEWS_DIR / f"{transcript_id}.json"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2)
        
        # Add to vector store
        try:
            vector_store = VectorStore()
            vector_store.add_document(transcript_data)
        except Exception as e:
            logger.error(f"Error adding transcript to vector store: {str(e)}")
            # Continue even if vector store update fails
        
        return jsonify({
            'status': 'success',
            'message': 'Transcript uploaded successfully',
            'transcript_id': transcript_id
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return jsonify({'error': 'Invalid form data format'}), 400
    except Exception as e:
        logger.error(f"Error uploading transcript: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    """Advanced search endpoint that supports text, semantic, emotion, and insight tag searches."""
    if request.method == 'GET':
        return render_template('advanced_search.html')
        
    try:
        data = request.form
        query = data.get('query', '').strip()
        search_type = data.get('type', 'text').lower()
        limit = int(data.get('limit', 10))

        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400

        if search_type not in ['text', 'semantic', 'emotion', 'insight']:
            return jsonify({'error': f'Invalid search type: {search_type}'}), 400

        # Initialize the ProcessedInterviewStore
        store = ProcessedInterviewStore()
        
        # Perform the search based on type
        results = store.search(query, search_type=search_type, limit=limit)
        
        # Format results for response
        formatted_results = []
        for result in results:
            formatted_result = {
                'interview_id': result['interview_id'],
                'chunk_id': result['chunk_id'],
                'project_name': result['project_name'],
                'content': result['content'],
                'similarity': result['similarity'],
                'timestamp': result['timestamp'],
                'metadata': {
                    'emotion': result['metadata'].get('emotion', 'neutral'),
                    'emotion_intensity': result['metadata'].get('emotion_intensity', 0.5),
                    'themes': result['metadata'].get('themes', []),
                    'insight_tags': result['metadata'].get('insight_tags', []),
                    'related_feature': result['metadata'].get('related_feature')
                }
            }
            formatted_results.append(formatted_result)

        return jsonify({
            'results': formatted_results,
            'total': len(formatted_results),
            'query': query,
            'type': search_type,
            'message': f'Found {len(formatted_results)} results for {search_type} search: "{query}"'
        })

    except Exception as e:
        app.logger.error(f"Error in advanced search: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/interviews')
def interviews_page():
    """Display the interviews page with interviews grouped by project."""
    try:
        # Get all interviews
        interviews = list_interviews()
        
        # Group interviews by project
        projects_dict = {}
        for interview in interviews:
            project_name = interview.get('project_name', 'Unassigned')
            if project_name not in projects_dict:
                projects_dict[project_name] = {
                    'name': project_name,
                    'interview_list': []
                }
            projects_dict[project_name]['interview_list'].append(interview)
        
        # Convert to list and sort by project name
        formatted_projects = list(projects_dict.values())
        formatted_projects.sort(key=lambda x: x['name'])
        
        # Add "All Projects" as the first option
        all_projects = {
            'name': 'All Projects',
            'interview_list': interviews
        }
        formatted_projects.insert(0, all_projects)
        
        return render_template('interviews.html', projects=formatted_projects)
    except Exception as e:
        logger.error(f"Error in interviews_page: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a list with just the "All Projects" option on error
        return render_template('interviews.html', projects=[{
            'name': 'All Projects',
            'interview_list': []
        }])

@app.template_filter('strftime')
def strftime_filter(date, format='%Y-%m-%d'):
    """Convert a date to a formatted string."""
    if not date:
        return ''
    if isinstance(date, str):
        try:
            # Try parsing different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    date = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    continue
            if isinstance(date, str):  # If still a string, parsing failed
                return date
        except Exception:
            return date
    try:
        return date.strftime(format)
    except Exception:
        return str(date)

@app.route('/new_project')
def new_project():
    """Display the new project creation page."""
    try:
        return render_template('new_project.html')
    except Exception as e:
        logger.error(f"Error in new_project: {str(e)}")
        logger.error(traceback.format_exc())
        return redirect(url_for('home'))

@app.route('/create_project', methods=['POST'])
def create_project():
    """Handle new project creation."""
    try:
        # Basic project info
        project_name = request.form.get('project_name')
        description = request.form.get('description')
        
        # Problem space
        business_problem = request.form.get('business_problem')
        stakeholders = request.form.get('stakeholders', '').split(',')
        stakeholders = [s.strip() for s in stakeholders if s.strip()]
        
        # Research methods
        methods = request.form.getlist('methods[]')
        
        # Research plan
        research_objectives = request.form.get('research_objectives')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # Action type
        action = request.form.get('action', 'start')  # 'start' or 'draft'

        # Validate required fields
        if not all([project_name, description, business_problem]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('new_project'))

        # Create projects directory if it doesn't exist
        projects_dir = Path('projects')
        projects_dir.mkdir(exist_ok=True)

        # Generate a unique project ID
        project_id = str(uuid.uuid4())

        # Create project data
        project_data = {
            'id': project_id,
            'name': project_name,
            'description': description,
            'business_problem': business_problem,
            'stakeholders': stakeholders,
            'methods': methods,
            'research_objectives': research_objectives,
            'start_date': start_date,
            'end_date': end_date,
            'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'status': 'draft' if action == 'draft' else 'active'
        }

        # Handle file uploads
        if 'file' in request.files:
            files = request.files.getlist('file')
            if any(files):
                # Create assets directory for this project
                assets_dir = projects_dir / project_id / 'assets'
                assets_dir.mkdir(parents=True, exist_ok=True)
                
                uploaded_files = []
                for file in files:
                    if file and file.filename:
                        # Secure the filename
                        filename = secure_filename(file.filename)
                        file_path = assets_dir / filename
                        file.save(file_path)
                        uploaded_files.append(filename)
                
                project_data['assets'] = uploaded_files

        # Save project data
        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)

        flash('Project created successfully!', 'success')
        if action == 'draft':
            return redirect(url_for('home'))
        return redirect(url_for('project_dashboard', project_id=project_id))
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error creating project. Please try again.', 'error')
        return redirect(url_for('new_project'))

@app.route('/project/<project_id>')
def project_dashboard(project_id):
    """Display the project dashboard."""
    try:
        # Load project data
        projects_dir = Path('projects')
        project_file = projects_dir / f"{project_id}.json"
        
        if not project_file.exists():
            flash('Project not found.', 'error')
            return redirect(url_for('home'))
            
        with open(project_file) as f:
            project = json.load(f)
            
        # Get project interviews
        interviews = list_interviews()
        project_interviews = [i for i in interviews if i.get('project_name') == project.get('name')]
        
        return render_template('project_dashboard.html', 
                             project=project,
                             interviews=project_interviews)
    except Exception as e:
        logger.error(f"Error in project_dashboard: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading project dashboard.', 'error')
        return redirect(url_for('home'))

@app.route('/delete_project/<project_id>', methods=['POST'])
def delete_project_route(project_id):
    """Delete a project and its associated files."""
    try:
        # Define project file path
        PROJECTS_DIR = Path('projects')
        project_file = PROJECTS_DIR / f"{project_id}.json"
        
        if not project_file.exists():
            return jsonify({'status': 'error', 'error': 'Project not found'}), 404
            
        # Delete the project file
        project_file.unlink()
        
        # Return success response
        return jsonify({'status': 'success', 'message': 'Project deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500

def get_interview(interview_id):
    """Get interview data by ID."""
    try:
        # Check both regular and raw interview directories
        possible_paths = [
            os.path.join('interviews', f'{interview_id}.json'),
            os.path.join('interviews', 'raw', f'{interview_id}.json'),
            os.path.join('interviews', 'processed', f'{interview_id}.json')
        ]
        
        for file_path in possible_paths:
            if os.path.exists(file_path):
                logger.info(f"Found interview file at: {file_path}")
                with open(file_path, 'r') as f:
                    interview_data = json.load(f)
                    # Add file path to data for reference
                    interview_data['_file_path'] = file_path
                    return interview_data
                    
        logger.error(f"Interview file not found: {interview_id}")
        logger.error(f"Checked paths: {possible_paths}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading interview {interview_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def save_interview(interview_data):
    """Save interview data to a JSON file."""
    try:
        # Ensure required fields are present
        required_fields = ['id', 'title', 'type', 'project_id', 'created_at', 'created_by']
        for field in required_fields:
            if field not in interview_data:
                logger.error(f"Missing required field: {field}")
                return False
                
        # Ensure interviews directory exists
        os.makedirs('interviews', exist_ok=True)
        
        # Construct file path
        file_path = os.path.join('interviews', f"{interview_data['id']}.json")
        
        # Validate chunks if present
        if 'chunks' in interview_data:
            for chunk in interview_data['chunks']:
                if not all(k in chunk for k in ['start_time', 'end_time', 'speaker', 'text']):
                    logger.error("Invalid chunk format")
                    return False
                    
        # Save interview data
        with open(file_path, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def process_semantic_chunks(transcript_text):
    """Process transcript into semantic chunks, filtering out low-information responses."""
    try:
        chunks = []
        current_chunk = None
        current_speaker = None
        
        for line in transcript_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for speaker change
            if '[' in line and ']' in line:
                speaker_match = re.search(r'\[(.*?)\]', line)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    # Save previous chunk if it exists
                    if current_chunk:
                        # Analyze the chunk
                        chunk_id = str(uuid.uuid4())
                        analysis = semantic_analyzer.analyze_chunk(current_chunk['text'])
                        current_chunk['metadata'].update(analysis['metadata'])
                        current_chunk['id'] = chunk_id
                        chunks.append(current_chunk)
                    
                    # Start new chunk
                    current_chunk = {
                        'speaker': speaker,
                        'text': '',
                        'metadata': {}
                    }
                    current_speaker = speaker
            else:
                # Add line to current chunk
                if current_chunk:
                    if current_chunk['text']:
                        current_chunk['text'] += ' '
                    current_chunk['text'] += line
        
        # Add final chunk
        if current_chunk and current_chunk['text'].strip():
            chunk_id = str(uuid.uuid4())
            analysis = semantic_analyzer.analyze_chunk(current_chunk['text'])
            current_chunk['metadata'].update(analysis['metadata'])
            current_chunk['id'] = chunk_id
            chunks.append(current_chunk)
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error processing semantic chunks: {str(e)}")
        logger.error(traceback.format_exc())
        return []

@app.route('/api/analyze/<interview_id>', methods=['POST'])
def analyze_interview(interview_id):
    """Generate semantic analysis for an interview if it doesn't exist."""
    try:
        interview_file = Path('interviews/raw') / f"{interview_id}.json"
        if not interview_file.exists():
            return jsonify({'error': 'Interview not found'}), 404
            
        with open(interview_file) as f:
            interview_data = json.load(f)
            
        # Check if semantic chunks already exist
        if interview_data.get('chunks'):
            return jsonify({
                'status': 'exists',
                'message': 'Interview already has semantic analysis'
            })
        
        # Process transcript into semantic chunks
        transcript = interview_data.get('transcript', '')
        if not transcript:
            return jsonify({'error': 'No transcript found'}), 400
            
        chunks = process_semantic_chunks(transcript)
        
        # Analyze each chunk for sentiment and themes
        for chunk in chunks:
            if chunk['speaker'] != 'Stephen':  # Only analyze participant responses
                semantic_data = analyze_chunk_semantics(chunk['text'])
                chunk['metadata'].update({
                    'sentiment': semantic_data.get('emotion', 'neutral'),
                    'themes': semantic_data.get('theme', []),
                    'insightTag': semantic_data.get('insightTag', []),
                    'relatedFeature': semantic_data.get('theme')[0] if semantic_data.get('theme') else None
                })
        
        # Update interview with chunks
        interview_data['chunks'] = chunks
        
        # Save updated interview back to the same location
        with open(interview_file, 'w') as f:
            json.dump(interview_data, f, indent=2)
            
        return jsonify({
            'status': 'success',
            'message': 'Semantic analysis completed',
            'chunks': chunks
        })
        
    except Exception as e:
        logger.error(f"Error in semantic analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/chunks/<chunk_id>', methods=['PUT'])
def update_chunk(chunk_id):
    """Update a specific chunk in an interview."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Get the interview ID from the chunk ID (format: interview_id_chunk_number)
        interview_id = chunk_id.split('_')[0]
        
        # Load the interview
        interview = load_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
            
        # Find and update the chunk
        for chunk in interview.get('chunks', []):
            if chunk.get('chunkId') == chunk_id:
                # Update text if provided
                if 'text' in data:
                    chunk['text'] = data['text']
                
                # Update metadata if provided
                if 'metadata' in data:
                    chunk['metadata'].update(data['metadata'])
                
                # Save the updated interview
                if not update_interview_data(interview_id, interview):
                    return jsonify({'error': 'Failed to save changes'}), 500
                    
                return jsonify({
                    'status': 'success',
                    'message': 'Chunk updated successfully',
                    'chunk': chunk
                })
        
        return jsonify({'error': 'Chunk not found'}), 404
        
    except Exception as e:
        logger.error(f"Error updating chunk: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def markdown(text):
    return markdown2.markdown(text)

app.jinja_env.filters['markdown'] = markdown

@app.route('/api/search/advanced', methods=['POST'])
def api_advanced_search():
    """Advanced search endpoint that supports natural language queries and various search types."""
    try:
        data = request.get_json()
        if not data:
            app.logger.error("No JSON data received in request")
            return jsonify({'error': 'No search data provided'}), 400

        query = data.get('query', '').strip()
        search_type = data.get('type', 'semantic').lower()  # Default to semantic search
        limit = data.get('limit', 10)

        app.logger.info(f"Processing advanced search - Query: '{query}', Type: {search_type}, Limit: {limit}")

        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400

        if search_type not in ['text', 'semantic', 'emotion', 'insight', 'theme']:
            app.logger.error(f"Invalid search type received: {search_type}")
            return jsonify({'error': f'Invalid search type: {search_type}'}), 400

        # Initialize the ProcessedInterviewStore
        store = ProcessedInterviewStore()
        
        try:
            # Perform the search based on type
            app.logger.info(f"Executing {search_type} search...")
            results = store.search(query, search_type=search_type, limit=limit)
            app.logger.info(f"Search completed. Found {len(results)} results")
            
            # Format results for response
            formatted_results = []
            for result in results:
                formatted_result = {
                    'interview_id': result['interview_id'],
                    'chunk_id': result['chunk_id'],
                    'project_name': result['project_name'],
                    'content': result['content'],
                    'similarity': result.get('similarity', 1.0),
                    'timestamp': result['timestamp'],
                    'interviewee_name': result.get('interviewee_name', ''),
                    'transcript_name': result.get('transcript_name', ''),
                    'metadata': {
                        'emotion': result['metadata'].get('emotion', 'neutral'),
                        'emotion_intensity': result['metadata'].get('emotion_intensity', 0.5),
                        'themes': result['metadata'].get('themes', []),
                        'insight_tags': result['metadata'].get('insight_tags', []),
                        'related_feature': result['metadata'].get('related_feature')
                    }
                }
                formatted_results.append(formatted_result)

            response_data = {
                'results': formatted_results,
                'total': len(formatted_results),
                'query': query,
                'type': search_type,
                'message': f"Found {len(formatted_results)} results for your search"
            }

            if not formatted_results:
                app.logger.info(f"No results found for query: '{query}'")
                response_data['message'] = "No results found. Try adjusting your search terms or using a different search type."

            return jsonify(response_data)

        except Exception as search_error:
            app.logger.error(f"Error during search operation: {str(search_error)}")
            app.logger.error(traceback.format_exc())
            return jsonify({
                'error': 'Error performing search',
                'message': 'An error occurred while searching. Please try again or contact support if the problem persists.'
            }), 500

    except Exception as e:
        app.logger.error(f"Error in advanced search endpoint: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500

@app.route('/annotated-transcript/<interview_id>')
@app.route('/annotated-transcript/<interview_id>/<int:page>')
def view_annotated_transcript(interview_id, page=1):
    try:
        # Look for the processed file
        processed_file = f'interviews/processed/{interview_id}.json'
        if not os.path.exists(processed_file):
            return jsonify({'error': 'Interview not found'}), 404

        with open(processed_file, 'r') as f:
            interview_data = json.load(f)

        # Extract metadata and chunks
        metadata = interview_data.get('metadata', {})
        raw_chunks = interview_data.get('chunks', [])

        # Process chunks to flatten the structure
        processed_chunks = []
        for chunk in raw_chunks:
            chunk_analysis = chunk.get('analysis', {})
            chunk_data = {
                'id': chunk.get('id', str(uuid.uuid4())),
                'timestamp': chunk.get('timestamp', ''),
                'text': chunk.get('combined_text', ''),
                'emotion': chunk_analysis.get('emotion', ''),
                'emotion_intensity': chunk_analysis.get('emotion_intensity', 0),
                'themes': chunk_analysis.get('themes', []),
                'insight_tags': chunk_analysis.get('insight_tags', []),
                'related_feature': chunk_analysis.get('related_feature'),
                'entries': chunk.get('entries', [])
            }
            processed_chunks.append(chunk_data)

        # Pagination
        items_per_page = 50
        total_chunks = len(processed_chunks)
        total_pages = (total_chunks + items_per_page - 1) // items_per_page

        # Validate page number
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # Get chunks for current page
        current_chunks = processed_chunks[start_idx:end_idx]
        
        # Prepare the response data
        response_data = {
            'interviewee_name': metadata.get('interviewee', {}).get('name', 'Unknown'),
            'project_name': metadata.get('project', {}).get('name', 'Unknown Project'),
            'date': metadata.get('date', 'No Date'),
            'chunks': current_chunks,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_chunks': total_chunks,
                'items_per_page': items_per_page
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error loading transcript: {str(e)}")
        return jsonify({'error': 'Failed to load transcript'}), 500

@app.route('/api/discovery/conversation', methods=['POST'])
def discovery_conversation():
    """Handle messages in the discovery conversation."""
    # Immediate debug logging
    logger.info("=== Starting discovery conversation request ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request raw data: {request.get_data(as_text=True)}")
    
    try:
        logger.info("Parsing request JSON")
        data = request.get_json()
        logger.info(f"Request data: {json.dumps(data, indent=2)}")
        
        if not data or 'message' not in data:
            logger.error("No message provided in request")
            return jsonify({'error': 'No message provided'}), 400
            
        message = data['message']
        conversation_history = data.get('conversation_history', [])
        
        logger.info(f"Processing message: {message}")
        logger.info(f"Conversation history: {json.dumps(conversation_history, indent=2)}")
        
        # Initialize OpenAI client
        try:
            logger.info("Creating OpenAI client")
            client = create_openai_client()
            if not client:
                logger.error("Failed to initialize OpenAI client")
                return jsonify({'error': 'Failed to initialize AI client: No API key found'}), 500
            logger.info("Successfully initialized OpenAI client")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Failed to initialize AI client: {str(e)}'}), 500
            
        # Initialize DiscoveryGPT
        try:
            discovery_gpt = DiscoveryGPT(client)
            logger.info("Successfully initialized DiscoveryGPT")
        except Exception as e:
            logger.error(f"Error initializing DiscoveryGPT: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Failed to initialize DiscoveryGPT: {str(e)}'}), 500
        
        # Process the message using async_to_sync
        try:
            logger.info("Processing message with DiscoveryGPT")
            result = async_to_sync(discovery_gpt.process_message)(message, conversation_history)
            logger.info(f"Received result: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Error processing message: {str(e)}'}), 500
        
        # If the conversation is complete and we have project data
        if result.get('isComplete') and 'project' in result:
            try:
                # Save the project data
                project_data = result['project']
                
                # Create project directory if it doesn't exist
                project_dir = os.path.join('projects', project_data['name'])
                os.makedirs(project_dir, exist_ok=True)
                
                # Save conversation history
                conversation_file = os.path.join(project_dir, 'discovery_conversation.json')
                with open(conversation_file, 'w') as f:
                    json.dump({
                        'conversation': conversation_history + [
                            {'role': 'user', 'content': message},
                            {'role': 'assistant', 'content': result['response']}
                        ],
                        'completed_at': datetime.now().isoformat()
                    }, f, indent=2)
                    
                # Save project data
                project_file = os.path.join(project_dir, 'project.json')
                with open(project_file, 'w') as f:
                    json.dump(project_data, f, indent=2)
                    
                logger.info(f"Saved project data for {project_data['name']}")
            except Exception as e:
                logger.error(f"Error saving project data: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue even if saving fails
                
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Unexpected error in discovery conversation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/interviews/raw/<interview_id>.json')
def get_raw_interview(interview_id):
    """Serve a raw interview file."""
    try:
        file_path = Path('interviews/raw') / f"{interview_id}.json"
        if not file_path.exists():
            return jsonify({'error': 'Interview not found'}), 404
            
        with open(file_path) as f:
            return jsonify(json.load(f))
    except Exception as e:
        logger.error(f"Error serving raw interview: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/interviews/raw')
def list_raw_interviews():
    """List all raw interviews."""
    try:
        interviews = []
        raw_dir = Path('interviews/raw')
        
        if not raw_dir.exists():
            return jsonify([])
            
        for file in raw_dir.glob('*.json'):
            try:
                with open(file) as f:
                    interview = json.load(f)
                    # Extract interview ID from filename
                    interview_id = file.stem
                    
                    # Create summary dictionary
                    summary = {
                        'id': interview_id,
                        'title': interview.get('title', 'Untitled Interview'),
                        'project_name': interview.get('project_name', 'Unassigned'),
                        'interview_type': interview.get('interview_type', 'Interview'),
                        'date': interview.get('date', ''),
                        'transcript': interview.get('transcript', ''),
                        'interviewee': interview.get('interviewee', ''),
                        'metadata': interview.get('metadata', {}),
                        'preview': interview.get('preview', '')
                    }
                    interviews.append(summary)
            except Exception as e:
                logger.error(f"Error reading interview file {file}: {str(e)}")
                continue
                
        # Sort by date, most recent first
        interviews.sort(key=lambda x: x.get('date', ''), reverse=True)
        return jsonify(interviews)
        
    except Exception as e:
        logger.error(f"Error listing raw interviews: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get a list of all projects that have interviews."""
    try:
        projects = set()
        # Check both interviews and interviews/raw directories
        interview_dirs = ['interviews', 'interviews/raw']
        
        for dir_path in interview_dirs:
            if os.path.exists(dir_path):
                for file in Path(dir_path).glob('*.json'):
                    try:
                        with open(file) as f:
                            interview_data = json.load(f)
                            project_name = interview_data.get('project_name')
                            project_id = interview_data.get('project_id', project_name)
                            
                            if project_name:
                                projects.add((project_name, project_id))
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"Error reading file {file}: {str(e)}")
                        continue
        
        # Convert to list of dictionaries
        project_list = [{'name': name, 'id': id} for name, id in projects]
        logger.info(f"Found {len(project_list)} projects")
        return jsonify(project_list)
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_persona', methods=['POST'])
def api_generate_persona():
    try:
        data = request.json
        project_id = data.get('project_id')
        interview_ids = data.get('interview_ids', [])
        model = data.get('model', 'gpt-4')

        if not project_id or not interview_ids:
             return jsonify({'error': 'Project ID and at least one interview ID are required.'}), 400

        interview_data = []
        for interview_id in interview_ids:
            interview = get_interview(interview_id)
            if interview:
                # Ensure transcript exists, default to empty string if not
                interview['transcript'] = interview.get('transcript', '') 
                interview_data.append(interview)

        if not interview_data:
            return jsonify({'error': 'No valid interviews found for the provided IDs.'}), 404

        interview_texts = [i['transcript'] for i in interview_data]

        # Generate persona using the multi-step process
        from daria_interview_tool.persona_gpt import generate_persona_from_interviews
        # Pass the user's preferred base model (e.g., gpt-4) for synthesis
        # The function itself will upgrade to gpt-4-turbo for final generation
        persona_data = generate_persona_from_interviews(
            interview_texts=interview_texts,
            project_name=project_id,
            model=model # Pass user's choice for synthesis stage
        )

        # Successfully generated
        return jsonify(persona_data)

    except ValueError as ve:
        # Catch specific errors raised from persona_gpt (like JSON parsing, validation, context limit)
        logger.error(f"ValueError during persona generation: {str(ve)}")
        # Return a specific error message to the frontend
        return jsonify({"error": f"Persona Generation Error: {str(ve)}"}), 500
    except NotImplementedError as nie:
        # Catch if Claude model was selected but logic isn't updated
        logger.error(f"NotImplementedError: {str(nie)}")
        return jsonify({"error": str(nie)}), 501 # 501 Not Implemented
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in /api/generate_persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "An unexpected internal server error occurred."}), 500

# Helper function to generate researcher avatar
def generate_researcher_avatar(survey_responses):
    try:
        # Create a simple avatar based on survey responses
        avatar_id = random.randint(1000, 9999)
        img_width, img_height = 400, 400
        
        # Background color based on research type
        if survey_responses.get('research_type') == 'qualitative':
            bg_color = (65, 105, 225)  # Royal Blue for qualitative
        else:
            bg_color = (46, 139, 87)   # Sea Green for quantitative
        
        # Create image with background
        image = Image.new('RGB', (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Add some visual elements based on survey responses
        # Method preference
        if survey_responses.get('methods') == 'interviews':
            # Draw interview icon (two circles representing people)
            draw.ellipse((100, 100, 180, 180), fill=(255, 255, 255, 128))
            draw.ellipse((220, 100, 300, 180), fill=(255, 255, 255, 128))
        else:
            # Draw survey icon (paper with lines)
            draw.rectangle((150, 100, 250, 200), fill=(255, 255, 255, 128))
            draw.line((170, 130, 230, 130), fill=(0, 0, 0), width=2)
            draw.line((170, 150, 230, 150), fill=(0, 0, 0), width=2)
            draw.line((170, 170, 230, 170), fill=(0, 0, 0), width=2)
        
        # Timeline affects border
        if survey_responses.get('timeline') == 'urgent':
            # Red border for urgent timeline
            border_width = 10
            draw.rectangle((0, 0, img_width-1, img_height-1), outline=(220, 20, 60), width=border_width)
        
        # Budget impacts bottom text
        if survey_responses.get('budget') == 'limited':
            budget_text = "Cost-Effective Approach"
        else:
            budget_text = "Comprehensive Approach"
        
        # Use a default font if available
        try:
            font = ImageFont.truetype("Arial", 20)
            draw.text((img_width//2, img_height-50), budget_text, fill=(255, 255, 255), anchor="ms", font=font)
        except IOError:
            # If font is not available, skip text
            pass
        
        # Save the image
        avatar_path = f"static/images/researcher_avatar_{avatar_id}.png"
        os.makedirs(os.path.dirname(os.path.join(app.root_path, avatar_path)), exist_ok=True)
        image.save(os.path.join(app.root_path, avatar_path))
        
        return avatar_path
    except Exception as e:
        logger.error(f"Error generating avatar: {str(e)}")
        return "static/images/default_researcher.png"

# Generate recommendations based on survey responses
def generate_research_recommendations(survey_responses):
    """Generate research method recommendations based on survey responses."""
    recommendations = {}
    
    # Primary objective
    objective = survey_responses.get('primary_objective')
    research_type = survey_responses.get('research_type')
    timeline = survey_responses.get('timeline')
    budget = survey_responses.get('budget')
    methods = survey_responses.get('methods')
    
    # Primary method
    if objective == 'user_needs':
        if research_type == 'qualitative':
            recommendations['primary_method'] = "In-depth user interviews focusing on needs, pain points, and goals"
        else:
            recommendations['primary_method'] = "Large-scale survey with targeted questions about user priorities and pain points"
    else:  # market validation
        if research_type == 'qualitative':
            recommendations['primary_method'] = "Competitor analysis and stakeholder interviews to validate market potential"
        else:
            recommendations['primary_method'] = "Market size assessment with segmentation analysis and competitor benchmarking"
    
    # Secondary method
    if timeline == 'urgent':
        if budget == 'limited':
            recommendations['secondary_method'] = "Rapid guerrilla usability testing with 5-8 participants"
        else:
            recommendations['secondary_method'] = "Fast-turnaround remote moderated testing with 12-15 participants"
    else:
        if budget == 'limited':
            recommendations['secondary_method'] = "Community forum/social media analysis to understand user conversations"
        else:
            recommendations['secondary_method'] = "Multi-phase research plan with diary studies and longitudinal analysis"
    
    # Innovative approach
    if methods == 'interviews':
        if budget == 'limited':
            recommendations['innovative_approach'] = "Virtual workshop with collaborative whiteboarding to explore concepts"
        else:
            recommendations['innovative_approach'] = "Design sprint with key stakeholders and representative users"
    else:
        if budget == 'limited':
            recommendations['innovative_approach'] = "Mobile ethnography using participant-captured videos/photos"
        else:
            recommendations['innovative_approach'] = "AI-powered sentiment analysis across customer touchpoints"
    
    return recommendations

# Research Survey and Adventure API Routes
@app.route('/api/submit-research-survey', methods=['POST'])
def submit_research_survey():
    """Handle research survey response submission."""
    try:
        data = request.json
        logger.info(f"Received survey data: {data}")
        
        # Process survey responses
        survey_responses = {
            'primary_objective': data.get('1'),
            'research_type': data.get('2'),
            'timeline': data.get('3'),
            'budget': data.get('4'),
            'methods': data.get('5')
        }
        
        # Generate avatar for researcher
        avatar_path = generate_researcher_avatar(survey_responses)
        if avatar_path:
            survey_responses['avatar_path'] = avatar_path
        else:
            survey_responses['avatar_path'] = 'static/images/default_researcher.png'
        
        # Generate recommendations
        recommendations = generate_research_recommendations(survey_responses)
        survey_responses['recommendations'] = recommendations
        
        # Store in session
        session['survey_responses'] = survey_responses
        
        # Save to database
        try:
            survey = ResearchSurveyResponse(
                primary_objective=survey_responses['primary_objective'],
                research_type=survey_responses['research_type'],
                timeline=survey_responses['timeline'],
                budget=survey_responses['budget'],
                methods=survey_responses['methods'],
                avatar_path=survey_responses['avatar_path'],
                recommendations=recommendations
            )
            db.session.add(survey)
            db.session.commit()
            logger.info(f"Survey response saved to database with ID: {survey.id}")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
        
        return jsonify({
            'success': True,
            'redirect': '/survey-results'
        })
    except Exception as e:
        logger.error(f"Error processing survey: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your responses.'
        })

@app.route('/api/survey-results', methods=['GET'])
def api_survey_results():
    """Return survey results and recommendations."""
    if 'survey_responses' not in session:
        return jsonify({
            'success': False,
            'message': 'No survey responses found. Please take the survey first.'
        })
    
    survey_responses = session.get('survey_responses', {})
    return jsonify({
        'success': True,
        'survey_responses': survey_responses
    })

@app.route('/api/game-state', methods=['GET'])
def game_state():
    """Get the current state of the research adventure game."""
    # Initialize or get game state
    if 'game_state' not in session:
        # Create initial game state
        game_state = {
            'research_methods': [
                {
                    'name': 'User Interviews',
                    'description': 'In-depth conversations with users to understand their needs, behaviors, and pain points.',
                    'key_researchers': ['Jakob Nielsen', 'Steve Portigal', 'Erika Hall'],
                    'common_techniques': ['Semi-structured interviews', 'Contextual inquiry', 'Laddering']
                },
                {
                    'name': 'Usability Testing',
                    'description': 'Observing users as they complete tasks with your product to identify usability issues.',
                    'key_researchers': ['Don Norman', 'Jakob Nielsen', 'Jared Spool'],
                    'common_techniques': ['Think-aloud protocol', 'Task analysis', 'Heuristic evaluation']
                },
                {
                    'name': 'Surveys & Questionnaires',
                    'description': 'Collecting quantitative and qualitative data from many users efficiently.',
                    'key_researchers': ['Likert', 'Dillman', 'Krosnick'],
                    'common_techniques': ['Likert scales', 'Multiple choice', 'Open-ended questions']
                }
            ],
            'discovered_methods': [],
            'current_location': 'Research Center',
            'history': [{
                'type': 'system',
                'text': """Welcome to the Research Discovery Adventure!

You find yourself in the Research Center, surrounded by different methodologies and approaches to understanding user needs. You have a mission to discover the best research methods for your project.

You can:
- Look around to explore the Research Center
- Move to different research method areas
- Explore specific methods in detail
- Learn about various techniques
- Talk to famous researchers for advice

Where would you like to start your research journey?"""
            }]
        }
        session['game_state'] = game_state
    
    return jsonify({
        'success': True,
        'game_state': session['game_state']
    })

@app.route('/api/game-action', methods=['POST'])
def game_action():
    """Handle game actions and commands."""
    data = request.json
    command = data.get('command', '').strip().lower()
    logger.info(f"Game action received: {command}")
    
    # Get or initialize game state
    if 'game_state' not in session:
        # This will create and return a new game state
        result = game_state()
        game_state_data = result.get_json()
        current_game_state = game_state_data['game_state']
    else:
        current_game_state = session.get('game_state', {})
    
    # Handle new game command
    if command == 'new game':
        # Reset game state
        result = game_state()
        game_state_data = result.get_json()
        current_game_state = game_state_data['game_state']
        session['game_state'] = current_game_state
        
        return jsonify({
            'success': True,
            'message': current_game_state['history'][0]['text'],
            'game_state': current_game_state
        })
    
    # Researcher conversations and method details
    researcher_info = {
        'jakob nielsen': {
            'expertise': 'Usability and User Experience',
            'famous_for': 'Heuristic Evaluation, Discount Usability Testing',
            'quote': "Bad usability is like having a store with a locked front door.",
            'advice': "Start with a small number of participants. You'll find that after testing 5 users, you've discovered most of the major usability issues."
        },
        'don norman': {
            'expertise': 'Cognitive Science and User-Centered Design',
            'famous_for': 'The Design of Everyday Things, User-Centered Design',
            'quote': "Good design is actually a lot harder to notice than poor design.",
            'advice': "Always remember that your users are people with goals, not just users of your system. Design for their goals, not for the technology."
        },
        'erika hall': {
            'expertise': 'Research Methods and Design',
            'famous_for': 'Just Enough Research',
            'quote': "The most expensive research is the research you don't do.",
            'advice': "Start with the right questions, not with the methods. Methods should serve your research questions, not the other way around."
        }
    }
    
    method_details = {
        'user interviews': {
            'overview': "User interviews are structured conversations designed to gather insights about users' experiences, needs, and pain points.",
            'when_to_use': "Early in the research process to understand user needs and goals, or later to dive deeper into specific issues.",
            'advantages': "Flexible, allows for follow-up questions, builds empathy, provides rich qualitative data.",
            'challenges': "Time-consuming, potential for bias, requires good interviewing skills, small sample sizes.",
            'key_techniques': [
                "Ask open-ended questions to encourage detailed responses",
                "Use the 'five whys' technique to get to underlying motivations",
                "Avoid leading questions that suggest a desired answer"
            ]
        },
        'usability testing': {
            'overview': "Usability testing involves observing users as they attempt to complete tasks with a product or prototype.",
            'when_to_use': "When you have a specific design or prototype to evaluate and want to identify usability issues.",
            'advantages': "Directly observes user behavior, identifies specific problems, provides clear evidence for stakeholders.",
            'challenges': "Can be resource-intensive to set up, may require special equipment, participation incentives.",
            'key_techniques': [
                "Think-aloud protocol: Ask users to verbalize their thoughts as they interact with the product",
                "Task-based testing: Have users complete specific, realistic tasks",
                "Remote testing: Use screen sharing software to test with geographically dispersed users"
            ]
        },
        'surveys': {
            'overview': "Surveys collect structured data from many users through standardized questions.",
            'when_to_use': "When you need quantitative data from a large sample, or to validate findings from qualitative research.",
            'advantages': "Reaches many users quickly, provides quantifiable data, cost-effective for large samples.",
            'challenges': "Limited depth, can't follow up on answers, response bias, question design is critical.",
            'key_techniques': [
                "Use Likert scales (1-5 or 1-7) for measuring attitudes",
                "Include a mix of closed and open-ended questions",
                "Keep surveys short to improve completion rates",
                "Test your survey with a small group before wide distribution"
            ]
        }
    }
    
    # Handle researcher conversations
    if any(name in command for name in researcher_info.keys()):
        for name, info in researcher_info.items():
            if name in command:
                response = f"You approach {name.title()}, known for expertise in {info['expertise']}.\n\n"
                response += f"'{info['quote']}'\n\n"
                response += f"Their advice for you: {info['advice']}"
                break
        else:
            response = "I'm not sure which researcher you'd like to talk to. Try asking about Jakob Nielsen, Don Norman, or Erika Hall."
    
    # Handle method exploration
    elif any(method in command for method in method_details.keys()):
        for method_name, details in method_details.items():
            if method_name in command:
                # Add to discovered methods if not already there
                method_discovered = False
                for discovered in current_game_state['discovered_methods']:
                    if discovered.get('name', '').lower() == method_name:
                        method_discovered = True
                        break
                
                if not method_discovered:
                    for method in current_game_state['research_methods']:
                        if method['name'].lower() == method_name or method_name in method['name'].lower():
                            current_game_state['discovered_methods'].append({
                                'name': method['name'],
                                'description': method['description'],
                                'researchers': method['key_researchers']
                            })
                            break
                
                response = f"**{method_name.title()} Method Overview**\n\n"
                response += f"{details['overview']}\n\n"
                response += f"**When to use:** {details['when_to_use']}\n\n"
                response += f"**Advantages:** {details['advantages']}\n\n"
                response += f"**Challenges:** {details['challenges']}\n\n"
                response += "**Key Techniques:**\n"
                for technique in details['key_techniques']:
                    response += f"- {technique}\n"
                
                current_game_state['current_location'] = method_name.title()
                break
        else:
            response = "I'm not sure which research method you'd like to explore. Try user interviews, usability testing, or surveys."
    
    # Handle look around command
    elif any(word in command for word in ['look', 'see', 'where', 'around']):
        current_location = current_game_state['current_location']
        
        if current_location == 'Research Center':
            response = """You're in the Research Center, a hub of activity where researchers plan their studies and analyze their findings.

Around you are different areas representing various research methods:
- User Interviews section with comfortable chairs and recording equipment
- Usability Testing lab with one-way mirrors and testing stations
- Surveys & Questionnaires area with statistical models and data visualizations

Each area contains experts and resources to help you learn more about that research method. Where would you like to go?"""
        else:
            # Return information about the current method location
            for method_name, details in method_details.items():
                if method_name in current_location.lower():
                    response = f"You're in the {current_location} area.\n\n"
                    response += f"{details['overview']}\n\n"
                    response += "You can see researchers working on projects and various tools related to this method."
                    break
            else:
                response = f"You're in the {current_location} area. Look around to see what's available, or try moving to a specific research method area."
    
    # Handle movement
    elif any(word in command for word in ['go', 'move', 'walk', 'head']):
        if 'center' in command or 'main' in command:
            current_game_state['current_location'] = 'Research Center'
            response = "You return to the Research Center, where you can see all the different research method areas."
        elif 'interview' in command:
            current_game_state['current_location'] = 'User Interviews'
            response = "You move to the User Interviews area, where researchers are conducting in-depth conversations with participants."
        elif 'usability' in command or 'testing' in command:
            current_game_state['current_location'] = 'Usability Testing'
            response = "You enter the Usability Testing lab, with its observation rooms and testing stations."
        elif 'survey' in command or 'questionnaire' in command:
            current_game_state['current_location'] = 'Surveys & Questionnaires'
            response = "You walk over to the Surveys & Questionnaires area, filled with statistical models and data analysis tools."
        else:
            response = "I'm not sure where you want to go. Try 'go to interviews', 'move to usability testing', or 'return to research center'."
    
    # Handle help command
    elif 'help' in command:
        response = """**Research Adventure Help**

You can use these commands:
- **Look/See**: Explore your current location
- **Go/Move to [location]**: Move to a different area (Research Center, User Interviews, Usability Testing, Surveys)
- **Explore [method]**: Learn details about a specific research method
- **Talk to [researcher]**: Get advice from famous researchers like Jakob Nielsen or Don Norman
- **Help**: Show this help message

Your goal is to discover different research methods and techniques to build your research plan."""
    
    # Default response
    else:
        response = "I'm not sure what you want to do. Try 'look around', 'explore user interviews', or 'help' for more options."
    
    # Save updated game state
    session['game_state'] = current_game_state
    
    return jsonify({
        'success': True,
        'message': response,
        'game_state': current_game_state
    })

@app.route('/api/transcript/<interview_id>')
def api_get_transcript(interview_id):
    """API endpoint to get interview transcript data as JSON."""
    try:
        # Load interview from raw directory
        interview_file = Path('interviews/raw') / f"{interview_id}.json"
        if not interview_file.exists():
            return jsonify({'error': 'Interview not found'}), 404
        
        with open(interview_file, 'r') as f:
            interview = json.load(f)
        
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        return jsonify(interview)
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        return jsonify({'error': 'Failed to retrieve transcript'}), 500

@app.route('/api/interviews/recent')
def get_recent_interviews():
    """Get the most recent interviews across all projects."""
    try:
        # Directories to check for interview files
        interview_dirs = ['interviews', 'interviews/raw']
        interviews = []
        
        # Read interviews from both directories
        for dir_path in interview_dirs:
            if os.path.exists(dir_path):
                # Get all JSON files in directory
                interview_files = list(Path(dir_path).glob('*.json'))
                
                # Sort by modification time, most recent first
                interview_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                for file in interview_files:
                    try:
                        with open(file) as f:
                            interview_data = json.load(f)
                            
                            # Extract interview ID from filename
                            interview_id = file.stem
                            
                            # Create standardized interview summary
                            summary = {
                                'id': interview_data.get('id', interview_id),
                                'title': interview_data.get('title', 'Untitled Interview'),
                                'project_name': interview_data.get('project_name', 'Unassigned'),
                                'participant_name': interview_data.get('interviewee', interview_data.get('participant_name', 'Anonymous')),
                                'created_at': interview_data.get('date', ''),
                                'type': interview_data.get('interview_type', 'Interview'),
                                'status': interview_data.get('status', 'Completed'),
                                'preview': interview_data.get('preview', '')
                            }
                            
                            # Check if we already have this interview (avoid duplicates)
                            if not any(i.get('id') == summary['id'] for i in interviews):
                                interviews.append(summary)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in file {file}")
                        continue
                    except Exception as e:
                        logger.error(f"Error reading interview file {file}: {str(e)}")
                        continue
        
        # Sort all interviews by date, most recent first
        interviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Return only the 10 most recent interviews
        return jsonify(interviews[:10])
        
    except Exception as e:
        logger.error(f"Error getting recent interviews: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Serve test_audio_endpoints.html directly from the root
@app.route('/test_audio_endpoints.html')
def test_audio_endpoints():
    return send_file('test_audio_endpoints.html')

@app.route('/api/interview-prompt', methods=['GET'])
def api_interview_prompt():
    """API endpoint to get interview prompt for a project."""
    try:
        project_name = request.args.get('project_name')
        if not project_name:
            logger.error("Project name is required for interview prompt")
            return jsonify({'error': 'Project name is required'}), 400

        logger.info(f"Getting interview prompt for project: {project_name}")
        
        # First, look for previously created interview configuration in the project files
        project_files = []
        project_config = None
        
        # Look in interviews directory for matching project name
        interviews_dir = Path('interviews')
        if interviews_dir.exists():
            json_files = list(interviews_dir.glob('*.json'))
            for file_path in json_files:
                try:
                    with open(file_path, 'r') as f:
                        interview_data = json.load(f)
                        if interview_data.get('project_name') == project_name:
                            project_files.append(interview_data)
                            # Use the most recent file's config as our base
                            if not project_config or (interview_data.get('created_at', '') > project_config.get('created_at', '')):
                                project_config = interview_data
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
        
        # Get the prompt information from our predefined prompts
        prompt_info = interview_prompts.get(project_name)
        
        # If we found project config but no predefined prompt, create one
        if project_config and not prompt_info:
            # Extract interview details to create a prompt
            project_description = project_config.get('project_description', f"Project {project_name}")
            interview_type = project_config.get('interview_type', 'User Interview')
            
            prompt_text = f"""
You are Daria, an experienced UX researcher conducting a {interview_type} for the following project:

Project: {project_name}
Description: {project_description}

Your goal is to gather meaningful insights about the user's experience, pain points, and needs. 
Ask open-ended questions and follow up on responses to uncover deeper insights.
Keep the conversation natural and conversational while guiding it towards valuable research outcomes.
"""
            
            # Create a prompt info based on the project configuration
            prompt_info = {
                'prompt': prompt_text,
                'form_data': {
                    'project_name': project_name,
                    'project_description': project_description,
                    'interview_type': interview_type,
                    'interviewee': {
                        'name': project_config.get('participant_name', 'Anonymous'),
                        'role': project_config.get('role', ''),
                        'experience_level': project_config.get('experience_level', ''),
                        'department': project_config.get('department', '')
                    },
                    'tags': project_config.get('tags', []),
                    'emotion': project_config.get('emotion', ''),
                    'status': project_config.get('status', 'Draft'),
                    'author': project_config.get('author', '')
                }
            }
        
        if not prompt_info:
            logger.warning(f"Interview prompt not found for project: {project_name}. Using default prompt.")
            # Return a default prompt for unknown projects
            default_prompt = f"""
You are Daria, an experienced UX researcher conducting an interview for project {project_name}.

Your goal is to:
1. Understand the user's experiences and needs
2. Identify pain points and challenges
3. Gather insights for product improvement

Ask open-ended questions, and follow up on interesting points. Maintain a conversational tone while
guiding the discussion toward valuable research outcomes.
"""
            prompt_info = {
                'prompt': default_prompt,
                'form_data': {'interviewee': {'name': 'Anonymous'}}
            }
        
        # Return the prompt information with enhanced context
        return jsonify(prompt_info)
        
    except Exception as e:
        logger.error(f"Error getting interview prompt: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostics/microphone', methods=['POST'])
def check_microphone():
    """Diagnostic endpoint to check microphone status and audio processing."""
    try:
        logger.info("Microphone diagnostic endpoint called")
        
        # Check for audio file
        if 'audio' not in request.files:
            logger.error("No audio file provided to diagnostic endpoint")
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided',
                'debug_info': {
                    'request_files': list(request.files.keys()),
                    'request_form': list(request.form.keys()),
                    'content_type': request.content_type
                }
            }), 400

        # Process the audio file
        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({'status': 'error', 'message': 'Empty audio file'}), 400
            
        # Get file details
        file_size = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)
            file_size = os.path.getsize(temp_audio.name)
            logger.info(f"Diagnostic audio file saved: {temp_audio.name}, size: {file_size} bytes")
            
            # Only attempt transcription if file is large enough
            if file_size > 1000:  # At least 1KB of data
                try:
                    client = OpenAI()
                    with open(temp_audio.name, 'rb') as audio:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio
                        )
                    logger.info(f"Diagnostic transcription successful: {transcription.text}")
                    
                    # Clean up the temporary file
                    os.unlink(temp_audio.name)
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Microphone and transcription working correctly',
                        'file_size': file_size,
                        'transcription': transcription.text
                    })
                except Exception as e:
                    logger.error(f"Diagnostic transcription error: {str(e)}")
                    # Clean up the temporary file
                    os.unlink(temp_audio.name)
                    return jsonify({
                        'status': 'error',
                        'message': f'Transcription error: {str(e)}',
                        'file_size': file_size
                    }), 500
            else:
                # File too small, likely no audio
                os.unlink(temp_audio.name)
                return jsonify({
                    'status': 'error',
                    'message': 'Audio file too small, no speech detected',
                    'file_size': file_size
                }), 400
                
    except Exception as e:
        logger.error(f"Microphone diagnostic error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/run_mic_test', methods=['GET'])
def run_mic_test():
    """Run the microphone test script and return results."""
    try:
        import subprocess
        import sys
        
        logger.info("Running microphone test script")
        
        # Path to the script
        script_path = os.path.join(app.root_path, 'test_mic_recording.py')
        
        # Check if script exists
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'Test script not found',
                'path': script_path
            }), 404
            
        # Run the script as a subprocess and capture output
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        # Return results
        return jsonify({
            'status': 'complete',
            'exit_code': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        })
        
    except Exception as e:
        logger.error(f"Error running microphone test: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/save_interview', methods=['POST'])
def api_save_interview():
    """API endpoint to save new interview configuration and generate prompt."""
    try:
        logger.info("=== /api/save_interview endpoint called ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Log detailed information about the request
        if request.content_type and 'application/json' in request.content_type:
            logger.info("Request has correct JSON content type")
        else:
            logger.warning(f"Unexpected content type: {request.content_type}")
        
        # Get and log the raw data
        raw_data = request.get_data(as_text=True)
        logger.info(f"Raw request data: {raw_data[:200]}...")
        
        data = request.get_json()
        if data is None:
            logger.error("Failed to parse JSON data from request")
            return jsonify({'error': 'Invalid JSON data or content-type'}), 400
            
        logger.info(f"Parsed JSON data: {data}")
        
        # Required fields
        project_name = data.get('project_name')
        interview_type = data.get('interview_type')
        project_description = data.get('project_description')
        
        logger.info(f"Project name: {project_name}")
        logger.info(f"Interview type: {interview_type}")
        logger.info(f"Project description: {project_description[:50]}..." if project_description else "No project description")
        
        # Validate required fields
        missing_fields = []
        if not project_name:
            missing_fields.append('project_name')
        if not interview_type:
            missing_fields.append('interview_type')
        if not project_description:
            missing_fields.append('project_description')
            
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        # Get the form_data field if it exists, or create it from the individual fields
        form_data = data.get('form_data', {})
        
        # Ensure the form_data has all the required fields
        if not form_data.get('interviewee'):
            form_data['interviewee'] = {
                'name': data.get('participant_name', 'Anonymous'),
                'role': data.get('role', ''),
                'experience_level': data.get('experience_level', ''),
                'department': data.get('department', '')
            }
            
        # Ensure project information is in form_data
        form_data['project_name'] = project_name
        form_data['project_description'] = project_description
        form_data['interview_type'] = interview_type
            
        # Get all the metadata fields
        metadata = {
            'participant': {
                'name': data.get('participant_name', 'Anonymous'),
                'role': data.get('role', ''),
                'experience_level': data.get('experience_level', ''),
                'department': data.get('department', '')
            },
            'session': {
                'date': datetime.now().isoformat(),
                'status': data.get('status', 'Draft')
            },
            'tags': data.get('tags', []),
            'emotion': data.get('emotion', 'Neutral'),
            'researcher': {
                'name': data.get('author', 'Unknown')
            }
        }

        logger.info(f"Prepared form data: {form_data}")
        logger.info(f"Prepared metadata: {metadata}")

        # Generate the interview prompt
        try:
            logger.info("Generating interview prompt...")
            interview_prompt = get_interview_prompt(interview_type, project_name, project_description)
            logger.info("Interview prompt generated successfully")
        except Exception as e:
            logger.error(f"Error generating interview prompt: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Failed to generate interview prompt'}), 500

        # Store the interview configuration
        interview_prompts[project_name] = {
            'prompt': interview_prompt,
            'metadata': metadata,
            'project_description': project_description,
            'type': interview_type,
            'form_data': form_data
        }
        
        logger.info(f"Successfully stored interview configuration for project: {project_name}")
        
        # Create response with redirect URL
        redirect_url = url_for('interview', project_name=project_name)
        logger.info(f"Generated redirect URL: {redirect_url}")
        
        response_data = {
            'status': 'success',
            'message': 'Interview configuration saved successfully',
            'project_name': project_name,
            'redirect_url': redirect_url
        }
        
        logger.info(f"Returning success response: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in api_save_interview: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# Add Jarvis interview routes
@app.route('/api/jarvis/start', methods=['POST'])
def jarvis_start():
    """Initialize a new Jarvis interview session."""
    try:
        data = request.get_json() or {}
        project_name = data.get('project_name', 'default')
        
        # Initialize a new session
        session_id = jarvis_wrapper.initialize_session(project_name)
        
        # Set the session ID in the response cookie
        response = jsonify({'status': 'success', 'session_id': session_id})
        response.set_cookie('jarvis_session_id', session_id)
        
        return response
    except Exception as e:
        logger.error(f"Error starting Jarvis interview: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/jarvis/record', methods=['POST'])
def jarvis_record():
    """Record audio from the user and return the transcript."""
    try:
        # For simplicity in this demo, we'll just return a simulated transcript
        # In a real implementation, this would handle browser-based audio recording
        data = request.get_json() or {}
        simulated_input = data.get('simulated_input')
        
        if simulated_input:
            # Return the simulated input as the transcript
            logger.info(f"Using simulated input: {simulated_input}")
            return jsonify({
                'transcript': simulated_input,
                'confidence': 0.98
            })
        
        # If no simulated input, return a default response
        logger.info("No simulated input provided, returning default response")
        return jsonify({
            'transcript': 'I am a manager of the ordering portal and use it daily for my work.',
            'confidence': 0.95
        })
    except Exception as e:
        logger.error(f"Error recording Jarvis audio: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/jarvis/respond', methods=['POST'])
def jarvis_respond():
    """Process user input and generate an AI response for the Jarvis interview."""
    try:
        data = request.get_json() or {}
        user_input = data.get('user_input', '')
        
        # Get session ID from cookie or request data
        session_id = request.cookies.get('jarvis_session_id')
        if not session_id:
            session_id = data.get('session_id')
            
        if not session_id:
            return jsonify({'error': 'No active session'}), 400
        
        # Process the user input using the wrapper
        response = jarvis_wrapper.process_user_input(session_id, user_input)
        
        # Return the response
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error generating Jarvis response: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add a route to get the current session data for debugging
@app.route('/api/jarvis/session/<session_id>', methods=['GET'])
def jarvis_session(session_id):
    """Get the current data for a Jarvis session."""
    try:
        session_data = jarvis_wrapper.get_session_data(session_id)
        
        if 'error' in session_data:
            return jsonify(session_data), 404
            
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"Error retrieving Jarvis session: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, 
        host='0.0.0.0',
        port=5003,
        debug=True,
        use_reloader=True
    )

