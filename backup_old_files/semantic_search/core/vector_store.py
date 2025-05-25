from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import uuid
from sentence_transformers import SentenceTransformer
import json
import os

class InterviewVectorStore:
    def __init__(self, persist_directory: str = "data/vector_store"):
        """Initialize the vector store with ChromaDB backend"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            is_persistent=True
        ))
        
        # Create collections for different types of embeddings
        self.interview_collection = self.client.get_or_create_collection(
            name="interview_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def process_interview(self, interview_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process interview data into chunks with metadata"""
        chunks = []
        messages = interview_data.get('messages', [])
        
        current_chunk = {
            'messages': [],
            'metadata': {
                'interview_id': interview_data['id'],
                'speaker': None,
                'timestamp': None
            }
        }
        
        for msg in messages:
            # Check if this is a speaker timestamp message
            if '] ' in msg['content'] and '[' in msg['content']:
                if current_chunk['messages']:
                    chunks.append(current_chunk)
                    current_chunk = {
                        'messages': [],
                        'metadata': {
                            'interview_id': interview_data['id'],
                            'speaker': None,
                            'timestamp': None
                        }
                    }
                
                # Extract speaker and timestamp
                parts = msg['content'].split('] ')
                if len(parts) == 2:
                    speaker = parts[0].replace('[', '').strip()
                    timestamp = parts[1].strip()
                    current_chunk['metadata']['speaker'] = speaker
                    current_chunk['metadata']['timestamp'] = timestamp
            else:
                current_chunk['messages'].append(msg['content'])
        
        # Add final chunk if not empty
        if current_chunk['messages']:
            chunks.append(current_chunk)
        
        return chunks
    
    def add_interview(self, interview_data: Dict[str, Any]):
        """Add an interview to the vector store"""
        chunks = self.process_interview(interview_data)
        
        for chunk in chunks:
            # Create combined text for embedding
            combined_text = ' '.join(chunk['messages'])
            
            # Generate embedding
            embedding = self.model.encode(combined_text)
            
            # Add to ChromaDB
            self.interview_collection.add(
                documents=[combined_text],
                embeddings=[embedding.tolist()],
                metadatas=[chunk['metadata']],
                ids=[str(uuid.uuid4())]
            )
    
    def semantic_search(self, 
                       query: str, 
                       filters: Optional[Dict] = None,
                       limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search over interview chunks
        
        Args:
            query: Search query
            filters: Optional filters for metadata
            limit: Maximum number of results to return
            
        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding
        query_embedding = self.model.encode(query)
        
        # Prepare filter conditions if any
        where = {}
        if filters:
            if filters.get('speaker_type') == 'participant':
                where['speaker'] = {'$ne': 'Dulaney, Stephen'}  # Exclude interviewer
            elif filters.get('speaker_type') == 'interviewer':
                where['speaker'] = 'Dulaney, Stephen'
        
        # Perform search
        results = self.interview_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=limit,
            where=where
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': float(results['distances'][0][i])
            })
        
        return formatted_results
    
    def get_all_interviews(self) -> List[str]:
        """Get all unique interview IDs in the store"""
        results = self.interview_collection.get()
        interview_ids = set()
        for metadata in results['metadatas']:
            interview_ids.add(metadata['interview_id'])
        return list(interview_ids) 