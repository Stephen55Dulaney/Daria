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
from datetime import datetime
from pathlib import Path
from src.vector_store import InterviewVectorStore
import traceback
import logging
from markupsafe import Markup
from openai import OpenAI
import markdown  # Added this import since it's used in the markdown filter

# Global variables
vector_store = None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
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

# Helper functions
def list_interviews():
    """List all saved interviews."""
    interviews = []
    if INTERVIEWS_DIR.exists():
        for file_path in INTERVIEWS_DIR.glob('*.json'):
            try:
                with open(file_path) as f:
                    interview = json.load(f)
                    # Ensure all required fields are present
                    interview.setdefault('date', datetime.now().isoformat())
                    interview.setdefault('project_name', 'Unknown Project')
                    interview.setdefault('interview_type', 'Unknown Type')
                    interview.setdefault('transcript', '')
                    interview.setdefault('analysis', '')
                    interviews.append(interview)
            except Exception as e:
                logger.error(f"Error loading interview {file_path}: {str(e)}")
                continue
    return sorted(interviews, key=lambda x: x.get('date', ''), reverse=True)

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

def save_interview_data(project_name, interview_type, transcript, analysis, form_data=None):
    """Save interview data to a JSON file."""
    try:
        interview_id = str(uuid.uuid4())
        interview_data = {
            'id': interview_id,
            'project_name': project_name,
            'interview_type': interview_type,
            'date': datetime.now().isoformat(),
            'transcript': transcript,
            'analysis': analysis,
            'metadata': form_data if form_data else {}
        }
        
        # Create interviews directory if it doesn't exist
        INTERVIEWS_DIR.mkdir(exist_ok=True)
        
        file_path = INTERVIEWS_DIR / f"{interview_id}.json"
        with open(file_path, 'w') as f:
            json.dump(interview_data, f, indent=2)
        
        logger.info(f"Interview saved successfully: {interview_id}")
        return interview_id
        
    except Exception as e:
        logger.error(f"Error saving interview: {str(e)}")
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

