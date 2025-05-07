# utils/auth.py
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
import os
import logging

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')  # In production, use a proper secret key
JWT_EXPIRATION_HOURS = 24

# !!! TEMPORARY DEBUG LOG - REMOVE AFTER USE !!!
# print(f"[AUTH DEBUG] JWT_SECRET being used by backend: {JWT_SECRET}") # REMOVED FOR SECURITY
# !!! END TEMPORARY DEBUG LOG !!!

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(password, hashed):
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def generate_token(user_id):
    """Generate a JWT token for a user"""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode(
        {
            'user_id': user_id,
            'exp': expiration
        },
        JWT_SECRET,
        algorithm='HS256'
    )

def token_required(f):
    """Decorator to protect routes with JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        logger.info(f"token_required decorator executing for: {request.path}")
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            logger.info(f"Authorization header found: {auth_header[:15]}...")
            try:
                token = auth_header.split(" ")[1]
                logger.info(f"Token extracted: {token[:10]}...")
            except IndexError:
                logger.warning("Invalid token format in Authorization header.")
                return jsonify({'error': 'Invalid token format'}), 401
        else:
            logger.warning("Authorization header missing.")

        if not token:
            logger.warning("Token is missing or could not be extracted.")
            return jsonify({'error': 'Token is required'}), 401

        try:
            logger.info(f"[AUTH DEBUG] Attempting to decode token: {token[:15]}... with secret: {JWT_SECRET[:10]}... (and on file load: {os.getenv('JWT_SECRET')[:10]}...)")
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience='authenticated')
            current_user_id = data['sub']
            logger.info(f"Token successfully decoded for user_id (from sub claim): {current_user_id}")
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired.")
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
             logger.error(f"An unexpected error occurred during token decoding: {e}")
             return jsonify({'error': 'Token processing error'}), 500

        return f(current_user_id, *args, **kwargs)

    return decorated

def premium_required(f):
    """Decorator to protect premium-only routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is required'}), 401

        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience='authenticated')
            current_user_id = data['sub']
            
            # Check if user is premium
            from database import get_db_connection
            conn = get_db_connection()
            user = conn.execute(
                'SELECT is_premium FROM users WHERE id = ?', 
                (current_user_id,)
            ).fetchone()
            conn.close()

            if not user or not user['is_premium']:
                return jsonify({'error': 'Premium subscription required'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated