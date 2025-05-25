from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import uuid
import secrets
from .extensions import db

class User(UserMixin, db.Model):
    """User model with role-based access control"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    role = db.Column(db.String(20), nullable=False)  # admin, interviewer, manager, viewer
    api_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    session_token = db.Column(db.String(64))
    session_expiry = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_session_token(self, expiry_hours=24):
        self.session_token = secrets.token_urlsafe(32)
        self.session_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        return self.session_token

    def check_session_token(self, token):
        return (self.session_token == token and 
                self.session_expiry and 
                self.session_expiry > datetime.utcnow())

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_interviewer(self):
        return self.role in ['admin', 'interviewer']

    @property
    def is_manager(self):
        return self.role in ['admin', 'manager']

    @property
    def is_viewer(self):
        return True  # All roles can view

    def can_edit_interviews(self):
        return self.role in ['admin', 'interviewer']

    def can_manage_projects(self):
        return self.role in ['admin', 'manager']

    def can_manage_users(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

# ... existing code ... 