@app.route('/')
def home():
    """Home page."""
    try:
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
                             recent_interviews=recent_interviews,
                             recent_personas=recent_personas,
                             recent_journey_maps=recent_journey_maps)
    except Exception as e:
        logger.error(f"Error loading home page: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Error loading home page', 'error')
        return render_template('home.html',
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
        project_data = data.get('project', {})
        project_name = project_data.get('name')
        interview_type = project_data.get('type')
        project_description = project_data.get('description')

        if not project_name or not interview_type or not project_description:
            logger.error(f"Missing required fields. Received: project_name={project_name}, interview_type={interview_type}")
            return jsonify({'error': 'Missing required fields'}), 400

        # Generate a unique ID for the interview
        interview_id = str(uuid.uuid4())
        logger.info(f"Creating new interview with ID: {interview_id}")

        # Generate the interview prompt based on interview type
        if interview_type == "Persona Interview":
            interview_prompt = f"""#Role: you are Daria, a UX researcher conducting a Persona Interview
#Objective: You are conducting a Persona Interview about {project_name}
#Project Description: {project_description}
#Instructions: 
1. Ask questions to understand the interviewee's characteristics, behaviors, goals, and needs
2. Focus on gathering information about:
   - Demographics: Age, role, experience level, and other relevant characteristics
   - Behaviors: How they interact with the system, their workflow, and habits
   - Goals: What they're trying to achieve and their motivations
   - Challenges: Pain points, frustrations, and obstacles they face
   - Preferences: Their likes, dislikes, and preferences in using the system
3. Keep questions concise and direct
4. Never repeat questions
5. Ask follow-up questions only when clarification is needed
6. Maintain a professional tone without unnecessary acknowledgments"""
        
        elif interview_type == "Journey Map Interview":
            interview_prompt = f"""#Role: you are Daria, a UX researcher conducting a Journey Map Interview
#Objective: You are conducting a Journey Map Interview about {project_name}
#Project Description: {project_description}
#Instructions: 
1. Ask questions to understand the user's journey through different stages
2. Focus on gathering information about:
   - Journey Stages: Different phases or steps in their experience
   - Touchpoints: Interactions with the system and other stakeholders
   - Emotions: How they feel at different stages
   - Pain Points: Challenges and frustrations
   - Moments of Delight: Positive experiences and successes
3. Keep questions concise and direct
4. Never repeat questions
5. Ask follow-up questions only when clarification is needed
6. Maintain a professional tone without unnecessary acknowledgments"""
        
        else:
            interview_prompt = f"""#Role: you are Daria, a UX researcher conducting an Application Interview
#Objective: You are conducting an Application Interview about {project_name}
#Project Description: {project_description}
#Instructions: 
1. Ask questions to understand the user's experience and needs
2. Focus on gathering information about:
   - Role and Experience: Their role and how they use the system
   - Key Tasks: Main tasks they perform
   - Pain Points: Any frustrations or challenges
   - Suggestions: Improvements they'd like to see
   - Overall Experience: Their satisfaction and needs
3. Keep questions concise and direct
4. Never repeat questions
5. Ask follow-up questions only when clarification is needed
6. Maintain a professional tone without unnecessary acknowledgments"""
        
        # Store the prompt
        interview_prompts[project_name] = interview_prompt
        logger.info(f"Stored interview prompt for project: {project_name}")
        
        # Initialize conversation using OpenAI client
        try:
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url="https://api.openai.com/v1"
            )
            logger.info("OpenAI client created successfully")
            
            # Initialize the conversation with the prompt
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Daria, a UX researcher conducting interviews."},
                    {"role": "user", "content": f"This is the start of a new interview. Here is your role and objective:\n\n{interview_prompt}"}
                ],
                temperature=0.7
            )
            logger.info("Initial conversation response received from OpenAI")
            
            # Store the initial conversation state
            conversations[project_name] = {
                'id': interview_id,
                'messages': [
                    {"role": "system", "content": "You are Daria, a UX researcher conducting interviews."},
                    {"role": "user", "content": f"This is the start of a new interview. Here is your role and objective:\n\n{interview_prompt}"},
                    {"role": "assistant", "content": response.choices[0].message.content}
                ]
            }
            logger.info(f"Stored conversation for project: {project_name}")
            
        except Exception as e:
            logger.error(f"Error with OpenAI client: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'error': 'Failed to initialize interview with AI',
                'details': str(e)
            }), 500
        
        return jsonify({
            'status': 'success',
            'interview_prompt': interview_prompt,
            'redirect_url': url_for('interview', project_name=project_name)
        })
        
    except Exception as e:
        logger.error(f"Error in save_interview route: {str(e)}")
        logger.error(traceback.format_exc())
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
            
            # Generate system message based on interview type
            if "Persona Interview" in prompt:
                system_message = """You are Daria, an expert UX researcher conducting a persona interview. 
                Your goal is to understand the user's background, behaviors, goals, and pain points to create a detailed persona."""
            elif "Journey Map Interview" in prompt:
                system_message = """You are Daria, an expert UX researcher conducting a journey mapping interview. 
                Your goal is to understand the user's experience at each stage of their journey with the system."""
            else:  # Application Interview
                system_message = """You are Daria, an expert UX researcher conducting an application evaluation interview. 
                Your goal is to understand how users interact with the system and identify areas for improvement."""
            
            # Add context about the current state of the interview
            system_message += f"\nThis is question {question_count} of the interview about {project_name}."
            
            # If we're near the end of the interview, guide the conversation towards wrap-up
            if question_count >= 12:  # 3 questions before max
                system_message += "\nThe interview is nearing completion. Guide the conversation towards a natural conclusion, asking for any final thoughts or insights."
            
            # Generate response using the language model
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_input}
            ]
            
            response = llm.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content.strip()
            
            return jsonify({
                'status': 'success',
                'response': response_text
            })
            
    except Exception as e:
        print(f"Error in interview route: {str(e)}")
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

