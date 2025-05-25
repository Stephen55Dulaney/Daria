#!/usr/bin/env python3
"""
Standalone Audio Services for DARIA Interview Tool
This script runs the Text-to-Speech and Speech-to-Text services on ports
that don't conflict with the main application.
"""
import os
import sys
import argparse
import logging
import subprocess
import time
import signal
import atexit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store process IDs for cleanup
processes = []

def cleanup():
    """Kill all child processes when this script terminates"""
    for p in processes:
        if p:
            logger.info(f"Cleaning up process {p.pid}")
            try:
                p.terminate()
                p.wait(3)  # Give it 3 seconds to terminate
            except:
                try:
                    p.kill()  # Force kill if terminate doesn't work
                except:
                    pass

def main():
    parser = argparse.ArgumentParser(description='DARIA Interview Tool - Audio Services')
    parser.add_argument('--tts-port', type=int, default=5015, help='Port for Text-to-Speech service')
    parser.add_argument('--stt-port', type=int, default=5016, help='Port for Speech-to-Text service')
    args = parser.parse_args()
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Force skip eventlet for Python 3.13+
    if sys.version_info.major == 3 and sys.version_info.minor >= 13:
        logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor} detected - setting SKIP_EVENTLET=1")
        os.environ['SKIP_EVENTLET'] = '1'
    
    print("="*60)
    print("DARIA INTERVIEW TOOL - AUDIO SERVICES")
    print("="*60)
    print(f"Starting Text-to-Speech server on port {args.tts_port}")
    print(f"Starting Speech-to-Text server on port {args.stt_port}")
    print("These services should be running in parallel with the main application")
    print("="*60)
    
    # Locate the simple_tts_test.py script in audio_tools directory
    audio_tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_tools')
    simple_tts_path = os.path.join(audio_tools_dir, 'simple_tts_test.py')
    
    if not os.path.exists(simple_tts_path):
        logger.error(f"Could not find audio tools at {simple_tts_path}")
        logger.info("Looking for simple_tts_test.py in current directory...")
        simple_tts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simple_tts_test.py')
        if not os.path.exists(simple_tts_path):
            logger.error("Audio services not found. Please ensure simple_tts_test.py exists.")
            return

    # Make the script executable
    try:
        os.chmod(simple_tts_path, 0o755)
    except:
        pass
        
    # Start the TTS server
    env = os.environ.copy()
    env['FLASK_APP'] = 'simple_tts_test.py'
    env['FLASK_ENV'] = 'development'
    env['FLASK_DEBUG'] = '1'
    env['PORT'] = str(args.tts_port)
    
    # Launch the TTS server with the port variable
    tts_cmd = [sys.executable, simple_tts_path, '--port', str(args.tts_port)]
    logger.info(f"Starting TTS server: {' '.join(tts_cmd)}")
    
    try:
        tts_process = subprocess.Popen(tts_cmd)
        processes.append(tts_process)
        logger.info(f"TTS server started with PID {tts_process.pid}")
    except Exception as e:
        logger.error(f"Error starting TTS server: {str(e)}")
    
    # Start STT service (this will be implemented later)
    stt_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_tools/simple_stt_test.py')
    if os.path.exists(stt_script_path):
        stt_command = f"{sys.executable} {stt_script_path} --port {args.stt_port}"
        logger.info(f"Starting STT server: {stt_command}")
        stt_process = subprocess.Popen(stt_command.split())
        processes.append(stt_process)
        logger.info(f"STT server started with PID {stt_process.pid}")
    else:
        logger.warning(f"STT script not found at {stt_script_path}")
        stt_process = None
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
        cleanup()

if __name__ == "__main__":
    main() 