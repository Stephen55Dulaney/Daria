#!/usr/bin/env python3
"""
Debug script to check all prompt YAML files for analysis_prompt field
"""

import os
import yaml
import sys
from pathlib import Path

def main():
    """Main function to check all YAML files."""
    # Use both possible prompt directories
    prompt_dirs = [
        "langchain_features/prompt_manager/prompts",
        "tools/prompt_manager/prompts"
    ]
    
    for prompt_dir in prompt_dirs:
        print(f"Checking prompts in {prompt_dir}...")
        if not os.path.exists(prompt_dir):
            print(f"  - Directory does not exist: {prompt_dir}")
            continue
            
        yaml_files = [f for f in os.listdir(prompt_dir) 
                     if f.endswith('.yml') and not f.startswith('.')]
        
        if not yaml_files:
            print(f"  - No YAML files found in {prompt_dir}")
            continue
            
        print(f"  - Found {len(yaml_files)} YAML files")
        
        for yaml_file in yaml_files:
            file_path = os.path.join(prompt_dir, yaml_file)
            try:
                with open(file_path, 'r') as f:
                    print(f"\nChecking {yaml_file}:")
                    data = yaml.safe_load(f)
                    
                    # Check if it loaded successfully
                    if not data:
                        print(f"  - ERROR: File is empty or failed to load")
                        continue
                        
                    # Print keys found in the file
                    print(f"  - Keys: {list(data.keys())}")
                    
                    # Check specifically for analysis_prompt
                    if 'analysis_prompt' in data:
                        ap = data['analysis_prompt']
                        if isinstance(ap, str):
                            print(f"  - analysis_prompt: {ap[:50]}...")
                        else:
                            print(f"  - ERROR: analysis_prompt is not a string, it's a {type(ap)}")
                    else:
                        print(f"  - WARNING: No analysis_prompt found")
                    
                    # Check dynamic_prompt_prefix (should be in all files)
                    if 'dynamic_prompt_prefix' in data:
                        dp = data['dynamic_prompt_prefix']
                        if isinstance(dp, str):
                            print(f"  - dynamic_prompt_prefix: {dp[:50]}...")
                        else:
                            print(f"  - ERROR: dynamic_prompt_prefix is not a string, it's a {type(dp)}")
                    else:
                        print(f"  - ERROR: No dynamic_prompt_prefix found")
                    
            except Exception as e:
                print(f"  - ERROR: Failed to load {yaml_file}: {str(e)}")

if __name__ == "__main__":
    main() 