@app.route('/final_analysis', methods=['POST'])
def final_analysis():
    try:
        project_name = request.args.get('project_name')
        if not project_name:
            return jsonify({'status': 'error', 'error': 'Project name is required'}), 400

        data = request.get_json()
        transcript = data.get('transcript', '')
        report_prompt = data.get('report_prompt', '')

        # Get the saved interview prompt to determine the interview type
        interview_prompt = interview_prompts.get(project_name)
        if not interview_prompt:
            return jsonify({'status': 'error', 'error': 'Interview prompt not found'}), 404

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
3. Pain Points: Identify any frustrations or challenges
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

        # Extract form data from the interview prompt
        form_data = {
            'researcher': {
                'name': extract_value(interview_prompt, 'Name:', 'researcher'),
                'role': extract_value(interview_prompt, 'Role:', 'researcher'),
                'email': extract_value(interview_prompt, 'Email:', 'researcher'),
                'phone': extract_value(interview_prompt, 'Phone:', 'researcher')
            },
            'interviewee': {
                'name': extract_value(interview_prompt, 'Name:', 'interviewee'),
                'age': extract_value(interview_prompt, 'Age Range:', 'interviewee'),
                'gender': extract_value(interview_prompt, 'Gender:', 'interviewee'),
                'location': extract_value(interview_prompt, 'Location:', 'interviewee'),
                'occupation': extract_value(interview_prompt, 'Occupation:', 'interviewee'),
                'industry': extract_value(interview_prompt, 'Industry:', 'interviewee'),
                'experience': extract_value(interview_prompt, 'Years of Experience:', 'interviewee'),
                'education': extract_value(interview_prompt, 'Education:', 'interviewee')
            },
            'technology': {
                'primaryDevice': extract_value(interview_prompt, 'Primary Device:', 'technology'),
                'operatingSystem': extract_value(interview_prompt, 'Operating System:', 'technology'),
                'browserPreference': extract_value(interview_prompt, 'Browser Preference:', 'technology'),
                'technicalProficiency': extract_value(interview_prompt, 'Technical Proficiency:', 'technology')
            }
        }

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
    interviews = list_interviews()
    return render_template('archive.html', interviews=interviews)

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
    """View interview analysis."""
    try:
        interview = load_interview(interview_id)
        if not interview:
            flash('Interview not found', 'error')
            return redirect(url_for('archive'))
        
        return render_template('analysis.html', 
                             interview=interview,
                             analysis=interview.get('analysis', ''))
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

