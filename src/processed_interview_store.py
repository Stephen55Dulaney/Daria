import json
import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
import uuid
from sentence_transformers import SentenceTransformer, util
import torch
import re

class ProcessedInterviewStore:
    def __init__(self, base_dir: str = "interviews/processed"):
        self.base_dir = base_dir
        self.default_project_name = "Daria Research of Researchers"
        self.model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
        self.emotion_mapping = {
            'frustration': {'frustration', 'annoyed', 'irritated', 'angry', 'upset'},
            'positive': {'joy', 'happiness', 'excited', 'satisfied', 'pleased', 'admiration'},
            'innovation': {'creative', 'innovative', 'novel', 'new idea', 'improvement'},
            'negative': {'sad', 'disappointed', 'unhappy', 'frustrated', 'confused'},
            'neutral': {'neutral', 'calm', 'balanced'}
        }
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
                data = json.load(f)
                data['_file_path'] = file_path  # Add file path to data
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _normalize_emotion(self, emotion: str) -> Set[str]:
        """Map an emotion to its normalized set of related emotions."""
        emotion = emotion.lower()
        for category, emotions in self.emotion_mapping.items():
            if emotion in emotions or emotion == category:
                return emotions
        return {emotion}

    def _extract_search_criteria(self, query: str) -> Dict:
        """Extract emotion and theme criteria from natural language query."""
        query = query.lower()
        criteria = {
            'emotions': set(),
            'themes': set(),
            'sentiment': None
        }
        
        # Check for emotion indicators
        if any(word in query for word in ['frustration', 'frustrated', 'annoying', 'annoyed']):
            criteria['emotions'].update(self.emotion_mapping['frustration'])
        if any(word in query for word in ['positive', 'happy', 'good', 'great']):
            criteria['emotions'].update(self.emotion_mapping['positive'])
        if any(word in query for word in ['negative', 'bad', 'poor', 'pain', 'painful']):
            criteria['emotions'].update(self.emotion_mapping['negative'])
            criteria['sentiment'] = 'negative'
        
        # Check for theme indicators
        if 'innovation' in query or 'innovative' in query:
            criteria['themes'].add('innovation')
        if 'team' in query:
            criteria['themes'].add('team dynamics')
        
        return criteria

    def semantic_search(self, query: str, k: int = 10) -> List[Dict]:
        """Enhanced semantic search with emotion and theme filtering."""
        results = []
        search_criteria = self._extract_search_criteria(query)
        
        # Encode the search query
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        
        for filename in os.listdir(self.base_dir):
            if not filename.endswith('.json'):
                continue
                
            interview_id = filename[:-5]
            interview_data = self.load_interview(interview_id)
            
            if not interview_data or 'chunks' not in interview_data:
                continue
                
            for chunk in interview_data['chunks']:
                content = chunk.get('content') or chunk.get('text') or chunk.get('combined_text', '')
                if not content:
                    continue

                # Get chunk embedding
                chunk_embedding = self.model.encode(content, convert_to_tensor=True)
                similarity = util.pytorch_cos_sim(query_embedding, chunk_embedding)[0][0].item()

                # Apply filters based on search criteria
                chunk_emotion = chunk.get('metadata', {}).get('emotion', '').lower()
                chunk_themes = {theme.lower() for theme in chunk.get('metadata', {}).get('themes', [])}
                
                # Check if chunk matches any of the search criteria
                emotion_match = (
                    not search_criteria['emotions'] or
                    any(emotion in self._normalize_emotion(chunk_emotion) 
                        for emotion in search_criteria['emotions'])
                )
                theme_match = (
                    not search_criteria['themes'] or
                    any(theme in chunk_themes for theme in search_criteria['themes'])
                )
                
                if similarity > 0.3 and (emotion_match or theme_match):
                    results.append(self._create_search_result(
                        interview_data=interview_data,
                        chunk=chunk,
                        similarity=similarity
                    ))
        
        # Sort by similarity score
        results.sort(key=lambda x: x['similarity'], reverse=True)
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
        """Extract interviewee name from interview data, prioritizing participant over researcher."""
        # Try different possible locations for the name, prioritizing participant
        name = (
            interview_data.get('metadata', {}).get('interviewee', {}).get('name') or  # Interviewee from metadata
            interview_data.get('interviewee', {}).get('name') or  # Direct interviewee name
            interview_data.get('metadata', {}).get('participant', {}).get('name') or  # Participant from metadata
            interview_data.get('participant', {}).get('name') or  # Direct participant name
            interview_data.get('participant_name') or  # Legacy participant name
            interview_data.get('metadata', {}).get('transcript_name') or  # Transcript name
            interview_data.get('metadata', {}).get('researcher', {}).get('name') or  # Researcher name as last resort
            ''  # Empty string if no name found
        )
        return name

    def _create_search_result(self, interview_data: Dict, chunk: Dict, similarity: float = 1.0) -> Dict:
        """Create a standardized search result dictionary."""
        # Extract interview_id from the chunk_id or from interview_data
        interview_id = (
            chunk.get('chunk_id', '').split('_')[0] or  # Try to get from chunk_id
            interview_data.get('interview_id') or  # Try direct interview_id
            interview_data.get('id')  # Try id field
        )
        
        # If no ID found, try to get it from the file path
        if not interview_id:
            file_path = interview_data.get('_file_path', '')  # We'll need to add this when loading the file
            if file_path:
                interview_id = os.path.splitext(os.path.basename(file_path))[0]
            else:
                interview_id = str(uuid.uuid4())  # Only generate UUID if absolutely necessary

        # Get timestamp from entries if available
        timestamp = None
        if 'entries' in chunk:
            # If multiple entries, use the first one's timestamp
            entries = chunk['entries']
            if entries and isinstance(entries, list) and len(entries) > 0:
                timestamp = entries[0].get('timestamp', '')
        
        # If no timestamp in entries, try other locations
        if not timestamp:
            timestamp = (
                chunk.get('timestamp', '') or  # Direct timestamp
                chunk.get('metadata', {}).get('timestamp', '') or  # Metadata timestamp
                interview_data.get('metadata', {}).get('date', '')  # Interview date as fallback
            )

        # Get all possible themes from various locations
        all_themes = []
        chunk_themes = chunk.get('themes', [])
        if isinstance(chunk_themes, list):
            all_themes.extend(chunk_themes)
        analysis_themes = chunk.get('analysis', {}).get('themes', [])
        if isinstance(analysis_themes, list):
            all_themes.extend(analysis_themes)
        metadata_themes = chunk.get('metadata', {}).get('themes', [])
        if isinstance(metadata_themes, list):
            all_themes.extend(metadata_themes)
        
        # Get all possible insight tags from various locations
        all_insight_tags = []
        chunk_tags = chunk.get('insight_tags', [])
        if isinstance(chunk_tags, list):
            all_insight_tags.extend(chunk_tags)
        analysis_tags = chunk.get('analysis', {}).get('insight_tags', [])
        if isinstance(analysis_tags, list):
            all_insight_tags.extend(analysis_tags)
        metadata_tags = chunk.get('metadata', {}).get('insight_tags', [])
        if isinstance(metadata_tags, list):
            all_insight_tags.extend(metadata_tags)

        # Get emotion data from various possible locations
        emotion = (
            chunk.get('emotion') or 
            chunk.get('analysis', {}).get('emotion') or 
            chunk.get('metadata', {}).get('emotion') or 
            'neutral'
        )
        
        emotion_intensity = (
            chunk.get('emotion_intensity') or 
            chunk.get('analysis', {}).get('emotion_intensity') or 
            chunk.get('metadata', {}).get('emotion_intensity') or 
            0.5
        )

        # Get content from entries if available
        content = None
        if 'entries' in chunk:
            entries = chunk['entries']
            if entries and isinstance(entries, list):
                # Combine text from all entries
                content = ' '.join(entry.get('text', '') for entry in entries if entry.get('text'))

        # If no content from entries, try other locations
        if not content:
            content = chunk.get('content') or chunk.get('text') or chunk.get('combined_text', '')

        return {
            'interview_id': interview_id,
            'chunk_id': chunk.get('chunk_id', str(uuid.uuid4())),
            'project_name': interview_data.get('project_name', self.default_project_name),
            'content': content,
            'similarity': similarity,
            'timestamp': timestamp,
            'interviewee_name': self._get_interviewee_name(interview_data),
            'transcript_name': interview_data.get('transcript_name', ''),
            'metadata': {
                'emotion': emotion,
                'emotion_intensity': self._normalize_emotion_intensity(emotion_intensity),
                'themes': list(set(all_themes)),
                'insight_tags': list(set(all_insight_tags)),
                'related_feature': chunk.get('metadata', {}).get('related_feature')
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
        """Enhanced search method that handles natural language queries."""
        if search_type == 'semantic':
            results = self.semantic_search(query, limit)
        elif search_type == 'emotion':
            results = self.emotion_search(query, limit)
        elif search_type == 'theme':
            results = self.theme_search(query, limit)
        elif search_type == 'insight':
            results = self.insight_tag_search(query, limit)
        elif search_type == 'text':
            results = self.text_search(query, limit)
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