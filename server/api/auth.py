from functools import wraps
from flask import request, jsonify, current_app

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            token = auth_header.split(' ')[1]
            supabase = current_app.supabase
            
            user_response = supabase.auth.get_user(token)
            if not user_response or not user_response.user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            user = user_response.user
            kwargs['user'] = {
                '$id': user.id,
                'id': user.id,
                'email': user.email,
                'emailVerification': user.email_confirmed_at is not None
            }
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated_function