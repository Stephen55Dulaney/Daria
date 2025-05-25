#!/usr/bin/env python3
"""
App Launcher for Daria Interview Tool

This script attempts to run the app.py Flask application.
It verifies the existence of app.py before attempting to run it,
and provides error information if the file is not found.
"""

import os
import subprocess
import sys

def main():
    """Check if app.py exists and run it."""
    print("Launching Daria Interview Tool application...")
    
    # Check if app.py exists
    if os.path.isfile("app.py"):
        try:
            # Run the Flask application
            print("Running app.py...")
            result = subprocess.run(
                ["python", "app.py"],
                check=True,
                text=True
            )
            return result.returncode
        except subprocess.CalledProcessError as e:
            print(f"Error running app.py: {e}")
            return e.returncode
        except KeyboardInterrupt:
            print("\nApplication terminated by user.")
            return 1
    else:
        # If app.py is not found, print error and current directory contents
        current_dir = os.getcwd()
        print(f"Error: app.py not found in {current_dir}")
        print("Current directory contains:")
        for item in os.listdir(current_dir):
            print(f"  - {item}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 