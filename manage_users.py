#!/usr/bin/env python3
"""
Manage Daria Interview Tool users
Usage:
    python manage_users.py list
    python manage_users.py create <username> <email> <password> <role>
    python manage_users.py reset <username> <new_password>
    python manage_users.py delete <username>
    
Roles: admin, researcher, user
"""

import sys
import os
from models.user import User, UserRepository

def list_users():
    """List all existing users in the system."""
    repo = UserRepository()
    
    print(f"\nUser storage path: {repo.storage_path}")
    
    if not os.path.exists(repo.storage_path):
        print(f"User directory not found: {repo.storage_path}")
        return
    
    print("\nExisting Users:")
    print("-" * 80)
    print(f"{'ID':<36} {'Username':<15} {'Email':<25} {'Role':<10} {'Last Login'}")
    print("-" * 80)
    
    for user_id, user in repo.users.items():
        username = user.username
        email = user.email
        role = user.role
        last_login = user.last_login or "Never"
        
        print(f"{user_id:<36} {username:<15} {email:<25} {role:<10} {last_login}")
    
    print("-" * 80)
    print(f"Total users: {len(repo.users)}")

def create_user(username, email, password, role):
    """Create a new user."""
    if role not in ['admin', 'researcher', 'user']:
        print(f"Error: Invalid role '{role}'. Must be 'admin', 'researcher', or 'user'.")
        return
    
    repo = UserRepository()
    
    # Check if user already exists
    if repo.get_user_by_username(username):
        print(f"Error: Username '{username}' already exists.")
        return
    
    if repo.get_user_by_email(email):
        print(f"Error: Email '{email}' already exists.")
        return
    
    # Create user
    user = User(
        username=username,
        email=email,
        role=role
    )
    user.set_password(password)
    
    # Save user
    success = repo.save_user(user)
    if success:
        print(f"User created successfully:")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Role: {role}")
        print(f"ID: {user.id}")
    else:
        print("Failed to create user.")

def reset_password(username, new_password):
    """Reset a user's password."""
    repo = UserRepository()
    
    # Find user
    user = repo.get_user_by_username(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        return
    
    # Update password
    user.set_password(new_password)
    
    # Save user
    success = repo.save_user(user)
    if success:
        print(f"Password reset successfully for user '{username}'.")
    else:
        print(f"Failed to reset password for user '{username}'.")

def delete_user(username):
    """Delete a user."""
    repo = UserRepository()
    
    # Find user
    user = repo.get_user_by_username(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        return
    
    # Delete user
    success = repo.delete_user(user.id)
    if success:
        print(f"User '{username}' deleted successfully.")
    else:
        print(f"Failed to delete user '{username}'.")

def print_usage():
    print(__doc__)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_users()
    
    elif command == "create":
        if len(sys.argv) < 6:
            print("Error: Missing arguments for create command.")
            print_usage()
            sys.exit(1)
        
        username = sys.argv[2]
        email = sys.argv[3]
        password = sys.argv[4]
        role = sys.argv[5]
        
        create_user(username, email, password, role)
    
    elif command == "reset":
        if len(sys.argv) < 4:
            print("Error: Missing arguments for reset command.")
            print_usage()
            sys.exit(1)
        
        username = sys.argv[2]
        new_password = sys.argv[3]
        
        reset_password(username, new_password)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Missing arguments for delete command.")
            print_usage()
            sys.exit(1)
        
        username = sys.argv[2]
        
        delete_user(username)
    
    else:
        print(f"Error: Unknown command '{command}'.")
        print_usage()
        sys.exit(1) 