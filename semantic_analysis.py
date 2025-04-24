from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import json
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    def __init__(self):
        """Initialize semantic analysis models and vector store."""
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            
            # Initialize emotion detection models
            self.emotion_model = pipeline(
                "text-classification",
                model="bhadresh-savani/bert-base-go-emotion",
                return_all_scores=True
            )
            
            # Initialize OpenAI client for theme extraction
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Initialize Qdrant vector store
            self.qdrant = QdrantClient(":memory:")  # In-memory for development
            self.collection_name = "interview_chunks"
            
            # Create collection
            self.qdrant.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,  # MiniLM-L6-v2 embedding size
                    distance=models.Distance.COSINE
                )
            )
            
            logger.info("Semantic analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing semantic analyzer: {str(e)}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a piece of text."""
        try:
            return self.embedding_model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return [0.0] * 384  # Return zero vector as fallback

    def analyze_chunk(self, text: str) -> Dict[str, Any]:
        """Analyze a chunk of text for emotions and semantic meaning."""
        try:
            # Get emotions
            emotions = self.emotion_model(text)[0]
            primary_emotion = max(emotions, key=lambda x: x['score'])
            
            # Extract themes and insights using OpenAI
            themes_response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a research analysis assistant that extracts themes and insights from interview text. You MUST respond with ONLY valid JSON, no other text."},
                    {"role": "user", "content": f"""Analyze this interview text and extract themes and insights.

Text: {text}

Respond with ONLY this exact JSON structure, no other text:
{{
    "themes": ["theme1", "theme2", "theme3"],
    "insight_tags": ["insight1", "insight2", "insight3"],
    "emotion_intensity": 3
}}"""}
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={ "type": "json_object" }
            )
            
            try:
                analysis = json.loads(themes_response.choices[0].message.content)
                
                # Validate expected fields are present
                if not all(k in analysis for k in ["themes", "insight_tags", "emotion_intensity"]):
                    logging.error(f"Missing required fields in OpenAI response: {analysis}")
                    raise ValueError("Invalid response structure")
                    
                # Ensure lists are not empty
                if not analysis["themes"] or not analysis["insight_tags"]:
                    logging.error(f"Empty themes or insights in response: {analysis}")
                    raise ValueError("Empty themes or insights")
                    
                # Validate emotion_intensity is in range 1-5
                if not (1 <= analysis["emotion_intensity"] <= 5):
                    logging.error(f"Invalid emotion intensity: {analysis['emotion_intensity']}")
                    raise ValueError("Invalid emotion intensity")
                    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logging.error(f"Error parsing OpenAI response: {e}")
                logging.error(f"Raw response: {themes_response.choices[0].message.content}")
                analysis = {
                    "themes": ["unclear"],
                    "insight_tags": ["needs review"],
                    "emotion_intensity": 3
                }
            
            return {
                'text': text,
                'emotion': primary_emotion['label'],
                'emotion_intensity': analysis.get('emotion_intensity', 3),
                'themes': analysis.get('themes', []),
                'insight_tags': analysis.get('insight_tags', []),
                'sentiment_score': primary_emotion['score']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing chunk: {str(e)}")
            return {
                'text': text,
                'emotion': 'neutral',
                'emotion_intensity': 3,
                'themes': [],
                'insight_tags': [],
                'sentiment_score': 0.5
            }

    def add_chunk(self, chunk_id: str, text: str, metadata: Optional[Dict] = None) -> bool:
        """Add a chunk to the vector store."""
        try:
            # Analyze chunk
            analysis = self.analyze_chunk(text)
            
            # Combine with additional metadata
            if metadata:
                analysis['metadata'] = metadata
            
            # Add to vector store
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=chunk_id,
                        vector=self.get_embedding(text),
                        payload={
                            "text": text,
                            "metadata": analysis
                        }
                    )
                ]
            )
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunk: {str(e)}")
            return False

    def search(self, query: str, k: int = 5, emotion_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar chunks with optional emotion filtering."""
        try:
            # Encode query
            query_vector = self.embedding_model.encode(query)
            
            # Prepare search filters
            search_params = models.SearchParams(hnsw_ef=128)
            if emotion_filter:
                filter_query = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.emotion",
                            match=models.MatchValue(value=emotion_filter)
                        )
                    ]
                )
            else:
                filter_query = None
            
            # Search
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=k,
                search_params=search_params,
                query_filter=filter_query
            )
            
            # Format results
            return [
                {
                    "id": str(hit.id),
                    "text": hit.payload["text"],
                    "metadata": hit.payload["metadata"],
                    "score": hit.score
                }
                for hit in results
            ]
            
        except Exception as e:
            logger.error(f"Error searching chunks: {str(e)}")
            return []

    def rerank_results(self, query: str, results: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """Rerank search results using cross-encoder."""
        try:
            from sentence_transformers import CrossEncoder
            
            # Initialize cross-encoder
            cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # Prepare pairs for reranking
            pairs = [(query, result["text"]) for result in results]
            
            # Get cross-encoder scores
            cross_scores = cross_encoder.predict(pairs)
            
            # Combine results with new scores
            for result, cross_score in zip(results, cross_scores):
                result["cross_score"] = float(cross_score)
            
            # Sort by cross-encoder score
            reranked = sorted(results, key=lambda x: x["cross_score"], reverse=True)
            
            return reranked[:k]
            
        except Exception as e:
            logger.error(f"Error reranking results: {str(e)}")
            return results[:k] 