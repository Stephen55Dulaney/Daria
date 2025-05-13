#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from daria_interview_tool import create_app
from daria_interview_tool.extensions import db
from daria_interview_tool.models import User
from flask import Flask

def create_admin_user(email, password, name):
    """Create an admin user in the database"""
    app = create_app()
    
    with app.app_context():
        # Check if admin user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists. Updating to admin role.")
            existing_user.role = 'admin'
            existing_user.set_password(password)
            existing_user.name = name
            db.session.commit()
            return
            
        # Create new admin user
        user = User(email=email, name=name, role='admin')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin user {email} created successfully.")

def update_admin_password(email, password):
    """Update an existing admin user's password."""
    user = User.query.filter_by(email=email).first()
    if user:
        user.set_password(password)
        db.session.commit()
        print(f"Updated password for admin user {email}")
    else:
        print(f"User with email {email} does not exist")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <email> <password> <name>")
        sys.exit(1)
        
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3]
    
    create_admin_user(email, password, name)

    app = create_app()
    with app.app_context():
        # Try to create new admin
        if not create_admin_user(email, password, name):
            # If user exists, update their password
            update_admin_password(email, password) 