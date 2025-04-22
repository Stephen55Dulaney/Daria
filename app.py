from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
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
from src.vector_store import InterviewVectorStore
from src.persona_gpt import generate_persona_with_architect
import traceback
import logging
from markupsafe import Markup
from openai import OpenAI
import markdown  # Added this import since it's used in the markdown filter
from src.google_ai import GeminiPersonaGenerator
from src.daria_resources import get_interview_prompt, BASE_SYSTEM_PROMPT, INTERVIEWER_BEST_PRACTICES
from langchain.schema import SystemMessage, HumanMessage
from langchain.vectorstores import VectorStore
import MySQLdb
from werkzeug.utils import secure_filename

# Global variables
vector_store = None

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['INTERVIEWS_DIR'] = 'interviews'
app.config['VECTOR_STORE_PATH'] = 'vector_store'
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')  # Add OpenAI API key configuration

socketio = SocketIO(app)
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

# Add after the existing configuration
INTERVIEWS_DIR = Path('interviews')
INTERVIEWS_DIR.mkdir(exist_ok=True)

# Add after INTERVIEWS_DIR definition
PERSONAS_DIR = Path('personas')
PERSONAS_DIR.mkdir(exist_ok=True)

# Add maximum rounds constant
MAX_ROUNDS = 3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize vector store
app.vector_store = None

# Helper functions
def list_interviews():
    """List all saved interviews."""
    try:
        interviews = []
        
        # Create interviews directory if it doesn't exist
        if not os.path.exists('interviews'):
            os.makedirs('interviews')
            return interviews
            
        # List all JSON files in interviews directory
        for filename in os.listdir('interviews'):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join('interviews', filename)) as f:
                        interview = json.load(f)
                        
                    # Ensure created_at exists
                    if not interview.get('created_at'):
                        interview['created_at'] = datetime.now().isoformat()
                        
                    # Extract metadata for display
                    interview_summary = {
                        'id': interview.get('id', filename.replace('.json', '')),
                        'title': interview.get('title', 'Untitled Interview'),
                        'type': interview.get('type', 'interview'),
                        'project_id': interview.get('project_id', ''),
                        'created_at': interview.get('created_at'),
                        'created_by': interview.get('created_by', ''),
                        'participant_name': interview.get('metadata', {}).get('participant', {}).get('name', 'Anonymous'),
                        'role': interview.get('metadata', {}).get('participant', {}).get('role', 'Unknown'),
                        'department': interview.get('metadata', {}).get('participant', {}).get('department', ''),
                        'date': interview.get('metadata', {}).get('session', {}).get('date'),
                        'duration': interview.get('metadata', {}).get('session', {}).get('duration'),
                        'format': interview.get('metadata', {}).get('session', {}).get('format', 'text'),
                        'language': interview.get('metadata', {}).get('session', {}).get('language', 'en'),
                        'researcher': interview.get('metadata', {}).get('researcher', {}).get('name', ''),
                        'chunk_count': len(interview.get('chunks', [])),
                        'has_analysis': bool(interview.get('analysis')),
                        'content_preview': _get_content_preview(interview)
                    }
                    
                    # Add to list if it has required fields
                    if interview_summary['id'] and interview_summary['created_at']:
                        interviews.append(interview_summary)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding {filename}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
                    continue
                    
        # Sort by date, most recent first, handling None values
        interviews.sort(
            key=lambda x: x.get('created_at') or '1970-01-01T00:00:00',
            reverse=True
        )
        
        return interviews
        
    except Exception as e:
        logger.error(f"Error listing interviews: {str(e)}")
        logger.error(traceback.format_exc())
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
            current_chunk = {'text': '', 'speaker': '', 'start_time': None, 'end_time': None}
            
            for line in lines:
                if ': ' in line:  # New speaker
                    if current_chunk['text']:  # Save previous chunk
                        transcript_chunks.append(current_chunk)
                        current_chunk = {'text': '', 'speaker': '', 'start_time': None, 'end_time': None}
                    
                    speaker, text = line.split(': ', 1)
                    current_chunk['speaker'] = speaker
                    current_chunk['text'] = text
                else:  # Continuation of previous speaker
                    current_chunk['text'] += f"\n{line}"
            
            if current_chunk['text']:  # Save last chunk
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

        # If analysis is not provided, create a structured template
        if not analysis:
            analysis = {
                'key_points': [],
                'user_needs': [],
                'pain_points': [],
                'recommendations': [],
                'insights': [],
                'notable_quotes': []
            }
        elif isinstance(analysis, str):
            # Convert string analysis to structured format
            analysis = {
                'raw_text': analysis,
                'key_points': [],
                'user_needs': [],
                'pain_points': [],
                'recommendations': [],
                'insights': [],
                'notable_quotes': []
            }
            
        # Prepare metadata
        metadata = {
            'researcher': {
                'name': '',
                'email': '',
                'role': 'UX Researcher'
            },
            'participant': {
                'name': participant_name,
                'role': '',
                'department': '',
                'experience_level': '',
                'consent_given': True
            },
            'session': {
                'date': interview_date,
                'duration': None,
                'format': 'text',
                'language': 'en',
                'notes': ''
            }
        }
        
        # Add form data if provided
        if form_data:
            if isinstance(form_data.get('tags'), str):
                form_data['tags'] = [tag.strip() for tag in form_data['tags'].split(',') if tag.strip()]
            elif not form_data.get('tags'):
                form_data['tags'] = []
                
            # Update metadata with form data
            if form_data.get('researcher'):
                metadata['researcher'].update(form_data['researcher'])
            
            if form_data.get('interviewee'):
                metadata['participant'].update({
                    'name': form_data['interviewee'].get('name', participant_name),
                    'role': form_data.get('role', ''),
                    'experience_level': form_data.get('experience_level', ''),
                    'department': form_data.get('department', ''),
                    'consent_given': form_data.get('consent', True)
                })
            
            if form_data.get('metadata'):
                metadata['session'].update({
                    'date': form_data['metadata'].get('interviewDate', interview_date),
                    'duration': form_data['metadata'].get('interviewDuration'),
                    'format': form_data['metadata'].get('interviewFormat', 'text'),
                    'language': form_data['metadata'].get('interviewLanguage', 'en'),
                    'notes': form_data['metadata'].get('interviewNotes', '')
                })
            
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

def create_openai_client():
    """Create an OpenAI client with consistent configuration."""
    try:
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url="https://api.openai.com/v1"
        )
        logger.info("OpenAI client created successfully")
        return client
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {str(e)}")
        logger.error(traceback.format_exc())
        raise

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
    if os.path.exists('interviews'):
        logger.info("Loading existing interviews into vector store...")
        for filename in os.listdir('interviews'):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join('interviews', filename)) as f:
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
        logger.warning("Interviews directory not found")
