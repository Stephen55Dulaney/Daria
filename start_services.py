#!/usr/bin/env python3
"""
Start both the main application and the audio service
"""

import os
import sys
import time
import subprocess
import requests
import threading
import platform

# ANSI colors for terminal output
class Colors:
    AUDIO = '\033[94m'  # Blue
    MAIN = '\033[92m'   # Green
    WARNING = '\033[93m'  # Yellow
    ERROR = '\033[91m'  # Red
    RESET = '\033[0m'   # Reset

# Function to capture and print output from a subprocess with a prefix
def print_output(process, prefix, color):
    def read_output(stream):
        for line in iter(stream.readline, ''):
            print(f"{color}[{prefix}]{Colors.RESET} {line.rstrip()}")
    
    thread1 = threading.Thread(target=read_output, args=(process.stdout,))
    thread1.daemon = True
    thread1.start()
    
    thread2 = threading.Thread(target=read_output, args=(process.stderr,))
    thread2.daemon = True
    thread2.start()

# Check if ELEVENLABS_API_KEY is set
if "ELEVENLABS_API_KEY" not in os.environ:
    print(f"{Colors.WARNING}Warning: ELEVENLABS_API_KEY environment variable is not set.{Colors.RESET}")
    print("Speech-to-text functionality will be limited.")
    print("Please set it before running this script with:")
    if platform.system() == "Windows":
        print("  set ELEVENLABS_API_KEY=your_api_key_here")
    else:
        print("  export ELEVENLABS_API_KEY=your_api_key_here")
    
    proceed = input("Do you want to continue without the API key? (y/n) ")
    if proceed.lower() not in ["y", "yes"]:
        print("Exiting...")
        sys.exit(1)

# Start the audio service
print(f"{Colors.AUDIO}Starting audio service on port 5007...{Colors.RESET}")
try:
    audio_process = subprocess.Popen(
        [sys.executable, "audio_tools/simple_tts_test.py"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True
    )
    print_output(audio_process, "AUDIO", Colors.AUDIO)
except Exception as e:
    print(f"{Colors.ERROR}Error starting audio service: {str(e)}{Colors.RESET}")
    sys.exit(1)

# Wait for the audio service to start
print(f"{Colors.AUDIO}Waiting for audio service to become available...{Colors.RESET}")
max_retries = 5
retries = 0

while retries < max_retries:
    time.sleep(2)  # Wait for 2 seconds
    try:
        response = requests.get("http://localhost:5007/", timeout=1)
        if response.status_code == 200:
            print(f"{Colors.AUDIO}Audio service started successfully!{Colors.RESET}")
            break
    except requests.RequestException:
        retries += 1
        print(f"{Colors.AUDIO}Audio service not yet available (attempt {retries}/{max_retries})...{Colors.RESET}")

if retries >= max_retries:
    print(f"{Colors.WARNING}Warning: Audio service did not start properly.{Colors.RESET}")
    print("Speech-to-text functionality may not work.")
    proceed = input("Do you want to continue without the audio service? (y/n) ")
    if proceed.lower() not in ["y", "yes"]:
        print("Exiting...")
        if audio_process:
            audio_process.terminate()
        sys.exit(1)

# Start the main application
print(f"{Colors.MAIN}Starting main application on port 5010...{Colors.RESET}")
try:
    main_process = subprocess.Popen(
        [sys.executable, "run_langchain_direct_fixed.py", "--port", "5010"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True
    )
    
    print_output(main_process, "MAIN", Colors.MAIN)
    
    # Wait for the main process to finish
    main_process.wait()
    
except Exception as e:
    print(f"{Colors.ERROR}Error starting main application: {str(e)}{Colors.RESET}")
except KeyboardInterrupt:
    print(f"\n{Colors.WARNING}Received keyboard interrupt. Shutting down...{Colors.RESET}")
finally:
    # Shut down the audio service
    print(f"{Colors.AUDIO}Shutting down audio service...{Colors.RESET}")
    if 'audio_process' in locals() and audio_process:
        audio_process.terminate()
        try:
            audio_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            audio_process.kill()
    
    print("All services shut down.") 