from functools import wraps
from flask import abort, request, current_app
from flask_login import current_user

def role_required(*roles):
    """Decorator to restrict access based on user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not any(getattr(current_user, f'is_{role}') for role in roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verify_api_key():
    """Verify API key from request headers"""
    from .models import User
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        abort(401, description="API key is required")
    
    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        abort(401, description="Invalid API key")
    
    return user

def api_key_required(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = verify_api_key()
        # Store the authenticated user for the request
        request.authenticated_user = user
        return f(*args, **kwargs)
    return decorated_function

def check_session_token():
    """Verify session token from request"""
    from .models import User
    token = request.cookies.get('session_token')
    if not token:
        return None
    
    user = User.query.filter_by(session_token=token).first()
    if not user or not user.check_session_token(token):
        return None
    
    return user 