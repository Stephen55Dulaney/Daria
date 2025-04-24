import os
import json
import logging
from typing import Dict, List, Any
import sys
from pathlib import Path
import re

# Add parent directory to path so we can import semantic_analysis
sys.path.append(str(Path(__file__).parent.parent))

from semantic_analysis import SemanticAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptProcessor:
    def __init__(self):
        """Initialize the transcript processor with semantic analyzer."""
        self.semantic_analyzer = SemanticAnalyzer()
        self.raw_dir = "interviews/raw"
        self.processed_dir = "interviews/processed"
        
        # Ensure processed directory exists
        os.makedirs(self.processed_dir, exist_ok=True)

    def parse_transcript(self, transcript_text: str) -> List[Dict[str, Any]]:
        """Parse transcript text into a list of entries."""
        # Split transcript into entries based on timestamp pattern
        entries = []
        
        # Pattern matches "[Name] HH:MM:SS" followed by text
        pattern = r'\[(.*?)\]\s+(\d{2}:\d{2}:\d{2})\n(.*?)(?=\n\[|$)'
        matches = re.finditer(pattern, transcript_text, re.DOTALL)
        
        for match in matches:
            speaker = match.group(1).strip()
            timestamp = match.group(2).strip()
            text = match.group(3).strip()
            
            entries.append({
                'speaker': speaker,
                'timestamp': timestamp,
                'text': text
            })
        
        return entries

    def chunk_transcript(self, transcript: str, chunk_size: int = 3) -> List[Dict[str, Any]]:
        """Split transcript into chunks of specified size."""
        # First parse the transcript string into entries
        entries = self.parse_transcript(transcript)
        
        chunks = []
        current_chunk = []
        current_text = []
        
        for entry in entries:
            current_chunk.append(entry)
            current_text.append(entry['text'])
            
            if len(current_chunk) >= chunk_size:
                chunks.append({
                    'entries': current_chunk,
                    'combined_text': ' '.join(current_text)
                })
                current_chunk = []
                current_text = []
        
        # Add remaining entries if any
        if current_chunk:
            chunks.append({
                'entries': current_chunk,
                'combined_text': ' '.join(current_text)
            })
            
        return chunks

    def process_interview(self, file_path: str) -> Dict[str, Any]:
        """Process a single interview file."""
        try:
            # Read raw interview
            with open(file_path, 'r') as f:
                interview = json.load(f)
            
            # Extract transcript
            transcript = interview.get('transcript')
            if not transcript:
                logger.warning(f"No transcript found in {file_path}")
                return None
            
            # Chunk transcript
            chunks = self.chunk_transcript(transcript)
            
            # Analyze each chunk
            analyzed_chunks = []
            for chunk in chunks:
                analysis = self.semantic_analyzer.analyze_chunk(chunk['combined_text'])
                analyzed_chunks.append({
                    'entries': chunk['entries'],
                    'combined_text': chunk['combined_text'],
                    'analysis': analysis
                })
            
            # Create processed version
            processed_interview = {
                'metadata': {
                    'interviewee': interview.get('metadata', {}).get('interviewee', {}),
                    'researcher': interview.get('metadata', {}).get('researcher', {}),
                    'project': {
                        'name': interview.get('project_name'),
                        'type': interview.get('interview_type'),
                        'description': interview.get('project_description')
                    },
                    'date': interview.get('date'),
                    'duration': interview.get('duration'),
                    'format': interview.get('format'),
                    'language': interview.get('language')
                },
                'chunks': analyzed_chunks
            }
            
            # Save processed version
            output_path = os.path.join(
                self.processed_dir,
                os.path.basename(file_path)
            )
            with open(output_path, 'w') as f:
                json.dump(processed_interview, f, indent=2)
            
            logger.info(f"Successfully processed {file_path} -> {output_path}")
            return processed_interview
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None

    def process_all(self):
        """Process all raw interview files."""
        # Get all JSON files in raw directory
        raw_files = [
            os.path.join(self.raw_dir, f)
            for f in os.listdir(self.raw_dir)
            if f.endswith('.json')
        ]
        
        logger.info(f"Found {len(raw_files)} raw interview files")
        
        # Process each file
        processed = 0
        for file_path in raw_files:
            if self.process_interview(file_path):
                processed += 1
        
        logger.info(f"Successfully processed {processed} out of {len(raw_files)} interviews")

if __name__ == '__main__':
    processor = TranscriptProcessor()
    processor.process_all() 