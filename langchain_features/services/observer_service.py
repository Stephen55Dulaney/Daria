"""
Observer Service for AI-driven interview monitoring and analysis.
"""

import logging
import datetime
import uuid
from typing import Dict, List, Any, Optional

try:
    from langchain_community.chat_models import ChatOpenAI
except ImportError:
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
                4. Insight types (include only if relevant):
                   - KEY_POINT: If this appears to be a significant finding or insight
                   - PATTERN: If this relates to a recurring theme in the interview
                   - ACTIONABLE: If this suggests a specific product/service improvement
                   - QUESTION: If this raises a question that should be investigated further
                   - CONTRADICTION: If this contradicts something stated earlier

                Format your response exactly as follows (include all sections):
                NOTE: Your insightful summary note here
                TAGS: tag1, tag2, tag3
                MOOD: [number]
                INSIGHT_TYPE: TYPE1, TYPE2 (omit if none apply)
                """
            ),
            HumanMessagePromptTemplate.from_template(
                """Analyze this interview segment:
                
                SPEAKER: {speaker}
                MESSAGE: {message}
                
                Previous context (if available):
                {context}
                
                Interview progress: {progress}
                Current topics: {current_topics}
                """
            )
        ])
        
        # Set up the insights extraction prompt
        self.insights_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                """You are an AI research observer analyzing user interviews in real-time.
                Based on the accumulated observations so far, identify 1-3 key insights
                that would be valuable for the researcher to know at this moment.
                
                An insight should be:
                1. Specific and actionable
                2. Related to user needs, pain points, or behaviors
                3. Phrased as a clear, concise statement
                
                Format your response exactly as follows:
                INSIGHT: Your first insight statement
                IMPORTANCE: [HIGH|MEDIUM|LOW]
                EVIDENCE: Brief supporting evidence from the transcript
                
                INSIGHT: Your second insight statement (if applicable)
                IMPORTANCE: [HIGH|MEDIUM|LOW]
                EVIDENCE: Brief supporting evidence from the transcript
                
                INSIGHT: Your third insight statement (if applicable)
                IMPORTANCE: [HIGH|MEDIUM|LOW]
                EVIDENCE: Brief supporting evidence from the transcript
                """
            ),
            HumanMessagePromptTemplate.from_template(
                """Here are the observer notes from the interview so far:
                
                {notes}
                
                Current topics: {topics}
                
                Extract 1-3 key insights that would be valuable for the researcher to know right now.
                """
            )
        ])
        
        # Set up question suggestions prompt
        self.questions_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                """You are an AI research assistant helping researchers conduct effective interviews.
                Based on the conversation so far, suggest 2-3 follow-up questions that would help
                deepen understanding or explore important areas that haven't been addressed.
                
                Your questions should be:
                1. Open-ended (not yes/no questions)
                2. Neutral (not leading or biased)
                3. Relevant to topics already discussed or logical next steps
                4. Designed to elicit rich, detailed responses
                
                Format your response exactly as follows (numbered list):
                1. Your first suggested question
                2. Your second suggested question 
                3. Your third suggested question (if applicable)
                """
            ),
            HumanMessagePromptTemplate.from_template(
                """Here is the current interview context:
                
                {context}
                
                Current topics being discussed: {topics}
                
                Suggest 2-3 follow-up questions to deepen understanding:
                """
            )
        ])
        
        # Set up the note-taking chain
        self.note_chain = LLMChain(llm=self.llm, prompt=self.note_prompt)
        self.insights_chain = LLMChain(llm=self.llm, prompt=self.insights_prompt)
        self.questions_chain = LLMChain(llm=self.llm, prompt=self.questions_prompt)
    
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
                'insights': [],
                'suggested_questions': [],
                'patterns': [],
                'key_points': [],
                'message_count': 0,
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
            
            # Update message count
            state['message_count'] += 1
            
            # Format context if available
            context_text = ""
            if context and len(context) > 0:
                for ctx_msg in context[-3:]:  # Use the last 3 messages for context
                    speaker = "Interviewer" if ctx_msg.get('role') == 'assistant' else "Participant"
                    context_text += f"{speaker}: {ctx_msg.get('content', '')}\n"
            
            # Extract message data
            speaker = "Interviewer" if message.get('role') == 'assistant' else "Participant"
            message_text = message.get('content', '')
            
            # Determine interview progress
            progress = "EARLY"
            if state['message_count'] > 20:
                progress = "LATE"
            elif state['message_count'] > 10:
                progress = "MIDDLE"
            
            # Get current topics
            current_topics = ", ".join(state['tags'][-5:]) if state['tags'] else "No topics identified yet"
            
            # Run the analysis
            result = self.note_chain.run(
                speaker=speaker,
                message=message_text,
                context=context_text,
                progress=progress,
                current_topics=current_topics
            )
            
            # Parse the result
            note = ""
            tags = []
            mood = 0
            insight_types = []
            
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
                elif line.startswith("INSIGHT_TYPE:"):
                    insight_types_text = line[13:].strip()
                    insight_types = [t.strip() for t in insight_types_text.split(",")]
            
            # Create observation data
            observation = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.datetime.now().isoformat(),
                'message_id': message.get('id', str(uuid.uuid4())),
                'note': note,
                'tags': tags,
                'mood': mood,
                'speaker': speaker,
                'insight_types': insight_types
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
            
            # Add to appropriate lists based on insight type
            if "KEY_POINT" in insight_types:
                state['key_points'].append({
                    'timestamp': observation['timestamp'],
                    'note': note,
                    'speaker': speaker,
                    'message_id': observation['message_id']
                })
            
            if "PATTERN" in insight_types:
                state['patterns'].append({
                    'timestamp': observation['timestamp'],
                    'note': note,
                    'tags': tags,
                    'message_id': observation['message_id']
                })
            
            # Generate new insights every 5 messages
            if state['message_count'] % 5 == 0:
                self._generate_insights(session_id)
                self._generate_question_suggestions(session_id, context)
            
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
    
    def _generate_insights(self, session_id: str) -> None:
        """
        Generate insights based on the accumulated observations.
        
        Args:
            session_id: The session ID
        """
        try:
            state = self.get_observer_state(session_id)
            
            # Only generate insights if we have enough notes
            if len(state['notes']) < 3:
                return
            
            # Format notes
            notes_text = ""
            for note in state['notes'][-10:]:  # Use the last 10 notes
                tags_str = ', '.join(note['tags'])
                notes_text += f"- {note['note']} [Speaker: {note['speaker']}, Tags: {tags_str}]\n"
            
            # Run the insights chain
            result = self.insights_chain.run(
                notes=notes_text,
                topics=', '.join(state['tags'][-5:])
            )
            
            # Parse insights
            current_section = None
            current_insight = {}
            insights = []
            
            for line in result.strip().split("\n"):
                if line.startswith("INSIGHT:"):
                    # Save previous insight if it exists
                    if current_insight and 'text' in current_insight:
                        insights.append(current_insight)
                    
                    # Start new insight
                    current_insight = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.datetime.now().isoformat(),
                        'text': line[8:].strip()
                    }
                    current_section = "insight"
                elif line.startswith("IMPORTANCE:"):
                    current_insight['importance'] = line[11:].strip()
                    current_section = "importance"
                elif line.startswith("EVIDENCE:"):
                    current_insight['evidence'] = line[9:].strip()
                    current_section = "evidence"
                elif current_section:
                    # Continue previous section
                    current_insight[current_section] += " " + line.strip()
            
            # Add the last insight if it exists
            if current_insight and 'text' in current_insight:
                insights.append(current_insight)
            
            # Add to state
            for insight in insights:
                state['insights'].append(insight)
            
            logger.info(f"Generated {len(insights)} new insights for session {session_id}")
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
    
    def _generate_question_suggestions(self, session_id: str, context: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Generate suggested follow-up questions.
        
        Args:
            session_id: The session ID
            context: Recent conversation context
        """
        try:
            state = self.get_observer_state(session_id)
            
            # Format context
            context_text = ""
            if context and len(context) > 0:
                for ctx_msg in context[-5:]:  # Use the last 5 messages
                    speaker = "Interviewer" if ctx_msg.get('role') == 'assistant' else "Participant"
                    context_text += f"{speaker}: {ctx_msg.get('content', '')}\n"
            
            # Run the questions chain
            result = self.questions_chain.run(
                context=context_text,
                topics=', '.join(state['tags'][-5:])
            )
            
            # Parse questions (numbered list format)
            questions = []
            for line in result.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() and line[1] == '.'):
                    question_text = line[2:].strip()
                    questions.append({
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.datetime.now().isoformat(),
                        'text': question_text
                    })
            
            # Add to state
            state['suggested_questions'] = questions
            
            logger.info(f"Generated {len(questions)} question suggestions for session {session_id}")
        except Exception as e:
            logger.error(f"Error generating question suggestions: {str(e)}")
    
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
                    5. Actionable recommendations
                    
                    Format your response in clear paragraphs with section headings.
                    """
                ),
                HumanMessagePromptTemplate.from_template(
                    """Here are the AI observer notes from the interview:
                    
                    {notes}
                    
                    Most frequent tags: {top_tags}
                    
                    Key points identified:
                    {key_points}
                    
                    Patterns identified:
                    {patterns}
                    
                    Insights generated:
                    {insights}
                    
                    Provide a concise, insightful summary with recommendations.
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
            
            # Format key points
            key_points_text = ""
            for point in state['key_points']:
                key_points_text += f"- {point['note']}\n"
            
            # Format patterns
            patterns_text = ""
            for pattern in state['patterns']:
                patterns_text += f"- {pattern['note']} [Tags: {', '.join(pattern['tags'])}]\n"
            
            # Format insights
            insights_text = ""
            for insight in state['insights']:
                importance = insight.get('importance', 'MEDIUM')
                insights_text += f"- {insight['text']} (Importance: {importance})\n"
            
            # Run the summary chain
            summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
            summary = summary_chain.run(
                notes=notes_text,
                top_tags=top_tags_text,
                key_points=key_points_text or "None identified.",
                patterns=patterns_text or "None identified.",
                insights=insights_text or "None generated."
            )
            
            # Create summary object
            result = {
                'generated_at': datetime.datetime.now().isoformat(),
                'session_id': session_id,
                'content': summary,
                'tags': list(tag_counts.keys()),
                'top_tags': [tag for tag, _ in top_tags],
                'mood_analysis': self._analyze_mood_timeline(state['mood_timeline']),
                'key_points': state['key_points'],
                'patterns': state['patterns'],
                'insights': state['insights'],
                'suggested_questions': state['suggested_questions'][-3:] if state['suggested_questions'] else []
            }
            
            return result
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                'generated_at': datetime.datetime.now().isoformat(),
                'session_id': session_id,
                'content': f"Error generating summary: {str(e)}",
                'error': str(e)
            }
    
    def _analyze_mood_timeline(self, mood_timeline: List[Dict[str, Any]]) -> str:
        """
        Analyze the mood timeline and provide a summary.
        
        Args:
            mood_timeline: The mood timeline data
            
        Returns:
            A summary of the mood analysis
        """
        if not mood_timeline:
            return "No mood data available."
        
        try:
            # Calculate average mood
            moods = [entry.get('mood', 0) for entry in mood_timeline]
            avg_mood = sum(moods) / len(moods) if moods else 0
            
            # Calculate trend
            trend = "stable"
            if len(moods) > 5:
                first_half = moods[:len(moods)//2]
                second_half = moods[len(moods)//2:]
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
                difference = second_avg - first_avg
                if difference > 2:
                    trend = "increasing (getting more positive)"
                elif difference < -2:
                    trend = "decreasing (getting more negative)"
            
            # Find highest and lowest points
            highest = max(moods)
            lowest = min(moods)
            
            # Categorize overall sentiment
            sentiment = "neutral"
            if avg_mood > 3:
                sentiment = "positive"
            elif avg_mood < -3:
                sentiment = "negative"
            elif avg_mood > 1:
                sentiment = "slightly positive"
            elif avg_mood < -1:
                sentiment = "slightly negative"
            
            return f"Overall mood: {sentiment} (avg: {avg_mood:.1f}), Trend: {trend}, Range: {lowest} to {highest}"
        except Exception as e:
            logger.error(f"Error analyzing mood timeline: {str(e)}")
            return "Error analyzing mood timeline."
    
    def get_suggested_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the current suggested follow-up questions.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of suggested questions
        """
        state = self.get_observer_state(session_id)
        return state['suggested_questions']
    
    def get_key_insights(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the key insights identified so far.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of key insights
        """
        state = self.get_observer_state(session_id)
        return state['insights'] 