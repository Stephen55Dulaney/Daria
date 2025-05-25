#!/usr/bin/env python
from daria_interview_tool import create_app
from daria_interview_tool.extensions import db
from daria_interview_tool.models import User

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Create admin user if not exists
    admin_email = "admin@example.com"
    if not User.query.filter_by(email=admin_email).first():
        admin = User(email=admin_email, name="Admin User", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user: {admin_email}")
    else:
        print(f"Admin user {admin_email} already exists")
    
    print("Database initialized successfully!") 