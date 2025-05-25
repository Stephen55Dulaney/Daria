# Remaining Tasks for Daria Interview Tool

## Priority Issues
1. Address LangChain deprecation warnings:
   - Update imports from `langchain.chat_models` to `langchain_community.chat_models`
   - Install langchain-community package if needed

2. Fix monitor interview functionality:
   - Address errors in `get_all_sessions` and `get_guide_sessions` methods
   - Error observed: `'DiscussionService' object has no attribute 'get_all_sessions'`

## Enhancement Opportunities
1. Improve transcript processing:
   - Create more robust speaker detection
   - Add support for additional transcript formats
   - Consider implementing ML-based speaker diarization

2. UI/UX Improvements:
   - Add loading indicators during transcript processing and analysis
   - Improve error messaging for failed transcript uploads
   - Add preview capability for uploaded transcripts

3. Refactoring Opportunities:
   - Move transcript processing into its own module
   - Improve error handling throughout the codebase
   - Add more comprehensive logging

## Testing Needed
1. Verify transcript upload with different formats:
   - Standard Zoom format
   - Teams format
   - Plain text with speaker names
   - Speaker-only format (without timestamps)

2. Test LangChain functionality:
   - Interview generation
   - Analysis capabilities
   - Observer functionality

3. Verify TTS/STT integration:
   - Test with different voices
   - Ensure proper audio playback
   - Test speech recognition accuracy 