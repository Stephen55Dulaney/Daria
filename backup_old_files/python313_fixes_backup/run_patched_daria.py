#!/usr/bin/env python3
"""
DARIA Interview Tool Launcher with Python 3.13 Compatibility Patch

This script imports and applies the ForwardRef._evaluate patch before
running the main DARIA interview tool.
"""

import os
import sys
import importlib.util

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Import our patch module
patch_path = os.path.join(script_dir, 'patch_typing.py')
spec = importlib.util.spec_from_file_location('patch_typing', patch_path)
patch_typing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch_typing)

# Import and run the main script
try:
    main_script_path = os.path.join(script_dir, 'run_interview_api.py')
    spec = importlib.util.spec_from_file_location('run_interview_api', main_script_path)
    run_interview_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_interview_api)
except Exception as e:
    print(f"Error running DARIA: {e}")
    sys.exit(1)
