import os
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Optional, List
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

VALID_ROLES = ['admin', 'researcher', 'user']

class User(UserMixin):
    """User model with authentication capabilities."""
    
    def __init__(self, 
                 id=None, 
                 username=None, 
                 email=None, 
                 password_hash=None, 
                 role='user', 
                 created_at=None, 
                 last_login=None):
        """Initialize a new user."""
        self.id = id if id else str(uuid.uuid4())
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at if created_at else datetime.datetime.now().isoformat()
        self.last_login = last_login
    
    def set_password(self, password: str) -> None:
        """Hash the password and store it in the user model."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary for serialization."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create a user from a dictionary."""
        return cls(
            id=data.get('id'),
            username=data.get('username'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
            role=data.get('role', 'user'),
            created_at=data.get('created_at'),
            last_login=data.get('last_login')
        )

class UserRepository:
    """Repository for managing users."""
    
    def __init__(self, data_dir=None):
        """Initialize the user repository."""
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users')
        self.storage_path = self.data_dir
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        self.users = self._load_users()
    
    def _load_users(self) -> Dict[str, User]:
        """Load all users from storage."""
        users = {}
        try:
            user_files = Path(self.storage_path).glob('*.json')
            for user_file in user_files:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                    user = User.from_dict(user_data)
                    users[user.id] = user
            return users
        except Exception as e:
            print(f"Error loading users: {str(e)}")
            return {}
    
    def save_user(self, user: User) -> bool:
        """Save a user to storage."""
        try:
            self.users[user.id] = user
            user_file = Path(self.storage_path) / f"{user.id}.json"
            with open(user_file, 'w') as f:
                json.dump(user.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving user: {str(e)}")
            return False
    
    def add_user(self, user: User) -> bool:
        """Add a new user to storage."""
        try:
            # Check if user with same ID, username, or email already exists
            if user.id in self.users:
                return False
                
            for existing_user in self.users.values():
                if (existing_user.username and user.username and 
                    existing_user.username.lower() == user.username.lower()):
                    return False
                if (existing_user.email and user.email and 
                    existing_user.email.lower() == user.email.lower()):
                    return False
            
            # Save the new user
            return self.save_user(user)
        except Exception as e:
            print(f"Error adding user: {str(e)}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user from storage."""
        try:
            if user_id in self.users:
                del self.users[user_id]
            
            user_file = Path(self.storage_path) / f"{user_id}.json"
            if user_file.exists():
                user_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting user: {str(e)}")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        for user in self.users.values():
            if user.username and user.username.lower() == username.lower():
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        for user in self.users.values():
            if user.email and user.email.lower() == email.lower():
                return user
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all users."""
        return list(self.users.values()) 