except Exception as e:
    logger.error(f"Error initializing vector store: {str(e)}")
    logger.error(traceback.format_exc())
    vector_store = None

def save_persona(project_name: str, persona_content: str, selected_elements: list) -> dict:
    """Save a generated persona to disk."""
    persona_id = str(uuid.uuid4())
    persona_data = {
        'id': persona_id,
        'project_name': project_name,
        'content': persona_content,
        'elements': selected_elements,
        'date': datetime.now().isoformat(),
        'last_modified': datetime.now().isoformat()
    }
    
    with open(PERSONAS_DIR / f"{persona_id}.json", 'w') as f:
        json.dump(persona_data, f, indent=2)
    
    return persona_data

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
    
    # Sort by last modified date, most recent first
    personas.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
    
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
    """List all projects."""
    try:
        projects = []
        PROJECTS_DIR = Path('projects')
        if PROJECTS_DIR.exists():
            for file in sorted(PROJECTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if all(key in data for key in ['id', 'name', 'description', 'status']):
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
    # Get list of projects for dropdown
    projects = set()
    if os.path.exists('interviews'):
        for filename in os.listdir('interviews'):
            if filename.endswith('.json'):
                with open(os.path.join('interviews', filename)) as f:
                    interview = json.load(f)
                    projects.add(interview['project_name'])
    
    return render_template('persona.html', projects=sorted(list(projects)))

@app.route('/journey_map')
def journey_map():
    """Journey map creation page"""
    try:
        # Get list of projects with their IDs and names
        projects = []
        if os.path.exists('interviews'):
            project_dict = {}
            for filename in os.listdir('interviews'):
                if filename.endswith('.json'):
                    with open(os.path.join('interviews', filename)) as f:
                        interview = json.load(f)
                        project_name = interview.get('project_name')
                        if project_name and project_name not in project_dict:
                            project_dict[project_name] = {
                                'id': str(uuid.uuid4()),  # Generate a unique ID for each project
                                'name': project_name
                            }
            projects = list(project_dict.values())
        
        logger.info(f"Found {len(projects)} projects for journey map")
        return render_template('journey_map.html', projects=sorted(projects, key=lambda x: x['name']))
    except Exception as e:
        logger.error(f"Error in journey_map route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('journey_map.html', projects=[])

@app.route('/save_interview', methods=['POST'])
def save_interview():
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        interview_type = data.get('interview_type')
        project_description = data.get('project_description')
        
        # Get all the new metadata fields
        form_data = {
            'participant_name': data.get('participant_name'),
            'role': data.get('role'),
            'experience_level': data.get('experience_level'),
            'department': data.get('department'),
            'tags': data.get('tags', []),
            'emotion': data.get('emotion'),
            'status': data.get('status', 'Draft'),
            'author': data.get('author')
        }

        if not all([project_name, interview_type, project_description]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Generate the interview prompt using the function from daria_resources
        interview_prompt = get_interview_prompt(interview_type, project_name, project_description)
        
        # Store the prompt and form data
        interview_prompts[project_name] = {
            'prompt': interview_prompt,
            'form_data': form_data,
            'project_description': project_description
        }
        
        logger.info(f"Stored interview prompt and form data for project: {project_name}")
        logger.debug(f"Form data: {form_data}")
        
        return jsonify({
            'status': 'success',
            'message': 'Interview prompt saved successfully',
            'project_name': project_name,
            'redirect_url': url_for('interview', project_name=project_name)
        })
        
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/interview/<project_name>', methods=['GET', 'POST'])
def interview(project_name):
    try:
        if request.method == 'GET':
            # Check if the project exists in interview_prompts
            if project_name not in interview_prompts:
                return redirect(url_for('new_interview'))
            
            # Get the prompt for this project
            prompt = interview_prompts[project_name]
            
            # Render the interview template
            return render_template('interview.html', project_name=project_name, prompt=prompt)
        else:  # POST request
            data = request.get_json()
            user_input = data.get('user_input', '')
            question_count = data.get('question_count', 0)
            
            # Create OpenAI client
            llm = create_openai_client()
            
            # Get the interview prompt
            prompt = interview_prompts.get(project_name)
            if not prompt:
                return jsonify({'error': 'Interview prompt not found'}), 404
            
            # Get the interview type from the prompt
            interview_type = "Application Interview"  # Default
            if "Persona Interview" in prompt['prompt']:
                interview_type = "Persona Interview"
            elif "Journey Map Interview" in prompt['prompt']:
                interview_type = "Journey Map Interview"
            
            # Generate system message based on interview type
            system_message = get_interview_prompt(interview_type, project_name, prompt['form_data'].get('project_description', ''))
            
            # Add the user's message to the conversation
            if project_name not in conversations:
                conversations[project_name] = {'messages': []}
            
            conversations[project_name]['messages'].append({"role": "user", "content": user_input})
            
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
            
            return jsonify({
                'response': assistant_response,
                'question_count': question_count + 1
            })
            
    except Exception as e:
        logger.error(f"Error in interview route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        project_name = request.args.get('project_name')
        if not project_name:
            return jsonify({'error': 'Project name is required'}), 400

        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({'error': 'Empty audio file'}), 400

        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)
            
            # Process the audio file with OpenAI's Whisper API
            client = OpenAI()
            with open(temp_audio.name, 'rb') as audio:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )

        # Clean up the temporary file
        os.unlink(temp_audio.name)

        # Get the saved interview prompt
        interview_prompt = interview_prompts.get(project_name)
        if not interview_prompt:
            return jsonify({'error': 'Interview prompt not found'}), 400

        # Get the current conversation
        conversation = conversations[project_name]
        current_round = len(conversation['messages']) // 2

        # Add the transcription to the conversation history
        conversation['messages'].append({"role": "user", "content": f"You: {transcription.text}\n\n"})

        # Get AI response using OpenAI client
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation['messages'],
            temperature=0.7
        )

        ai_response = response.choices[0].message.content
        conversation['messages'].append({"role": "assistant", "content": f"Daria: {ai_response}\n\n"})

        # Only set should_stop_interview if we've reached max rounds and have meaningful conversation
        should_stop = False
        if current_round > 0 and len(transcription.text.split()) > 2 and current_round >= MAX_ROUNDS:
            should_stop = False  # Don't stop the interview automatically

        return jsonify({
            'transcription': transcription.text,
            'response': ai_response,
            'should_stop_interview': should_stop
        })

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Convert text to speech using ElevenLabs
        audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=AVAILABLE_VOICES['rachel'],
            model_id="eleven_multilingual_v2"
        )
        
        # Convert stream to bytes
        audio_data = BytesIO()
        for chunk in audio_stream:
            audio_data.write(chunk)
        audio_data.seek(0)
        
        return send_file(
            audio_data,
            mimetype='audio/wav',
            as_attachment=False
        )
        
    except Exception as e:
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
            return jsonify({'status': 'error', 'error': 'Interview data not found'}), 404

        interview_prompt = interview_data['prompt']
        form_data = interview_data['form_data']

        # Determine interview type from the prompt
        interview_type = "Application Interview"  # default
        if "Persona Interview" in interview_prompt:
            interview_type = "Persona Interview"
        elif "Journey Map Interview" in interview_prompt:
            interview_type = "Journey Map Interview"

        # Create a new instance of ChatOpenAI for analysis
        analysis_llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4",
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )

        # Generate analysis prompt based on interview type
        if interview_type == "Application Interview":
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher conducting Application Evaluation interviews.
#Objective: Evaluate the interviewee's experience with {project_name}
#Instructions: Evaluate the interview transcript and provide a comprehensive analysis.

