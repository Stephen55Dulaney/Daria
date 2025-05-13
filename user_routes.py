from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash
from datetime import datetime

from models.user import UserRepository, User

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def profile():
    """Display the user's profile page."""
    return render_template('profile.html')

@user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Handle password change requests."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate the form data
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required', 'danger')
        return redirect(url_for('user.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('user.profile'))
    
    # Verify current password
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('user.profile'))
    
    # Update password
    repo = UserRepository()
    user = repo.get_user_by_id(current_user.id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('user.profile'))
    
    user.set_password(new_password)
    success = repo.save_user(user)
    
    if success:
        flash('Password changed successfully', 'success')
    else:
        flash('Failed to change password', 'danger')
    
    return redirect(url_for('user.profile'))

@user_bp.route('/admin/users')
@login_required
def admin_users():
    """Display the user management page (admin only)."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    repo = UserRepository()
    users = list(repo.users.values())
    
    return render_template('admin/users.html', users=users)

@user_bp.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    """Add a new user (admin only)."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    # Validate form data
    if not username or not email or not password or not role:
        flash('All fields are required', 'danger')
        return redirect(url_for('user.admin_users'))
    
    if len(password) < 8:
        flash('Password must be at least 8 characters long', 'danger')
        return redirect(url_for('user.admin_users'))
    
    # Check if user already exists
    repo = UserRepository()
    if repo.get_user_by_username(username):
        flash(f'Username "{username}" is already taken', 'danger')
        return redirect(url_for('user.admin_users'))
    
    if repo.get_user_by_email(email):
        flash(f'Email "{email}" is already registered', 'danger')
        return redirect(url_for('user.admin_users'))
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        role=role
    )
    new_user.set_password(password)
    
    success = repo.add_user(new_user)
    
    if success:
        flash(f'User "{username}" created successfully', 'success')
    else:
        flash('Failed to create user', 'danger')
    
    return redirect(url_for('user.admin_users'))

@user_bp.route('/admin/users/reset-password', methods=['POST'])
@login_required
def reset_user_password():
    """Reset a user's password (admin only)."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate form data
    if not username or not new_password or not confirm_password:
        flash('All fields are required', 'danger')
        return redirect(url_for('user.admin_users'))
    
    if new_password != confirm_password:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('user.admin_users'))
    
    if len(new_password) < 8:
        flash('Password must be at least 8 characters long', 'danger')
        return redirect(url_for('user.admin_users'))
    
    # Get user and update password
    repo = UserRepository()
    user = repo.get_user_by_username(username)
    
    if not user:
        flash(f'User "{username}" not found', 'danger')
        return redirect(url_for('user.admin_users'))
    
    user.set_password(new_password)
    success = repo.save_user(user)
    
    if success:
        flash(f'Password for "{username}" reset successfully', 'success')
    else:
        flash('Failed to reset password', 'danger')
    
    return redirect(url_for('user.admin_users'))

@user_bp.route('/admin/users/delete', methods=['POST'])
@login_required
def delete_user():
    """Delete a user (admin only)."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    username = request.form.get('username')
    
    if not username:
        flash('Username is required', 'danger')
        return redirect(url_for('user.admin_users'))
    
    # Prevent deleting yourself
    if username == current_user.username:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('user.admin_users'))
    
    # Delete user
    repo = UserRepository()
    user = repo.get_user_by_username(username)
    
    if not user:
        flash(f'User "{username}" not found', 'danger')
        return redirect(url_for('user.admin_users'))
    
    success = repo.delete_user(user.id)
    
    if success:
        flash(f'User "{username}" deleted successfully', 'success')
    else:
        flash('Failed to delete user', 'danger')
    
    return redirect(url_for('user.admin_users')) 