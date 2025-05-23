# DARIA Interview Tool Python 3.13 Compatibility Fix

This README provides instructions for running the DARIA Interview Tool with Python 3.13, which requires some compatibility fixes for ForwardRef handling in pydantic/LangChain.

## Issue Description

When running DARIA with Python 3.13, you may encounter the following error:

```
ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

This is due to changes in how the `typing.ForwardRef` class works in Python 3.13, which breaks compatibility with certain versions of pydantic and LangChain.

## Solutions

We've created several scripts to fix the issue:

1. `fix_pydantic_forward_refs.py` - A patch script that monkey-patches pydantic's ForwardRef evaluation
2. `test_langchain_patch.py` - A test script to verify that the patch is working correctly
3. `start_daria_fixed.sh` - A comprehensive startup script that applies the patch and starts all DARIA services

## Running DARIA with Python 3.13

### Method 1: All-In-One Script (Recommended)

The simplest way to run DARIA with Python 3.13 is to use the all-in-one script:

```bash
chmod +x start_daria_fixed.sh
./start_daria_fixed.sh
```

This script will:
1. Stop any existing DARIA processes
2. Set up required directories
3. Apply the pydantic patch for Python 3.13
4. Start all available DARIA services (main server, TTS, STT, memory companion)
5. Create test files for debugging
6. Verify that all services are working

### Method 2: Manual Patch Application

If you want to manually apply the patch to your own scripts, you can use:

```bash
python fix_pydantic_forward_refs.py your_script.py [arguments]
```

This will apply the patch and then run your script with the provided arguments.

## Testing Your Installation

After starting DARIA, you can access the following URLs:

- Main application: http://localhost:5025/
- Debug interview tool: http://localhost:5025/static/debug_interview_flow.html?port=5025
- Character test tool: http://localhost:5025/static/debug_character_test.html

You can also run the included health check script:

```bash
python check_daria_server.py
```

## File Structure

The following files are part of the Python 3.13 compatibility fix:

- `fix_pydantic_forward_refs.py` - The main patch script
- `test_langchain_patch.py` - Test script for the patch
- `start_daria_fixed.sh` - All-in-one startup script
- `check_daria_server.py` - Health check script
- `data/interviews/sessions/test_session_123456.json` - Test session
- `data/interviews/test_guide_123456.json` - Test discussion guide

## Troubleshooting

If you encounter issues:

1. Check the logs in the `logs/` directory:
   ```bash
   tail -f logs/daria.log
   ```

2. Make sure all required ports are free:
   ```bash
   lsof -i :5025  # Main API
   lsof -i :5015  # TTS service
   lsof -i :5016  # STT service
   lsof -i :5030  # Memory companion
   ```

3. If services are running but endpoints are failing, try restarting with:
   ```bash
   ./start_daria_fixed.sh
   ```

## Notes

- This patch is specifically designed for Python 3.13 compatibility
- It will not affect operation on Python 3.12 or earlier
- The patch is applied at runtime and doesn't modify any library files 