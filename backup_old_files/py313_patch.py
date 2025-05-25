#!/usr/bin/env python3
"""
Python 3.13 Compatibility Patch for ForwardRef._evaluate

This is a simple script that patches typing.ForwardRef._evaluate to be 
compatible with Python 3.13's new requirements.
"""

import sys
import typing
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("py313_patcher")

# Store original method
original_evaluate = typing.ForwardRef._evaluate

def patched_evaluate(self, globalns, localns, *args, **kwargs):
    """Patched version of _evaluate to handle different Python versions."""
    if sys.version_info < (3, 13):
        # Python < 3.13 doesn't expect additional arguments
        return original_evaluate(self, globalns, localns)
    else:
        # Python 3.13+ requires recursive_guard
        if 'recursive_guard' not in kwargs and not args:
            return original_evaluate(self, globalns, localns, recursive_guard=set())
        elif args and len(args) == 1 and 'recursive_guard' not in kwargs:
            return original_evaluate(self, globalns, localns, recursive_guard=args[0])
        else:
            return original_evaluate(self, globalns, localns, *args, **kwargs)

# Apply the patch
typing.ForwardRef._evaluate = patched_evaluate
logger.info(f"Applied ForwardRef._evaluate patch for Python {sys.version}")

if __name__ == "__main__":
    # If this script is run directly, import and run whatever module was specified
    if len(sys.argv) > 1:
        import importlib.util
        import os
        
        script_name = sys.argv[1]
        script_path = os.path.abspath(script_name)
        sys.argv = sys.argv[1:]  # Remove this script's name from argv
        
        if os.path.exists(script_path):
            # Import and run the script
            spec = importlib.util.spec_from_file_location("__main__", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            logger.error(f"Script not found: {script_path}")
            sys.exit(1)
    else:
        logger.info("No script to run. Patch has been applied.") 