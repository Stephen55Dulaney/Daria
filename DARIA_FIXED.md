# DARIA LangChain Fix for Python 3.13

## Summary of Changes

We've addressed the critical issue with running DARIA Interview Tool on Python 3.13 by creating a patch for the pydantic ForwardRef evaluation error.

### Key Files Created

1. **fix_pydantic_forward_refs.py**
   - Monkey-patches the pydantic typing module
   - Fixes the 'recursive_guard' parameter issue
   - Can be used as a wrapper for any Python script

2. **start_daria_with_patch.sh**
   - Starts DARIA with LangChain enabled
   - Auto-detects Python version and applies the patch when needed
   - Handles proper shutdown of existing processes

3. **test_langchain_patch.py**
   - Validates that our patch resolves the LangChain issue
   - Tests import and functionality of key LangChain components

4. **start_all_daria_services.sh**
   - Comprehensive script to start all DARIA services
   - Applies the patch to each service when running Python 3.13
   - Reports on service status

### Why This Approach

1. **Maintains Core Functionality**: DARIA requires LangChain for interview functionality
2. **Minimal Code Changes**: No need to modify the original codebase
3. **Python Version Compatibility**: Works with both Python 3.13 and earlier versions
4. **Preserves All Features**: Handles transcripts, session management, and interviews

### How to Use

To start DARIA with all services and LangChain enabled:

```bash
./start_all_daria_services.sh
```

To test just the interview API with LangChain:

```bash
./start_daria_with_patch.sh
```

To verify the patch is working:

```bash
python test_langchain_patch.py
```

### Next Steps

1. Test the full interview flow with the patched version
2. Verify transcript upload and session management
3. Ensure health check returns the correct LangChain status
4. Update the main documentation to reflect these changes 