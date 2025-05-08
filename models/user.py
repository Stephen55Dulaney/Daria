from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class User(UserMixin):
    """User model for authentication."""
    
    def __init__(self, id=None, username="", email="", role="user", created_at=None):
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.email = email
        self.role = role  # 'admin', 'researcher', 'user'
        self.password_hash = None
        self.created_at = created_at or datetime.now().isoformat()
        self.last_login = None
    
    def set_password(self, password: str) -> None:
        """Set password hash from plain text password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'last_login': self.last_login,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user object from dictionary."""
        user = cls(
            id=data.get('id'),
            username=data.get('username', ''),
            email=data.get('email', ''),
            role=data.get('role', 'user'),
            created_at=data.get('created_at')
        )
        user.password_hash = data.get('password_hash')
        user.last_login = data.get('last_login')
        return user


class UserRepository:
    """Repository for user data storage and retrieval."""
    
    def __init__(self, storage_path: str = 'data/users'):
        import os
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.users = {}
        self._load_users()
    
    def _load_users(self) -> None:
        """Load users from disk."""
        import json
        import os
        
        for file_path in self.storage_path.glob('*.json'):
            try:
                with open(file_path, 'r') as f:
                    user_data = json.load(f)
                    user = User.from_dict(user_data)
                    self.users[user.id] = user
            except Exception as e:
                print(f"Error loading user {file_path}: {e}")
        
        # Create default admin if no users exist
        if not self.users:
            admin = User(username="admin", email="admin@example.com", role="admin")
            admin.set_password("admin")  # Default password - should be changed
            self.save_user(admin)
    
    def save_user(self, user: User) -> bool:
        """Save user to disk."""
        import json
        
        self.users[user.id] = user
        file_path = self.storage_path / f"{user.id}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(user.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving user {user.id}: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self.users.values():
            if user.username.lower() == username.lower():
                return user
        return None
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user from disk."""
        import os
        
        if user_id not in self.users:
            return False
        
        file_path = self.storage_path / f"{user_id}.json"
        
        try:
            if file_path.exists():
                os.remove(file_path)
            
            if user_id in self.users:
                del self.users[user_id]
                
            return True
        except Exception as e:
            print(f"Error deleting user {user_id}: {e}")
            return False 