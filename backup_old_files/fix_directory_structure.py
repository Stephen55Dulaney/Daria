#!/usr/bin/env python3
"""
Fix Directory Structure for DARIA

This script ensures all required directories for the DARIA Interview Tool
are created before the application runs.
"""

import os
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist"""
    try:
        base_dir = Path.cwd()
        
        # Main data directories
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured data directory: {data_dir}")
        
        # Interview data directories
        interviews_dir = data_dir / "interviews"
        interviews_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured interviews directory: {interviews_dir}")
        
        # Sessions directory (critical for transcript uploads)
        sessions_dir = interviews_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured sessions directory: {sessions_dir}")
        
        # Other key directories
        processed_dir = interviews_dir / "processed"
        processed_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured processed directory: {processed_dir}")
        
        raw_dir = interviews_dir / "raw"
        raw_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured raw directory: {raw_dir}")
        
        # Create logs directory
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured logs directory: {logs_dir}")
        
        # Create uploads directory
        uploads_dir = base_dir / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured uploads directory: {uploads_dir}")
        
        # Create prompt directory
        prompt_dir = base_dir / "tools" / "prompt_manager" / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured prompts directory: {prompt_dir}")
        
        # Create issues directory
        issues_dir = data_dir / "issues"
        issues_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured issues directory: {issues_dir}")
        
        # Create discussions directory
        discussions_dir = data_dir / "discussions"
        discussions_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured discussions directory: {discussions_dir}")
        
        # Create backups directory
        backups_dir = data_dir / "backups"
        backups_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured backups directory: {backups_dir}")
        
        # Create users directory
        users_dir = data_dir / "users"
        users_dir.mkdir(exist_ok=True)
        logger.info(f"Ensured users directory: {users_dir}")
        
        # Verify permissions
        for directory in [sessions_dir, processed_dir, raw_dir, logs_dir, uploads_dir]:
            try:
                test_file = directory / "test_write_access.tmp"
                with open(test_file, "w") as f:
                    f.write("Test write access")
                os.remove(test_file)
                logger.info(f"Verified write access to {directory}")
            except Exception as e:
                logger.warning(f"Warning: Could not verify write access to {directory}: {str(e)}")
        
        logger.info("✅ All required directories have been created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Fixing directory structure for DARIA...")
    if ensure_directories():
        logger.info("Directory structure fixed successfully.")
        
        # If a script name is provided, run it with the rest of the arguments
        if len(sys.argv) > 1:
            script_path = sys.argv[1]
            script_args = sys.argv[2:]
            
            logger.info(f"Running {script_path} with arguments: {' '.join(script_args)}")
            
            try:
                # Use exec to run the script
                script_globals = {
                    "__file__": script_path,
                    "__name__": "__main__"
                }
                
                # Add the current directory to sys.path
                sys.path.insert(0, os.getcwd())
                
                # Prepare the command line arguments
                sys.argv = [script_path] + script_args
                
                # Load and execute the script
                with open(script_path) as f:
                    exec(f.read(), script_globals)
                    
            except Exception as e:
                logger.error(f"Error running {script_path}: {str(e)}")
                sys.exit(1)
    else:
        logger.error("Failed to fix directory structure.")
        sys.exit(1) 