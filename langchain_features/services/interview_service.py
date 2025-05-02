import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage

from langchain_features.models import InterviewSession

# In-memory store for sessions - would be replaced with DB in production
interview_sessions = {}

class InterviewService:
    """Service for managing LangChain interview sessions"""
    
    @staticmethod
    def create_session(title: str, prompt: str) -> InterviewSession:
        """Create a new interview session"""
        session = InterviewSession.create(title, prompt)
        interview_sessions[session.id] = session
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[InterviewSession]:
        """Get an interview session by ID"""
        # First, check if it's in memory
        session = interview_sessions.get(session_id)
        
        # If not in memory, check if it's saved to disk
        if session is None:
            try:
                filename = f"interviews/remote_interview_{session_id}.json"
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        
                        # Create session object from saved data
                        session = InterviewSession(
                            id=data.get('id'),
                            title=data.get('title'),
                            prompt=data.get('prompt'),
                            project=data.get('project'),
                            interview_type=data.get('interview_type'),
                            interview_prompt=data.get('interview_prompt'),
                            analysis_prompt=data.get('analysis_prompt'),
                            interviewee=data.get('interviewee', {}),
                            custom_questions=data.get('custom_questions', []),
                            time_per_question=data.get('time_per_question', 2),
                            options=data.get('options', {})
                        )
                        
                        # Add additional fields from the saved data
                        session.transcript = data.get('transcript', '')
                        session.messages = data.get('messages', [])
                        session.summary = data.get('summary', '')
                        session.analysis = data.get('analysis', '')
                        session.status = data.get('status', 'created')
                        
                        # Parse dates
                        created_at = data.get('created_at')
                        updated_at = data.get('updated_at')
                        expiration_date = data.get('expiration_date')
                        
                        if created_at:
                            try:
                                session.created_at = datetime.fromisoformat(created_at)
                            except:
                                pass
                        if updated_at:
                            try:
                                session.updated_at = datetime.fromisoformat(updated_at)
                            except:
                                pass
                        if expiration_date:
                            try:
                                session.expiration_date = datetime.fromisoformat(expiration_date)
                            except:
                                pass
                        
                        # Check if interview has expired
                        if session.expiration_date and session.expiration_date < datetime.now():
                            session.status = 'expired'
                        
                        # Store in memory for future use
                        interview_sessions[session_id] = session
                        print(f"Loaded interview session {session_id} from disk")
            except Exception as e:
                print(f"Error loading interview session from disk: {str(e)}")
                return None
        
        # Check if the interview has expired (for in-memory sessions)
        if session and session.expiration_date and session.expiration_date < datetime.now():
            session.status = 'expired'
            # Save the updated status
            InterviewService.save_session(session)
        
        return session
    
    @staticmethod
    def list_sessions() -> List[InterviewSession]:
        """List all interview sessions"""
        return list(interview_sessions.values())
    
    @staticmethod
    def update_session(session_id: str, **kwargs) -> Optional[InterviewSession]:
        """Update an interview session"""
        session = interview_sessions.get(session_id)
        if not session:
            return None
            
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
                
        session.updated_at = datetime.now()
        interview_sessions[session_id] = session
        return session
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete an interview session"""
        if session_id in interview_sessions:
            del interview_sessions[session_id]
            return True
        return False
    
    @staticmethod
    def start_interview(session_id: str) -> Dict[str, Any]:
        """Start an interview and get the first question"""
        session = interview_sessions.get(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        
        # Make sure we have a prompt to use
        prompt_text = session.interview_prompt
        if not prompt_text:
            prompt_text = session.prompt  # Fallback to legacy prompt field
        
        if not prompt_text:
            return {"status": "error", "error": "No interview prompt found"}
        
        try:
            # Initialize conversation with LangChain
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=1)
            memory = ConversationBufferMemory()
            conversation = ConversationChain(llm=llm, memory=memory)
            
            # Get the first question from the model
            first_question = conversation.predict(input=prompt_text)
            
            # Update session with first message
            session.status = "active"
            session.messages = [
                {"role": "system", "content": prompt_text},
                {"role": "assistant", "content": first_question}
            ]
            session.transcript = f"Interviewer: Daria (UX Researcher)\nDaria: {first_question}\n"
            session.updated_at = datetime.now()
            
            # Save the session
            InterviewService.save_session(session)
            
            return {
                "status": "success",
                "session_id": session_id,
                "first_question": first_question
            }
        except Exception as e:
            print(f"Error starting interview: {str(e)}")
            return {
                "status": "error", 
                "error": f"Error starting interview: {str(e)}"
            }
    
    @staticmethod
    def process_response(session_id: str, user_input: str) -> Dict[str, Any]:
        """Process user response and get next interview question"""
        session = interview_sessions.get(session_id)
        if not session:
            return {
                "status": "error",
                "error": "Session not found",
                "next_question": "I'm sorry, your session has expired. Please refresh the page and start again."
            }
            
        try:
            # Append user's response to transcript
            session.transcript += f"Participant: {user_input}\n"
            session.messages.append({"role": "user", "content": user_input})
            
            # Initialize LangChain components
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=1)
            memory = ConversationBufferMemory()
            
            # Load previous messages into memory
            for msg in session.messages:
                if msg["role"] == "system":
                    # Skip system message for memory but keep it in our message list
                    continue
                elif msg["role"] == "assistant":
                    memory.chat_memory.add_ai_message(msg["content"])
                elif msg["role"] == "user" and msg["content"]:  # Make sure content is not None
                    memory.chat_memory.add_user_message(msg["content"])
            
            # Create conversation chain
            conversation = ConversationChain(llm=llm, memory=memory)
            
            # Get next question
            prompt = "Continue the interview and ask the next question or follow-up question."
            next_question = conversation.predict(input=prompt)
            
            # Update transcript and messages
            session.transcript += f"Daria: {next_question}\n"
            session.messages.append({"role": "assistant", "content": next_question})
            session.updated_at = datetime.now()
            
            # Save session
            InterviewService.save_session(session)
            
            return {
                "status": "success",
                "next_question": next_question,
                "transcript": session.transcript
            }
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing response: {str(e)}",
                "next_question": "I'm sorry, there was an error processing your response. Please try again."
            }
    
    @staticmethod
    def analyze_interview(session_id: str) -> Dict[str, Any]:
        """Analyze the interview transcript"""
        session = interview_sessions.get(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
            
        if not session.transcript:
            return {"status": "error", "error": "No interview transcript to analyze"}
        
        try:
            # Construct the prompt for analysis
            context = f"""
            You are Daria, an expert UX researcher conducting interviews. You evaluate interview transcripts and generate a report 
            on the interviewee's responses. The report should include insights into their role, experience, needs, and any key 
            frustrations or suggestions they have mentioned. Be critical in your evaluation and provide a comprehensive summary 
            of the interviewee's input.
            
            Here is the transcript:
            {session.transcript}
            
            What is your assessment of the interviewee's responses?
            """
            
            # Generate analysis
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
            analysis = llm.invoke(context).content
            
            # Update session with analysis
            session.analysis = {
                "content": analysis,
                "created_at": datetime.now().isoformat()
            }
            session.status = "completed"
            session.updated_at = datetime.now()
            
            # Save the session with the updated analysis
            InterviewService.save_session(session)
            
            return {
                "status": "success",
                "analysis": analysis
            }
        except Exception as e:
            print(f"Error analyzing interview: {str(e)}")
            return {
                "status": "error", 
                "error": f"Error analyzing interview: {str(e)}"
            }
    
    @staticmethod
    def save_session(session):
        """Save an interview session.
        
        Args:
            session: The InterviewSession object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs('interviews', exist_ok=True)
            
            # Save session to file
            filename = f"interviews/remote_interview_{session.id}.json"
            with open(filename, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
                
            print(f"Saved interview session to {filename}")
            return True
        except Exception as e:
            print(f"Error saving interview session: {str(e)}")
            return False 