Your analysis should include:
1. Role and Experience: Describe their role and how they use the system
2. Key Tasks: List the main tasks they perform
3. Pain Points: Identify any frustrations and challenges
4. Suggestions: Note any improvements they mentioned
5. Overall Assessment: Evaluate their experience and needs

Format your response with clear sections using headers."""
        elif interview_type == "Persona Interview":
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher conducting Creating a Persona interviews.
#Objective: Generate a persona based on the interviewee's responses about {project_name}
#Instructions: Evaluate the interview transcript and generate a persona based on the interviewee's responses.

Your analysis should include:
1. Demographics: Age, role, experience level, and other relevant characteristics
2. Behaviors: How they interact with the system, their workflow, and habits
3. Goals: What they're trying to achieve and their motivations
4. Challenges: Pain points, frustrations, and obstacles they face
5. Preferences: Their likes, dislikes, and preferences in using the system
6. Key Insights: Important quotes or observations that define their experience

Format your response with clear sections using headers and include relevant quotes from the transcript."""
        else:  # Journey Map Interview
            analysis_prompt = f"""#Role: You are Daria, an expert UX researcher conducting Creating a Journey Map interviews.
#Objective: Generate a comprehensive Journey Map based on the interviewee's responses about {project_name}
#Instructions: Evaluate the interview transcript and generate a Journey Map based on the interviewee's responses.

Your analysis should include:
1. User Journey Stages: Break down the experience into key stages or phases
2. Touchpoints: Identify all interactions with the system and other stakeholders
3. Emotions: Track emotional highs and lows throughout the journey
4. Pain Points: Identify frustrations and challenges at each stage
5. Moments of Delight: Note positive experiences and successful interactions
6. Opportunities: Suggest improvements for each stage of the journey

Format your response with clear sections using headers and include relevant quotes from the transcript."""

        # Generate the analysis using the actual transcript from the current interview
        analysis = analysis_llm.predict(analysis_prompt + "\n\nInterview Transcript:\n" + transcript)

        # Save the interview data with the transcript and analysis
        save_interview_data(project_name, interview_type, transcript, analysis, form_data)

        return jsonify({
            'status': 'success',
            'message': 'Interview analysis completed successfully',
            'analysis': analysis
        })

    except Exception as e:
        print(f"Error in final_analysis: {str(e)}")
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
        interviews = list_interviews()
        
        # Format interviews for display
        for interview in interviews:
            # Set type and status
            interview['type'] = interview.get('type', 'Interview').title()
            interview['status'] = interview.get('status', 'draft').title()
            
            # Set preview text
            interview['preview'] = interview.get('content_preview', 'No preview available')
            
            # Set tags (placeholder for now)
            interview['tags'] = []
            
            # Format project info
            if not interview.get('project_name'):
                interview['project_name'] = 'Unassigned'
                
            # Get participant name from all possible sources
            participant_name = (
                interview.get('transcript_name') or  # Try transcript_name first
                interview.get('metadata', {}).get('participant', {}).get('name') or
                interview.get('participant_name') or
                'Anonymous'
            )
            interview['participant_name'] = participant_name
        
        return render_template('archive.html', interviews=interviews)
    except Exception as e:
        logger.error(f"Error in archive route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', 
                             error="Failed to load interviews archive",
                             details=str(e))

