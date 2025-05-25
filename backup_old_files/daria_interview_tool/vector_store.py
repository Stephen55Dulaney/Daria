from langchain_community.vectorstores import FAISS
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from pathlib import Path
import json
from typing import List, Dict, Any, Optional, Union
import traceback
import numpy as np
from dotenv import load_dotenv
import faiss
import logging
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class CustomEmbeddings:
    def __init__(self, api_key: str):
        """Initialize the embeddings class with API key."""
        try:
            self.api_key = api_key
            self.model = "text-embedding-3-small"
            self.embedding_dimension = 1536
            
            # Initialize the client once during initialization
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.openai.com/v1"
            )
            logger.info("CustomEmbeddings initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CustomEmbeddings: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts."""
        try:
            # Process texts in batches of 100
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
        except Exception as e:
            logger.error(f"Error embedding documents: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def embed_query(self, text: str) -> List[float]:
        """Embed a single piece of text."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding query: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def __call__(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Make the class callable for compatibility with LangChain."""
        if isinstance(texts, str):
            return [self.embed_query(texts)]
        return self.embed_documents(texts)

class InterviewVectorStore:
    def __init__(self, openai_api_key: str, vector_store_path: str = "vector_store"):
        """Initialize the vector store with OpenAI API key."""
        try:
            self.api_key = openai_api_key
            self.vector_store_path = vector_store_path
            self.embeddings = CustomEmbeddings(api_key=openai_api_key)
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Larger chunks to maintain context
                chunk_overlap=200,  # More overlap for better matching
                length_function=len,
                separators=["\n\n", "\n", " ", ""]  # Better separators for interview content
            )
            self.index = None
            self.interview_ids = []
            self.interview_metadata = {}
            
            # Initialize FAISS index if it doesn't exist
            if not os.path.exists(vector_store_path):
                dimension = self.embeddings.embedding_dimension
                self.index = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index with dimension {dimension}")
            else:
                self.load_vector_store()
                
            logger.info(f"Vector store initialized with path: {self.vector_store_path}")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _clean_content(self, content: str) -> str:
        """Clean content by removing Daria's comments and extracting only user responses."""
        try:
            lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Daria:') or line.startswith('daria:'):
                    continue
                if line and not any(skip in line.lower() for skip in [
                    'previous response:',
                    'continue the interview',
                    'role:',
                    'objective:',
                    'instructions:',
                    'project:',
                    'type:',
                    'date:'
                ]):
                    lines.append(line)
            return '\n'.join(lines)
        except Exception as e:
            print(f"Error cleaning content: {str(e)}")
            return content
    
    def _extract_user_responses(self, transcript: str) -> str:
        """Extract only the user responses from the transcript."""
        try:
            user_responses = []
            for line in transcript.split('\n'):
                line = line.strip()
                if line.startswith('You:'):
                    response = line[4:].strip()  # Remove 'You: ' prefix
                    if response and not response.startswith('Daria:'):  # Extra check to ensure no Daria responses
                        # Clean up the response
                        response = response.replace('Previous response:', '').strip()
                        response = response.replace('Role:', '').strip()
                        response = response.replace('Objective:', '').strip()
                        response = response.replace('Instructions:', '').strip()
                        if response:
                            user_responses.append(response)
            return '\n'.join(user_responses)
        except Exception as e:
            print(f"Error extracting user responses: {str(e)}")
            return ""
    
    def _prepare_interview_text(self, interview: Dict[str, Any]) -> str:
        """Prepare interview text for vectorization."""
        try:
            # Extract user responses from transcript
            user_responses = self._extract_user_responses(interview.get('transcript', ''))
            
            # Clean and format the analysis, handling None case
            analysis = interview.get('analysis')
            if analysis is None:
                analysis = ''
            else:
                analysis = str(analysis).strip()
            
            # Add project context
            project_name = interview.get('project_name', '')
            interview_type = interview.get('interview_type', '')
            
            # Prepare the text with clear section markers
            prepared_text = f"""
Project: {project_name}
Type: {interview_type}

User Responses:
{user_responses}

Analysis:
{analysis}
"""
            return prepared_text
        except Exception as e:
            logger.error(f"Error preparing interview text: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def add_interviews(self, interviews: List[Dict[str, Any]]) -> None:
        """Add multiple interviews to the vector store."""
        try:
            if not interviews:
                logger.warning("No interviews provided to add")
                return

            texts = []
            for interview in interviews:
                # Prepare the interview text using the helper method
                prepared_text = self._prepare_interview_text(interview)
                texts.append(prepared_text)
                self.interview_ids.append(interview['id'])
                self.interview_metadata[interview['id']] = {
                    'project_name': interview.get('project_name', ''),
                    'interview_type': interview.get('interview_type', ''),
                    'date': interview.get('date', ''),
                    'last_updated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                }

            logger.info(f"Processing {len(texts)} interviews for vectorization")

            # Get embeddings for all texts
            embeddings = self.embeddings.embed_documents(texts)
            
            # Add embeddings to the index
            if embeddings:
                if self.index is None:
                    dimension = len(embeddings[0])
                    self.index = faiss.IndexFlatL2(dimension)
                    logger.info(f"Created new FAISS index with dimension {dimension}")
                
                self.index.add(np.array(embeddings).astype('float32'))
                self.save_vector_store()
                logger.info("Successfully added interviews to vector store")
            else:
                logger.warning("No embeddings generated")
            
        except Exception as e:
            logger.error(f"Error adding interviews to vector store: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def save_vector_store(self) -> None:
        """Save the vector store to disk."""
        try:
            if self.index is not None:
                print(f"Saving vector store to {self.vector_store_path}")
                faiss.write_index(self.index, self.vector_store_path)
                metadata = {
                    'interview_ids': self.interview_ids,
                    'interview_metadata': self.interview_metadata
                }
                with open(f"{self.vector_store_path}_metadata.json", 'w') as f:
                    json.dump(metadata, f)
                print("Vector store saved successfully")
            else:
                print("No vector store to save")
        except Exception as e:
            print(f"Error saving vector store: {str(e)}")
            raise
    
    def load_vector_store(self) -> bool:
        """Load the vector store from disk."""
        try:
            if os.path.exists(self.vector_store_path):
                print(f"Loading vector store from {self.vector_store_path}")
                self.index = faiss.read_index(self.vector_store_path)
                metadata_path = f"{self.vector_store_path}_metadata.json"
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        self.interview_ids = metadata.get('interview_ids', [])
                        self.interview_metadata = metadata.get('interview_metadata', {})
                print("Vector store loaded successfully")
                return True
            return False
        except Exception as e:
            print(f"Error loading vector store: {str(e)}")
            return False
    
    def _extract_relevant_content(self, content: str) -> str:
        """Extract only relevant content from the interview text."""
        try:
            # Remove the metadata header section
            if 'User Responses:' in content:
                content = content.split('User Responses:')[1].split('Analysis:')[0].strip()
                # For user responses, keep the "You:" prefix temporarily to identify them
                lines = []
                for line in content.split('\n'):
                    line = line.strip()
                    # Skip metadata-like lines but preserve user responses
                    if any(pattern in line for pattern in [
                        'Project:', 'Type:', 'Date:', 
                        'Previous response:', 'Role:', 'Objective:', 'Instructions:'
                    ]):
                        continue
                    if line.startswith('You:'):
                        # Keep the actual response without the prefix
                        response = line[4:].strip()
                        if response:
                            lines.append(response)
                    elif not line.startswith('Daria:'):
                        lines.append(line)
                return '\n'.join(lines)
            elif 'Analysis:' in content:
                content = content.split('Analysis:')[1].strip()
                # For analysis content, filter out all metadata and system text
                lines = []
                for line in content.split('\n'):
                    line = line.strip()
                    if any(pattern in line for pattern in [
                        'Project:', 'Type:', 'Date:', 
                        'Daria:', 'Previous response:', 
                        'Role:', 'Objective:', 'Instructions:'
                    ]):
                        continue
                    if line:
                        lines.append(line)
                return '\n'.join(lines)
            
            return content
        except Exception as e:
            print(f"Error extracting relevant content: {str(e)}")
            return content

    def semantic_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar interviews using semantic search."""
        try:
            if not self.index or not self.interview_ids:
                logger.warning("No interviews in vector store")
                return []

            # Normalize the query
            query = query.strip().lower()
            if not query:
                return []

            # Get query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search the index with a larger k to get more potential matches
            search_k = min(k * 10, len(self.interview_ids))  # Increased from 5x to 10x
            distances, indices = self.index.search(
                np.array([query_embedding]).astype('float32'),
                search_k
            )
            
            # Get unique interview IDs from search results
            unique_interviews = {}
            for i, idx in enumerate(indices[0]):
                if idx < len(self.interview_ids):  # Ensure valid index
                    interview_id = self.interview_ids[idx]
                    if interview_id not in unique_interviews:
                        # Load the interview data
                        interview_file = Path('interviews') / f"{interview_id}.json"
                        interview_data = {}
                        if interview_file.exists():
                            with open(interview_file) as f:
                                interview_data = json.load(f)
                        
                        # Skip interviews with empty transcripts
                        if not interview_data.get('transcript'):
                            continue
                        
                        # Calculate similarity score using a modified sigmoid function
                        l2_distance = float(distances[0][i])
                        similarity_score = 1 / (1 + np.exp(l2_distance / 5))
                        
                        # Skip results with very low similarity
                        if similarity_score < 0.1:
                            continue
                        
                        # Format the result with all necessary fields
                        unique_interviews[interview_id] = {
                            'id': interview_id,
                            'project_name': interview_data.get('project_name', 'Unknown Project'),
                            'interview_type': interview_data.get('interview_type', 'Unknown Type'),
                            'date': interview_data.get('date') or datetime.now().isoformat(),
                            'transcript': interview_data.get('transcript', ''),
                            'analysis': interview_data.get('analysis', ''),
                            'score': similarity_score
                        }
                        if len(unique_interviews) >= k:
                            break
            
            # Convert to list and sort by score
            results = list(unique_interviews.values())
            results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Found {len(results)} unique interviews")
            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def find_similar_interviews(self, interview_id: str, k: int = 3) -> List[Dict[str, Any]]:
        """Find interviews similar to a given interview."""
        try:
            if interview_id not in self.interview_ids:
                return []

            # Get the index of the interview
            idx = self.interview_ids.index(interview_id)
            
            # Get the embedding at that index
            embedding = self.index.reconstruct(idx)
            
            # Search for similar interviews
            distances, indices = self.index.search(
                np.array([embedding]).astype('float32'), k + 1
            )

            # Get results (excluding the input interview)
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.interview_ids) and idx != self.interview_ids.index(interview_id):
                    similar_id = self.interview_ids[idx]
                    metadata = self.interview_metadata.get(similar_id, {})
                    results.append({
                        'id': similar_id,
                        'score': float(distances[0][i]),
                        'metadata': metadata
                    })

            return results
        except Exception as e:
            print(f"Error finding similar interviews: {str(e)}")
            return []

    def remove_interview(self, interview_id: str):
        """Remove an interview from the vector store."""
        try:
            if interview_id in self.interview_ids:
                idx = self.interview_ids.index(interview_id)
                # Remove the embedding
                self.index.remove_ids(np.array([idx]))
                # Remove from metadata
                self.interview_ids.pop(idx)
                self.interview_metadata.pop(interview_id, None)
                self.save_vector_store()
                print(f"Successfully removed interview {interview_id}")
        except Exception as e:
            print(f"Error removing interview: {str(e)}")
            raise

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        try:
            # Get embeddings for both texts
            embedding1 = self.embeddings.embed_query(text1)
            embedding2 = self.embeddings.embed_query(text2)
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0 