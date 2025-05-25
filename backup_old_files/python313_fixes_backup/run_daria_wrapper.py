#!/usr/bin/env python3
# Import and apply the patch
import patch_typing
patch_typing.apply_patch()

# Now run the main script
import sys
import os
import argparse

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run DARIA with Python 3.13 compatibility patch')
    parser.add_argument('--port', type=int, default=5025, help='Port to run the API server on')
    parser.add_argument('--use-langchain', action='store_true', help='Use LangChain features')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Parse the command line arguments
    args = parser.parse_args()
    
    # Modify sys.argv to match what run_interview_api.py expects
    sys.argv = ['run_interview_api.py']
    if args.port:
        sys.argv.extend(['--port', str(args.port)])
    if args.use_langchain:
        sys.argv.append('--use-langchain')
    if args.debug:
        sys.argv.append('--debug')
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the interview API script
    main_script = os.path.join(current_dir, 'run_interview_api.py')
    with open(main_script) as f:
        code = compile(f.read(), main_script, 'exec')
        exec(code, {'__name__': '__main__', '__file__': main_script})

if __name__ == '__main__':
    main()
