from functools import wraps
from flask import request, jsonify
from appwrite.client import Client
from appwrite.services.account import Account
import os

def get_user_client(jwt_token):
    """Create a user-specific Appwrite client"""
    user_client = Client()
    user_client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
    user_client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
    user_client.set_jwt(jwt_token)
    return user_client

def auth_required(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            jwt_token = auth_header.split(' ')[1]
            user_client = get_user_client(jwt_token)
            user_account = Account(user_client)
            user = user_account.get()
            kwargs['user'] = user
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated_function