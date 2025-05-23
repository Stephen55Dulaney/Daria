#!/usr/bin/env python
"""
Test script to verify that the pydantic patch for Python 3.13 is functioning correctly.
"""

import sys
import typing
from typing import Dict, List, Optional, Any, ForwardRef

try:
    import importlib
except ImportError:
    print("ERROR: importlib module is missing. This is required for the patch.")
    sys.exit(1)

def test_forward_ref_patch():
    """Test that ForwardRef evaluation works in Python 3.13+"""
    print(f"Testing ForwardRef patch for Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Only run the test if we're on Python 3.13+
    if sys.version_info >= (3, 13):
        try:
            # Import pydantic
            import pydantic
            from pydantic import BaseModel
            
            # Create a model with a ForwardRef
            NodeRef = ForwardRef("Node")
            
            class Node(BaseModel):
                name: str
                children: List[NodeRef] = []
            
            # Try to create an instance
            root = Node(name="root", children=[
                Node(name="child1"),
                Node(name="child2")
            ])
            
            print("✅ ForwardRef test passed! The patch is working correctly.")
            return True
            
        except Exception as e:
            print(f"❌ ForwardRef test failed: {str(e)}")
            return False
    else:
        print("ℹ️ Not running test on Python < 3.13")
        return True

if __name__ == "__main__":
    success = test_forward_ref_patch()
    sys.exit(0 if success else 1) 