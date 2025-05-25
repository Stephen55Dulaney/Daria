import os
import json
import logging
from typing import Dict, List, Any
import sys
from pathlib import Path
import re
import uuid

# Add parent directory to path so we can import semantic_analysis
sys.path.append(str(Path(__file__).parent.parent))

from semantic_analysis import SemanticAnalyzer, split_transcript_safe

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

    def chunk_transcript(self, transcript: str) -> List[Dict[str, Any]]:
        """Split transcript into safe-sized chunks while preserving chronological order."""
        # First parse the transcript string into entries
        logger.info("Parsing transcript into entries...")
        entries = self.parse_transcript(transcript)
        logger.info(f"Found {len(entries)} entries in the transcript")
        
        # Sort entries by timestamp to ensure chronological order
        entries.sort(key=lambda x: x['timestamp'])
        
        # Now split into safe chunks, making sure each chunk doesn't exceed token limits
        safe_chunks = split_transcript_safe(transcript, max_length=350)
        logger.info(f"Split transcript into {len(safe_chunks)} safe chunks")
        
        chunks = []
        remaining_entries = entries.copy()
        
        # For each safe chunk, find all entries that belong to it
        for chunk_text in safe_chunks:
            chunk_entries = []
            chunk_start_idx = None
            
            # Find entries that belong to this chunk
            for i, entry in enumerate(remaining_entries):
                # Check if entry text is in this chunk
                if entry['text'] in chunk_text:
                    if chunk_start_idx is None:
                        chunk_start_idx = i
                    chunk_entries.append(entry)
                elif chunk_entries:  # If we've found entries but this one isn't in the chunk
                    break  # Stop looking as we've gone past the chunk's entries
            
            # If we found entries, remove them from remaining entries
            if chunk_entries:
                remaining_entries = remaining_entries[chunk_start_idx + len(chunk_entries):]
                
                chunks.append({
                    'entries': chunk_entries,
                    'combined_text': chunk_text,
                    'timestamp': chunk_entries[0]['timestamp']  # Use first entry's timestamp
                })
            else:
                # If no entries found but chunk has content, try to extract timestamp
                if chunk_text.strip():
                    # Look for timestamp in the chunk text
                    time_match = re.search(r'\d{2}:\d{2}:\d{2}', chunk_text)
                    timestamp = time_match.group(0) if time_match else None
                    
                    # Look for speaker information
                    speaker_match = re.search(r'\[(.*?)\]', chunk_text)
                    speaker = speaker_match.group(1) if speaker_match else "Unknown"
                    
                    # If we found a timestamp, create an entry
                    if timestamp:
                        chunks.append({
                            'entries': [{
                                'speaker': speaker,
                                'timestamp': timestamp,
                                'text': chunk_text.strip()
                            }],
                            'combined_text': chunk_text,
                            'timestamp': timestamp
                        })
        
        # Sort final chunks by timestamp
        chunks.sort(key=lambda x: x['timestamp'])
        
        logger.info(f"Created {len(chunks)} chunks with chronological ordering")
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
            
            # Chunk transcript using safe chunking
            logger.info(f"Processing transcript from {file_path}...")
            chunks = self.chunk_transcript(transcript)
            
            # Analyze each chunk
            analyzed_chunks = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Analyzing chunk {i+1} of {len(chunks)}...")
                combined_text = chunk['combined_text']
                
                # Skip empty chunks
                if not combined_text.strip():
                    logger.warning(f"Skipping empty chunk {i+1}")
                    continue
                
                # Check token length
                token_count = len(combined_text.split())
                if token_count > 500:
                    logger.warning(f"Chunk {i+1} still has {token_count} tokens, which might be too long. Splitting further.")
                    # Split further if needed
                    sub_chunks = split_transcript_safe(combined_text, max_length=250)
                    for j, sub_text in enumerate(sub_chunks):
                        try:
                            logger.info(f"Analyzing sub-chunk {j+1} of {len(sub_chunks)} from chunk {i+1}...")
                            sub_analysis = self.semantic_analyzer.analyze_chunk(sub_text)
                            analyzed_chunks.append({
                                'entries': chunk['entries'],  # Use same entries for all sub-chunks
                                'combined_text': sub_text,
                                'analysis': sub_analysis,
                                'id': str(uuid.uuid4()),  # Generate unique ID
                                'timestamp': chunk['entries'][0]['timestamp'] if chunk['entries'] else "00:00:00"
                            })
                        except Exception as e:
                            logger.error(f"Error analyzing sub-chunk {j+1} of chunk {i+1}: {str(e)}")
                            # Continue with next sub-chunk
                else:
                    # Normal analysis for appropriately sized chunks
                    try:
                        analysis = self.semantic_analyzer.analyze_chunk(combined_text)
                        analyzed_chunks.append({
                            'entries': chunk['entries'],
                            'combined_text': combined_text,
                            'analysis': analysis,
                            'id': str(uuid.uuid4()),  # Generate unique ID
                            'timestamp': chunk['entries'][0]['timestamp'] if chunk['entries'] else "00:00:00"
                        })
                    except Exception as e:
                        logger.error(f"Error analyzing chunk {i+1}: {str(e)}")
                        # Continue with next chunk
            
            # Create processed version
            processed_interview = {
                'id': interview.get('id', Path(file_path).stem),
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