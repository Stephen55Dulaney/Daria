from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from .extensions import db
from .auth_utils import role_required
import secrets

auth_bp = Blueprint('auth', __name__)

VALID_ROLES = ['admin', 'interviewer', 'manager', 'viewer']

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        from .models import User
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return redirect(url_for('auth.login'))
            
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            # Generate new session token
            session_token = user.generate_session_token()
            db.session.commit()
            
            response = redirect(request.args.get('next') or url_for('home'))
            # Set session token cookie
            response.set_cookie(
                'session_token',
                session_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=86400  # 24 hours
            )
            return response
            
        flash('Invalid email or password', 'error')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        from .models import User
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role', 'viewer')
        
        if not all([email, password, name]):
            flash('Please fill in all fields', 'error')
            return redirect(url_for('register'))
            
        if role not in VALID_ROLES:
            flash('Invalid role selected', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
            
        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
        
    return render_template('auth/register.html', roles=VALID_ROLES)

@auth_bp.route('/logout')
@login_required
def logout():
    if current_user.is_authenticated:
        # Clear session token
        current_user.session_token = None
        current_user.session_expiry = None
        db.session.commit()
    logout_user()
    response = redirect(url_for('auth.login'))
    response.delete_cookie('session_token')
    return response

@auth_bp.route('/api/token', methods=['POST'])
@login_required
def get_api_token():
    """Get or generate API token for the current user"""
    if not current_user.api_key:
        current_user.api_key = secrets.token_urlsafe(32)
        db.session.commit()
    
    return jsonify({
        'api_key': current_user.api_key
    })

@auth_bp.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def list_users():
    """List all users (admin only)"""
    from .models import User
    users = User.query.all()
    return render_template('auth/users.html', users=[user.to_dict() for user in users])

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_user(user_id):
    """Update user role (admin only)"""
    from .models import User
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'role' in data:
        if data['role'] not in VALID_ROLES:
            return jsonify({'error': 'Invalid role'}), 400
        user.role = data['role']
        db.session.commit()
    
    return jsonify(user.to_dict()) 