import os
import logging
import tempfile
import requests
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Flask app
app = Flask(__name__, template_folder='templates')

# Initialize ElevenLabs API key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    logger.warning("ELEVENLABS_API_KEY not found. Text-to-speech functionality will be limited.")

# Available voices from ElevenLabs
AVAILABLE_VOICES = {
    "rachel": "EXAVITQu4vr4xnSDxMaL",
    "antoni": "ErXwobaYiN019PkySvjV",
    "elli": "MF3mGyEYCl7XYWbV9V6O",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "fin": "JBFqnCBsd6RMkjVDRZzb"
}

# Serve the test page
@app.route('/test_audio_endpoints.html')
def test_audio_endpoints():
    return render_template('test_audio_endpoints.html')

# Text-to-speech endpoint using direct API call
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
        
        # Make a direct API call to ElevenLabs
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 500
            
            # Get audio data
            audio_data = BytesIO(response.content)
            
            logger.info(f"Text-to-speech conversion successful, size: {len(response.content)} bytes")
            
            # Return audio file as response
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False
            )
            
        except Exception as elevenlabs_error:
            logger.error(f"ElevenLabs API error: {str(elevenlabs_error)}")
            return jsonify({'error': f'ElevenLabs API error: {str(elevenlabs_error)}'}), 500
        
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Speech-to-text endpoint
@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    try:
        # Check if audio file is provided
        if 'audio' not in request.files:
            logger.error("No audio file provided for speech-to-text")
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        if not audio_file:
            logger.error("Empty audio file provided for speech-to-text")
            return jsonify({'error': 'Empty audio file provided'}), 400
        
        logger.info("Speech-to-text request received")
        
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not found in environment")
            return jsonify({'error': 'ElevenLabs API key is not configured'}), 500
        
        # Save the audio file temporarily
        temp_dir = os.path.join(tempfile.gettempdir(), 'audio_temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filepath = os.path.join(temp_dir, f"audio_{uuid.uuid4()}.wav")
        
        audio_file.save(temp_filepath)
        logger.info(f"Audio file saved temporarily at {temp_filepath}")
        
        try:
            # Make a direct API call to ElevenLabs for speech-to-text
            url = "https://api.elevenlabs.io/v1/speech-to-text"
            
            headers = {
                "Accept": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            
            # Use scribe_v1 model instead of whisper-1 as per the error message
            with open(temp_filepath, 'rb') as f:
                files = {'file': (os.path.basename(temp_filepath), f, 'audio/wav')}
                data = {
                    'model_id': 'scribe_v1'  # Changed from whisper-1 to scribe_v1
                }
                
                logger.info(f"Sending request to ElevenLabs with model_id: scribe_v1")
                response = requests.post(url, headers=headers, files=files, data=data)
            
            # Clean up the temporary file
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
                logger.info(f"Temporary audio file removed: {temp_filepath}")
            
            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 500
            
            result = response.json()
            logger.info(f"Response from ElevenLabs: {result}")
            
            transcription = result.get('text', 'No transcription available')
            
            logger.info(f"Speech-to-text conversion successful: {transcription[:30]}...")
            
            return jsonify({'text': transcription})
            
        except Exception as elevenlabs_error:
            logger.error(f"ElevenLabs API error: {str(elevenlabs_error)}")
            
            # Provide a fallback response for testing
            return jsonify({
                'text': "Sorry, I couldn't transcribe that. The error was: " + str(elevenlabs_error)
            }), 200  # Still return 200 to not break the UI
        
    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Make sure temp files are always cleaned up
        try:
            if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
                logger.info(f"Temporary audio file removed in finally block: {temp_filepath}")
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temporary file: {str(cleanup_error)}")

# Add a root route to redirect to the test page
@app.route('/')
def index():
    return render_template('test_audio_endpoints.html')

# Run the app
if __name__ == '__main__':
    # Try a different port since both 5005 and 5006 are in use
    port = int(os.environ.get('PORT', 5007))
    logger.info(f"Starting text-to-speech server on port {port}")
    app.run(debug=True, port=port) 