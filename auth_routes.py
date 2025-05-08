from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse as url_parse
import secrets
import os

from models.user import User, UserRepository
from forms.auth import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        repo = UserRepository()
        user = repo.get_user_by_username(form.username.data)
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Update last login timestamp
        from datetime import datetime
        user.last_login = datetime.now().isoformat()
        repo.save_user(user)
        
        # Log the user in
        login_user(user, remember=form.remember_me.data)
        
        # Redirect to the requested page, or dashboard if none
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
def logout():
    """Logout route."""
    logout_user()
    return redirect(url_for('dashboard'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        repo = UserRepository()
        
        # Check if username or email already exists
        if repo.get_user_by_username(form.username.data):
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if repo.get_user_by_email(form.email.data):
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create a new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='user'  # Default role
        )
        
        # Set the password
        user.set_password(form.password.data)
        
        # Save the user
        if not repo.save_user(user):
            flash('Failed to create user', 'danger')
            return redirect(url_for('auth.register'))
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Route to request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RequestPasswordResetForm()
    
    if form.validate_on_submit():
        repo = UserRepository()
        user = repo.get_user_by_email(form.email.data)
        
        if user:
            # In a real application, send an email with a password reset link
            # For this simple implementation, we'll just flash a message
            flash('Check your email for instructions to reset your password', 'info')
        else:
            flash('Email not found', 'danger')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Route to reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # In a real application, validate the token
    # For this simple implementation, we'll just show the form
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # In a real application, find the user from the token
        # For this simple implementation, we'll just flash a message
        flash('Your password has been reset', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Reset Password', form=form) 