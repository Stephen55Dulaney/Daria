import os
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Optional, List, Union
from enum import Enum

class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved" 
    CLOSED = "closed"
    BACKLOG = "backlog"
    DESIGN = "in_design"
    READY_FOR_CURSOR = "ready_for_cursor"
    PROTOTYPED = "prototyped"

class IssueType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    TASK = "task"
    OPPORTUNITY = "opportunity"
    EPIC = "epic"
    USER_STORY = "user_story"

class IssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Issue:
    """
    Issue model for bug tracking, feature requests, and research-to-prototype pipeline
    """
    def __init__(self, 
                id=None, 
                title=None,
                description=None,
                issue_type=IssueType.BUG,
                status=IssueStatus.OPEN,
                priority=IssuePriority.MEDIUM,
                creator_id=None,
                assigned_to=None,
                screenshots=None,
                created_at=None,
                updated_at=None,
                environment=None,
                tags=None,
                comments=None,
                # Research-to-prototype fields
                linked_persona=None,
                journey_stage=None,
                insights=None,
                ethics=None,
                root_cause=None,
                parent_id=None,
                linked_prototype_prompt=None,
                cursor_prompt_template=None):
        """Initialize a new issue."""
        self.id = id if id else str(uuid.uuid4())
        self.title = title
        self.description = description
        self.issue_type = issue_type
        self.status = status
        self.priority = priority
        self.creator_id = creator_id
        self.assigned_to = assigned_to  # User ID of currently assigned person
        self.screenshots = screenshots or []  # List of screenshot file paths
        self.created_at = created_at if created_at else datetime.datetime.now().isoformat()
        self.updated_at = updated_at if updated_at else self.created_at
        self.environment = environment or {}  # Dict with browser, OS, etc.
        self.tags = tags or []
        self.history = []  # List of history entries
        self.comments = comments or []  # List of comments
        
        # Research-to-prototype fields
        self.linked_persona = linked_persona  # Name or ID of associated persona
        self.journey_stage = journey_stage  # Stage in journey map
        self.insights = insights or []  # List of key insights
        self.ethics = ethics or []  # List of ethical considerations
        self.root_cause = root_cause  # Root cause of problem (for opportunities)
        self.parent_id = parent_id  # ID of parent issue (epic for stories, opportunity for epics)
        self.linked_prototype_prompt = linked_prototype_prompt  # Link to generated prototype prompt
        self.cursor_prompt_template = cursor_prompt_template  # Template for Cursor AI prompt
        
        self._record_history("Issue created")
    
    def _record_history(self, action, user_id=None, details=None):
        """Record an action in the issue history"""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details
        }
        self.history.append(entry)
        self.updated_at = entry["timestamp"]
    
    def assign_to(self, user_id, assigner_id):
        """Assign the issue to a user"""
        prev_assigned = self.assigned_to
        self.assigned_to = user_id
        self._record_history(
            "Issue reassigned", 
            user_id=assigner_id,
            details={"from": prev_assigned, "to": user_id}
        )
    
    def add_screenshot(self, file_path, user_id):
        """Add a screenshot to the issue"""
        self.screenshots.append(file_path)
        self._record_history(
            "Screenshot added", 
            user_id=user_id,
            details={"file": file_path}
        )
    
    def update_status(self, new_status, user_id):
        """Update the status of the issue"""
        if new_status == IssueStatus.CLOSED and user_id != self.creator_id:
            # If someone other than creator tries to close, reassign to creator for verification
            prev_status = self.status
            self.status = IssueStatus.RESOLVED
            self.assigned_to = self.creator_id
            self._record_history(
                "Issue marked as resolved", 
                user_id=user_id,
                details={"from": prev_status, "to": self.status, "reassigned_to_creator": True}
            )
        else:
            # Normal status update
            prev_status = self.status
            self.status = new_status
            self._record_history(
                "Status updated", 
                user_id=user_id,
                details={"from": prev_status, "to": new_status}
            )
    
    def move_to_backlog(self, user_id):
        """Move a feature request to the backlog"""
        if self.issue_type != IssueType.FEATURE:
            raise ValueError("Only feature requests can be moved to backlog")
        
        prev_status = self.status
        self.status = IssueStatus.BACKLOG
        self._record_history(
            "Moved to backlog", 
            user_id=user_id,
            details={"from": prev_status}
        )
    
    def add_comment(self, user_id, content, attachments=None):
        """Add a comment to the issue"""
        comment = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "content": content,
            "attachments": attachments or [],
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.comments.append(comment)
        self._record_history(
            "Comment added", 
            user_id=user_id,
            details={"comment_id": comment["id"]}
        )
        return comment["id"]
    
    def to_dict(self) -> Dict:
        """Convert issue to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "issue_type": self.issue_type,
            "status": self.status,
            "priority": self.priority,
            "creator_id": self.creator_id,
            "assigned_to": self.assigned_to,
            "screenshots": self.screenshots,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "environment": self.environment,
            "tags": self.tags,
            "history": self.history,
            "comments": self.comments,
            # Research-to-prototype fields
            "linked_persona": self.linked_persona,
            "journey_stage": self.journey_stage,
            "insights": self.insights,
            "ethics": self.ethics,
            "root_cause": self.root_cause,
            "parent_id": self.parent_id,
            "linked_prototype_prompt": self.linked_prototype_prompt,
            "cursor_prompt_template": self.cursor_prompt_template
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Issue':
        """Create an Issue instance from a dictionary"""
        issue = cls(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            issue_type=data.get("issue_type"),
            status=data.get("status"),
            priority=data.get("priority"),
            creator_id=data.get("creator_id"),
            assigned_to=data.get("assigned_to"),
            screenshots=data.get("screenshots"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            environment=data.get("environment"),
            tags=data.get("tags"),
            comments=data.get("comments"),
            # Research-to-prototype fields
            linked_persona=data.get("linked_persona"),
            journey_stage=data.get("journey_stage"),
            insights=data.get("insights"),
            ethics=data.get("ethics"),
            root_cause=data.get("root_cause"),
            parent_id=data.get("parent_id"),
            linked_prototype_prompt=data.get("linked_prototype_prompt"),
            cursor_prompt_template=data.get("cursor_prompt_template")
        )
        issue.history = data.get("history", [])
        return issue


class IssueManager:
    """
    Manager class for handling issues storage and retrieval
    """
    def __init__(self, data_dir="./data/issues"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_issue(self, 
                   title: str, 
                   description: str, 
                   creator_id: str, 
                   issue_type: IssueType = IssueType.BUG,
                   priority: IssuePriority = IssuePriority.MEDIUM,
                   screenshots: List[str] = None) -> Issue:
        """Create a new issue"""
        issue = Issue(
            title=title,
            description=description,
            issue_type=issue_type,
            creator_id=creator_id,
            priority=priority,
            screenshots=screenshots or []
        )
        self._save_issue(issue)
        return issue
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get an issue by ID"""
        issue_path = self.data_dir / f"{issue_id}.json"
        if not issue_path.exists():
            return None
        
        with open(issue_path, "r") as f:
            data = json.load(f)
        
        return Issue.from_dict(data)
    
    def update_issue(self, issue: Issue) -> None:
        """Update an existing issue"""
        self._save_issue(issue)
    
    def _save_issue(self, issue: Issue) -> None:
        """Save issue to disk"""
        issue_path = self.data_dir / f"{issue.id}.json"
        with open(issue_path, "w") as f:
            json.dump(issue.to_dict(), f, indent=2)
    
    def get_issues_by_creator(self, user_id: str) -> List[Issue]:
        """Get all issues created by a specific user"""
        return self._filter_issues(lambda issue: issue.creator_id == user_id)
    
    def get_issues_assigned_to(self, user_id: str) -> List[Issue]:
        """Get all issues assigned to a specific user"""
        return self._filter_issues(lambda issue: issue.assigned_to == user_id)
    
    def get_open_issues(self) -> List[Issue]:
        """Get all open issues"""
        return self._filter_issues(lambda issue: issue.status == IssueStatus.OPEN)
    
    def get_backlog_issues(self) -> List[Issue]:
        """Get all backlog issues"""
        return self._filter_issues(lambda issue: issue.status == IssueStatus.BACKLOG)
    
    def get_all_issues(self) -> List[Issue]:
        """Get all issues"""
        issues = []
        for issue_file in self.data_dir.glob("*.json"):
            with open(issue_file, "r") as f:
                try:
                    issue_data = json.load(f)
                    issues.append(Issue.from_dict(issue_data))
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON files
        return issues
    
    def _filter_issues(self, filter_func) -> List[Issue]:
        """Filter issues using the provided function"""
        all_issues = self.get_all_issues()
        return [issue for issue in all_issues if filter_func(issue)] 