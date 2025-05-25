# Build and Development Notes

## Data Export Features

### FigJam Export
The project includes a script to export interview insights to FigJam-compatible CSV files:

```bash
# Basic usage
python scripts/create_figjam_notes.py --interview interviews/processed/[interview_id].json

# Options
--max-chunks N     # Number of chunks to process (default: 5)
--start-chunk N    # Starting chunk index (default: 0)
```

The script creates a CSV file that can be imported into FigJam as sticky notes with:
- Interview quotes (with attribution)
- Insight tags
- Themes

To use in FigJam:
1. Click the "+" button
2. Select "Import"
3. Choose the generated CSV file
4. Each cell becomes a sticky note automatically 