# LangChain Python 3.13 Compatibility Fix

## Problem

DARIA Interview Tool requires LangChain to function properly. When running Python 3.13, the following error occurs with the LangChain dependencies:

```
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

This is due to changes in how Python 3.13 handles typing.ForwardRef._evaluate() which now requires an additional parameter.

## Solution

We've created a patch script (`fix_pydantic_forward_refs.py`) that:

1. Monkey-patches the pydantic.typing.evaluate_forwardref function
2. Adds the missing 'recursive_guard' parameter when calling ForwardRef._evaluate()
3. Can be used as a wrapper to run any Python script with the patch applied

## Usage

### Option 1: Direct usage with any script

```bash
python fix_pydantic_forward_refs.py run_interview_api.py --use-langchain --port 5025
```

### Option 2: Using the helper script

We've created a shell script that automatically detects your Python version and applies the patch when needed:

```bash
./start_daria_with_patch.sh
```

## Why LangChain is Essential

The DARIA Interview Tool relies heavily on LangChain for:

1. Conversation management and history
2. Interview agent functionality
3. Prompt templating and handling
4. Integration with various LLM providers

Running without LangChain is not a viable option for core functionality.

## Troubleshooting

If you still encounter issues:

1. Verify your Python version with `python --version`
2. Make sure you're using the latest patch script
3. Check that all services are properly stopped before starting
4. Review the logs in daria.log for specific errors

## Testing Your Setup

After starting DARIA with the patch, test the core functionality:

1. Visit http://localhost:5025/static/debug_interview_flow.html?port=5025
2. Verify that session creation is successful
3. Test that interviews can be started and messages loaded 