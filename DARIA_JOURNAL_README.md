# Daria Project Journal Utility

This utility helps maintain project continuity by tracking important updates and making them available to the Memory Companion feature.

## Quick Start

Display the journal summary:
```bash
./journal.sh
```

Add new session notes:
```bash
./journal.sh update
```

## How to Use

### 1. Viewing Project Status

To see a quick summary of the current project status, run:
```bash
./journal.sh
```

This displays:
- Current build status
- Active branch
- Core features
- Recent fixes/additions
- Next steps
- Last session notes

For more detailed information, refer to `DARIA_PROJECT_JOURNAL.md`.

### 2. Adding New Session Notes

After completing work, add notes about what you accomplished:

1. Run the update command:
   ```bash
   ./journal.sh update
   ```

2. When prompted, select option `2` for "Add new session notes"

3. Enter a title for your session (e.g., "Memory Companion Configuration")

4. Enter detailed notes about what was accomplished

5. Confirm the update when prompted

### 3. Integration with Memory Companion

The Project Journal Utility works together with the Memory Companion feature:

1. When you add notes via `./journal.sh update`, these are saved to the project journal
2. The Memory Companion reads this journal when started to maintain context
3. This creates the "50 First Dates" experience where Daria remembers past work

## Recent Major Fixes

### Character Identity and Context Leakage Fix (May 15, 2025)

A critical update was made to address two persistent issues in the interview system:

#### Issues Fixed:
1. **Character Identity Persistence** - Characters like Thomas, Synthia, etc. now maintain consistent identity across all transitions between pages and through entire interview sessions.
2. **Context Data Leakage** - Fixed the problem where internal context data (e.g. "I am {'Topic': 'General Interview'...}") leaked into agent responses.

#### Key Improvements:
- Enhanced regex patterns for sanitizing responses
- Added URL parameter passing between pages to maintain character selection
- Fixed character handling in debug tools and production pages
- Modified session creation to properly copy character information
- Added suspicious content detection as a fallback for improved sanitization
- Created test guide with Thomas character for verification

To verify the fix:
1. Use the debug character test tool: http://localhost:5025/static/debug_character_test.html
2. Select different characters and test their identity responses
3. Try moving between debug_character_test and debug_interview_flow pages
4. Verify remote interview sessions maintain character identity

Full technical details are available in `DARIA_PROJECT_JOURNAL.md` under Session 5.

## Memory Companion Setup

The Memory Companion can be accessed in two ways:

1. **Main Application Integration**:
   - Start the main Daria app with `./start_server.sh`
   - Access the Memory Companion at http://localhost:5025/static/daria_memory_companion.html

2. **Debug Mode**:
   - Run `./debug_memory.sh` for a standalone server
   - Access at http://localhost:5030/static/daria_memory_companion.html
   - Use the "Test API" button to verify connectivity

## Technical Details

- Project journal data is stored in `data/daria_memory.json`
- Backups are created in the `.journal_backups` directory
- The `update_journal.py` script handles data persistence
- The memory journal is read by the Memory Companion service when initialized

## Commands Summary

| Command | Description |
|---------|-------------|
| `./journal.sh` | View project summary |
| `./journal.sh update` | Add new session notes |
| `./start_daria_with_memory.sh` | Start the Memory Companion server |
| `./debug_memory.sh` | Start Memory Companion in debug mode |

## Tips for Effective Use

1. Update the journal at the end of each work session
2. Be specific about what was accomplished
3. Include details about any configuration changes
4. Mention any issues or workarounds discovered
5. Note any important decisions made 