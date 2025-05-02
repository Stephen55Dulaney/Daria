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