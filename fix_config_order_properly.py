#!/usr/bin/env python3
"""
Fix the order of app.config settings in run_interview_api.py properly
"""

import re
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_config_order_properly():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # First, find and remove any incorrect app.config lines
    i = 0
    while i < len(lines):
        if "app.config['INTERVIEW_DATA_DIR']" in lines[i] or "app.config['INTERVIEW_SESSIONS_DIR']" in lines[i]:
            logger.info(f"Found incorrect app.config setting at line {i+1}, removing it")
            lines.pop(i)
        else:
            i += 1
    
    # Find where to add the app.config lines - after app initialization but before any routes
    app_init_index = -1
    route_start_index = -1
    
    for i, line in enumerate(lines):
        if "app = Flask(__name__" in line:
            app_init_index = i
        if "@app.route" in line and route_start_index == -1:
            route_start_index = i
    
    if app_init_index != -1 and route_start_index != -1:
        logger.info(f"Found app initialization at line {app_init_index+1} and first route at line {route_start_index+1}")
        
        # Find where to add app.config - right after app secret key config
        for i in range(app_init_index, route_start_index):
            if "app.config['SECRET_KEY']" in lines[i]:
                logger.info(f"Found SECRET_KEY config at line {i+1}, adding INTERVIEW_SESSIONS_DIR after it")
                
                # Add our configuration after a blank line
                lines.insert(i + 2, "\n")
                lines.insert(i + 3, "# Initialize base directories\n")
                lines.insert(i + 4, "BASE_DIR = Path(__file__).parent.absolute()\n")
                lines.insert(i + 5, "DATA_DIR = BASE_DIR / \"data\" / \"interviews\"\n")
                lines.insert(i + 6, "SESSIONS_DIR = DATA_DIR / 'sessions'\n")
                lines.insert(i + 7, "\n")
                lines.insert(i + 8, "# Ensure directories exist\n")
                lines.insert(i + 9, "DATA_DIR.mkdir(parents=True, exist_ok=True)\n")
                lines.insert(i + 10, "SESSIONS_DIR.mkdir(parents=True, exist_ok=True)\n")
                lines.insert(i + 11, "\n")
                lines.insert(i + 12, "# Configure app paths\n")
                lines.insert(i + 13, "app.config['INTERVIEW_DATA_DIR'] = str(DATA_DIR)\n")
                lines.insert(i + 14, "app.config['INTERVIEW_SESSIONS_DIR'] = str(SESSIONS_DIR)\n")
                lines.insert(i + 15, "\n")
                
                # Now find and remove the duplicate definitions
                j = i + 16
                while j < len(lines):
                    if "BASE_DIR = Path" in lines[j] or "DATA_DIR = BASE_DIR" in lines[j]:
                        logger.info(f"Removing duplicate directory definition at line {j+1}")
                        lines.pop(j)
                    elif "SESSIONS_DIR = DATA_DIR" in lines[j]:
                        logger.info(f"Removing duplicate SESSIONS_DIR definition at line {j+1}")
                        lines.pop(j)
                    elif "DATA_DIR.mkdir" in lines[j] and "SESSIONS_DIR.mkdir" not in lines[j]:
                        logger.info(f"Removing duplicate DATA_DIR.mkdir at line {j+1}")
                        lines.pop(j)
                    else:
                        j += 1
                
                break
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        logger.info(f"✅ Successfully fixed configuration order in {file_path}")
        return True
    else:
        logger.error("Could not find app initialization or first route")
        return False

if __name__ == "__main__":
    logger.info("Fixing configuration order in run_interview_api.py properly")
    success = fix_config_order_properly()
    if success:
        logger.info("Configuration order fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix configuration order")
        sys.exit(1) 