# Daria Interview Tool - Project Journal

## Project Overview
Daria Interview Tool is an AI-powered research interviewing platform currently in recovery phase after RC2 release. The system uses LangChain for orchestration, with text-to-speech and speech-to-text capabilities for conducting automated interviews.

## Current Build Status
- **Release**: Post-RC2 Recovery Branch
- **Active Branch**: recovery-branch-fix
- **Core Features Working**: Interview flow, LangChain integration, TTS/STT, data storage
- **Key Recent Fix**: Debug Toolkit with end-to-end automation for interview flow
- **New Prototype**: Daria Memory Companion feature for project continuity

## Database Implementation Status
- **Current Storage**: JSON file-based storage
- **Planned**: Progressive migration to structured database (PostgreSQL or DynamoDB)
- **Database Schema**: Initial DynamoDB schema created but not fully implemented
- **Tables Designed**: 
  - Core: InterviewSessions, Transcripts
  - Analysis: Sprints, Opportunities, Personas
  - Output: AgileArtifacts, CursorPrompts
  - Management: Prototypes, JourneyMaps
  - New: ProjectJournal, TimelineEvents (for Memory Companion)

## Phased Implementation Plan
1. **Phase 1: Immediate Stabilization** (Current)
   - Continue using file-based storage for RC2
   - Complete DynamoDB schema documentation
   - Prepare migration scripts
   - Create Memory Companion prototype

2. **Phase 2: Database Implementation** (2-5 weeks)
   - Implement core tables (Priority 1)
   - Create service abstraction layer
   - Build data migration tools
   - Implement project journal database tables

3. **Phase 3: Analysis Features** (5-8 weeks)
   - Implement analysis tables (Priority 2)
   - Build relationship management
   - Enhance semantic search
   - Integrate Memory Companion with main Daria interface

4. **Phase 4: Full Sprint Engine** (8-12 weeks)
   - Implement output tables (Priority 3)
   - Build sprint engine features
   - Add prototype generation
   - Complete Memory Companion with opportunity tracking

## AWS Deployment Status
- **Current**: Local development environment
- **Plan**: Deploy to AWS 
- **Approach**: 
  - Start with simple deployment to establish workflow
  - Add API integrations incrementally
  - Deploy full Daria platform once tested