@app.route('/search_interviews', methods=['POST'])
def search_interviews():
    """Search interviews using vector store."""
    try:
        data = request.get_json()
        query = data.get('query')
        k = data.get('k', 5)  # Number of results to return
        search_params = data.get('search_params', {})

        if not query:
            logger.warning("No search query provided")
            return jsonify({'error': 'No search query provided'}), 400

        if not vector_store:
            logger.error("Vector store not initialized")
            return jsonify({'error': 'Vector store not initialized'}), 500

        logger.info(f"Performing search with query: {query}")
        
        # Debug information to be sent to frontend
        debug_info = {
            'query': query,
            'search_params': search_params,
            'exact_matches': [],
            'semantic_results': [],
            'final_results': []
        }
        
        # First try exact match search
        exact_matches = []
        seen_interview_ids = set()  # Track seen interview IDs to prevent duplicates
        
        for interview_id in vector_store.interview_ids:
            try:
                # Skip if we've already seen this interview
                if interview_id in seen_interview_ids:
                    continue
                    
                # Load the interview
                interview_file = Path('interviews') / f"{interview_id}.json"
                if not interview_file.exists():
                    continue
                    
                with open(interview_file) as f:
                    interview = json.load(f)
                    
                transcript = interview.get('transcript', '')
                if not transcript:
                    continue
                    
                # Look for exact matches in the transcript
                for line in transcript.split('\n'):
                    if line.startswith('You:'):
                        response = line[4:].strip()
                        response_lower = response.lower()
                        query_lower = query.lower()
                        
                        # First check for exact phrase match
                        if query_lower in response_lower:
                            exact_matches.append({
                                'id': interview_id,
                                'project_name': interview.get('project_name', 'Unknown Project'),
                                'interview_type': interview.get('interview_type', 'Unknown Type'),
                                'date': interview.get('date', datetime.now().isoformat()),
                                'transcript_preview': response,
                                'score': 1.0,  # Exact matches get highest score
                                'debug_info': {
                                    'match_type': 'Exact Phrase Match',
                                    'word_overlap': len(query_lower.split()),
                                    'word_overlap_ratio': 1.0
                                }
                            })
                            seen_interview_ids.add(interview_id)
                            break
                        
                        # If no exact phrase match, try word overlap
                        query_words = set(query_lower.split())
                        response_words = set(response_lower.split())
                        
                        # Calculate word overlap
                        matching_words = query_words & response_words
                        word_overlap_ratio = len(matching_words) / len(query_words)
                        
                        # If we have a good match, add it to results
                        if word_overlap_ratio >= 0.7:  # Increased threshold for word overlap
                            exact_matches.append({
                                'id': interview_id,
                                'project_name': interview.get('project_name', 'Unknown Project'),
                                'interview_type': interview.get('interview_type', 'Unknown Type'),
                                'date': interview.get('date', datetime.now().isoformat()),
                                'transcript_preview': response,
                                'score': 0.8,  # High score for word overlap
                                'debug_info': {
                                    'match_type': 'Word Overlap Match',
                                    'word_overlap': len(matching_words),
                                    'word_overlap_ratio': word_overlap_ratio
                                }
                            })
                            seen_interview_ids.add(interview_id)
                            break
            except Exception as e:
                logger.error(f"Error processing interview {interview_id}: {str(e)}")
                continue
                
        # If we found exact matches, return those
        if exact_matches:
            debug_info['final_results'] = exact_matches[:k]
            return jsonify({
                'results': exact_matches[:k],
                'debug_info': debug_info
            })
            
        # If no exact matches, try semantic search
        results = vector_store.semantic_search(query, k=k)
        
        if not results:
            return jsonify({
                'results': [],
                'debug_info': debug_info
            })

        # Process and format results
        formatted_results = []
        for result in results:
            try:
                result_debug = {
                    'id': result.get('id'),
                    'score': result.get('score', 0),
                    'responses_found': 0,
                    'most_relevant_response': None,
                    'word_overlap': 0
                }
                
                # Format the transcript preview
                transcript = result.get('transcript', '')
                transcript_preview = ''
                
                if transcript:
                    # Extract user responses
                    responses = []
                    for line in transcript.split('\n'):
                        if line.startswith('You:'):
                            response = line[4:].strip()
                            # Skip permission responses if exclude_permission is True
                            if search_params.get('exclude_permission'):
                                if any(x in response.lower() for x in ['yes, you have my', 'permission', 'proceed', 'yes, proceed', 'all right']):
                                    continue
                            # Skip short responses and system messages
                            if len(response) > 10 and not any(x in response.lower() for x in ['start', 'yes, proceed', 'all right']):
                                responses.append(response)
                    
                    if responses:
                        result_debug['responses_found'] = len(responses)
                        # Find the most relevant response
                        most_relevant = None
                        highest_overlap = 0
                        for response in responses:
                            # Calculate word overlap with query
                            query_words = set(query.lower().split())
                            response_words = set(response.lower().split())
                            matching_words = query_words & response_words
                            overlap = len(matching_words) / len(query_words)
                            
                            if overlap > highest_overlap:
                                highest_overlap = overlap
                                most_relevant = response
                        
                        if most_relevant:
                            result_debug['most_relevant_response'] = most_relevant
                            result_debug['word_overlap'] = highest_overlap
                            transcript_preview = most_relevant
                            if len(transcript_preview) > 200:
                                transcript_preview = transcript_preview[:200] + '...'

                # Check if the result meets minimum relevance threshold
                min_relevance = search_params.get('min_relevance', 0.2)  # Reduced from 0.3 to 0.2
                if result.get('score', 0) < min_relevance:
                    result_debug['skipped'] = True
                    result_debug['reason'] = f"Score {result.get('score', 0)} below threshold {min_relevance}"
                    debug_info['semantic_results'].append(result_debug)
                    continue

                formatted_results.append({
                    'id': result.get('id'),
                    'project_name': result.get('project_name'),
                    'interview_type': result.get('interview_type'),
                    'date': result.get('date'),
                    'transcript_preview': transcript_preview,
                    'score': result.get('score', 0),
                    'debug_info': result_debug
                })
            except Exception as e:
                logger.error(f"Error processing search result: {str(e)}")
                continue

        debug_info['final_results'] = formatted_results
        return jsonify({
            'results': formatted_results,
            'debug_info': debug_info
        })

    except Exception as e:
        logger.error(f"Error in search_interviews: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
        project_name = data.get('project_name')
        interview_ids = data.get('interview_ids', [])
        
        logger.info(f"Generating persona for project: {project_name}")
        logger.info(f"Selected interview IDs: {interview_ids}")
        
        if not project_name or not interview_ids:
            return jsonify({'error': 'Project name and interview IDs are required'}), 400
        
        # Load selected interviews
        interviews = []
        for interview_id in interview_ids:
            interview_path = os.path.join('interviews', f"{interview_id}.json")
            logger.info(f"Loading interview from: {interview_path}")
            
            if not os.path.exists(interview_path):
                logger.error(f"Interview file not found: {interview_path}")
                continue
                
            try:
                with open(interview_path, 'r') as f:
                    interview_data = json.load(f)
                    logger.info(f"Loaded interview {interview_id}")
                    logger.info(f"Interview type: {interview_data.get('interview_type')}")
                    logger.info(f"Transcript length: {len(interview_data.get('transcript', ''))}")
                    logger.info(f"Analysis length: {len(interview_data.get('analysis', ''))}")
                    interviews.append(interview_data)
            except Exception as e:
                logger.error(f"Error loading interview {interview_id}: {str(e)}")
                continue
        
        if not interviews:
            return jsonify({'error': 'No valid interviews found'}), 400
        
        logger.info(f"Successfully loaded {len(interviews)} interviews")
        
        # Create OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Create a structured prompt for persona generation
        analysis_prompt = f"""As a UX research expert, analyze these {len(interviews)} interviews and create a detailed user persona. 
Focus on extracting specific, actionable insights from the interviews.

For each interview, I'll provide:
1. The interview transcript
2. The individual analysis
3. The interview date and type

Please create a comprehensive persona and return it as a JSON object with the following structure:

{{
    "demographics": {{
        "age_range": "Age range",
        "gender": "Gender",
        "occupation": "Occupation",
        "location": "Location",
        "education": "Education level"
    }},
    "goals": [
        {{
            "goal": "Primary goal",
            "motivation": "Why this goal is important",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "behaviors": [
        {{
            "behavior": "Specific behavior",
            "frequency": "How often this occurs",
            "context": "When/where this happens",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "pain_points": [
        {{
            "pain_point": "Description of the pain point",
            "impact": "How it affects the user",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "needs": [
        {{
            "need": "Specific need",
            "priority": "High, Medium, or Low",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ],
    "preferences": [
        {{
            "preference": "Specific preference",
            "reason": "Why this preference exists",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }}
    ]
}}

Interview Data:
{json.dumps(interviews, indent=2)}

Please ensure your response is a valid JSON object with all the sections and fields as shown above. Include specific quotes from the interviews to support each insight."""

        logger.info("Sending request to OpenAI")
        # Get analysis from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a UX research expert specializing in persona creation. Your task is to analyze interview data and create a detailed, evidence-based persona with specific insights and supporting quotes. Return your analysis as a structured JSON object."},
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
            persona_data = json.loads(analysis)
            logger.info("Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.error("Raw response:")
            logger.error(analysis)
            raise
        
        # Generate HTML for the persona
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
        
        logger.info("Generated HTML content")
        return jsonify({
            'html': html,
            'persona_data': persona_data
        })
        
    except Exception as e:
        logger.error(f"Error generating persona: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
    # Pre-configured test data
    project_name = "Green Eggs and Ham"
    interview_type = "Journey Map Interview"
    prompt = """#Role: you are Daria, a UX researcher conducting a Journey Map Interview
#Objective: You are conducting a Journey Map Interview about Green Eggs and Ham
#Project Description: study how they order green eggs and ham
#Instructions: 
1. Ask questions to understand the user's journey through different stages
2. Focus on gathering information about:
   - Journey Stages: Different phases or steps in their experience
   - Touchpoints: Interactions with the system and other stakeholders
   - Emotions: How they feel at different stages
   - Pain Points: Challenges and frustrations
   - Moments of Delight: Positive experiences and successes
3. Keep questions concise and direct
4. Never repeat questions
5. Ask follow-up questions only when clarification is needed
6. Maintain a professional tone without unnecessary acknowledgments"""

    # Store the interview prompt
    interview_prompts[project_name] = prompt

    # Create initial conversation
    conversations[project_name] = {
        'messages': [
            {"role": "system", "content": prompt}
        ]
    }

    # Create interview object with required data
    interview = {
        'id': str(uuid.uuid4()),
        'project': {
            'name': project_name,
            'type': interview_type,
            'description': 'Study how users order green eggs and ham'
        },
        'researcher': {
            'name': 'Daria'
        },
        'interviewee': {
            'name': 'Test User'
        },
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return render_template('interview.html', 
                         project_name=project_name,
                         prompt=prompt,
                         interview=interview)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5003) 