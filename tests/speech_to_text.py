import sounddevice as sd
import numpy as np
import wave
import os
from io import BytesIO
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    print(f"Recording for {duration} seconds...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    print("Recording finished")
    return recording

def save_audio(recording, filename="temp_recording.wav", sample_rate=16000):
    """Save recorded audio to WAV file"""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((recording * 32767).astype(np.int16).tobytes())
    return filename

def transcribe_audio(client, audio_file):
    """Transcribe audio using ElevenLabs API"""
    with open(audio_file, 'rb') as f:
        audio_data = BytesIO(f.read())
        transcription = client.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",
            tag_audio_events=True,
            language_code="eng",
            diarize=True,
        )
    return transcription.text

def main():
    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    
    try:
        # Record audio
        recording = record_audio()
        
        # Save audio to temporary file
        audio_file = save_audio(recording)
        
        # Transcribe audio
        print("Transcribing...")
        text = transcribe_audio(client, audio_file)
        print("\nTranscription:")
        print(text)
        
    finally:
        # Clean up temporary file
        if os.path.exists("temp_recording.wav"):
            os.remove("temp_recording.wav")

if __name__ == "__main__":
    main()

