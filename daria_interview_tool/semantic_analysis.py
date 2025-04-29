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
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def split_transcript_safe(transcript, max_length=400):
    """
    Split a transcript into safe-sized chunks that won't exceed model token limits.
    
    Args:
        transcript (str): The text to split
        max_length (int): Maximum number of words per chunk (default: 400)
        
    Returns:
        List[str]: List of text chunks, each below the maximum length
    """
    logger.info(f"Splitting transcript into chunks (max length: {max_length} words)")
    
    # Split by speaker turns if transcript contains speaker markers
    if '[' in transcript and ']' in transcript:
        # Try to split by speaker turns first
        speaker_pattern = r'\[.*?\]'
        turns = re.split(f'({speaker_pattern}\\s+)', transcript)
        
        # Group speaker with their text
        i = 0
        grouped_turns = []
        while i < len(turns) - 1:
            if re.match(speaker_pattern, turns[i]):
                # Speaker marker is in this element
                grouped_turns.append(turns[i] + (turns[i+1] if i+1 < len(turns) else ""))
                i += 2
            else:
                # No speaker marker, just add the text
                grouped_turns.append(turns[i])
                i += 1
        
        # Add any remaining turn
        if i < len(turns):
            grouped_turns.append(turns[i])
            
        chunks = []
        current_chunk = []
        current_length = 0
        
        for turn in grouped_turns:
            if not turn.strip():
                continue
                
            turn_length = len(turn.split())
            
            # If this turn alone exceeds max length, split it further
            if turn_length > max_length:
                # Process the current chunk if it's not empty
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long turn by sentences
                sentences = re.split(r'(?<=[.!?]) +', turn)
                sub_chunk = []
                sub_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence.split())
                    
                    if sub_length + sentence_length <= max_length:
                        sub_chunk.append(sentence)
                        sub_length += sentence_length
                    else:
                        if sub_chunk:  # Add accumulated sentences as a chunk
                            chunks.append(' '.join(sub_chunk))
                            sub_chunk = [sentence]
                            sub_length = sentence_length
                        else:  # Single sentence is too long, split by words
                            words = sentence.split()
                            for i in range(0, len(words), max_length):
                                word_chunk = ' '.join(words[i:i+max_length])
                                if word_chunk:
                                    chunks.append(word_chunk)
                
                # Add any remaining sub-chunk
                if sub_chunk:
                    chunks.append(' '.join(sub_chunk))
            
            # If adding this turn would exceed max length, create a new chunk
            elif current_length + turn_length > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [turn]
                current_length = turn_length
            else:
                current_chunk.append(turn)
                current_length += turn_length
        
        # Add the last chunk if there's anything left
        if current_chunk:
            chunks.append(' '.join(current_chunk))
    
    else:
        # No speaker markers, just split by paragraphs and sentences
        paragraphs = transcript.split('\n\n')
        chunks = []
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            para_length = len(para.split())
            
            # If paragraph is too long, split it
            if para_length > max_length:
                # Split by sentences
                sentences = re.split(r'(?<=[.!?]) +', para)
                current = []
                current_length = 0
                
                for sent in sentences:
                    sent_length = len(sent.split())
                    
                    if current_length + sent_length <= max_length:
                        current.append(sent)
                        current_length += sent_length
                    else:
                        if current:  # Add accumulated sentences as a chunk
                            chunks.append(' '.join(current))
                            current = [sent]
                            current_length = sent_length
                        else:  # Single sentence is too long, split by words
                            words = sent.split()
                            for i in range(0, len(words), max_length):
                                word_chunk = ' '.join(words[i:i+max_length])
                                if word_chunk:
                                    chunks.append(word_chunk)
                
                # Add any remaining sentences
                if current:
                    chunks.append(' '.join(current))
            else:
                chunks.append(para)
    
    # Remove empty chunks and log
    result = [c.strip() for c in chunks if c.strip()]
    logger.info(f"Split transcript into {len(result)} chunks")
    
    return result

