import os
import json
import logging
import traceback
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptProcessor:
    def __init__(self, persist_directory: str = "chroma_db"):
        """Initialize the transcript processor with ChromaDB and embeddings."""
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="transcripts",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize LLM for tagging
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1
        )
        
        # Define the tagging prompt template
        self.tagging_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing interview transcripts and identifying key themes, insights, and patterns.\n            For each chunk of text, identify:\n            1. Key themes and topics\n            2. Important insights\n            3. Sentiment (positive, negative, neutral)\n            4. Action items or next steps\n            5. Pain points or challenges mentioned\n            \n            Format your response as a JSON object with these fields:\n            {{
                "themes": ["theme1", "theme2"],\n                "insights": ["insight1", "insight2"],\n                "sentiment": "positive/negative/neutral",\n                "action_items": ["item1", "item2"],\n                "pain_points": ["point1", "point2"]
            }}"""),
            ("human", "{chunk}")
        ])
    
    async def _generate_tags(self, chunk: str) -> dict:
        """Generate tags and insights for a chunk using LLM."""
        try:
            logger.info(f"Calling LLM with chunk: {chunk!r}")
            response = await self.llm.ainvoke(
                self.tagging_prompt.format_messages(chunk=chunk)
            )
            logger.info(f"LLM full response object: {response!r}")
            logger.info(f"LLM raw response content: {getattr(response, 'content', None)!r}")
            
            # Try to parse as JSON
            try:
                tags = json.loads(getattr(response, 'content', ''))
            except Exception as e:
                logger.error(f"Failed to parse LLM response as JSON: {getattr(response, 'content', None)!r}")
                logger.error(traceback.format_exc())
                raise
            
            # Convert lists to comma-separated strings for ChromaDB
            return {
                "themes": ", ".join(tags.get("themes", [])),
                "insights": ", ".join(tags.get("insights", [])),
                "sentiment": tags.get("sentiment", "neutral"),
                "action_items": ", ".join(tags.get("action_items", [])),
                "pain_points": ", ".join(tags.get("pain_points", []))
            }
        except Exception as e:
            logger.error(f"Error generating tags: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "themes": "",
                "insights": "",
                "sentiment": "neutral",
                "action_items": "",
                "pain_points": ""
            }
    
    async def process_transcript(self, transcript: List[Dict[str, Any]]) -> None:
        """Process a transcript and store it in ChromaDB with tags."""
        try:
            # Extract messages from transcript
            messages = [msg["content"] for msg in transcript if "content" in msg]
            text = "\n".join(messages)
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                # Generate tags for the chunk
                tags = await self._generate_tags(chunk)
                
                # Add chunk to ChromaDB with metadata
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "chunk_id": i,
                        "session_id": transcript[0].get("session_id", "unknown"),
                        **tags
                    }],
                    ids=[f"chunk_{i}"]
                )
            
            logger.info(f"Successfully processed transcript with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            raise
    
    def search_transcript(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search the transcript collection."""
        try:
            # Perform the search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching transcript: {str(e)}")
            return []

async def main():
    # Example usage
    processor = TranscriptProcessor()
    
    # Sample transcript
    test_transcript = [
        {
            "session_id": "test_123",
            "content": "I'm really excited about the new features we're planning to implement.",
            "role": "user",
            "timestamp": "2024-03-20T10:00:00Z"
        },
        {
            "session_id": "test_123",
            "content": "However, we need to be careful about the timeline and resource allocation.",
            "role": "assistant",
            "timestamp": "2024-03-20T10:01:00Z"
        }
    ]
    
    # Process transcript
    await processor.process_transcript(test_transcript)
    
    # Test search with sentiment filter
    results = processor.search_transcript(
        "features and timeline",
        where={"sentiment": "positive"}
    )
    
    print("\nSearch Results:")
    for result in results:
        print(f"\nText: {result['text']}")
        print(f"Metadata: {result['metadata']}")
        print(f"Distance: {result['distance']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 