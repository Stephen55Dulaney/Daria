# Interview Analysis Feature

## Overview

The Interview Analysis feature automatically processes completed interview transcripts to identify user needs, goals, pain points, and opportunities. This enables researchers to extract valuable insights without manual coding of transcripts.

## Features

1. **Automated Analysis**: Generate structured analysis from interview transcripts using AI
2. **Character-Specific Analysis**: Each character persona uses tailored analysis prompts
3. **Structured Results**: Analysis is organized into key sections (Needs, Goals, Pain Points, etc.)
4. **Visual Presentation**: Analysis results are presented in an easy-to-read tabbed interface

## Requirements

- Python 3.8+
- OpenAI API key (environment variable: `OPENAI_API_KEY`)
- Completed interviews in the system

## Implementation Details

### Data Structure

The analysis results are stored in a structured JSON format within each interview:

```json
{
  "analysis": {
    "performed_at": "2025-05-05T22:45:12.123456",
    "analysis_prompt_used": "Analyze this interview...",
    "summary": "Brief summary of the interview",
    "user_needs": ["Need 1", "Need 2", ...],
    "goals": ["Goal 1", "Goal 2", ...],
    "pain_points": ["Pain point 1", "Pain point 2", ...],
    "opportunities": ["Opportunity 1", "Opportunity 2", ...],
    "recommendations": ["Recommendation 1", "Recommendation 2", ...],
    "key_quotes": ["Quote 1", "Quote 2", ...]
  }
}
```

### API Endpoints

- `POST /api/interview/analyze/<interview_id>`: Analyze a specific interview
  - Parameters:
    - `force` (optional): Boolean to regenerate analysis if it already exists

### User Interface

- View analysis in the "Analysis" tab on the interview details page
- Generate analysis with a single button click for completed interviews
- Status indicators show which interviews have been analyzed

## Getting Started

1. **Run the Migration Script**:
   ```bash
   python migration_scripts/migrate_interviews_for_analysis.py
   ```

2. **Configure Your OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Restart the Daria Interview Tool**:
   ```bash
   ./cleanup_services.sh
   ./start_services.sh
   ```

4. **Using the Feature**:
   - Navigate to any completed interview
   - Click on the "Analysis" tab
   - Click the "Generate Analysis" button
   - View the structured analysis results

## Customizing Analysis Prompts

Each character can have a custom analysis prompt. To set a character-specific analysis prompt:

1. Edit the character's YAML file in `tools/prompt_manager/prompts/`
2. Add or update the `analysis_prompt` field with your custom prompt
3. Restart the application

## Troubleshooting

- **"Analysis generation failed"**: Check that your OpenAI API key is valid and has enough credits
- **Empty analysis sections**: Try regenerating the analysis or check that your interview has sufficient content
- **Missing transcripts**: Ensure the interview was completed and has conversation history

## Future Enhancements

- Add ability to export analysis as PDF or CSV
- Implement batch analysis of multiple interviews
- Add support for creating personas directly from analysis
- Provide visualization of patterns across multiple interview analyses 