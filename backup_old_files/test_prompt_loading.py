#!/usr/bin/env python3
"""
Test script to verify proper loading of all character prompts, with specific
attention to evaluation_metrics field formats.
"""

import sys
import os
import yaml
from pathlib import Path

def check_prompt_format(prompt_path):
    """Check if a prompt file has correct format for all fields."""
    try:
        with open(prompt_path, 'r') as file:
            config = yaml.safe_load(file)
        
        prompt_name = os.path.basename(prompt_path).replace('.yml', '')
        print(f"Checking prompt: {prompt_name}")
        
        # Required fields
        required_fields = [
            'agent_name', 
            'description', 
            'role', 
            'dynamic_prompt_prefix'
        ]
        
        for field in required_fields:
            if field not in config:
                print(f"  ❌ Missing required field: {field}")
            else:
                print(f"  ✅ Found required field: {field}")
        
        # Check evaluation_metrics format
        if 'evaluation_metrics' in config:
            metrics = config['evaluation_metrics']
            if isinstance(metrics, dict):
                print(f"  ✅ evaluation_metrics is a dictionary with {len(metrics)} items")
                for key, value in metrics.items():
                    print(f"    - {key}: {value[:30]}...")
            elif isinstance(metrics, list):
                print(f"  ❌ evaluation_metrics is a list with {len(metrics)} items")
                print("    This format may cause issues with the Prompt Manager view function")
                # Show the format
                for item in metrics:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            print(f"    - {k}: {v[:30]}...")
            else:
                print(f"  ❓ evaluation_metrics has unexpected type: {type(metrics)}")
        else:
            print("  ⚠️ No evaluation_metrics found")
        
        print("")
        return True
    except Exception as e:
        print(f"Error loading prompt {prompt_path}: {str(e)}")
        return False

def main():
    # Find the prompts directory
    script_dir = Path(__file__).parent.absolute()
    base_dir = script_dir
    prompt_dir = base_dir / "tools" / "prompt_manager" / "prompts"
    
    if not prompt_dir.exists():
        # Try one level up
        base_dir = script_dir.parent
        prompt_dir = base_dir / "tools" / "prompt_manager" / "prompts"
    
    if not prompt_dir.exists():
        print(f"Error: Could not find prompts directory at {prompt_dir}")
        sys.exit(1)
    
    print(f"Found prompts directory: {prompt_dir}")
    
    # Check all prompt files
    all_prompts = list(prompt_dir.glob("*.yml"))
    if not all_prompts:
        print("No prompt files found!")
        sys.exit(1)
    
    print(f"Found {len(all_prompts)} prompt files")
    print("-" * 50)
    
    success_count = 0
    for prompt_path in all_prompts:
        if check_prompt_format(prompt_path):
            success_count += 1
    
    if success_count == len(all_prompts):
        print(f"✅ All {success_count} prompts loaded successfully!")
    else:
        print(f"⚠️ {success_count} of {len(all_prompts)} prompts loaded successfully.")
        print(f"❌ {len(all_prompts) - success_count} prompts had issues.")

if __name__ == "__main__":
    main() 