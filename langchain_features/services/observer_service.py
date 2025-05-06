"""
Observer Service for AI-driven interview monitoring and analysis.
"""

import logging
import datetime
import uuid
from typing import Dict, List, Any, Optional

from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

logger = logging.getLogger(__name__)

class ObserverService:
    """Service for AI-driven monitoring and analysis of interview transcripts."""
    
    def __init__(self, openai_api_key: str = None, model: str = "gpt-4"):
        """
        Initialize the observer service.
        
        Args:
            openai_api_key: OpenAI API key
            model: The model to use for analysis (default: gpt-4)
        """
        self.openai_api_key = openai_api_key
        self.model_name = model
        self.llm = ChatOpenAI(temperature=0.2, model=model, openai_api_key=openai_api_key)
        
        # Initialize observer state storage
        self.observer_states = {}
        
        # Set up the note-taking prompt
        self.note_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                """You are an AI research observer analyzing user interviews in real-time.
                Analyze the provided transcript segment and generate:
                1. A brief, insightful note (1-2 sentences) summarizing the key point
                2. 1-3 semantic tags that categorize this segment (e.g., pain points, user needs, emotions)
                3. A mood estimate on a scale of -10 to +10, where:
                   - Negative numbers (-10 to -1) represent negative emotions (frustration, confusion, etc.)
                   - 0 represents neutral
                   - Positive numbers (1 to 10) represent positive emotions (excitement, satisfaction, etc.)
                
                Format your response exactly as follows (include all sections):
                NOTE: Your insightful summary note here
                TAGS: tag1, tag2, tag3
                MOOD: [number]
                """
            ),
            HumanMessagePromptTemplate.from_template(
                """Analyze this interview segment:
                
                SPEAKER: {speaker}
                MESSAGE: {message}
                
                Previous context (if available):
                {context}
                """
            )
        ])
        
        # Set up the note-taking chain
        self.note_chain = LLMChain(llm=self.llm, prompt=self.note_prompt)
    
    def get_observer_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current observer state for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The observer state
        """
        if session_id not in self.observer_states:
            self.observer_states[session_id] = {
                'tags': [],
                'mood_timeline': [],
                'notes': [],
                'last_update': datetime.datetime.now().isoformat(),
                'session_id': session_id
            }
        
        return self.observer_states[session_id]
    
    def analyze_message(self, session_id: str, message: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze a new message and update the observer state.
        
        Args:
            session_id: The session ID
            message: The message to analyze
            context: Previous messages for context (optional)
            
        Returns:
            The updated observer data for this message
        """
        try:
            # Get current state
            state = self.get_observer_state(session_id)
            
            # Format context if available
            context_text = ""
            if context and len(context) > 0:
                for ctx_msg in context[-3:]:  # Use the last 3 messages for context
                    speaker = "Interviewer" if ctx_msg.get('role') == 'assistant' else "Participant"
                    context_text += f"{speaker}: {ctx_msg.get('content', '')}\n"
            
            # Extract message data
            speaker = "Interviewer" if message.get('role') == 'assistant' else "Participant"
            message_text = message.get('content', '')
            
            # Run the analysis
            result = self.note_chain.run(
                speaker=speaker,
                message=message_text,
                context=context_text
            )
            
            # Parse the result
            note = ""
            tags = []
            mood = 0
            
            for line in result.strip().split("\n"):
                if line.startswith("NOTE:"):
                    note = line[5:].strip()
                elif line.startswith("TAGS:"):
                    tags_text = line[5:].strip()
                    tags = [tag.strip() for tag in tags_text.split(",")]
                elif line.startswith("MOOD:"):
                    try:
                        mood_text = line[5:].strip()
                        # Extract number from brackets if present
                        if '[' in mood_text and ']' in mood_text:
                            mood = int(mood_text.split('[')[1].split(']')[0])
                        else:
                            mood = int(mood_text)
                    except ValueError:
                        mood = 0
            
            # Create observation data
            observation = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'message_id': message.get('id', str(uuid.uuid4())),
                'note': note,
                'tags': tags,
                'mood': mood,
                'speaker': speaker
            }
            
            # Update state
            state['notes'].append(observation)
            
            # Add new tags to the global tag list if they don't exist
            for tag in tags:
                if tag not in state['tags']:
                    state['tags'].append(tag)
            
            # Add to mood timeline
            state['mood_timeline'].append({
                'timestamp': observation['timestamp'],
                'mood': mood,
                'message_id': observation['message_id']
            })
            
            state['last_update'] = datetime.datetime.now().isoformat()
            
            return observation
        except Exception as e:
            logger.error(f"Error analyzing message: {str(e)}")
            return {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'message_id': message.get('id', str(uuid.uuid4())),
                'note': f"Error analyzing message: {str(e)}",
                'tags': ["error"],
                'mood': 0,
                'speaker': "System"
            }
    
    def generate_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a summary of the observations for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            A summary of the observations
        """
        try:
            state = self.get_observer_state(session_id)
            
            # Create a prompt for summarizing
            summary_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    """You are an AI research observer analyzing user interviews.
                    Create a concise summary of the interview based on the AI observer notes provided.
                    
                    Focus on:
                    1. Key themes and patterns
                    2. Important insights
                    3. Notable participant emotions/reactions
                    4. Primary user needs and pain points identified
                    
                    Format your response in clear paragraphs with section headings.
                    """
                ),
                HumanMessagePromptTemplate.from_template(
                    """Here are the AI observer notes from the interview:
                    
                    {notes}
                    
                    Most frequent tags: {top_tags}
                    
                    Provide a concise, insightful summary.
                    """
                )
            ])
            
            # Format notes
            notes_text = ""
            for note in state['notes']:
                notes_text += f"- {note['note']} [Tags: {', '.join(note['tags'])}]\n"
            
            # Get top tags (most frequent)
            tag_counts = {}
            for note in state['notes']:
                for tag in note['tags']:
                    if tag in tag_counts:
                        tag_counts[tag] += 1
                    else:
                        tag_counts[tag] = 1
            
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tags_text = ", ".join([f"{tag} ({count})" for tag, count in top_tags])
            
            # Run the summary chain
            summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
            summary = summary_chain.run(
                notes=notes_text,
                top_tags=top_tags_text
            )
            
            return {
                'summary': summary,
                'top_tags': [tag for tag, _ in top_tags],
                'mood_analysis': self._analyze_mood_timeline(state['mood_timeline']),
                'generated_at': datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'top_tags': [],
                'mood_analysis': "Unable to analyze mood",
                'generated_at': datetime.datetime.now().isoformat()
            }
    
    def _analyze_mood_timeline(self, mood_timeline: List[Dict[str, Any]]) -> str:
        """
        Analyze the mood timeline and return a textual summary.
        
        Args:
            mood_timeline: The mood timeline to analyze
            
        Returns:
            A textual summary of the mood timeline
        """
        if not mood_timeline:
            return "No mood data available"
        
        moods = [point['mood'] for point in mood_timeline]
        avg_mood = sum(moods) / len(moods)
        min_mood = min(moods)
        max_mood = max(moods)
        
        # Determine trend (rising, falling, stable)
        if len(moods) < 2:
            trend = "insufficient data for trend analysis"
        else:
            first_half = moods[:len(moods)//2]
            second_half = moods[len(moods)//2:]
            
            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg + 1:
                trend = "rising (improving)"
            elif second_avg < first_avg - 1:
                trend = "falling (deteriorating)"
            else:
                trend = "stable"
        
        # Categorize overall mood
        if avg_mood > 5:
            mood_category = "very positive"
        elif avg_mood > 2:
            mood_category = "positive"
        elif avg_mood > -2:
            mood_category = "neutral"
        elif avg_mood > -5:
            mood_category = "negative"
        else:
            mood_category = "very negative"
        
        return f"Overall mood: {mood_category} (avg: {avg_mood:.1f}, range: {min_mood} to {max_mood}). Trend: {trend}." 