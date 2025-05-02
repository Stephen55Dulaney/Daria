#!/usr/bin/env python
import os
import sys
import logging
from flask import Flask, redirect, url_for, render_template, abort

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app factory
from daria_interview_tool import create_app

# Create the app
app = create_app()

# Direct legacy routes
@app.route('/langchain_interview_test')
def langchain_interview_test():
    """Render langchain interview test page directly"""
    return render_template('langchain_interview_test.html')

@app.route('/langchain_interview_setup')
def langchain_interview_setup():
    """Render langchain interview setup page directly"""
    return render_template('langchain_interview_setup.html')

@app.route('/langchain_interview_session')
def langchain_interview_session():
    """Render langchain interview session page directly"""
    return render_template('langchain_interview_session.html')

# Run the app on a port that's likely free
if __name__ == '__main__':
    # Try various ports until one works
    ports_to_try = [5004, 5005, 5006, 5007, 5008, 5009]
    
    for port in ports_to_try:
        try:
            print(f"Attempting to start server on port {port}...")
            app.run(host='127.0.0.1', port=port, debug=True)
            break
        except OSError as e:
            print(f"Port {port} is in use, trying next port...")
            continue
    else:
        print("All ports are in use. Please free up a port and try again.") 