@app.route('/transcript/<interview_id>')
def view_transcript(interview_id):
    """View interview transcript."""
    try:
        interview = load_interview(interview_id)
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
        interview = load_interview(interview_id)
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        # If analysis doesn't exist or is empty, generate it
        if not interview.get('analysis') or interview['analysis'].endswith('**'):
            try:
                # Initialize OpenAI client
                analysis_llm = ChatOpenAI(
                    temperature=0.7,
                    model_name="gpt-4",
                    openai_api_key=os.getenv('OPENAI_API_KEY')
                )
                
                # Get interview type and generate appropriate prompt
                interview_type = interview.get('interview_type', 'Application Interview')
                project_name = interview.get('project_name', '')
                transcript = interview.get('transcript', '')
                
                # Split transcript into manageable chunks (roughly 2000 tokens each)
                transcript_chunks = []
                current_chunk = []
                current_length = 0
                
                for line in transcript.split('\n'):
                    # Rough estimate: 1 token ≈ 4 characters
                    line_length = len(line) / 4
                    if current_length + line_length > 2000:
                        transcript_chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_length = line_length
                    else:
                        current_chunk.append(line)
                        current_length += line_length
                
                if current_chunk:
                    transcript_chunks.append('\n'.join(current_chunk))
                
                # Generate base prompt
                base_prompt = f"""#Role: You are Daria, an expert UX researcher conducting {interview_type}.
#Objective: Analyze the interview about {project_name}
#Context: You will receive the interview transcript in parts. Analyze each part and we'll combine the insights at the end.

For each part, identify:
1. Key points and insights
2. User needs and pain points
3. Notable quotes
4. Recommendations (if any)

Format your response with clear sections using headers."""

                # Analyze each chunk
                chunk_analyses = []
                for i, chunk in enumerate(transcript_chunks):
                    chunk_prompt = f"{base_prompt}\n\nPart {i+1} of {len(transcript_chunks)}:\n\n{chunk}"
                    messages = [
                        SystemMessage(content=chunk_prompt)
                    ]
                    response = analysis_llm.invoke(messages)
                    chunk_analyses.append(response.content)
                
                # Generate final synthesis prompt
                synthesis_prompt = f"""#Role: You are Daria, an expert UX researcher conducting {interview_type}.
#Objective: Synthesize the analysis of multiple transcript parts for {project_name}
#Context: Below are the analyses of different parts of the interview. Create a cohesive final analysis.

Previous analyses:

{'\n\n---\n\n'.join(chunk_analyses)}

Create a comprehensive final analysis that:
1. Synthesizes key findings across all parts
2. Identifies main themes and patterns
3. Summarizes user needs and pain points
4. Provides actionable recommendations

Format your response with clear sections using headers."""

                # Generate final synthesis
                messages = [
                    SystemMessage(content=synthesis_prompt)
                ]
                response = analysis_llm.invoke(messages)
                analysis = response.content
                
                # Update the interview with the new analysis
                interview['analysis'] = analysis
                
                # Update the existing interview
                if not update_interview_data(interview_id, analysis):
                    raise Exception("Failed to update interview")
                
                # Update vector store with new analysis
                if vector_store:
                    vector_store.add_texts(
                        texts=[analysis],
                        metadatas=[{
                            'id': interview_id,
                            'project_name': project_name,
                            'type': 'analysis',
                            'interview_type': interview_type
                        }]
                    )
                
            except Exception as e:
                logger.error(f"Error generating analysis: {str(e)}")
                logger.error(traceback.format_exc())
                flash('Error generating analysis', 'error')
                return redirect(url_for('archive'))
        
        return render_template('analysis.html', 
                             interview=interview)
    except Exception as e:
        logger.error(f"Error viewing analysis: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading analysis', 'error')
        return redirect(url_for('archive'))

@app.route('/metadata/<interview_id>')
def view_metadata(interview_id):
    """View interview metadata."""
    try:
        interview = load_interview(interview_id)
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        return render_template('metadata.html', 
                             interview=interview,
                             metadata=interview.get('metadata', {}))
    except Exception as e:
        logger.error(f"Error viewing metadata: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading metadata', 'error')
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
def save_persona():
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
        if not data or 'interviews' not in data:
            return jsonify({'error': 'No interviews provided'}), 400
            
        interviews = data['interviews']
        project_name = data.get('project_name', '')
        selected_elements = data.get('selected_elements', [])
        
        # Load interview data
        interview_data = []
        for interview_id in interviews:
            interview = get_interview(interview_id)
            if interview:
                interview_data.append(interview)
                
        if not interview_data:
            return jsonify({'error': 'No valid interviews found'}), 400
            
        # Create OpenAI client
        client = create_openai_client()
        if not client:
            return jsonify({'error': 'Failed to initialize AI client'}), 500
            
        # Generate persona content
        try:
            system_prompt = """You are an expert UX researcher and persona creator. 
            Create a detailed persona based on the interview data provided. 
            Format the response as valid JSON with the following structure:
            {
                "name": "Name and title",
                "summary": "Brief summary",
                "image_prompt": "Detailed prompt for image generation",
                "details": {
                    "goals": ["goal1", "goal2"],
                    "pain_points": ["pain1", "pain2"],
                    "needs": ["need1", "need2"]
                }
            }"""
            
            user_prompt = f"Create a persona based on these interviews: {json.dumps(interview_data, indent=2)}"
            
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            # Parse and validate response
            content = response.choices[0].message.content
            persona_data = json.loads(content)
            
            # Save persona
            result = save_persona(project_name, content, selected_elements)
            
            return jsonify(result), 200
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing persona JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            return jsonify({'error': 'Invalid persona format from AI'}), 500
        except Exception as e:
            logger.error(f"Error generating persona content: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': 'Failed to generate persona'}), 500
            
    except Exception as e:
        logger.error(f"Error in generate_persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

def generate_persona_html(persona_data):
    """Generate HTML representation of the persona data."""
    
    # Check if we have the enhanced persona format or the standard format
    if 'name' in persona_data and 'summary' in persona_data:
        # Enhanced format from Persona Architect GPT
        html = f"""
        <div class="persona-container space-y-8">
            <div class="header-section bg-indigo-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-indigo-800 mb-2">{persona_data['name']}</h2>
                <p class="text-gray-700">{persona_data['summary']}</p>
            </div>
            
            <div class="demographics-section bg-blue-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-blue-800 mb-4">Demographics</h2>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <p class="text-sm font-medium text-blue-700">Age Range</p>
                        <p class="text-gray-600">{persona_data['demographics']['age_range']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Gender</p>
                        <p class="text-gray-600">{persona_data['demographics']['gender']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Occupation</p>
                        <p class="text-gray-600">{persona_data['demographics']['occupation']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Location</p>
                        <p class="text-gray-600">{persona_data['demographics']['location']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Education</p>
                        <p class="text-gray-600">{persona_data['demographics']['education']}</p>
                    </div>
                </div>
            </div>
            
            <div class="background-section bg-gray-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">Background & Context</h2>
                <p class="text-gray-700">{persona_data.get('background', 'No background information provided.')}</p>
            </div>
            
            <div class="goals-section bg-green-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-green-800 mb-4">Goals & Motivations</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="goal-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-green-700 mb-2">{goal['goal']}</h3>
                            <p class="text-gray-600 mb-2">{goal['motivation']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-green-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in goal['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for goal in persona_data['goals'])}
                </div>
            </div>
            
            <div class="pain-points-section bg-red-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-red-800 mb-4">Pain Points & Challenges</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="pain-point-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-red-700 mb-2">{pain_point['pain_point']}</h3>
                            <p class="text-gray-600 mb-2">Impact: {pain_point['impact']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-red-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in pain_point['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for pain_point in persona_data['pain_points'])}
                </div>
            </div>
            
            <div class="behaviors-section bg-yellow-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-yellow-800 mb-4">Behaviors & Habits</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="behavior-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-yellow-700 mb-2">{behavior['behavior']}</h3>
                            <p class="text-gray-600 mb-2">Frequency: {behavior['frequency']}</p>
                            <p class="text-gray-600 mb-2">Context: {behavior['context']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-yellow-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in behavior['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for behavior in persona_data['behaviors'])}
                </div>
            </div>
            
            {f"""
            <div class="technology-section bg-blue-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-blue-800 mb-4">Technology Usage</h2>
                <div class="space-y-4">
                    <div class="bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-blue-700 mb-2">Devices</h3>
                        <ul class="list-disc list-inside text-gray-600">
                            {''.join(f'<li>{device}</li>' for device in persona_data['technology'].get('devices', []))}
                        </ul>
                    </div>
                    <div class="bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-blue-700 mb-2">Software</h3>
                        <ul class="list-disc list-inside text-gray-600">
                            {''.join(f'<li>{software}</li>' for software in persona_data['technology'].get('software', []))}
                        </ul>
                    </div>
                    <div class="bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-blue-700 mb-2">Tech Comfort Level</h3>
                        <p class="text-gray-600">{persona_data['technology'].get('comfort_level', 'Not specified')}</p>
                    </div>
                    <div class="bg-white p-4 rounded-lg shadow-sm">
                        <h3 class="font-semibold text-blue-700 mb-2">Supporting Quotes</h3>
                        <ul class="list-disc list-inside text-gray-600">
                            {''.join(f'<li>{quote}</li>' for quote in persona_data['technology'].get('supporting_quotes', []))}
                        </ul>
                    </div>
                </div>
            </div>
            """ if 'technology' in persona_data else ''}
            
            <div class="quotes-section bg-indigo-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-indigo-800 mb-4">Key Quotes</h2>
                <div class="space-y-4">
                    <ul class="list-disc list-inside text-gray-600">
                        {''.join(f'<li class="mb-2">"{quote}"</li>' for quote in persona_data.get('key_quotes', []))}
                    </ul>
                </div>
            </div>
            
            <div class="opportunities-section bg-emerald-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-emerald-800 mb-4">Opportunities & Recommendations</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="opportunity-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-emerald-700 mb-2">{opportunity['opportunity']}</h3>
                            <p class="text-gray-600 mb-2">Impact: {opportunity['impact']}</p>
                            <p class="text-gray-600 mb-2">Implementation: {opportunity['implementation']}</p>
                        </div>
                    ''' for opportunity in persona_data.get('opportunities', []))}
                </div>
            </div>
            
            <div class="needs-section bg-purple-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-purple-800 mb-4">Needs & Preferences</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-xl font-semibold text-purple-700 mb-4">Needs</h3>
                        <div class="space-y-4">
                            {''.join(f'''
                                <div class="need-card bg-white p-4 rounded-lg shadow-sm">
                                    <h4 class="font-semibold text-purple-600 mb-2">{need['need']}</h4>
                                    <p class="text-gray-600 mb-2">Priority: {need['priority']}</p>
                                    <div class="mt-2">
                                        <p class="text-sm font-medium text-purple-600">Supporting Quotes:</p>
                                        <ul class="list-disc list-inside text-sm text-gray-600">
                                            {''.join(f'<li>{quote}</li>' for quote in need['supporting_quotes'])}
                                        </ul>
                                    </div>
                                </div>
                            ''' for need in persona_data['needs'])}
                        </div>
                    </div>
                    <div>
                        <h3 class="text-xl font-semibold text-purple-700 mb-4">Preferences</h3>
                        <div class="space-y-4">
                            {''.join(f'''
                                <div class="preference-card bg-white p-4 rounded-lg shadow-sm">
                                    <h4 class="font-semibold text-purple-600 mb-2">{preference['preference']}</h4>
                                    <p class="text-gray-600 mb-2">Reason: {preference['reason']}</p>
                                    <div class="mt-2">
                                        <p class="text-sm font-medium text-purple-600">Supporting Quotes:</p>
                                        <ul class="list-disc list-inside text-sm text-gray-600">
                                            {''.join(f'<li>{quote}</li>' for quote in preference['supporting_quotes'])}
                                        </ul>
                                    </div>
                                </div>
                            ''' for preference in persona_data['preferences'])}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="image-prompt-section bg-gray-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">Image Generation Prompt</h2>
                <div class="bg-white p-4 rounded-lg shadow-sm">
                    <p class="text-gray-600">{persona_data.get('image_prompt', 'No image prompt provided.')}</p>
                </div>
            </div>
        </div>
        """
    else:
        # Standard format
        html = f"""
        <div class="persona-container space-y-8">
            <div class="demographics-section bg-blue-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-blue-800 mb-4">Demographics</h2>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <p class="text-sm font-medium text-blue-700">Age Range</p>
                        <p class="text-gray-600">{persona_data['demographics']['age_range']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Gender</p>
                        <p class="text-gray-600">{persona_data['demographics']['gender']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Occupation</p>
                        <p class="text-gray-600">{persona_data['demographics']['occupation']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Location</p>
                        <p class="text-gray-600">{persona_data['demographics']['location']}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-blue-700">Education</p>
                        <p class="text-gray-600">{persona_data['demographics']['education']}</p>
                    </div>
                </div>
            </div>
            
            <div class="goals-section bg-green-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-green-800 mb-4">Goals & Motivations</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="goal-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-green-700 mb-2">{goal['goal']}</h3>
                            <p class="text-gray-600 mb-2">{goal['motivation']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-green-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in goal['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for goal in persona_data['goals'])}
                </div>
            </div>
            
            <div class="behaviors-section bg-yellow-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-yellow-800 mb-4">Behaviors & Habits</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="behavior-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-yellow-700 mb-2">{behavior['behavior']}</h3>
                            <p class="text-gray-600 mb-2">Frequency: {behavior['frequency']}</p>
                            <p class="text-gray-600 mb-2">Context: {behavior['context']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-yellow-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in behavior['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for behavior in persona_data['behaviors'])}
                </div>
            </div>
            
            <div class="pain-points-section bg-red-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-red-800 mb-4">Pain Points</h2>
                <div class="space-y-4">
                    {''.join(f'''
                        <div class="pain-point-card bg-white p-4 rounded-lg shadow-sm">
                            <h3 class="font-semibold text-red-700 mb-2">{pain_point['pain_point']}</h3>
                            <p class="text-gray-600 mb-2">Impact: {pain_point['impact']}</p>
                            <div class="mt-2">
                                <p class="text-sm font-medium text-red-600">Supporting Quotes:</p>
                                <ul class="list-disc list-inside text-sm text-gray-600">
                                    {''.join(f'<li>{quote}</li>' for quote in pain_point['supporting_quotes'])}
                                </ul>
                            </div>
                        </div>
                    ''' for pain_point in persona_data['pain_points'])}
                </div>
            </div>
            
            <div class="needs-section bg-purple-50 p-6 rounded-lg shadow-md">
                <h2 class="text-2xl font-bold text-purple-800 mb-4">Needs & Preferences</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-xl font-semibold text-purple-700 mb-4">Needs</h3>
                        <div class="space-y-4">
                            {''.join(f'''
                                <div class="need-card bg-white p-4 rounded-lg shadow-sm">
                                    <h4 class="font-semibold text-purple-600 mb-2">{need['need']}</h4>
                                    <p class="text-gray-600 mb-2">Priority: {need['priority']}</p>
                                    <div class="mt-2">
                                        <p class="text-sm font-medium text-purple-600">Supporting Quotes:</p>
                                        <ul class="list-disc list-inside text-sm text-gray-600">
                                            {''.join(f'<li>{quote}</li>' for quote in need['supporting_quotes'])}
                                        </ul>
                                    </div>
                                </div>
                            ''' for need in persona_data['needs'])}
                        </div>
                    </div>
                    <div>
                        <h3 class="text-xl font-semibold text-purple-700 mb-4">Preferences</h3>
                        <div class="space-y-4">
                            {''.join(f'''
                                <div class="preference-card bg-white p-4 rounded-lg shadow-sm">
                                    <h4 class="font-semibold text-purple-600 mb-2">{preference['preference']}</h4>
                                    <p class="text-gray-600 mb-2">Reason: {preference['reason']}</p>
                                    <div class="mt-2">
                                        <p class="text-sm font-medium text-purple-600">Supporting Quotes:</p>
                                        <ul class="list-disc list-inside text-sm text-gray-600">
                                            {''.join(f'<li>{quote}</li>' for quote in preference['supporting_quotes'])}
                                        </ul>
                                    </div>
                                </div>
                            ''' for preference in persona_data['preferences'])}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
    return html

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
        personas.sort(key=lambda x: x.get('created_at', ''), reverse=True)
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
        # Get all interview files
        interview_files = list(Path('interviews').glob('*.json'))
        interviews = []
        project_name = None
        
        # First, find the project name from any interview with this project ID
        for file in interview_files:
            with open(file) as f:
                interview_data = json.load(f)
                if interview_data.get('project_id') == project_id:
                    project_name = interview_data.get('project_name')
                    break
        
        # If we didn't find by project_id, try matching by project_name
        if not project_name:
            for file in interview_files:
                with open(file) as f:
                    interview_data = json.load(f)
                    if interview_data.get('project_name') == project_id:  # Try using project_id as project_name
                        project_name = project_id
                        break
        
        if project_name:
            # Now get all interviews for this project
            for file in interview_files:
                with open(file) as f:
                    interview_data = json.load(f)
                    if interview_data.get('project_name') == project_name:
                        # Format date for display
                        date = datetime.fromisoformat(interview_data.get('date', ''))
                        formatted_date = date.strftime('%B %d, %Y')
                        
                        interviews.append({
                            'id': interview_data.get('id'),
                            'date': formatted_date,
                            'interview_type': interview_data.get('interview_type', 'Unknown Type')
                        })
        
        logger.info(f"Found {len(interviews)} interviews for project {project_name}")
        return jsonify(interviews)
    except Exception as e:
        logger.error(f"Error getting project interviews: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/interviews/<interview_id>/<content_type>')
def get_interview_content(interview_id, content_type):
    """Get specific content (transcript, analysis, or metadata) for an interview."""
    try:
        interview_file = Path('interviews') / f"{interview_id}.json"
        if not interview_file.exists():
            return jsonify({'error': 'Interview not found'}), 404
            
        with open(interview_file) as f:
            interview_data = json.load(f)
            
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
        logger.info(f"Processing {len(interview_ids)} interview IDs: {interview_ids}")
        
        if not interview_ids:
            logger.error("No interviews selected")
            return jsonify({'error': 'No interviews selected'}), 400
            
        # Load all selected interviews
        interviews = []
        for interview_id in interview_ids:
            interview_file = Path('interviews') / f"{interview_id}.json"
            logger.info(f"Loading interview file: {interview_file}")
            
            if interview_file.exists():
                with open(interview_file) as f:
                    interview_data = json.load(f)
                    interviews.append(interview_data)
                    logger.info(f"Successfully loaded interview {interview_id}")
            else:
                logger.error(f"Interview file not found: {interview_file}")
        
        if not interviews:
            logger.error("No valid interviews found")
            return jsonify({'error': 'No valid interviews found'}), 404
            
        logger.info(f"Successfully loaded {len(interviews)} interviews")
        
        # Generate journey map HTML
        logger.info("Generating journey map HTML")
        journey_map_html = generate_journey_map_html(interviews)
        logger.info(f"Generated HTML content length: {len(journey_map_html)}")
        
        return jsonify({'html': journey_map_html})
    except Exception as e:
        logger.error(f"Error creating journey map: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def generate_journey_map_html(interviews):
    """Generate HTML for the journey map based on interview data."""
    try:
        # Create OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Log interview data
        logger.info(f"Processing {len(interviews)} interviews for journey map")
        
        # Package interview data with clear structure
        interview_packages = []
        for i, interview in enumerate(interviews):
            interview_package = {
                'id': interview.get('id'),
                'date': interview.get('date'),
                'type': interview.get('interview_type'),
                'transcript': interview.get('transcript', ''),
                'analysis': interview.get('analysis', '')
            }
            interview_packages.append(interview_package)
            logger.info(f"Interview {i+1} ID: {interview_package['id']}")
            logger.info(f"Interview {i+1} transcript length: {len(interview_package['transcript'])}")
            logger.info(f"Interview {i+1} analysis length: {len(interview_package['analysis'])}")
        
        # Create a structured prompt for the journey map
        analysis_prompt = f"""As a UX research expert, analyze these {len(interview_packages)} interviews and create a detailed journey map. 
Focus on extracting specific, actionable insights from the interviews.

For each interview, I'll provide:
1. The interview transcript
2. The individual analysis
3. The interview date and type

Please create a comprehensive journey map and return it as a JSON object with the following structure:

{{
    "journey_stages": [
        {{
            "stage_number": 1,
            "name": "Stage name",
            "description": "What the user is doing",
            "thoughts": "What they're thinking",
            "feelings": "How they're feeling",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "touchpoints": [
        {{
            "stage": "Stage name",
            "interactions": ["Interaction 1", "Interaction 2"],
            "tools": ["Tool 1", "Tool 2"],
            "channels": ["Channel 1", "Channel 2"],
            "support": ["Support mechanism 1", "Support mechanism 2"],
            "examples": ["Example 1", "Example 2"]
        }}
    ],
    "emotions": [
        {{
            "stage": "Stage name",
            "emotion": "Primary emotion",
            "triggers": ["Trigger 1", "Trigger 2"],
            "quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "pain_points": [
        {{
            "stage": "Stage name",
            "challenge": "Description of the challenge",
            "impact": "Impact on the user",
            "quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "opportunities": [
        {{
            "stage": "Stage name",
            "improvement": "Description of the improvement",
            "type": "Quick win or long-term solution",
            "impact": "Expected impact",
            "priority": "High, Medium, or Low"
        }}
    ]
}}

Interview Data:
{json.dumps(interview_packages, indent=2)}

Please ensure your response is a valid JSON object with all the sections and fields as shown above. Include specific quotes from the interviews to support each insight."""

        logger.info("Sending request to OpenAI")
        # Get analysis from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a UX research expert specializing in journey mapping. Your task is to analyze interview data and create a detailed, evidence-based journey map. Return your analysis as a structured JSON object."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7
        )
        
        # Log the raw response
        analysis = response.choices[0].message.content
        logger.info(f"Received analysis from OpenAI, length: {len(analysis)}")
        logger.info("Analysis content preview:")
        logger.info(analysis[:500] + "...")
        
        # Parse the JSON response
        try:
            journey_map_data = json.loads(analysis)
            logger.info("Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.error("Raw response:")
            logger.error(analysis)
            raise
        
        # Generate HTML structure with the extracted insights
        html = f"""
        <div class="journey-map space-y-8 p-6">
            <div class="stages-section">
                <h3 class="text-xl font-semibold mb-4">Journey Stages</h3>
                <div class="grid grid-cols-1 md:grid-cols-{max(len(journey_map_data['journey_stages']), 1)} gap-4">
                    {''.join(f'''
                        <div class="stage-card p-4 bg-blue-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                            <p class="font-medium text-blue-800 mb-2">Stage {stage['stage_number']}: {stage['name']}</p>
                            <div class="space-y-2">
                                <p class="text-sm text-gray-600"><strong>What they're doing:</strong> {stage['description']}</p>
                                <p class="text-sm text-gray-600"><strong>What they're thinking:</strong> {stage['thoughts']}</p>
                                <p class="text-sm text-gray-600"><strong>How they're feeling:</strong> {stage['feelings']}</p>
                                <div class="mt-2">
                                    <p class="text-sm font-medium text-blue-700">Supporting Quotes:</p>
                                    <ul class="list-disc list-inside text-sm text-gray-600">
                                        {''.join(f'<li>{quote}</li>' for quote in stage['supporting_quotes'])}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ''' for stage in journey_map_data['journey_stages'])}
                </div>
            </div>
            
            <div class="touchpoints-section">
                <h3 class="text-xl font-semibold mb-4">Touchpoints</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {''.join(f'''
                        <div class="touchpoint-card p-4 bg-green-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                            <p class="font-medium text-green-800 mb-2">{touchpoint['stage']}</p>
                            <div class="space-y-2">
                                <p class="text-sm text-gray-600"><strong>Interactions:</strong> {', '.join(touchpoint['interactions'])}</p>
                                <p class="text-sm text-gray-600"><strong>Tools:</strong> {', '.join(touchpoint['tools'])}</p>
                                <p class="text-sm text-gray-600"><strong>Channels:</strong> {', '.join(touchpoint['channels'])}</p>
                                <p class="text-sm text-gray-600"><strong>Support:</strong> {', '.join(touchpoint['support'])}</p>
                                <div class="mt-2">
                                    <p class="text-sm font-medium text-green-700">Examples:</p>
                                    <ul class="list-disc list-inside text-sm text-gray-600">
                                        {''.join(f'<li>{example}</li>' for example in touchpoint['examples'])}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ''' for touchpoint in journey_map_data['touchpoints'])}
                </div>
            </div>
            
            <div class="emotions-section">
                <h3 class="text-xl font-semibold mb-4">User Emotions</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {''.join(f'''
                        <div class="emotion-card p-4 bg-yellow-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                            <p class="font-medium text-yellow-800 mb-2">{emotion['stage']}</p>
                            <div class="space-y-2">
                                <p class="text-sm text-gray-600"><strong>Emotion:</strong> {emotion['emotion']}</p>
                                <p class="text-sm text-gray-600"><strong>Triggers:</strong> {', '.join(emotion['triggers'])}</p>
                                <div class="mt-2">
                                    <p class="text-sm font-medium text-yellow-700">Supporting Quotes:</p>
                                    <ul class="list-disc list-inside text-sm text-gray-600">
                                        {''.join(f'<li>{quote}</li>' for quote in emotion['quotes'])}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ''' for emotion in journey_map_data['emotions'])}
                </div>
            </div>
            
            <div class="pain-points-section">
                <h3 class="text-xl font-semibold mb-4">Pain Points</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {''.join(f'''
                        <div class="pain-point-card p-4 bg-red-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                            <p class="font-medium text-red-800 mb-2">{pain_point['stage']}</p>
                            <div class="space-y-2">
                                <p class="text-sm text-gray-600"><strong>Challenge:</strong> {pain_point['challenge']}</p>
                                <p class="text-sm text-gray-600"><strong>Impact:</strong> {pain_point['impact']}</p>
                                <div class="mt-2">
                                    <p class="text-sm font-medium text-red-700">Supporting Quotes:</p>
                                    <ul class="list-disc list-inside text-sm text-gray-600">
                                        {''.join(f'<li>{quote}</li>' for quote in pain_point['quotes'])}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ''' for pain_point in journey_map_data['pain_points'])}
                </div>
            </div>
            
            <div class="opportunities-section">
                <h3 class="text-xl font-semibold mb-4">Opportunities</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {''.join(f'''
                        <div class="opportunity-card p-4 bg-purple-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                            <p class="font-medium text-purple-800 mb-2">{opportunity['stage']}</p>
                            <div class="space-y-2">
                                <p class="text-sm text-gray-600"><strong>Improvement:</strong> {opportunity['improvement']}</p>
                                <p class="text-sm text-gray-600"><strong>Type:</strong> {opportunity['type']}</p>
                                <p class="text-sm text-gray-600"><strong>Impact:</strong> {opportunity['impact']}</p>
                                <p class="text-sm text-gray-600"><strong>Priority:</strong> {opportunity['priority']}</p>
                            </div>
                        </div>
                    ''' for opportunity in journey_map_data['opportunities'])}
                </div>
            </div>
        </div>
        """
        
        logger.info("Generated HTML content")
        return html
        
    except Exception as e:
        logger.error(f"Error generating journey map HTML: {str(e)}")
        logger.error(traceback.format_exc())
        return f"""
        <div class="journey-map">
            <div class="error-message p-4 bg-red-50 rounded-lg">
                <p class="text-red-600">Error generating journey map: {str(e)}</p>
            </div>
        </div>
        """

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
        # Get form data
        researcher = json.loads(request.form.get('researcher', '{}'))
        project = json.loads(request.form.get('project', '{}'))
        interviewee = json.loads(request.form.get('interviewee', '{}'))
        technology = json.loads(request.form.get('technology', '{}'))
        consent = request.form.get('consent') == 'true'
        transcript_name = request.form.get('transcriptName')
        
        # Get the transcript file
        transcript_file = request.files.get('transcriptFile')
        if not transcript_file:
            return jsonify({'error': 'No transcript file provided'}), 400
        
        # Get file extension
        file_ext = transcript_file.filename.split('.')[-1].lower()
        
        # Read the file content based on file type
        if file_ext in ['txt']:
            # For text files, read directly
            transcript_text = transcript_file.read().decode('utf-8')
        elif file_ext in ['docx']:
            # For Word documents, use python-docx to extract text
            try:
                import docx
                doc = docx.Document(transcript_file)
                transcript_text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                return jsonify({'error': 'python-docx package is required for Word document processing. Please install it with: pip install python-docx'}), 400
        elif file_ext in ['doc']:
            return jsonify({'error': 'Old .doc format is not supported. Please convert to .docx or .txt format'}), 400
        elif file_ext in ['pdf']:
            return jsonify({'error': 'PDF support is not yet implemented. Please convert to .docx or .txt format'}), 400
        else:
            return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
        
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
            'analysis': None,
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
    """Handle advanced search requests."""
    if request.method == 'GET':
        return render_template('advanced_search.html')
        
    try:
        # Get search parameters
        query = request.form.get('query', '').strip()
        search_type = request.form.get('type', 'text')  # 'text' or 'semantic'
        
        if not query:
            return jsonify({'results': [], 'message': 'Please enter a search query'})
            
        # Get all interviews
        interviews = list_interviews()
        if not interviews:
            return jsonify({'results': [], 'message': 'No interviews found'})
            
        formatted_results = []
        
        # Try semantic search if requested and vector store is available
        if search_type == 'semantic':
            try:
                # Initialize vector store if needed
                if not hasattr(app, 'vector_store') or app.vector_store is None:
                    from src.vector_store import InterviewVectorStore
                    app.vector_store = InterviewVectorStore(
                        openai_api_key=app.config['OPENAI_API_KEY'],
                        vector_store_path='vector_store'
                    )
                    # Add interviews to vector store
                    app.vector_store.add_interviews(interviews)
                
                # Perform semantic search
                results = app.vector_store.semantic_search(query, k=5)
                if results:
                    for result in results:
                        # Extract relevant content for display
                        content = result.get('transcript', '')
                        if len(content) > 300:
                            content = content[:300] + '...'
                            
                        formatted_results.append({
                            'interview_id': result['id'],
                            'content': content,
                            'similarity': result['score'],
                            'project_name': result.get('project_name', 'Unknown Project'),
                            'interview_type': result.get('interview_type', 'Unknown Type'),
                            'date': result.get('date')
                        })
                        
            except Exception as e:
                logger.error(f"Semantic search failed: {str(e)}")
                logger.error(traceback.format_exc())
                search_type = 'text'  # Fall back to text search
        
        # If no semantic results or text search requested, perform text search
        if not formatted_results:
            query_lower = query.lower()
            for interview in interviews:
                if not interview:
                    continue
                    
                # Convert interview data to searchable text
                interview_text = json.dumps(interview, default=str).lower()
                
                if query_lower in interview_text:
                    # Find the context around the match
                    match_start = interview_text.find(query_lower)
                    context_start = max(0, match_start - 100)
                    context_end = min(len(interview_text), match_start + len(query) + 100)
                    context = interview_text[context_start:context_end]
                    
                    formatted_results.append({
                        'interview_id': interview.get('id'),
                        'content': context,
                        'similarity': 1.0 if query_lower in interview_text else 0.0,
                        'project_name': interview.get('project_name', 'Unknown Project'),
                        'interview_type': interview.get('type', 'Unknown Type'),
                        'date': interview.get('created_at')
                    })
        
        # Sort results by similarity
        formatted_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        return jsonify({
            'results': formatted_results,
            'message': f"Found {len(formatted_results)} results using {search_type} search",
            'search_type': search_type
        })
        
    except Exception as e:
        logger.error(f"Advanced search error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during search',
            'message': str(e)
        }), 500

@app.route('/interviews')
def interviews_page():
    """Display the interviews page with interviews grouped by project."""
    try:
        # Get interviews grouped by project
        projects = list_interviews(group_by_project=True)
        
        # If no projects found, initialize with just "All Projects"
        if not projects:
            return render_template('interviews.html', projects=[{
                'name': 'All Projects',
                'interview_list': []  # Changed from 'items' to 'interview_list' to avoid conflict
            }])
        
        # Ensure each project has the correct structure
        formatted_projects = []
        for project in projects:
            if isinstance(project, dict):
                # Create new dict with renamed 'items' key to avoid conflict with dict.items() method
                formatted_projects.append({
                    'name': project.get('name', 'Unknown Project'),
                    'interview_list': list(project.get('items', []))  # Changed from 'items' to 'interview_list'
                })
            else:
                # Project is not a dict, create proper structure
                formatted_projects.append({
                    'name': str(project),
                    'interview_list': []  # Changed from 'items' to 'interview_list'
                })
        
        # Sort projects by name
        formatted_projects.sort(key=lambda x: x['name'])
        
        # Add "All Projects" as the first option
        formatted_projects.insert(0, {
            'name': 'All Projects',
            'interview_list': []  # Changed from 'items' to 'interview_list'
        })
        
        return render_template('interviews.html', projects=formatted_projects)
    except Exception as e:
        logger.error(f"Error in interviews_page: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a list with just the "All Projects" option on error
        return render_template('interviews.html', projects=[{
            'name': 'All Projects',
            'interview_list': []  # Changed from 'items' to 'interview_list'
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
    """Get a specific interview by ID."""
    try:
        # Ensure interviews directory exists
        if not os.path.exists('interviews'):
            logger.error("Interviews directory does not exist")
            return None
            
        # Construct file path
        file_path = os.path.join('interviews', f"{interview_id}.json")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Interview file not found: {interview_id}")
            return None
            
        # Load and return interview data
        with open(file_path) as f:
            interview = json.load(f)
            
        # Add computed fields
        interview['chunk_count'] = len(interview.get('chunks', []))
        interview['has_analysis'] = bool(interview.get('analysis'))
        
        # Format timestamps in chunks
        for chunk in interview.get('chunks', []):
            if 'start_time' in chunk:
                chunk['start_time_formatted'] = format_timestamp(chunk['start_time'])
            if 'end_time' in chunk:
                chunk['end_time_formatted'] = format_timestamp(chunk['end_time'])
                
        return interview
        
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding interview {interview_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting interview {interview_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return None
        
def format_timestamp(seconds):
    """Format seconds into MM:SS format."""
    try:
        minutes = int(seconds) // 60
        remaining_seconds = int(seconds) % 60
        return f"{minutes:02d}:{remaining_seconds:02d}"
    except:
        return "00:00"

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

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5003) 