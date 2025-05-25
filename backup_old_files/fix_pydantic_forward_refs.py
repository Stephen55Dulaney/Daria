#!/usr/bin/env python
"""
Patch script for Python 3.13 compatibility with pydantic and LangChain.
This fixes the 'ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'' error.
"""

import sys
import types
import typing
import importlib
import importlib.util
from typing import Any, Dict, Optional, Set, cast

# Check if we need to apply the patch
if sys.version_info >= (3, 13):
    # Import the problematic module
    import pydantic.typing

    # Original evaluate_forwardref function
    original_evaluate_forwardref = pydantic.typing.evaluate_forwardref

    # Create a patched version of the function
    def patched_evaluate_forwardref(type_, globalns, localns):
        """
        Patched version of evaluate_forwardref that adds the missing recursive_guard parameter
        when calling _evaluate() on ForwardRef objects in Python 3.13.
        """
        if hasattr(type_, '_evaluate') and 'recursive_guard' in type_._evaluate.__code__.co_varnames:
            return cast(Any, type_)._evaluate(globalns, localns, set(), recursive_guard=set())
        else:
            # Fall back to original behavior for other cases
            return original_evaluate_forwardref(type_, globalns, localns)

    # Apply the patch
    pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref
    
    print("Applied pydantic ForwardRef patch for Python 3.13 compatibility")
else:
    print("Python version is < 3.13, no patch needed")

# Allow this script to be used as a wrapper to run another Python script
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Get the script to run
        script_path = sys.argv[1]
        sys.argv = sys.argv[1:]  # Remove this script from sys.argv
        
        # Load the script as a module and run it
        module_name = "__main__"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        else:
            print(f"Error: Could not load {script_path}")
            sys.exit(1)
    else:
        print("Usage: python fix_pydantic_forward_refs.py <script_to_run> [args...]")
        sys.exit(1) 