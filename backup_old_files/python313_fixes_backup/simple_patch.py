#!/usr/bin/env python3
"""
Simple Python 3.13 Compatibility Patch

This script adds a simple monkey patch for ForwardRef._evaluate
to make it work with Python 3.13.
"""

import inspect
from typing import ForwardRef

# Store the original method
original_evaluate = ForwardRef._evaluate

# Create a patched version that handles both calling conventions
def patched_evaluate(*args, **kwargs):
    """
    Patched version of ForwardRef._evaluate that works with all Python versions.
    
    This handles both:
    - Old style: _evaluate(self, globalns, localns)
    - New style: _evaluate(self, globalns, localns, recursive_guard)
    """
    self = args[0]
    globalns = args[1]
    localns = args[2] if len(args) > 2 else None
    
    # If recursive_guard came in as a positional arg
    if len(args) > 3:
        # Original method doesn't expect recursive_guard, so call with just the args it wants
        return original_evaluate(self, globalns, localns)
    
    # If recursive_guard came in as a keyword arg
    if 'recursive_guard' in kwargs:
        # Original method doesn't want recursive_guard, so call without it
        return original_evaluate(self, globalns, localns)
        
    # Regular call from older Python versions
    return original_evaluate(self, globalns, localns)

# Apply the patch
ForwardRef._evaluate = patched_evaluate

print("ForwardRef._evaluate has been patched for Python 3.13 compatibility.") 