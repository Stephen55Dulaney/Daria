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
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document

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
            if not openai_api_key:
                raise ValueError("OpenAI API key is required")
                
            self.api_key = openai_api_key
            
            # Ensure vector_store_path is not empty
            if not vector_store_path:
                vector_store_path = "vector_store"
                
            self.vector_store_path = vector_store_path
            
            # Initialize embeddings
            logger.info("Initializing embeddings...")
            self.embeddings = CustomEmbeddings(api_key=openai_api_key)
            
            # Initialize text splitter
            logger.info("Initializing text splitter...")
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Larger chunks to maintain context
                chunk_overlap=200,  # More overlap for better matching
                length_function=len,
                separators=["\n\n", "\n", " ", ""]  # Better separators for interview content
            )
            
            # Initialize state
            self.index = None
            self.interview_ids = []
            self.interview_metadata = {}
            
            # Create vector store directory if it doesn't exist
            os.makedirs(vector_store_path, exist_ok=True)
            
            # Set up the index file path
            self.index_file = os.path.join(vector_store_path, "index.faiss")
            self.metadata_file = os.path.join(vector_store_path, "metadata.json")
            
            # Initialize or load FAISS index
            if os.path.exists(self.index_file):
                logger.info("Loading existing FAISS index...")
                if not self.load_vector_store():
                    logger.warning("Failed to load existing vector store, creating new one...")
                    dimension = self.embeddings.embedding_dimension
                    self.index = faiss.IndexFlatL2(dimension)
                    logger.info(f"Created new FAISS index with dimension {dimension}")
            else:
                logger.info("Creating new FAISS index...")
                dimension = self.embeddings.embedding_dimension
                self.index = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index with dimension {dimension}")
                
            # Validate initialization
            if not self.index:
                raise RuntimeError("Failed to initialize FAISS index")
            if not hasattr(self.embeddings, 'embed_query'):
                raise RuntimeError("Embeddings not properly initialized")
                
            logger.info(f"Vector store initialized successfully with path: {self.vector_store_path}")
            logger.info(f"Current state: {len(self.interview_ids)} interviews loaded")
            
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
            
            # Clean and format the analysis
            analysis = interview.get('analysis', '').strip()
            
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

            if not self.index:
                logger.error("Vector store not initialized")
                raise RuntimeError("Vector store not initialized")

            # Validate interviews
            valid_interviews = []
            for interview in interviews:
                if not isinstance(interview, dict):
                    logger.warning(f"Skipping invalid interview format: {type(interview)}")
                    continue
                    
                if 'id' not in interview:
                    logger.warning("Skipping interview without ID")
                    continue
                    
                if interview['id'] in self.interview_ids:
                    logger.info(f"Skipping duplicate interview: {interview['id']}")
                    continue
                    
                valid_interviews.append(interview)

            if not valid_interviews:
                logger.warning("No valid interviews to add")
                return

            logger.info(f"Processing {len(valid_interviews)} interviews for vectorization")
            
            texts = []
            for interview in valid_interviews:
                try:
                    # Prepare the interview text using the helper method
                    prepared_text = self._prepare_interview_text(interview)
                    if not prepared_text.strip():
                        logger.warning(f"Skipping interview {interview['id']} with empty content")
                        continue
                        
                    texts.append(prepared_text)
                    self.interview_ids.append(interview['id'])
                    self.interview_metadata[interview['id']] = {
                        'project_name': interview.get('project_name', ''),
                        'interview_type': interview.get('interview_type', ''),
                        'date': interview.get('date', '')
                    }
                except Exception as e:
                    logger.error(f"Error processing interview {interview.get('id', 'unknown')}: {str(e)}")
                    continue

            if not texts:
                logger.warning("No valid texts to embed")
                return

            # Get embeddings for all texts
            try:
                embeddings = self.embeddings.embed_documents(texts)
                if not embeddings:
                    logger.error("Failed to generate embeddings")
                    return
                    
                # Add embeddings to the index
                self.index.add(np.array(embeddings).astype('float32'))
                
                # Save the updated vector store
                self.save_vector_store()
                logger.info(f"Successfully added {len(texts)} interviews to vector store")
                
            except Exception as e:
                logger.error(f"Error during embedding process: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
        except Exception as e:
            logger.error(f"Error adding interviews to vector store: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def save_vector_store(self) -> None:
        """Save the vector store to disk."""
        try:
            if not self.index:
                logger.warning("No vector store to save")
                return

            logger.info(f"Saving vector store to {self.index_file}")
            
            # Ensure the directory exists
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Save the FAISS index
            faiss.write_index(self.index, self.index_file)
            
            # Save metadata
            metadata = {
                'interview_ids': self.interview_ids,
                'interview_metadata': self.interview_metadata,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Vector store saved successfully with {len(self.interview_ids)} interviews")
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def load_vector_store(self) -> bool:
        """Load the vector store from disk."""
        try:
            if not os.path.exists(self.index_file):
                logger.warning(f"Vector store file not found at {self.index_file}")
                return False

            logger.info(f"Loading vector store from {self.index_file}")
            
            # Load the FAISS index
            self.index = faiss.read_index(self.index_file)
            
            # Load metadata
            if not os.path.exists(self.metadata_file):
                logger.warning(f"Metadata file not found at {self.metadata_file}")
                return False
                
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                self.interview_ids = metadata.get('interview_ids', [])
                self.interview_metadata = metadata.get('interview_metadata', {})
                last_updated = metadata.get('last_updated')
                if last_updated:
                    logger.info(f"Vector store last updated: {last_updated}")
            
            logger.info(f"Vector store loaded successfully with {len(self.interview_ids)} interviews")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _extract_relevant_content(self, content: str) -> str:
        """Extract only the relevant content from a search result, removing metadata headers."""
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
            search_k = min(k * 20, len(self.interview_ids))  # Increased multiplier for more candidates
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
                        # This provides better differentiation between results
                        l2_distance = float(distances[0][i])
                        # Use a more lenient sigmoid function with a larger divisor
                        similarity_score = 1 / (1 + np.exp(l2_distance / 15))  # Increased divisor for smoother falloff
                        
                        # Skip results with very low similarity
                        if similarity_score < 0.05:  # Lowered threshold to catch more near matches
                            continue
                        
                        # Format the result with all necessary fields
                        unique_interviews[interview_id] = {
                            'id': interview_id,
                            'project_name': interview_data.get('project_name', 'Unknown Project'),
                            'interview_type': interview_data.get('interview_type', 'Unknown Type'),
                            'date': interview_data.get('date', datetime.now().isoformat()),
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

class VectorStore:
    def __init__(self, index_path: str = "vector_store"):
        """Initialize the vector store with a specified path."""
        self.index_path = index_path
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self.load_or_create_store()

    def load_or_create_store(self) -> None:
        """Load an existing vector store or create a new one if it doesn't exist."""
        try:
            if os.path.exists(os.path.join(self.index_path, "index.faiss")):
                self.vector_store = FAISS.load_local(
                    self.index_path,
                    self.embeddings
                )
            else:
                # Create a new store with an empty document
                self.vector_store = FAISS.from_documents(
                    [Document(page_content="", metadata={})],
                    self.embeddings
                )
                self.save_store()
        except Exception as e:
            print(f"Error loading/creating vector store: {e}")
            # Create a new store with an empty document
            self.vector_store = FAISS.from_documents(
                [Document(page_content="", metadata={})],
                self.embeddings
            )
            self.save_store()

    def save_store(self) -> None:
        """Save the vector store to disk."""
        if self.vector_store:
            os.makedirs(self.index_path, exist_ok=True)
            self.vector_store.save_local(self.index_path)

    def add_interview(self, interview_data: Dict[str, Any]) -> None:
        """Add an interview to the vector store."""
        try:
            # Create a document for each message in the transcript
            documents = []
            
            # Add interview metadata
            metadata = {
                "interview_id": interview_data.get("interview_id", ""),
                "project_name": interview_data.get("project", {}).get("name", ""),
                "interview_type": interview_data.get("project", {}).get("type", ""),
                "researcher_name": interview_data.get("researcher", {}).get("name", ""),
                "interviewee_name": interview_data.get("interviewee", {}).get("name", ""),
                "date": datetime.now().isoformat(),
            }
            
            # Process transcript
            transcript = interview_data.get("transcript", [])
            for entry in transcript:
                # Create a document for each message
                doc = Document(
                    page_content=f"{entry['speaker']}: {entry['text']}",
                    metadata={
                        **metadata,
                        "timestamp": entry["timestamp"],
                        "speaker": entry["speaker"]
                    }
                )
                documents.append(doc)
            
            # Add documents to vector store
            if documents:
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(documents, self.embeddings)
                else:
                    self.vector_store.add_documents(documents)
                self.save_store()
                
                # Save raw interview data
                self._save_interview_json(interview_data)
        except Exception as e:
            print(f"Error adding interview: {e}")
            raise

    def _save_interview_json(self, interview_data: Dict[str, Any]) -> None:
        """Save the raw interview data as JSON."""
        try:
            interviews_dir = os.path.join(self.index_path, "interviews")
            os.makedirs(interviews_dir, exist_ok=True)
            
            interview_id = interview_data.get("interview_id", "")
            if interview_id:
                file_path = os.path.join(interviews_dir, f"{interview_id}.json")
                with open(file_path, "w") as f:
                    json.dump(interview_data, f, indent=2)
        except Exception as e:
            print(f"Error saving interview JSON: {e}")
            raise

    def search(self, query: str, filter_dict: Optional[Dict[str, str]] = None, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant messages.
        
        Args:
            query: The search query
            filter_dict: Optional dictionary of metadata filters
            k: Number of results to return
            
        Returns:
            List of dictionaries containing the search results
        """
        try:
            if not self.vector_store:
                return []
            
            # Perform the search
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
            
            # Format results
            results = []
            for doc, score in docs_and_scores:
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                }
                results.append(result)
            
            return results
        except Exception as e:
            print(f"Error searching vector store: {e}")
            return []

    def get_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the full interview data by ID."""
        try:
            file_path = os.path.join(self.index_path, "interviews", f"{interview_id}.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error retrieving interview: {e}")
            return None

    def list_interviews(self) -> List[Dict[str, Any]]:
        """List all interviews with their metadata."""
        try:
            interviews_dir = os.path.join(self.index_path, "interviews")
            if not os.path.exists(interviews_dir):
                return []
            
            interviews = []
            for filename in os.listdir(interviews_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(interviews_dir, filename)
                    with open(file_path, "r") as f:
                        interview_data = json.load(f)
                        # Extract key metadata for the list view
                        interviews.append({
                            "interview_id": interview_data.get("interview_id", ""),
                            "project_name": interview_data.get("project", {}).get("name", ""),
                            "interview_type": interview_data.get("project", {}).get("type", ""),
                            "researcher_name": interview_data.get("researcher", {}).get("name", ""),
                            "interviewee_name": interview_data.get("interviewee", {}).get("name", ""),
                            "date": interview_data.get("date", "")
                        })
            
            # Sort by date, most recent first
            interviews.sort(key=lambda x: x["date"], reverse=True)
            return interviews
        except Exception as e:
            print(f"Error listing interviews: {e}")
            return []

    def delete_interview(self, interview_id: str) -> bool:
        """Delete an interview and its associated data."""
        try:
            # Delete JSON file
            json_path = os.path.join(self.index_path, "interviews", f"{interview_id}.json")
            if os.path.exists(json_path):
                os.remove(json_path)
            
            # Remove documents from vector store
            if self.vector_store:
                # Create a new store without the deleted interview's documents
                docs = []
                for doc in self.vector_store.docstore._dict.values():
                    if doc.metadata.get("interview_id") != interview_id:
                        docs.append(doc)
                
                if docs:
                    self.vector_store = FAISS.from_documents(docs, self.embeddings)
                else:
                    # If no documents left, create empty store
                    self.vector_store = FAISS.from_documents(
                        [Document(page_content="", metadata={})],
                        self.embeddings
                    )
                self.save_store()
            
            return True
        except Exception as e:
            print(f"Error deleting interview: {e}")
            return False 

class RawInterviewStore:
    """Vector store for raw interview transcripts using FAISS."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the raw interview store."""
        self.api_key = openai_api_key
        self.embeddings = OpenAIEmbeddings()
        self.raw_dir = Path('interviews/raw')
        self.index_path = Path('vector_store/raw')
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load FAISS index
        self.load_or_create_store()
        
    def load_or_create_store(self) -> None:
        """Load existing vector store or create new one."""
        try:
            index_file = self.index_path / 'index.faiss'
            if index_file.exists():
                self.vector_store = FAISS.load_local(
                    str(self.index_path),
                    self.embeddings
                )
                logger.info("Loaded existing raw interview vector store")
            else:
                # Create new store with empty document
                self.vector_store = FAISS.from_documents(
                    [{'page_content': '', 'metadata': {}}],
                    self.embeddings
                )
                self.save_store()
                logger.info("Created new raw interview vector store")
        except Exception as e:
            logger.error(f"Error in load_or_create_store: {str(e)}")
            raise

    def save_store(self) -> None:
        """Save the vector store to disk."""
        if self.vector_store:
            self.vector_store.save_local(str(self.index_path))
            
    def add_interview(self, interview_data: Dict[str, Any]) -> None:
        """Add a raw interview to the vector store."""
        try:
            # Create document from interview transcript
            transcript = ' '.join(
                f"{msg['speaker']}: {msg['text']}"
                for msg in interview_data.get('transcript', [])
            )
            
            metadata = {
                'id': interview_data.get('id'),
                'project_name': interview_data.get('project_name'),
                'title': interview_data.get('title'),
                'created_at': interview_data.get('created_at'),
                'type': interview_data.get('type')
            }
            
            document = {
                'page_content': transcript,
                'metadata': metadata
            }
            
            # Add to vector store
            if not self.vector_store:
                self.vector_store = FAISS.from_documents([document], self.embeddings)
            else:
                self.vector_store.add_documents([document])
            
            self.save_store()
            logger.info(f"Added raw interview {metadata['id']} to vector store")
            
        except Exception as e:
            logger.error(f"Error adding raw interview: {str(e)}")
            raise
            
    def exact_match_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform exact text match search on raw interviews."""
        try:
            # Load all raw interviews
            results = []
            for file in self.raw_dir.glob('*.json'):
                with file.open() as f:
                    interview = json.load(f)
                    transcript = ' '.join(
                        f"{msg['speaker']}: {msg['text']}"
                        for msg in interview.get('transcript', [])
                    )
                    if query.lower() in transcript.lower():
                        results.append({
                            'id': interview.get('id'),
                            'title': interview.get('title'),
                            'project_name': interview.get('project_name'),
                            'match_type': 'exact',
                            'score': 1.0
                        })
                        
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error in exact match search: {str(e)}")
            return []
            
    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic similarity search on raw interviews."""
        try:
            if not self.vector_store:
                return []
                
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            return [
                {
                    'id': doc.metadata.get('id'),
                    'title': doc.metadata.get('title'),
                    'project_name': doc.metadata.get('project_name'),
                    'match_type': 'semantic',
                    'score': float(score)
                }
                for doc, score in results
            ]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []

class ProcessedInterviewStore:
    """Vector store for processed interview chunks using Qdrant."""
    
    def __init__(self):
        """Initialize the processed interview store."""
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        self.processed_dir = Path('interviews/processed')
        self.semantic_analyzer = SemanticAnalyzer()
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(":memory:")
        self.collection_name = "interview_chunks"
        
        # Create collection for chunks
        self.qdrant.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=384,  # MiniLM-L6-v2 embedding size
                distance=models.Distance.COSINE
            )
        )
        
    def add_interview(self, interview_data: Dict[str, Any]) -> None:
        """Add a processed interview's chunks to the vector store."""
        try:
            for chunk in interview_data.get('chunks', []):
                # Get chunk embedding
                embedding = self.semantic_analyzer.get_embedding(chunk['text'])
                
                # Add to Qdrant
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=[{
                        'id': f"{interview_data['id']}_{chunk['timestamp']}",
                        'vector': embedding,
                        'payload': {
                            'interview_id': interview_data['id'],
                            'project_name': interview_data['project_name'],
                            'text': chunk['text'],
                            'speaker': chunk['speaker'],
                            'timestamp': chunk['timestamp'],
                            'metadata': chunk['metadata']
                        }
                    }]
                )
                
            logger.info(f"Added processed interview {interview_data['id']} chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding processed interview: {str(e)}")
            raise
            
    def semantic_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for semantically similar chunks."""
        try:
            # Get query embedding
            query_embedding = self.semantic_analyzer.get_embedding(query)
            
            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            
            return [
                {
                    'chunk_id': hit.id,
                    'interview_id': hit.payload['interview_id'],
                    'project_name': hit.payload['project_name'],
                    'text': hit.payload['text'],
                    'speaker': hit.payload['speaker'],
                    'timestamp': hit.payload['timestamp'],
                    'metadata': hit.payload['metadata'],
                    'score': hit.score
                }
                for hit in results
            ]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
            
    def emotion_search(self, emotion: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for chunks with specific emotion."""
        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * 384,  # Dummy vector for filtering
                limit=k,
                query_filter={
                    'must': [{
                        'key': 'metadata.emotion',
                        'match': {'value': emotion}
                    }]
                }
            )
            
            return [
                {
                    'chunk_id': hit.id,
                    'interview_id': hit.payload['interview_id'],
                    'project_name': hit.payload['project_name'],
                    'text': hit.payload['text'],
                    'speaker': hit.payload['speaker'],
                    'timestamp': hit.payload['timestamp'],
                    'metadata': hit.payload['metadata'],
                    'score': hit.score
                }
                for hit in results
            ]
            
        except Exception as e:
            logger.error(f"Error in emotion search: {str(e)}")
            return []
            
    def find_similar_chunks(self, chunk_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find chunks similar to a given chunk across all interviews."""
        try:
            # Get the chunk's vector
            chunk_info = self.qdrant.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id]
            )[0]
            
            # Search for similar chunks
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=chunk_info.vector,
                limit=k + 1  # Add 1 to account for the query chunk
            )
            
            # Filter out the query chunk and format results
            return [
                {
                    'chunk_id': hit.id,
                    'interview_id': hit.payload['interview_id'],
                    'project_name': hit.payload['project_name'],
                    'text': hit.payload['text'],
                    'speaker': hit.payload['speaker'],
                    'timestamp': hit.payload['timestamp'],
                    'metadata': hit.payload['metadata'],
                    'score': hit.score
                }
                for hit in results
                if hit.id != chunk_id
            ]
            
        except Exception as e:
            logger.error(f"Error finding similar chunks: {str(e)}")
            return [] 
