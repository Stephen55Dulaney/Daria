#!/usr/bin/env python3
"""
Fix syntax errors in Python files
"""

import os
import sys
import re
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_syntax_errors(file_path):
    """
    Fixes common syntax errors in a Python file:
    1. Removes stray '%' characters at the end of lines
    2. Closes unclosed try blocks
    """
    logger.info(f"Checking file: {file_path}")
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove stray '%' characters
    fixed_lines = []
    for line in lines:
        if line.strip().endswith('%'):
            fixed_line = line.rstrip('% \t\n') + '\n'
            logger.info(f"Removed stray '%' character from line")
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    # Check for unclosed try blocks
    try_stack = []
    except_stack = []
    
    for i, line in enumerate(fixed_lines):
        if re.search(r'\btry\s*:', line):
            try_stack.append(i)
        
        if re.search(r'\bexcept\b', line):
            if try_stack:
                try_stack.pop()  # Match with the last open try
        
        if re.search(r'\bfinally\s*:', line):
            if try_stack:
                try_stack.pop()  # Match with the last open try
    
    # If there are still unclosed try blocks, add except blocks
    if try_stack:
        logger.info(f"Found {len(try_stack)} unclosed try blocks")
        new_lines = fixed_lines.copy()
        
        # Add missing except blocks (in reverse order to avoid index shifts)
        for try_index in sorted(try_stack, reverse=True):
            # Find the indentation level
            match = re.match(r'^(\s*)', fixed_lines[try_index])
            indent = match.group(1) if match else '    '
            
            # Add a generic except block before the next line at the same indentation level
            for i in range(try_index + 1, len(fixed_lines)):
                line = fixed_lines[i]
                if line.strip() and re.match(f'^{re.escape(indent)}[^\\s]', line):
                    logger.info(f"Adding except block after line {try_index}")
                    new_lines.insert(i, f"{indent}except Exception as e:\n{indent}    logger.error(f\"Error: {{str(e)}}\")\n")
                    break
        
        fixed_lines = new_lines
    
    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    logger.info(f"File fixed and saved: {file_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_all_syntax_issues.py <python_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    success = fix_syntax_errors(file_path)
    if success:
        logger.info("Syntax issues fixed successfully!")
    else:
        logger.error("Failed to fix syntax issues.")
        sys.exit(1) 