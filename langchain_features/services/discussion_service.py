import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models import DiscussionGuide, InterviewSession

logger = logging.getLogger(__name__)

class DiscussionService:
    """Service for managing discussion guides and sessions"""
    
    def __init__(self, data_dir: str = None):
        """Initialize the discussion service.
        
        Args:
            data_dir (str, optional): Directory to store data files
        """
        self.data_dir = Path(data_dir or "data/discussions")
        self.sessions_dir = self.data_dir / "sessions"
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)
        logger.info(f"Initialized DiscussionService with data_dir={self.data_dir}")
    
    # Discussion Guide Methods
    
    def create_guide(self, guide_data: Dict[str, Any]) -> str:
        """Create a new discussion guide.
        
        Args:
            guide_data (Dict): The guide data
            
        Returns:
            str: The guide ID
        """
        guide_id = guide_data.get("id", str(uuid.uuid4()))
        guide_data["id"] = guide_id
        guide_data["created_at"] = datetime.now()
        guide_data["updated_at"] = datetime.now()
        guide_data["status"] = "active"
        guide_data["sessions"] = []
        
        self._save_guide(guide_id, guide_data)
        logger.info(f"Created discussion guide with ID {guide_id}")
        
        return guide_id
    
    def update_guide(self, guide_id: str, guide_data: Dict[str, Any]) -> bool:
        """Update an existing discussion guide.
        
        Args:
            guide_id (str): The guide ID
            guide_data (Dict): The updated guide data
            
        Returns:
            bool: True if successful
        """
        existing_guide = self._load_guide(guide_id)
        if not existing_guide:
            logger.warning(f"Discussion guide not found: {guide_id}")
            return False
        
        # Update fields while preserving metadata
        for key, value in guide_data.items():
            if key not in ["id", "created_at", "sessions"]:
                existing_guide[key] = value
        
        existing_guide["updated_at"] = datetime.now()
        self._save_guide(guide_id, existing_guide)
        logger.info(f"Updated discussion guide with ID {guide_id}")
        
        return True
    
    def get_guide(self, guide_id: str) -> Optional[Dict[str, Any]]:
        """Get a discussion guide by ID.
        
        Args:
            guide_id (str): The guide ID
            
        Returns:
            Dict: The guide data or None if not found
        """
        return self._load_guide(guide_id)
    
    def list_guides(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all discussion guides.
        
        Args:
            active_only (bool): If True, only return active guides
            
        Returns:
            List[Dict]: List of guides
        """
        guides = []
        
        if not self.data_dir.exists():
            return guides
        
        for file_path in self.data_dir.glob("*.json"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            
            try:
                with open(file_path, "r") as f:
                    guide_data = json.load(f)
                
                if active_only and guide_data.get("status") != "active":
                    continue
                    
                # Ensure essential fields exist
                if "id" not in guide_data:
                    guide_data["id"] = file_path.stem
                
                if "updated_at" not in guide_data:
                    guide_data["updated_at"] = datetime.now().isoformat()
                
                if "created_at" not in guide_data:
                    guide_data["created_at"] = datetime.now().isoformat()
                    
                guides.append(guide_data)
            except Exception as e:
                logger.error(f"Error loading guide from {file_path}: {str(e)}")
        
        return sorted(guides, key=lambda g: g.get("updated_at", ""), reverse=True)
    
    def archive_guide(self, guide_id: str) -> bool:
        """Archive a discussion guide.
        
        Args:
            guide_id (str): The guide ID
            
        Returns:
            bool: True if successful
        """
        guide = self._load_guide(guide_id)
        if not guide:
            return False
        
        guide["status"] = "archived"
        guide["updated_at"] = datetime.now()
        self._save_guide(guide_id, guide)
        logger.info(f"Archived discussion guide with ID {guide_id}")
        
        return True
    
    def delete_guide(self, guide_id: str) -> bool:
        """Permanently delete a discussion guide.
        
        Args:
            guide_id (str): The guide ID
            
        Returns:
            bool: True if successful
        """
        guide_path = self.data_dir / f"{guide_id}.json"
        if not guide_path.exists():
            logger.warning(f"Guide not found for deletion: {guide_id}")
            return False
            
        # Load the guide to get session IDs
        guide = self._load_guide(guide_id)
        if guide and guide.get("sessions"):
            # Optionally delete associated sessions or mark them as orphaned
            for session_id in guide.get("sessions", []):
                # We're not deleting sessions, just updating them to mark them as orphaned
                session = self._load_session(session_id)
                if session:
                    session["guide_id"] = None
                    session["status"] = "orphaned"
                    session["updated_at"] = datetime.now().isoformat()
                    self._save_session(session_id, session)
                    logger.info(f"Marked session {session_id} as orphaned")
        
        # Delete the guide file
        try:
            guide_path.unlink()
            logger.info(f"Deleted discussion guide with ID {guide_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting guide {guide_id}: {str(e)}")
            return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all interview sessions across all guides.
        
        Returns:
            List[Dict]: List of all sessions
        """
        all_sessions = []
        
        # List all session files in the sessions directory
        try:
            session_files = list(self.sessions_dir.glob("*.json"))
            
            for session_file in session_files:
                try:
                    session_id = session_file.stem
                    session = self._load_session(session_id)
                    if session:
                        all_sessions.append(session)
                except Exception as e:
                    logger.error(f"Error loading session from {session_file}: {str(e)}")
                    continue
                
            # Sort by last updated time, most recent first
            all_sessions = sorted(
                all_sessions, 
                key=lambda s: s.get("updated_at", s.get("created_at", "")),
                reverse=True
            )
            
            logger.info(f"Loaded {len(all_sessions)} sessions across all guides")
            return all_sessions
            
        except Exception as e:
            logger.error(f"Error getting all sessions: {str(e)}")
            return []
    
    # Alias list_sessions to get_all_sessions for compatibility with InterviewService
    list_sessions = get_all_sessions
    
    # Session Methods
    
    def create_session(self, guide_id: str, interviewee_data: Dict[str, Any] = None) -> Optional[str]:
        """Create a new interview session for a discussion guide.
        
        Args:
            guide_id (str): The discussion guide ID
            interviewee_data (Dict, optional): Information about the interviewee
            
        Returns:
            str: The session ID or None if guide not found
        """
        guide = self._load_guide(guide_id)
        if not guide:
            logger.warning(f"Guide not found for session creation: {guide_id}")
            return None
        
        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "guide_id": guide_id,
            "interviewee": interviewee_data or {},
            "status": "active",
            "messages": [],
            "transcript": "",
            "analysis": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Copy important fields from the guide to the session
        if "title" in guide:
            session_data["title"] = guide["title"]
        if "project" in guide:
            session_data["project"] = guide["project"]
        if "interview_type" in guide:
            session_data["interview_type"] = guide["interview_type"]
        if "topic" in guide:
            session_data["topic"] = guide["topic"]
        if "context" in guide:
            session_data["context"] = guide["context"]
        if "goals" in guide:
            session_data["goals"] = guide["goals"]
        if "character_select" in guide:
            session_data["character"] = guide["character_select"]
            session_data["character_select"] = guide["character_select"]
        if "voice_id" in guide:
            session_data["voice_id"] = guide["voice_id"]
        
        # Save the session
        self._save_session(session_id, session_data)
        
        # Update the guide with the new session ID
        if "sessions" not in guide:
            guide["sessions"] = []
        guide["sessions"].append(session_id)
        guide["updated_at"] = datetime.now()
        self._save_guide(guide_id, guide)
        
        logger.info(f"Created session {session_id} for guide {guide_id} with character {session_data.get('character', 'None')}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            Dict: The session data or None if not found
        """
        return self._load_session(session_id)
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            List[Dict]: List of messages or empty list if not found
        """
        session = self._load_session(session_id)
        if not session:
            return []
        
        return session.get("messages", [])
    
    def list_guide_sessions(self, guide_id: str) -> List[Dict[str, Any]]:
        """List all sessions for a discussion guide.
        
        Args:
            guide_id (str): The discussion guide ID
            
        Returns:
            List[Dict]: List of sessions
        """
        guide = self._load_guide(guide_id)
        if not guide or "sessions" not in guide:
            return []
        
        sessions = []
        for session_id in guide["sessions"]:
            session = self._load_session(session_id)
            if session:
                sessions.append(session)
        
        return sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update a session.
        
        Args:
            session_id (str): The session ID
            data (Dict): The updated session data
            
        Returns:
            bool: True if successful
        """
        session = self._load_session(session_id)
        if not session:
            return False
        
        # Update fields while preserving metadata
        for key, value in data.items():
            if key not in ["id", "guide_id", "created_at"]:
                session[key] = value
        
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id, session)
        
        logger.info(f"Updated session {session_id}")
        return True
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add a message to a session.
        
        Args:
            session_id (str): The session ID
            message (Dict): The message to add
            
        Returns:
            bool: True if successful
        """
        session = self._load_session(session_id)
        if not session:
            return False
        
        if "messages" not in session:
            session["messages"] = []
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        session["messages"].append(message)
        session["updated_at"] = datetime.now().isoformat()
        
        # Update transcript
        if "transcript" not in session:
            session["transcript"] = ""
        
        speaker = "Moderator" if message.get("role") == "assistant" else "Participant"
        session["transcript"] += f"\n\n{speaker}: {message.get('content', '')}"
        
        self._save_session(session_id, session)
        logger.info(f"Added message to session {session_id}")
        
        return True
    
    def add_message_to_session(self, session_id: str, content: str, role: str, message_id: str = None) -> str:
        """Add a message to a session with separate parameters.
        
        Args:
            session_id (str): The session ID
            content (str): The message content
            role (str): The message role (user or assistant)
            message_id (str, optional): The message ID, generated if not provided
            
        Returns:
            str: The message ID
        """
        if not message_id:
            message_id = str(uuid.uuid4())
            
        message = {
            "id": message_id,
            "content": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        }
        
        success = self.add_message(session_id, message)
        if not success:
            logger.error(f"Failed to add message to session {session_id}")
            
        return message_id
    
    def complete_session(self, session_id: str) -> bool:
        """Mark a session as completed.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            bool: True if successful
        """
        session = self._load_session(session_id)
        if not session:
            return False
        
        session["status"] = "completed"
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id, session)
        
        logger.info(f"Marked session {session_id} as completed")
        return True
    
    def analyze_session(self, session_id: str, analysis: Dict[str, Any]) -> bool:
        """Add analysis to a session.
        
        Args:
            session_id (str): The session ID
            analysis (Dict): The analysis data
            
        Returns:
            bool: True if successful
        """
        session = self._load_session(session_id)
        if not session:
            logger.warning(f"Session not found for analysis: {session_id}")
            return False
        
        session["analysis"] = analysis
        session["updated_at"] = datetime.now()
        self._save_session(session_id, session)
        logger.info(f"Added analysis to session {session_id}")
        
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session permanently.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            bool: True if successful
        """
        session_path = self.sessions_dir / f"{session_id}.json"
        if not session_path.exists():
            logger.warning(f"Session not found for deletion: {session_id}")
            return False
        
        # Load the session to get guide ID
        session = self._load_session(session_id)
        if session and session.get("guide_id"):
            # Remove this session ID from the guide's sessions list
            guide_id = session.get("guide_id")
            guide = self._load_guide(guide_id)
            if guide and "sessions" in guide:
                if session_id in guide["sessions"]:
                    guide["sessions"].remove(session_id)
                    guide["updated_at"] = datetime.now()
                    self._save_guide(guide_id, guide)
                    logger.info(f"Removed session {session_id} from guide {guide_id}")
        
        # Delete the session file
        try:
            session_path.unlink()
            logger.info(f"Deleted session with ID {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    def get_character_info(self, guide_id: str) -> Dict[str, Any]:
        """Get character information from a guide.
        
        Args:
            guide_id (str): The guide ID
            
        Returns:
            Dict: Character information
        """
        guide = self._load_guide(guide_id)
        if not guide:
            return {
                "name": "interviewer",
                "prompt": "You are a professional interviewer conducting a research interview."
            }
        
        character_name = guide.get("character_select", "").lower()
        if not character_name:
            return {
                "name": "interviewer", 
                "prompt": "You are a professional interviewer conducting a research interview."
            }
        
        # Return the character info
        return {
            "name": character_name,
            "prompt": guide.get("interview_prompt", "")
        }
    
    # Helper methods
    
    def _save_guide(self, guide_id: str, guide_data: Dict[str, Any]) -> bool:
        """Save a discussion guide to file.
        
        Args:
            guide_id (str): The guide ID
            guide_data (Dict): The guide data
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert datetime objects to ISO format strings
            serializable_data = {}
            for key, value in guide_data.items():
                if isinstance(value, datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            file_path = self.data_dir / f"{guide_id}.json"
            with open(file_path, "w") as f:
                json.dump(serializable_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving guide {guide_id}: {str(e)}")
            return False
    
    def _save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Save a session to file.
        
        Args:
            session_id (str): The session ID
            session_data (Dict): The session data
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert datetime objects to ISO format strings
            serializable_data = {}
            for key, value in session_data.items():
                if isinstance(value, datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            file_path = self.sessions_dir / f"{session_id}.json"
            with open(file_path, "w") as f:
                json.dump(serializable_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {str(e)}")
            return False
    
    def _load_guide(self, guide_id: str) -> Optional[Dict[str, Any]]:
        """Load a discussion guide from disk.
        
        Args:
            guide_id (str): The guide ID
            
        Returns:
            Dict or None: The guide data or None if not found
        """
        guide_path = self.data_dir / f"{guide_id}.json"
        if not guide_path.exists():
            logger.warning(f"Guide file not found: {guide_path}")
            return None
        
        try:
            with open(guide_path, "r") as f:
                guide_data = json.load(f)
            
            # Ensure essential fields exist
            if "id" not in guide_data:
                guide_data["id"] = guide_id
            
            if "updated_at" not in guide_data:
                guide_data["updated_at"] = datetime.now().isoformat()
            
            if "created_at" not in guide_data:
                guide_data["created_at"] = datetime.now().isoformat()
                
            if "status" not in guide_data:
                guide_data["status"] = "active"
                
            if "sessions" not in guide_data:
                guide_data["sessions"] = []
            
            # Ensure options field exists to prevent template errors
            if "options" not in guide_data:
                guide_data["options"] = {
                    "record_transcript": True,
                    "analysis": True,
                    "use_tts": True
                }
                
            # Ensure custom_questions field exists
            if "custom_questions" not in guide_data:
                guide_data["custom_questions"] = []
                
            return guide_data
        except Exception as e:
            logger.error(f"Error loading guide {guide_id}: {str(e)}")
            return None
    
    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from file.
        
        Args:
            session_id (str): The session ID
            
        Returns:
            Dict: The session data or None if not found
        """
        try:
            file_path = self.sessions_dir / f"{session_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}")
            return None 