"""
Database package for the DARIA Interview Tool.
"""

from .database import get_dynamodb_resource, get_dynamodb_client
from .interview_sessions import InterviewSessionsDB
from .transcripts import TranscriptsDB
from .sprints import SprintsDB
from .opportunities import OpportunitiesDB
from .personas import PersonasDB
from .agile_artifacts import AgileArtifactsDB
from .cursor_prompts import CursorPromptsDB
from .prototypes import PrototypesDB
from .journey_maps import JourneyMapsDB

__all__ = [
    'get_dynamodb_resource',
    'get_dynamodb_client',
    'InterviewSessionsDB',
    'TranscriptsDB',
    'SprintsDB',
    'OpportunitiesDB',
    'PersonasDB',
    'AgileArtifactsDB',
    'CursorPromptsDB',
    'PrototypesDB',
    'JourneyMapsDB',
] 