#!/usr/bin/env python
import os
import sys
import logging
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, render_template, request, jsonify, abort, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil
import socket

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

def copy_templates():
    """Copy templates from langchain_features to daria_interview_tool"""
    src_dir = Path('langchain_features/templates/langchain')
    dest_dir = Path('daria_interview_tool/templates/langchain')
    
    if not src_dir.exists():
        logger.error(f"Source directory {src_dir} does not exist!")
        return False
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all files
    count = 0
    for src_file in src_dir.glob('*.html'):
        dest_file = dest_dir / src_file.name
        try:
            shutil.copy2(src_file, dest_file)
            count += 1
            logger.info(f"Copied {src_file.name} to {dest_file}")
        except Exception as e:
            logger.error(f"Failed to copy {src_file.name}: {str(e)}")
    
    logger.info(f"Successfully copied {count} template files")
    return count > 0

def setup_interview_directory():
    """Set up the interviews directory for storing interview data"""
    interviews_dir = Path('interviews/raw')
    interviews_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Interview directory set up at {interviews_dir}")
    return True

def run_daria_interview_system():
    """Main function to run the DARIA interview system"""
    # Copy templates first
    if not copy_templates():
        print("ERROR: Failed to copy templates from langchain_features. Make sure the directory exists.")
        sys.exit(1)
    
    # Set up interviews directory
    if not setup_interview_directory():
        print("ERROR: Failed to set up interviews directory.")
        sys.exit(1)
    
    # Find a free port
    port = find_free_port(8000)
    if port is None:
        print("ERROR: Could not find a free port. Please free up ports in the 8000-8010 range.")
        sys.exit(1)
    
    # Set Flask environment variables
    os.environ['FLASK_APP'] = 'daria_interview_tool:create_app'
    os.environ['FLASK_DEBUG'] = '1'
    
    # Import and create app
    from daria_interview_tool import create_app
    app = create_app()
    
    # Print startup information
    print(f"\n===========================================================")
    print(f"DARIA INTERVIEW SYSTEM - SECURE EDITION")
    print(f"===========================================================")
    print(f"Server running on: http://127.0.0.1:{port}")
    print(f"Dashboard: http://127.0.0.1:{port}/langchain/dashboard")
    print(f"Generate Interview Link: http://127.0.0.1:{port}/langchain/generate_link")
    print(f"===========================================================")
    print(f"Security Notes:")
    print(f"- All interview links are secured with unique tokens")
    print(f"- Interviews expire after the configured time period")
    print(f"- Real-time monitoring is available for interview sessions")
    print(f"- For production deployment, add additional security measures")
    print(f"===========================================================\n")
    
    # Start the Flask app
    app.run(host='127.0.0.1', port=port, debug=True)

if __name__ == '__main__':
    run_daria_interview_system() 