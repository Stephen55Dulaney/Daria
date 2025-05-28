import json
from transcript_processor import TranscriptProcessor
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_transcript_processing():
    """Test the transcript processing and search functionality."""
    try:
        # Initialize processor
        processor = TranscriptProcessor()
        # Clear the collection for a clean test
        processor.collection.delete(where={"chunk_id": {"$gte": 0}})
        
        # Create a sample transcript
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
        
        # Process the transcript
        logger.info("Processing test transcript...")
        await processor.process_transcript(test_transcript)
        
        # Test basic search
        logger.info("\nTesting basic search...")
        results = processor.search_transcript("features and timeline")
        print("\nBasic Search Results:")
        for result in results:
            print(f"\nText: {result['text']}")
            print(f"Metadata: {result['metadata']}")
            print(f"Distance: {result['distance']}")
        
        # Test search with sentiment filter
        logger.info("\nTesting search with sentiment filter...")
        results = processor.search_transcript(
            "features and timeline",
            where={"sentiment": "positive"}
        )
        print("\nFiltered Search Results:")
        for result in results:
            print(f"\nText: {result['text']}")
            print(f"Metadata: {result['metadata']}")
            print(f"Distance: {result['distance']}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_transcript_processing()) 