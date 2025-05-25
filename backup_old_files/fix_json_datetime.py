#!/usr/bin/env python3
"""
Fix datetime JSON serialization in run_interview_api.py
"""

import re
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_json_datetime():
    # Read the file content
    file_path = 'run_interview_api.py'
    logger.info(f"Reading {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the custom JSON encoder is already defined
    if "class DateTimeEncoder(json.JSONEncoder):" in content:
        logger.info("DateTimeEncoder class already defined, skipping")
        return True
    
    # Find where to add the custom encoder class - after the imports
    import_section_end = re.search(r'(import.*?\n\n)', content, re.DOTALL)
    if not import_section_end:
        logger.error("Could not find the end of the import section")
        return False
    
    # Add the DateTimeEncoder class
    encoder_class = """
# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        import datetime
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

"""
    # Insert the encoder class after the imports
    content = content[:import_section_end.end()] + encoder_class + content[import_section_end.end():]
    
    # Now find instances of json.dump and replace with json.dump using the custom encoder
    json_dump_pattern = r'json\.dump\(([^,]+), ([^,]+)(?:, indent=(\d+))?\)'
    
    # Function to modify a json.dump call
    def replace_json_dump(match):
        obj = match.group(1)
        file_obj = match.group(2)
        indent = match.group(3) or "2"
        return f'json.dump({obj}, {file_obj}, cls=DateTimeEncoder, indent={indent})'
    
    # Replace all instances of json.dump
    content = re.sub(json_dump_pattern, replace_json_dump, content)
    
    # Save the modified content
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info(f"✅ Successfully added DateTimeEncoder class and updated json.dump calls")
    return True

if __name__ == "__main__":
    logger.info("Fixing datetime JSON serialization issue")
    success = fix_json_datetime()
    if success:
        logger.info("JSON datetime serialization fixed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to fix JSON datetime serialization")
        sys.exit(1) 