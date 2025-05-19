# DARIA Interview Tool with Python 3.13 Compatibility Fix

## Problem

DARIA was developed with older versions of Python and LangChain, which are incompatible with Python 3.13 due to changes in the typing module. Specifically, in Python 3.13, the `ForwardRef._evaluate()` method requires a new parameter called `recursive_guard` that older libraries don't provide.

This causes errors like:

```
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

## Solution

We've created a compatibility patch that adapts the `ForwardRef._evaluate()` method to work with both old and new parameter formats. The patch is implemented in `patch_typing.py` and automatically applied when running DARIA through our launcher script.

## How to Run DARIA with Python 3.13

Simply use the provided launcher script:

```bash
./run_fixed_daria.sh
```

This script:

1. Stops any existing DARIA processes
2. Starts the TTS service on port 5015
3. Starts the STT service on port 5016
4. Applies the Python 3.13 compatibility patch
5. Starts the DARIA API server on port 5025

## Services

After starting, you can access the following services:

- TTS Service: http://localhost:5015
- STT Service: http://localhost:5016
- DARIA API: http://localhost:5025
- DARIA Dashboard: http://localhost:5025/dashboard

## Logs

The script generates the following log files:

- `tts.log` - TTS service logs
- `stt.log` - STT service logs
- `daria.log` - Main API server logs

## Technical Details

The compatibility patch works by intercepting calls to `typing.ForwardRef._evaluate()` and handling the parameter differences between Python versions. It:

1. Captures all arguments passed to the method
2. Detects if the call is coming from Python 3.13+ by checking for the `recursive_guard` parameter
3. Calls the original method with the appropriate parameters based on the detected version

This approach allows DARIA to run on Python 3.13 without modifying any of its internal code or dependencies.

## Troubleshooting

If you encounter issues:

1. Check the log files for specific error messages
2. Make sure all required dependencies are installed:
   ```bash
   pip install langchain==0.0.267 pydantic==1.10.8 openai==0.28.1
   ```
3. Try running the patch and API server manually:
   ```bash
   ./patch_typing.py run_interview_api.py --port 5025 --use-langchain
   ``` 