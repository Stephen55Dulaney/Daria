import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid

class ProcessedInterviewStore:
    def __init__(self, base_dir: str = "interviews/processed"):
        self.base_dir = base_dir
        self.default_project_name = "Daria Research of Researchers"
        os.makedirs(base_dir, exist_ok=True)

    def _get_interview_path(self, interview_id: str) -> str:
        return os.path.join(self.base_dir, f"{interview_id}.json")

    def save_interview(self, interview_id: str, data: Dict) -> None:
        """Save processed interview data to JSON file."""
        file_path = self._get_interview_path(interview_id)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_interview(self, interview_id: str) -> Optional[Dict]:
        """Load processed interview data from JSON file."""
        file_path = self._get_interview_path(interview_id)
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def semantic_search(self, query: str, k: int = 10) -> List[Dict]:
        """Search through processed interviews using semantic similarity."""
        results = []
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]  # Remove .json extension
            interview_data = self.load_interview(interview_id)
            
            if not interview_data or 'chunks' not in interview_data:
                continue
                
            for chunk in interview_data['chunks']:
                # For now, use text similarity as a placeholder
                # This should be replaced with actual semantic similarity
                score = self._text_similarity(chunk.get('content', ''), query)
                if score > 0:
                    results.append({
                        'interview_id': interview_id,
                        'chunk_id': chunk.get('id'),
                        'project_name': self.default_project_name,
                        'content': chunk.get('content') or chunk.get('text') or chunk.get('combined_text', ''),
                        'timestamp': chunk.get('timestamp'),
                        'score': score,
                        'metadata': {
                            'emotion': chunk.get('emotion', 'neutral'),
                            'emotion_intensity': chunk.get('emotion_intensity', 0.5),
                            'themes': chunk.get('themes', []),
                            'insight_tags': chunk.get('insight_tags', []),
                            'related_feature': chunk.get('related_feature')
                        }
                    })
        
        # Sort by score and limit results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]

    def _normalize_emotion_intensity(self, intensity):
        """Normalize emotion intensity to a value between 0 and 1."""
        if intensity is None:
            return 0.5
        try:
            # Convert to float if it's a string
            intensity = float(intensity)
            # If it's already between 0 and 1, return as is
            if 0 <= intensity <= 1:
                return intensity
            # If it's on a different scale (e.g. 0-3), normalize it
            if intensity > 1:
                return min(intensity / 3, 1.0)
            return max(0.0, intensity)
        except (ValueError, TypeError):
            return 0.5

    def _get_interviewee_name(self, interview_data: Dict) -> str:
        """Extract interviewee name from interview data."""
        # Try different possible locations for the name
        name = (
            interview_data.get('interviewee', {}).get('name') or
            interview_data.get('participant', {}).get('name') or
            interview_data.get('participant_name') or
            interview_data.get('transcript_name', 'Unknown Participant')
        )
        return name

    def _create_search_result(self, interview_data: Dict, chunk: Dict, similarity: float = 1.0) -> Dict:
        """Create a standardized search result dictionary."""
        return {
            'interview_id': interview_data.get('id'),
            'chunk_id': chunk.get('id') or str(uuid.uuid4()),
            'project_name': self.default_project_name,
            'content': chunk.get('content') or chunk.get('text') or chunk.get('combined_text', ''),
            'timestamp': chunk.get('timestamp') or datetime.now().isoformat(),
            'interviewee_name': self._get_interviewee_name(interview_data),
            'similarity': similarity,
            'metadata': {
                'emotion': chunk.get('emotion', 'neutral'),
                'emotion_intensity': self._normalize_emotion_intensity(chunk.get('emotion_intensity')),
                'themes': chunk.get('themes', []),
                'insight_tags': chunk.get('insight_tags', []),
                'related_feature': chunk.get('related_feature')
            }
        }

    def emotion_search(self, emotion: str, k: int = 10) -> List[Dict]:
        """Search through processed interviews for chunks with specific emotions."""
        results = []
        emotion_lower = emotion.lower()
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]  # Remove .json extension
            interview_data = self.load_interview(interview_id)
            
            if not interview_data or 'chunks' not in interview_data:
                continue
                
            for chunk in interview_data.get('chunks', []):
                # Look for emotion in both the direct emotion field and in analysis
                chunk_emotion = (
                    chunk.get('emotion', '') or 
                    chunk.get('analysis', {}).get('emotion', '') or 
                    chunk.get('metadata', {}).get('emotion', '')
                ).lower()
                
                # Get emotion intensity from various possible locations
                emotion_intensity = (
                    chunk.get('emotion_intensity') or 
                    chunk.get('analysis', {}).get('emotion_intensity') or 
                    chunk.get('metadata', {}).get('emotion_intensity') or 
                    0.5
                )
                
                # Normalize emotion intensity
                normalized_intensity = self._normalize_emotion_intensity(emotion_intensity)
                
                if chunk_emotion == emotion_lower:
                    results.append(self._create_search_result(
                        interview_data=interview_data,
                        chunk=chunk,
                        similarity=normalized_intensity
                    ))
        
        # Sort by emotion intensity and limit results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:k]

    def insight_tag_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for chunks with matching insight tags."""
        results = []
        query = query.lower() if query else ''
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]  # Remove .json extension
            interview = self.load_interview(interview_id)
            
            if not interview:
                continue
                
            for chunk in interview.get('chunks', []):
                # Look for insight tags in various possible locations, handling None values
                all_tags = []
                
                # Collect tags from all possible locations
                chunk_tags = chunk.get('insight_tags', [])
                if isinstance(chunk_tags, list):
                    all_tags.extend(chunk_tags)
                
                analysis_tags = chunk.get('analysis', {}).get('insight_tags', [])
                if isinstance(analysis_tags, list):
                    all_tags.extend(analysis_tags)
                
                metadata_tags = chunk.get('metadata', {}).get('insight_tags', [])
                if isinstance(metadata_tags, list):
                    all_tags.extend(metadata_tags)
                
                # Convert all tags to lowercase for comparison
                insight_tags = [tag.lower() for tag in all_tags if tag]
                
                if query in insight_tags:
                    # Ensure all required fields have default values
                    results.append({
                        'interview_id': interview_id,
                        'chunk_id': chunk.get('id') or str(uuid.uuid4()),
                        'project_name': self.default_project_name,
                        'content': chunk.get('content') or chunk.get('text') or chunk.get('combined_text', ''),
                        'timestamp': chunk.get('timestamp') or datetime.now().isoformat(),
                        'metadata': {
                            'emotion': chunk.get('emotion', 'neutral'),
                            'emotion_intensity': float(chunk.get('emotion_intensity', 0.5)),
                            'themes': chunk.get('themes', []),
                            'insight_tags': insight_tags,
                            'related_feature': chunk.get('related_feature')
                        },
                        'similarity': 1.0  # Exact match
                    })
                    
        # Sort by timestamp (most recent first) and limit results
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results[:limit]

    def text_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search through processed interviews using basic text matching."""
        results = []
        query = query.lower() if query else ''
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]  # Remove .json extension
            interview_data = self.load_interview(interview_id)
            
            if not interview_data:
                continue
                
            for chunk in interview_data.get('chunks', []):
                # Get text content from various possible locations
                text = (
                    chunk.get('content') or 
                    chunk.get('text') or 
                    chunk.get('combined_text', '')
                ).lower()
                
                if query in text:
                    results.append(self._create_search_result(
                        interview_data=interview_data,
                        chunk=chunk
                    ))
        
        # Sort by timestamp (most recent first) and limit results
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results[:limit]

    def theme_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for chunks with matching themes."""
        results = []
        query = query.lower() if query else ''
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]  # Remove .json extension
            interview_data = self.load_interview(interview_id)
            
            if not interview_data:
                continue
                
            for chunk in interview_data.get('chunks', []):
                # Look for themes in various possible locations, handling None values
                all_themes = []
                
                # Collect themes from all possible locations
                chunk_themes = chunk.get('themes', [])
                if isinstance(chunk_themes, list):
                    all_themes.extend(chunk_themes)
                
                analysis_themes = chunk.get('analysis', {}).get('themes', [])
                if isinstance(analysis_themes, list):
                    all_themes.extend(analysis_themes)
                
                metadata_themes = chunk.get('metadata', {}).get('themes', [])
                if isinstance(metadata_themes, list):
                    all_themes.extend(metadata_themes)
                
                # Convert all themes to lowercase for comparison
                themes = [theme.lower() for theme in all_themes if theme]
                
                # Check if any theme contains the query
                if any(query in theme for theme in themes):
                    results.append(self._create_search_result(
                        interview_data=interview_data,
                        chunk=chunk
                    ))
                    
        # Sort by timestamp (most recent first) and limit results
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results[:limit]

    def search(self, query: str, search_type: str = 'text', limit: int = 10) -> List[Dict]:
        """Search through processed interviews based on the specified type."""
        if search_type == 'text':
            results = self.text_search(query, limit)
        elif search_type == 'semantic':
            results = self.semantic_search(query, limit)
        elif search_type == 'emotion':
            results = self.emotion_search(query, limit)
        elif search_type == 'insight':
            results = self.insight_tag_search(query, limit)
        else:
            raise ValueError(f"Invalid search type: {search_type}")

        # Add interview metadata to results
        for result in results:
            interview_id = result['interview_id']
            interview = self.load_interview(interview_id)
            if interview:
                result['interviewee_name'] = self._get_interviewee_name(interview)
                result['transcript_name'] = interview.get('metadata', {}).get('transcript_name', '')

        return results

    def _calculate_score(self, chunk: Dict, query: str, search_type: str) -> float:
        """Calculate similarity score based on search type."""
        if search_type == "text":
            return self._text_similarity(chunk.get('content', '') or chunk.get('text', ''), query)
        elif search_type == "semantic":
            return self._semantic_similarity(chunk, query)
        elif search_type == "emotion":
            return self._emotion_similarity(chunk, query)
        return 0.0

    def _text_similarity(self, text: str, query: str) -> float:
        """Simple text-based similarity."""
        if not text or not query:
            return 0.0
        text_lower = text.lower()
        query_lower = query.lower()
        if query_lower in text_lower:
            return 1.0
        return 0.0

    def _semantic_similarity(self, chunk: Dict, query: str) -> float:
        """Semantic similarity using pre-computed embeddings."""
        # For now, return text similarity. This can be enhanced with actual semantic search.
        return self._text_similarity(chunk.get('content', ''), query)

    def _emotion_similarity(self, chunk: Dict, query: str) -> float:
        """Emotion-based similarity."""
        chunk_emotion = chunk.get('emotion', '').lower()
        query_lower = query.lower()
        if chunk_emotion == query_lower:
            return 1.0
        return 0.0

    def list_interviews(self) -> List[Dict]:
        """List all processed interviews with basic metadata."""
        interviews = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith('.json'):
                interview_id = filename[:-5]
                data = self.load_interview(interview_id)
                if data:
                    interviews.append({
                        'id': interview_id,
                        'project_name': data.get('project_name'),
                        'created_at': data.get('created_at'),
                        'chunk_count': len(data.get('chunks', []))
                    })
        return interviews 