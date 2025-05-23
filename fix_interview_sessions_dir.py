#!/usr/bin/env python3
"""
Fix INTERVIEW_SESSIONS_DIR Configuration for DARIA

This script applies a patch to run_interview_api.py to ensure
the INTERVIEW_SESSIONS_DIR configuration is properly set.
"""

import os
import sys
import re
import logging
from pathlib import Path
import importlib.util

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def patch_interview_api_file():
    """Patch the run_interview_api.py file to properly set INTERVIEW_SESSIONS_DIR"""
    try:
        # Find the run_interview_api.py file
        api_file = Path('run_interview_api.py')
        if not api_file.exists():
            logger.error(f"Could not find {api_file}")
            return False
        
        logger.info(f"Found API file: {api_file}")
        
        # Read the content of the file
        with open(api_file, 'r') as f:
            content = f.read()
        
        # Check if we need to apply the patch
        if "app.config['INTERVIEW_SESSIONS_DIR']" in content:
            logger.info("INTERVIEW_SESSIONS_DIR is already configured in the file")
            
            # But we need to make sure it's correctly set
            if "SESSIONS_DIR = DATA_DIR / 'sessions'" in content:
                logger.info("SESSIONS_DIR is already defined")
            else:
                # Add SESSIONS_DIR definition where DATA_DIR is defined
                data_dir_pattern = r"(DATA_DIR = .*?\n)"
                if re.search(data_dir_pattern, content):
                    content = re.sub(
                        data_dir_pattern,
                        r"\1SESSIONS_DIR = DATA_DIR / 'sessions'\n",
                        content
                    )
                    logger.info("Added SESSIONS_DIR definition")
        else:
            logger.info("Applying patch to add INTERVIEW_SESSIONS_DIR configuration")
            
            # Check if the DATA_DIR line exists
            data_dir_pattern = r"(DATA_DIR = .*?\n)"
            if re.search(data_dir_pattern, content):
                # Add SESSIONS_DIR definition after DATA_DIR
                content = re.sub(
                    data_dir_pattern,
                    r"\1SESSIONS_DIR = DATA_DIR / 'sessions'\n",
                    content
                )
                logger.info("Added SESSIONS_DIR definition")
            
            # Find a good place to add the app.config setting
            # After DATA_DIR.mkdir line
            mkdir_pattern = r"(DATA_DIR\.mkdir\(.*?\).*?\n)"
            if re.search(mkdir_pattern, content):
                content = re.sub(
                    mkdir_pattern,
                    r"\1SESSIONS_DIR.mkdir(parents=True, exist_ok=True)\n\n# Configure app paths\napp.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)\napp.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)\n",
                    content
                )
                logger.info("Added app.config for INTERVIEW_SESSIONS_DIR")
            else:
                # Try to add after the PROMPT_DIR configuration
                prompt_dir_pattern = r"(PROMPT_DIR\.mkdir\(.*?\).*?\n)"
                if re.search(prompt_dir_pattern, content):
                    content = re.sub(
                        prompt_dir_pattern,
                        r"\1SESSIONS_DIR = DATA_DIR / 'sessions'\nSESSIONS_DIR.mkdir(parents=True, exist_ok=True)\n\n# Configure app paths\napp.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)\napp.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)\n",
                        content
                    )
                    logger.info("Added app.config for INTERVIEW_SESSIONS_DIR after PROMPT_DIR")
                else:
                    logger.error("Could not find a suitable location to insert the configuration")
                    return False
        
        # Now modify the API upload transcript function to ensure it uses the right directory
        upload_pattern = r"(file_path = os\.path\.join\(app\.config\['INTERVIEW_SESSIONS_DIR'\], f\"{session_id}\.json\"\))"
        if not re.search(upload_pattern, content):
            # Try to find the upload_transcript function
            upload_func_pattern = r"@app\.route\('\/api\/upload_transcript', methods=\['POST'\]\)\ndef api_upload_transcript\(\):"
            if re.search(upload_func_pattern, content):
                logger.info("Found api_upload_transcript function")
                
                # Find the part where it creates the file_path
                old_file_path_pattern = r"file_path = os\.path\.join\(.*?, f\"{session_id}\.json\"\)"
                if re.search(old_file_path_pattern, content):
                    content = re.sub(
                        old_file_path_pattern,
                        "file_path = os.path.join(app.config['INTERVIEW_SESSIONS_DIR'], f\"{session_id}.json\")",
                        content
                    )
                    logger.info("Fixed file_path in api_upload_transcript function")
        
        # Write the modified content back to the file
        with open(api_file, 'w') as f:
            f.write(content)
        
        logger.info(f"✅ Successfully patched {api_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error patching interview API file: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Fixing INTERVIEW_SESSIONS_DIR configuration...")
    if patch_interview_api_file():
        logger.info("Configuration fixed successfully.")
        
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
        logger.error("Failed to fix configuration.")
        sys.exit(1) 