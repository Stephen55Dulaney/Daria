import os
import json
import csv
from pathlib import Path
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_insights_and_quotes(file_path: str, max_chunks: int = 5, start_chunk: int = 0):
    """Extract insights and their associated quotes from a single interview file."""
    quotes = []
    insights = []
    themes = []
    
    try:
        with open(file_path, 'r') as f:
            interview = json.load(f)
            
        # Extract interviewee name for reference
        interviewee_name = interview.get('metadata', {}).get('interviewee', {}).get('name', 'Unknown')
        
        # Get total chunks for logging
        total_chunks = len(interview.get('chunks', []))
        logger.info(f"Interview has {total_chunks} total chunks")
        
        # Process chunks from start_chunk up to start_chunk + max_chunks
        chunks = interview.get('chunks', [])[start_chunk:start_chunk + max_chunks]
        logger.info(f"Processing chunks {start_chunk} to {start_chunk + len(chunks)}")
        
        for chunk in chunks:
            quote = chunk.get('combined_text', '').strip()
            insight_tags = chunk.get('analysis', {}).get('insight_tags', [])
            theme_tags = chunk.get('analysis', {}).get('themes', [])
            
            # Add quote with attribution
            quotes.append(f'"{quote}"\n- {interviewee_name}')
            
            # Add insights and themes
            insights.extend(insight_tags)
            themes.extend(theme_tags)
            
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
    
    return quotes, insights, themes

def create_figjam_csv(quotes, insights, themes, output_file: str = "figjam_notes.csv"):
    """Create a simple three-column CSV file for FigJam import."""
    # Make lists equal length by padding with empty strings
    max_length = max(len(quotes), len(insights), len(themes))
    quotes.extend([''] * (max_length - len(quotes)))
    insights.extend([''] * (max_length - len(insights)))
    themes.extend([''] * (max_length - len(themes)))
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['Quotes', 'Insights', 'Themes'])
        
        # Write data rows
        for quote, insight, theme in zip(quotes, insights, themes):
            writer.writerow([quote, insight, theme])
    
    logger.info(f"Created FigJam CSV file: {output_file}")
    return output_file

def main():
    """Main function to generate FigJam notes from a single interview."""
    parser = argparse.ArgumentParser(description='Generate FigJam sticky notes from interview insights')
    parser.add_argument('--interview', type=str, help='Interview file to process (e.g., interviews/processed/filename.json)')
    parser.add_argument('--max-chunks', type=int, default=5, help='Maximum number of chunks to process (default: 5)')
    parser.add_argument('--start-chunk', type=int, default=0, help='Starting chunk index (default: 0)')
    args = parser.parse_args()
    
    try:
        # Use specified file or find first available interview
        if args.interview:
            interview_file = args.interview
        else:
            # Find first interview in processed directory
            processed_dir = "interviews/processed"
            for filename in os.listdir(processed_dir):
                if filename.endswith('.json'):
                    interview_file = os.path.join(processed_dir, filename)
                    break
            else:
                logger.error("No interview files found")
                return
        
        logger.info(f"Processing interview file: {interview_file}")
        
        # Extract data from interview
        quotes, insights, themes = extract_insights_and_quotes(
            interview_file, 
            args.max_chunks,
            args.start_chunk
        )
        
        if not quotes and not insights and not themes:
            logger.warning("No data found in interview")
            return
        
        # Create CSV file
        output_file = create_figjam_csv(quotes, insights, themes)
        
        print(f"\nCreated FigJam-compatible CSV file: {output_file}")
        print(f"Generated {len(quotes)} rows of data")
        print(f"Starting from chunk {args.start_chunk}")
        print("\nTo use in FigJam:")
        print("1. Open FigJam")
        print("2. Click the '+' button and select 'Import'")
        print("3. Select the CSV file")
        print("4. Each cell will become its own sticky note!")
        print("\nColumns:")
        print("- Column 1: Quotes from interviews")
        print("- Column 2: Insight tags")
        print("- Column 3: Themes")
        
    except Exception as e:
        logger.error(f"Error generating FigJam notes: {str(e)}")

if __name__ == '__main__':
    main() 