from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime
import secrets
import os

from models.user import User, UserRepository
from forms.auth import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm

# Create Blueprint for auth routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize user repository
user_repository = UserRepository()

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return user_repository.get_user(user_id)

# Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username or email
        user = user_repository.get_user_by_username(form.username.data)
        if user is None:
            user = user_repository.get_user_by_email(form.username.data)
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Update last login time
        user.last_login = datetime.now().isoformat()
        user_repository.save_user(user)
        
        # Log in the user
        login_user(user, remember=form.remember_me.data)
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        if user_repository.save_user(user):
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Error creating user. Please try again.', 'danger')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = user_repository.get_user_by_email(form.email.data)
        if user:
            # In a real application, you would send an email with a reset link
            # For this minimal implementation, we'll just show a success message
            flash('Check your email for instructions to reset your password', 'info')
            return redirect(url_for('auth.login'))
        
        # Don't reveal that the user doesn't exist
        flash('Check your email for instructions to reset your password', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # In a real application, you would validate the token
    # For this minimal implementation, we'll just show the form
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # In a real application, you would find the user from the token
        flash('Your password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form, token=token)

# Add auth middleware
def init_auth(app):
    """Initialize authentication for the app."""
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    
    # Create users directory if it doesn't exist
    os.makedirs('data/users', exist_ok=True) 