class SemanticAnalyzer:
    def __init__(self):
        """Initialize the semantic analyzer with required models."""
        logger.info("Initializing SemanticAnalyzer...")
        
        # Initialize sentence transformer
        try:
            self.sentence_transformer = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("Loaded sentence transformer model")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {str(e)}")
            raise
        
        # Initialize emotion classifier with error handling
        try:
            self.emotion_classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                return_all_scores=True
            )
            logger.info("Loaded emotion model successfully")
        except Exception as e:
            logger.error(f"Failed to load emotion model: {str(e)}")
            # Initialize with a simple fallback
            self.emotion_classifier = None
            logger.info("Using fallback emotion analysis")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text for semantic meaning and emotions."""
        try:
            # Get embeddings
            embeddings = self.sentence_transformer.encode(text)
            
            # Get emotions if classifier is available
            emotions = []
            if self.emotion_classifier:
                try:
                    emotion_results = self.emotion_classifier(text)
                    emotions = [{"label": r["label"], "score": r["score"]} for r in emotion_results[0]]
                except Exception as e:
                    logger.warning(f"Emotion analysis failed: {str(e)}")
                    emotions = []
            
            return {
                "embeddings": embeddings.tolist(),
                "emotions": emotions
            }
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {
                "embeddings": [],
                "emotions": []
            }
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        try:
            emb1 = self.sentence_transformer.encode(text1)
            emb2 = self.sentence_transformer.encode(text2)
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.0

    def get_embeddings(self, text):
        """Get embeddings for a piece of text."""
        try:
            return self.sentence_transformer.encode(text)
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            return None

    def analyze_emotions(self, text):
        """Analyze emotions in text."""
        if not self.emotion_classifier:
            logger.warning("Emotion model not available")
            return {'label': 'neutral', 'score': 0.0}
            
        # Handle empty or whitespace-only text
        if not text or not text.strip():
            return {'label': 'neutral', 'score': 0.0}
            
        try:
            result = self.emotion_classifier(text)
            if result and len(result) > 0:
                # The model returns a list with a single dict containing label and score
                return result[0]  # Returns {'label': 'emotion', 'score': 0.123}
            return {'label': 'neutral', 'score': 0.0}
        except Exception as e:
            logger.error(f"Error analyzing emotions: {str(e)}")
            return {'label': 'neutral', 'score': 0.0}

    def analyze_chunk(self, text: str) -> Dict[str, Any]:
        """Analyze a chunk of text for emotions and semantic meaning."""
        # Initialize default values
        emotion_result = {'label': 'neutral', 'score': 0.0}
        analysis = {
            "themes": [],
            "insight_tags": [],
            "emotion_intensity": 3
        }
        
        try:
            # Extract participant's response if present
            if '[Participant]' in text:
                parts = text.split('[Participant]')
                if len(parts) > 1:
                    # Use the participant's response for emotion analysis
                    participant_text = parts[1]
                    # Remove any remaining speaker markers
                    participant_text = re.sub(r'\[[^\]]+\]', '', participant_text).strip()
                    emotion_result = self.analyze_emotions(participant_text)
                else:
                    emotion_result = self.analyze_emotions(text)
            else:
                emotion_result = self.analyze_emotions(text)
                
        except Exception as e:
            logger.error(f"Error in emotion analysis: {str(e)}")
            # Continue with theme analysis even if emotion fails
            
        # Extract themes and insights using OpenAI (use full text including context)
        try:
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
                    logger.error(f"Missing required fields in OpenAI response: {analysis}")
                    raise ValueError("Invalid response structure")
                    
                # Ensure lists are not empty
                if not analysis["themes"] or not analysis["insight_tags"]:
                    logger.error(f"Empty themes or insights in response: {analysis}")
                    raise ValueError("Empty themes or insights")
                    
                # Validate emotion_intensity is in range 1-5
                if not (1 <= analysis["emotion_intensity"] <= 5):
                    logger.error(f"Invalid emotion intensity: {analysis['emotion_intensity']}")
                    raise ValueError("Invalid emotion intensity")
                    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"Error parsing OpenAI response: {e}")
                logger.error(f"Raw response: {themes_response.choices[0].message.content}")
                analysis = {
                    "themes": ["unclear"],
                    "insight_tags": ["needs review"],
                    "emotion_intensity": 3
                }
        except Exception as e:
            logger.error(f"Error in theme analysis: {str(e)}")
            # Keep default analysis values
            
        return {
            'text': text,
            'emotion': emotion_result['label'],
            'emotion_intensity': analysis.get('emotion_intensity', 3),
            'themes': analysis.get('themes', []),
            'insight_tags': analysis.get('insight_tags', []),
            'sentiment_score': emotion_result['score']
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
                        vector=self.get_embeddings(text),
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
            query_vector = self.get_embeddings(query)
            
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