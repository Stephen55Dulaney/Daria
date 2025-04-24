from pathlib import Path
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from scripts.process_transcripts import TranscriptProcessor
from vector_store import RawInterviewStore, ProcessedInterviewStore

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterviewManager:
    def __init__(self):
        """Initialize the interview manager."""
        self.raw_store = RawInterviewStore(os.getenv('OPENAI_API_KEY'))
        self.processed_store = ProcessedInterviewStore()
        self.processor = TranscriptProcessor()
        
        # Ensure directory structure
        self.raw_dir = Path('interviews/raw')
        self.processed_dir = Path('interviews/processed')
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def add_raw_interview(self, interview_data: Dict[str, Any]) -> str:
        """Add a new raw interview and process it."""
        try:
            # Generate ID if not provided
            if 'id' not in interview_data:
                interview_data['id'] = str(uuid.uuid4())
                
            # Save raw interview
            raw_file = self.raw_dir / f"{interview_data['id']}.json"
            with raw_file.open('w') as f:
                json.dump(interview_data, f, indent=2)
                
            # Add to raw vector store
            self.raw_store.add_interview(interview_data)
            
            # Process the interview
            self.processor.process_raw_transcript(raw_file)
            
            # Load and add processed version to processed store
            processed_file = self.processed_dir / f"{interview_data['id']}.json"
            if processed_file.exists():
                with processed_file.open() as f:
                    processed_data = json.load(f)
                self.processed_store.add_interview(processed_data)
            
            return interview_data['id']
            
        except Exception as e:
            logger.error(f"Error adding raw interview: {str(e)}")
            raise

    def search_raw_interviews(self, query: str, use_semantic: bool = False, k: int = 5) -> List[Dict[str, Any]]:
        """Search raw interviews using either exact match or semantic search."""
        try:
            if use_semantic:
                return self.raw_store.similarity_search(query, k=k)
            else:
                return self.raw_store.exact_match_search(query, k=k)
                
        except Exception as e:
            logger.error(f"Error searching raw interviews: {str(e)}")
            return []

    def search_processed_chunks(self, 
                              query: str = None, 
                              emotion: str = None,
                              k: int = 5) -> List[Dict[str, Any]]:
        """Search processed chunks by semantic similarity or emotion."""
        try:
            if query:
                return self.processed_store.semantic_search(query, k=k)
            elif emotion:
                return self.processed_store.emotion_search(emotion, k=k)
            else:
                raise ValueError("Must provide either query or emotion")
                
        except Exception as e:
            logger.error(f"Error searching processed chunks: {str(e)}")
            return []

    def find_similar_chunks(self, chunk_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find chunks similar to a given chunk across all interviews."""
        try:
            return self.processed_store.find_similar_chunks(chunk_id, k=k)
        except Exception as e:
            logger.error(f"Error finding similar chunks: {str(e)}")
            return []

    def reprocess_interview(self, interview_id: str) -> bool:
        """Reprocess a raw interview to update its processed version."""
        try:
            raw_file = self.raw_dir / f"{interview_id}.json"
            if not raw_file.exists():
                logger.error(f"Raw interview {interview_id} not found")
                return False
                
            # Process the raw interview
            self.processor.process_raw_transcript(raw_file)
            
            # Load and add new processed version to store
            processed_file = self.processed_dir / f"{interview_id}.json"
            if processed_file.exists():
                with processed_file.open() as f:
                    processed_data = json.load(f)
                self.processed_store.add_interview(processed_data)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error reprocessing interview: {str(e)}")
            return False

    def get_raw_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Get a raw interview by ID."""
        try:
            raw_file = self.raw_dir / f"{interview_id}.json"
            if raw_file.exists():
                with raw_file.open() as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error getting raw interview: {str(e)}")
            return None

    def get_processed_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Get a processed interview by ID."""
        try:
            processed_file = self.processed_dir / f"{interview_id}.json"
            if processed_file.exists():
                with processed_file.open() as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error getting processed interview: {str(e)}")
            return None

    def list_raw_interviews(self) -> List[Dict[str, Any]]:
        """List all raw interviews with basic metadata."""
        try:
            interviews = []
            for file in self.raw_dir.glob('*.json'):
                with file.open() as f:
                    interview = json.load(f)
                    interviews.append({
                        'id': interview.get('id'),
                        'title': interview.get('title'),
                        'project_name': interview.get('project_name'),
                        'created_at': interview.get('created_at'),
                        'status': interview.get('status')
                    })
            return interviews
        except Exception as e:
            logger.error(f"Error listing raw interviews: {str(e)}")
            return []

    def list_processed_interviews(self) -> List[Dict[str, Any]]:
        """List all processed interviews with basic metadata."""
        try:
            interviews = []
            for file in self.processed_dir.glob('*.json'):
                with file.open() as f:
                    interview = json.load(f)
                    interviews.append({
                        'id': interview.get('id'),
                        'title': interview.get('title'),
                        'project_name': interview.get('project_name'),
                        'created_at': interview.get('created_at'),
                        'chunk_count': len(interview.get('chunks', []))
                    })
            return interviews
        except Exception as e:
            logger.error(f"Error listing processed interviews: {str(e)}")
            return [] 