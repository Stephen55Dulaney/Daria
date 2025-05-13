from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid

@dataclass
class InterviewSession:
    """Data model for remote interview sessions"""
    id: str
    created_at: datetime
    updated_at: datetime
    title: str
    prompt: str
    project: str
    interview_type: str
    interview_prompt: str
    analysis_prompt: str
    interviewee: Dict
    custom_questions: List
    time_per_question: int
    options: Dict
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    status: str = "created"  # created, active, completed, expired
    messages: List[Dict] = None
    transcript: str = ""
    summary: Optional[str] = None
    analysis: Optional[Dict] = None
    expiration_date: datetime = None
    notes: str = ""
    duration: Optional[int] = None
    
    def __init__(self, id=None, title=None, prompt=None, project=None, 
                 interview_type=None, interview_prompt=None, analysis_prompt=None, 
                 interviewee=None, custom_questions=None, time_per_question=2, 
                 options=None, participant_name=None, participant_email=None):
        """
        Initialize an interview session.
        
        Args:
            id (str, optional): The unique identifier for the session
            title (str, optional): The title of the interview
            prompt (str, optional): Legacy prompt field (for backward compatibility)
            project (str, optional): The project name
            interview_type (str, optional): The type of interview
            interview_prompt (str, optional): The prompt for the interview
            analysis_prompt (str, optional): The prompt for the analysis
            interviewee (dict, optional): Information about the interviewee
            custom_questions (list, optional): Custom questions for the interview
            time_per_question (int, optional): Time per question in minutes
            options (dict, optional): Additional options for the interview
            participant_name (str, optional): Legacy field for participant name
            participant_email (str, optional): Legacy field for participant email
        """
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.prompt = prompt
        self.project = project
        self.interview_type = interview_type
        self.interview_prompt = interview_prompt or prompt  # Use prompt as fallback
        self.analysis_prompt = analysis_prompt
        self.interviewee = interviewee or {}
        self.custom_questions = custom_questions or []
        self.time_per_question = time_per_question
        self.options = options or {}
        self.participant_name = participant_name or (self.interviewee.get('name') if self.interviewee else None)
        self.participant_email = participant_email
        self.status = "active"
        self.transcript = ""
        self.messages = []
        self.summary = ""
        self.analysis = {}
        self.notes = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.expiration_date = None
        self.duration = None

    @classmethod
    def create(cls, title: str, prompt: str):
        """Create a new interview session"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            title=title,
            prompt=prompt,
            project="",
            interview_type="",
            interview_prompt="",
            analysis_prompt="",
            interviewee={},
            custom_questions=[],
            time_per_question=2,
            options={},
            messages=[]
        )

    def to_dict(self):
        """Convert the interview session to a dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "interview_type": self.interview_type,
            "prompt": self.prompt,
            "interview_prompt": self.interview_prompt,
            "analysis_prompt": self.analysis_prompt,
            "interviewee": self.interviewee,
            "custom_questions": self.custom_questions,
            "transcript": self.transcript,
            "messages": self.messages,
            "summary": self.summary,
            "analysis": self.analysis,
            "status": self.status,
            "time_per_question": self.time_per_question,
            "options": self.options,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "notes": self.notes,
            "duration": self.duration
        }

@dataclass
class ResearchPlan:
    """Data model for AI-generated research plans"""
    id: str
    created_at: datetime
    updated_at: datetime
    title: str
    description: str
    objectives: List[str]
    methodology: str
    timeline: Dict[str, Any]
    questions: List[Dict[str, str]]
    
    @classmethod
    def create(cls, title: str, description: str):
        """Create a new research plan"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            title=title,
            description=description,
            objectives=[],
            methodology="",
            timeline={},
            questions=[]
        )

@dataclass
class DiscoveryPlan:
    """Data model for AI-generated discovery plans"""
    id: str
    created_at: datetime
    updated_at: datetime
    title: str
    description: str
    key_findings: List[str]
    themes: List[Dict[str, Any]]
    next_steps: List[str]
    
    @classmethod
    def create(cls, title: str, description: str):
        """Create a new discovery plan"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            title=title,
            description=description,
            key_findings=[],
            themes=[],
            next_steps=[]
        )

@dataclass
class DiscussionGuide:
    """Data model for discussion guides"""
    id: str
    title: str
    project: str
    interview_type: str
    prompt: str
    interview_prompt: str
    analysis_prompt: str
    character_select: str
    voice_id: str
    target_audience: Dict
    created_at: datetime
    updated_at: datetime
    status: str
    sessions: List
    custom_questions: List
    time_per_question: int
    options: Dict
    
    def __init__(self, id=None, title=None, project=None, interview_type=None, prompt=None, 
                 interview_prompt=None, analysis_prompt=None, character_select=None, voice_id=None,
                 target_audience=None, status="active", sessions=None, custom_questions=None, 
                 time_per_question=2, options=None):
        """
        Initialize a discussion guide.
        
        Args:
            id (str, optional): The unique identifier for the guide
            title (str, optional): The title of the guide
            project (str, optional): The project name
            interview_type (str, optional): The type of interview
            prompt (str, optional): Legacy prompt field
            interview_prompt (str, optional): The prompt for the interview
            analysis_prompt (str, optional): The prompt for the analysis
            character_select (str, optional): The character to use for the interview
            voice_id (str, optional): The voice ID to use for TTS
            target_audience (dict, optional): Information about the target audience
            status (str, optional): The status of the guide
            sessions (list, optional): List of session IDs using this guide
            custom_questions (list, optional): Custom questions for the interview
            time_per_question (int, optional): Time per question in minutes
            options (dict, optional): Additional options for the guide
        """
        self.id = id or str(uuid.uuid4())
        self.title = title or "Untitled Guide"
        self.project = project or ""
        self.interview_type = interview_type or "research_interview"
        self.prompt = prompt or ""
        self.interview_prompt = interview_prompt or ""
        self.analysis_prompt = analysis_prompt or ""
        self.character_select = character_select or "interviewer"
        self.voice_id = voice_id or "EXAVITQu4vr4xnSDxMaL"
        self.target_audience = target_audience or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.status = status
        self.sessions = sessions or []
        self.custom_questions = custom_questions or []
        self.time_per_question = time_per_question
        self.options = options or {}
    
    def to_dict(self):
        """Convert the discussion guide to a dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "interview_type": self.interview_type,
            "prompt": self.prompt,
            "interview_prompt": self.interview_prompt,
            "analysis_prompt": self.analysis_prompt,
            "character_select": self.character_select,
            "voice_id": self.voice_id,
            "target_audience": self.target_audience,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "sessions": self.sessions,
            "custom_questions": self.custom_questions,
            "time_per_question": self.time_per_question,
            "options": self.options
        }
        
    @classmethod
    def create(cls, title: str, project: str = "", interview_type: str = "research_interview"):
        """Create a new discussion guide"""
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            project=project,
            interview_type=interview_type
        ) 