#!/usr/bin/env python3
"""
Python 3.13 Compatibility Patch for ForwardRef._evaluate

This script directly monkey-patches the ForwardRef._evaluate method to be compatible with both
Python <3.13 and >=3.13 calling conventions.
"""

import sys
import types
import typing
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("py313_patcher")

def apply_patch():
    """Apply the monkey patch to typing.ForwardRef._evaluate."""
    # Only apply the patch for Python 3.13+
    if sys.version_info < (3, 13):
        logger.info(f"No patch needed for Python {sys.version_info}")
        return
    
    logger.info(f"Applying ForwardRef._evaluate patch for Python {sys.version_info}")
    
    # Get original method
    original_method = typing.ForwardRef._evaluate
    
    # Define our monkey patch that will handle different calling conventions
    def patched_evaluate(self, globalns, localns, *args, **kwargs):
        """
        Patched version of _evaluate that handles both old and new calling conventions.
        
        In Python <3.13, ForwardRef._evaluate expects (self, globalns, localns)
        In Python >=3.13, it expects (self, globalns, localns, recursive_guard=None)
        
        This patch handles both cases by ensuring recursive_guard is always provided
        when running on Python 3.13+.
        """
        # Add the recursive_guard parameter if not already present
        if 'recursive_guard' not in kwargs and not args:
            return original_method(self, globalns, localns, recursive_guard=set())
        
        # If args has recursive_guard as positional arg (common in pydantic)
        elif args and len(args) == 1 and 'recursive_guard' not in kwargs:
            return original_method(self, globalns, localns, recursive_guard=args[0])
            
        # Let other cases pass through as-is
        else:
            return original_method(self, globalns, localns, *args, **kwargs)
    
    # Apply our monkey patch
    typing.ForwardRef._evaluate = patched_evaluate
    logger.info("Successfully applied ForwardRef._evaluate patch")

# Apply the patch when imported
apply_patch()

if __name__ == "__main__":
    logger.info(f"Starting Python {sys.version} compatibility patch")
    
    # If command line arguments are provided, run the specified script
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
        script_args = sys.argv[2:]
        
        logger.info(f"Running: {script_path} {' '.join(script_args)}")
        
        # Save original argv
        original_argv = sys.argv
        sys.argv = [script_path] + script_args
        
        try:
            # Execute the script
            with open(script_path) as f:
                script_code = f.read()
            
            # Execute in a new namespace
            script_globals = {
                '__file__': script_path,
                '__name__': '__main__',
                '__builtins__': __builtins__,
            }
            
            exec(script_code, script_globals)
            logger.info(f"Successfully executed {script_path}")
        except Exception as e:
            logger.error(f"Error executing {script_path}: {e}")
            sys.exit(1)
        finally:
            # Restore original argv
            sys.argv = original_argv
    else:
        logger.info("No script specified to run. Patch has been applied.")
        logger.info("You can now import this module to apply the patch in other scripts.") 