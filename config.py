import os
from pathlib import Path

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    
    # Interview data directory
    INTERVIEWS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'interviews')
    Path(INTERVIEWS_DIR).mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    LOG_LEVEL = 'INFO' 