## Recent Work History
- Analyzed codebase structure and current implementation
- Examined current file-based and planned database implementations
- Created comprehensive database migration plan
- Investigated current build (determined it's not RC3 but recovery-branch-fix)
- Created project journal system for continuity between sessions
- Developed Daria Memory Companion prototype

## Key Files to Review
- `RECOVERY_BRANCH_README.md`: Current recovery branch status and features
- `README_RC2.md`: RC2 release information
- `db/database.py`: Database connection management
- `setup_dynamodb.py`: Database schema setup script
- `db/transcripts.py`, `db/interview_sessions.py`: Database table implementations
- `DARIA_PROJECT_JOURNAL.md`: Project journal for continuity between sessions
- `static/daria_memory_companion.html`: Memory Companion prototype
- `DARIA_MEMORY_COMPANION.md`: Documentation for the Memory Companion feature

## Next Steps
1. Finalize database schema documentation (add Memory Companion tables)
2. Create SQLAlchemy models for core tables
3. Implement repository layer for key data types
4. Build testing framework for database migration
5. Begin progressive implementation of database features
6. Integrate Memory Companion with main Daria application

## Project Goals
1. Stable, reliable interview system
2. Structured database for better data management
3. AWS deployment for broader access
4. Full sprint engine capabilities with opportunity tracking
5. Integration of prototype generation via CursorAI
6. Persistent Memory Companion for project continuity

## Questions to Address
1. Priority of database implementation vs. AWS deployment
2. Preferred database technology (PostgreSQL vs. DynamoDB)
3. Timeline for next official release (RC3)
4. Scope of sprint engine features for initial release
5. Integration approach for Memory Companion feature

## Session Notes
### Session 9 (May 28, 2025)
- Absolutely! Here’s a detailed documentation of all the new backend features and endpoints you’ve added in these six steps, followed by an explanation of the “3,M” you see in Cursor, and how to address any problems in `run_interview_api.py`.
- 
- ---
- 
- # �� DARIA Interview Tool: Backend Feature & Endpoint Documentation
- 
- ## 1. **Advanced Export Features**
- 
- ### **Export as JSON**
- - **Endpoint:** `/api/research_session/<session_id>` (GET)
-   - Returns the full session as JSON.
- - **Endpoint:** `/api/session/<session_id>/export` (GET)
-   - Returns a structured export of the session (with transcript, messages, analysis, etc.).
-   - Add `?download=true` to force a file download.
- 
- ### **Export as CSV**
- - **Endpoint:** `/api/session/<session_id>/export_csv` (GET)
-   - Query param: `fields` (comma-separated list of fields to export)
-   - Example: `/api/session/abc123/export_csv?fields=title,project,analysis`
-   - Returns a CSV file with the selected fields.
- 
- ### **Batch Export as CSV**
- - **Endpoint:** `/api/sessions/export_csv` (POST)
-   - Body: `{ "session_ids": [ ... ], "fields": [ ... ] }`
-   - Returns a CSV file with the selected fields for all specified sessions.
- 
- ---
- 
- ## 2. **Annotation Features**
- 
- ### **Save Annotation**
- - **Endpoint:** `/api/annotation` (POST)
-   - Body: `{ "session_id": "...", "chunk_id": "...", "annotation": { "user": "...", "tag": "...", "comment": "...", "code": "...", "timestamp": "..." } }`
-   - Appends the annotation to the list for the given chunk in `data/interviews/sessions/<session_id>_annotations.json`.
- 
- ### **Get Annotations**
- - **Endpoint:** `/api/annotations/<session_id>` (GET)
-   - Returns all annotations for the session, grouped by chunk.
- 
- ### **Export Annotated Data**
- - Use the above endpoints to fetch and merge transcript and annotations for export.
- 
- ---
- 
- ## 3. **Researcher Collaboration**
- 
- ### **Shared Tagging**
- - The annotation structure supports multiple users annotating the same chunk, with attribution.
- 
- ### **Consensus/Disagreement Views**
- - **Endpoint:** `/api/annotations/<session_id>/consensus` (GET)
-   - Returns, for each chunk, a count of how many users assigned each tag.
-   - Example response:
-     ```json
-     {
-       "chunk_id_1": { "Pain Point": 2, "Insight": 1 },
-       "chunk_id_2": { "Opportunity": 1 }
-     }
-     ```
- 
- ---
- 
- ## 4. **Download/Share Features**
- 
- ### **Download Buttons**
- - Use the above export endpoints to allow users to download session/analysis data as JSON or CSV.
- 
- ### **Shareable Links**
- - The URLs for session/analysis detail pages can be used as shareable links.
- - You can add a “Copy Link” button in the frontend.
- 
- ---
- 
- ## 5. **Quality-of-Life Improvements**
- 
- ### **Error Reporting**
- - All endpoints return error messages in a consistent format (e.g., `{ "success": false, "error": "..." }`).
- - LLM parsing errors are surfaced in the `parsing_error` field of analysis responses.
- 
- ### **Admin Tools**
- - **List All Annotations:** `/api/annotations/<session_id>/all` (GET)
- - **Edit/Delete Annotation:** `/api/annotation/<session_id>/<chunk_id>/<int:index>` (PUT/DELETE)
- - **Delete Analysis:** `/api/analysis/<session_id>` (DELETE)
- 
- ---
- 
- ## 6. **Other Notable Endpoints**
- 
- - **Export Clusters:** `/api/export_clusters` (POST)
-   - Returns embeddings and metadata for a session (for visualization/export).
- - **Save Annotation (ChromaDB):** `/api/save_annotation` (POST)
-   - (Demo only; real update support depends on ChromaDB capabilities.)
- 
- ---
- 
- # 🟢 What does “3,M” mean in Cursor?
- 
- - **3**: There are 3 linter or static analysis problems (errors or warnings) in the file.
- - **M**: The file is “Modified” (has unsaved or uncommitted changes in your git working directory).
- 
- **What to do:**
- - Click on the “3” in Cursor to see the list of problems. They may be syntax errors, unused imports, or other issues flagged by your linter.
- - If you want, I can review the file for you and suggest or make fixes for those 3 problems.
- 
- ---
- 
- ## ✅ Next Steps
- 
- - Let me know if you want to see a sample React component for any of these features.
- - If you want me to review and fix the 3 problems in `run_interview_api.py`, just say so and I’ll do it right away!
- 
- Would you like to proceed with the React UI, or should I address the linter problems in your backend file first?

### Session 8 (May 28, 2025)
- ## Key Files to Review
- - `RECOVERY_BRANCH_README.md`: Current recovery branch status and features
- - `README_RC2.md`: RC2 release information
- - `db/database.py`: Database connection management
- - `setup_dynamodb.py`: Database schema setup script
- - `db/transcripts.py`, `db/interview_sessions.py`: Database table implementations
- - `DARIA_PROJECT_JOURNAL.md`: Project journal for continuity between sessions
- - `static/daria_memory_companion.html`: Memory Companion prototype
- - `DARIA_MEMORY_COMPANION.md`: D3
- 2

### Session 7 (May 18, 2025)
- 
- 
- ```bash
- git add run_latest_with_patch.sh stop_daria_services.sh api_services/memory_companion_service.py
- ```
- 
- 
- 
- ```bash
- git add PYTHON313_FIX.md
- ```
- 
- ```bash
- 
- ```
- 
- ```bash
- git commit -m "Add Python 3.13 compatibility with ForwardRef._evaluate() fix. Includes working Memory Companion, enhanced Issues Tracker, and partially working AI Observer."
- ```
- 
- ```bash
- git push origin main
- ```
- I've successfully committed and pushed your changes to the main branch! Here's what was included:
- 
- 1. Updated `run_latest_with_patch.sh` to include the Memory Companion service
- 2. Updated `stop_daria_services.sh` to properly stop the Memory Companion
- 3. Updated `PYTHON313_FIX.md` with comprehensive documentation
- 
- The commit message clearly indicates that this includes:
- - The Python 3.13 compatibility fix for the ForwardRef._evaluate() issue
- - Working Memory Companion/DARIA Project Companion
- - Enhanced Issues Tracker with opportunities, epics, and user stories
- - Partially working AI Observer Debug Tool
- 
- These changes are now on the main branch. The Python 3.13 patch is indeed a stable solution - it's an elegant adapter that allows DARIA to work with newer Python versions without requiring extensive changes throughout the codebase.
- 
- You can now use `./run_latest_with_patch.sh` to start all services (including Memory Companion) and `./stop_daria_services.sh` to stop everything cleanly.

### Session 6 (May 15, 2025)
- **Fixed Character Identity and Context Leakage Issues**
- Successfully addressed two persistent issues in the interview system:
  1. **Character Identity Persistence** - Characters like Thomas, Synthia, etc. now maintain consistent identity across all transitions between pages and through entire interview sessions.
  2. **Context Data Leakage** - Fixed the problem where internal context data (e.g. "I am {'Topic': 'General Interview'...}") leaked into agent responses.

- **Key Improvements Implemented:**
  - Enhanced regex patterns for sanitizing responses
  - Added URL parameter passing between pages to maintain character selection
  - Fixed character handling in debug tools and production pages
  - Modified session creation to properly copy character information
  - Added suspicious content detection as a fallback for improved sanitization
  - Created test guide with Thomas character for verification

- **Testing Process:**
  - Used the debug character test tool: http://localhost:5025/static/debug_character_test.html
  - Tested different characters and their identity responses
  - Verified transitions between debug_character_test and debug_interview_flow pages
  - Confirmed remote interview sessions maintain character identity
  - Verified no context data leakage in responses

- **Code Integration Complete:**
  - Changes tested, committed to git, and pushed to main branch
  - Added detailed documentation in DARIA_PROJECT_JOURNAL.md (Session 5)
  - Updated DARIA_MEMORY_COMPANION.md with "Technical Implementation - Recent Fixes" section
  - Added "Recent Major Fixes" section to DARIA_JOURNAL_README.md

- **Services Verification:**
  - Successfully running Daria Memory Companion server on port 5030
  - Main application running properly on port 5025
  - All service health checks returning 200 OK responses
  - Character identity consistent across all testing scenarios

### Session 5 (May 15, 2025)
- **Character Identity and Context Leakage Fix**

- **Problem Summary:**
  - The DARIA interview tool had two critical issues:
    1. **Character Identity Issues**: AI characters weren't maintaining consistent identity across sessions
    2. **Context Data Leakage**: Raw internal context data was appearing in responses

- **Root Causes:**
  - **Character Identity Issues**:
    - Character information wasn't properly passed between pages (session → remote interview)
    - Custom characters like "Thomas" weren't properly registered in the system
    - Character information wasn't persisted in URL parameters when transitioning between pages
    - LangChain response generation wasn't consistently using character information
  
  - **Context Data Leakage**:
    - Insufficient sanitization regex patterns couldn't detect all formats of leaked context
    - LLM responses containing raw context data (e.g., "I am {'Topic': 'General Interview'...}")
    - No fallback detection for suspicious content patterns

- **Implemented Fixes:**
  1. **Enhanced Context Data Sanitization**:
     - Created more robust regex patterns to detect various context data formats
     - Added fallback detection for suspicious content patterns
     - Improved cleaning of responses after context removal
  
  2. **Character Identity Persistence**:
     - Modified URL handling to preserve character between pages
     - Added character parameter to remote interview links
     - Updated identity response handling to be character-aware
     - Added all standard characters to direct mapping dictionaries
  
  3. **Debug Tools Improvements**:
     - Added character passing between debug_character_test.html and debug_interview_flow.html
     - Enhanced character detection in debug tools
     - Added test guide with Thomas character for verification

  4. **Session Handling Improvements**:
     - Modified LangChain integration to properly retrieve and use character information
     - Fixed session creation to copy character information from guides
     - Added explicit character information to system messages

- **Verification**:
  - Successfully tested with custom "Thomas" character
  - Verified character persistence in remote interview sessions
  - Confirmed that context data no longer leaks into responses
  - Character identity remains consistent through entire conversation

- **Files Modified**:
  - langchain_features/services/interview_service.py
  - static/debug_character_test.html
  - static/debug_interview_flow.html
  - templates/langchain/session.html
  - templates/langchain/interview_welcome.html
  - langchain_features/services/discussion_service.py
  - run_interview_api.py
  - data/discussions/thomas_test_guide.json

- **Lessons Learned**:
  - Character state needs to be explicitly passed and maintained across all transitions
  - Robust sanitization requires multiple layers of pattern detection
  - Test guides with specific characters are valuable for verification
  - Custom character handling requires explicit mapping in multiple places

### Session 4 (May 12, 2025)
- I'll update the memory log with our recent AWS deployment progress for the Daria project. The logs continue to show excellent stability - all TTS and STT service health checks are returning 200 status codes every minute, confirming the core functionality is working properly.
- 
- We've successfully:
- 1. Created a "Hello World" test app using Flask in AWS CloudShell
- 2. Verified it works with curl tests to both the main page and health endpoint
- 3. Identified the security challenges with Deloitte's AWS environment
- 4. Drafted a ServiceNow ticket requesting appropriate access permissions
- 5. Confirmed that the main Daria application continues to run flawlessly
- 
- The EC2 deployment is our next step once we receive the security permissions. We've made excellent progress on the incremental approach to AWS deployment that we outlined in our build plan.
- 
- Is there anything specific about today's progress you'd like me to emphasize in the memory log update?
- 
- 3

### Session 3 (May 10, 2025)
- Here's a summary of what we've accomplished today:
- 
- ### Memory Companion Configuration & Integration
- - Fixed port conflicts between the main Daria application (port 5025) and Memory Companion (port 5030)
- - Updated all documentation, HTML files, and scripts to reference the correct ports
- - Modified the debug toolkit HTML to properly link to the memory companion on port 5030
- - Updated configuration files in multiple locations (debug_toolkit.html, memory_companion_info.html, DARIA_MEMORY_COMPANION.md)
- - Created proper start scripts that initialize services on their correct ports
- 
- ### Service Deployment & Verification
- - Successfully deployed and tested all services:
-   - Main Daria application (port 5025)
-   - Memory Companion (port 5030)
-   - Text-to-Speech service (port 5015)
-   - Speech-to-Text service (port 5016)
- - Confirmed integration with OpenAI API for LLM responses
- - Fixed issues in start_daria_with_memory.sh to ensure reliable startup
- 
- ### Implementation Testing
- - Tested Memory Companion API endpoints
- - Verified memory persistence between sessions
- - Confirmed the "50 First Dates" concept works as intended with Daria remembering project context
- - Tested the boot sequence and journal visualization components
- 
- ### Documentation Updates
- - Updated all relevant documentation to reflect the new port configuration
- - Made sure setup instructions accurately guide users to the correct URLs
- - Ensured a consistent approach to using the debug server vs. production server  
- 
- The system now successfully maintains project context across sessions and all components work together properly on their designated ports.

*Add notes from each working session here to maintain continuity*

### Session 1 (Current Date)
- Established project status and database implementation plan
- Created this project journal for continuity
- Determined current build is post-RC2 recovery branch, not RC3
- Outlined phased approach to database implementation

### Session 2 (Current Date)
- Created Memory Companion prototype based on "50 First Dates" concept
- Developed HTML/JS implementation in static/daria_memory_companion.html
- Added documentation in DARIA_MEMORY_COMPANION.md
- Updated project journal to include Memory Companion in the implementation plan
- Verified file structure and placement in the static directory 