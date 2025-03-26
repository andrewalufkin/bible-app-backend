# routes/auth.py
from flask import Blueprint, request, jsonify
import jwt
import datetime
from models.auth import AuthUser
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()
auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
            current_user = AuthUser.objects(id=data['user_id']).first()
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
        except:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password') or not data.get('username'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user already exists
    if AuthUser.objects(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 400
    
    if AuthUser.objects(username=data['username']).first():
        return jsonify({'message': 'Username already taken'}), 400
    
    # Create new user
    new_user = AuthUser(
        email=data['email'],
        username=data['username']
    )
    new_user.set_password(data['password'])
    new_user.save()
    
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400
    
    user = AuthUser.objects(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    token = jwt.encode({
        'user_id': str(user.id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, os.getenv('JWT_SECRET'))
    
    return jsonify({
        'token': token,
        'user': user.to_json()
    })

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify(current_user.to_json())

@auth_bp.route('/premium', methods=['POST'])
@token_required
def upgrade_to_premium(current_user):
    current_user.is_premium = True
    current_user.save()
    return jsonify({'message': 'Upgraded to premium successfully', 'user': current_user.to_json()})

@auth_bp.route('/premium/cancel', methods=['POST'])
@token_required
def cancel_premium(current_user):
    current_user.is_premium = False
    current_user.save()
    return jsonify({'message': 'Premium subscription cancelled', 'user': current_user.to_json()})

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    current_user.online = False
    current_user.save()
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/delete-account', methods=['DELETE'])
@token_required
def delete_account(current_user):
    try:
        # Remove this user from all other users' friends lists
        AuthUser.objects(friends=current_user.id).update(
            pull__friends=current_user.id
        )
        
        # Delete the user's account
        current_user.delete()
        
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        print(f"Error deleting account: {str(e)}")
        return jsonify({'message': 'Failed to delete account'}), 500

@auth_bp.route('/settings/notes', methods=['POST'])
@token_required
def update_note_settings(current_user):
    try:
        data = request.get_json()
        
        # Update the user's note privacy settings
        current_user.can_view_friend_notes = data.get('can_view_friend_notes', True)
        current_user.share_notes_with_friends = data.get('share_notes_with_friends', True)
        current_user.save()
        
        return jsonify({
            'id': str(current_user.id),
            'username': current_user.username,
            'email': current_user.email,
            'is_premium': current_user.is_premium,
            'can_view_friend_notes': current_user.can_view_friend_notes,
            'share_notes_with_friends': current_user.share_notes_with_friends
        })
    except Exception as e:
        print(f"Error updating note settings: {str(e)}")
        return jsonify({'message': 'Failed to update note settings'}), 500

@auth_bp.route('/settings/ai', methods=['POST'])
@token_required
def update_ai_preferences(current_user):
    try:
        data = request.get_json()
        
        # Update AI preferences if provided
        if 'model_temperature' in data:
            current_user.ai_preferences.model_temperature = data['model_temperature']
            
        if 'response_length' in data:
            current_user.ai_preferences.response_length = data['response_length']
            
        if 'writing_style' in data:
            current_user.ai_preferences.writing_style = data['writing_style']
            
        if 'preferred_topics' in data:
            current_user.ai_preferences.preferred_topics = data['preferred_topics']
            
        if 'challenge_level' in data:
            current_user.ai_preferences.challenge_level = data['challenge_level']
            
        if 'depth_level' in data:
            current_user.ai_preferences.depth_level = data['depth_level']
            
        if 'time_orientation' in data:
            current_user.ai_preferences.time_orientation = data['time_orientation']
            
        if 'user_context' in data:
            current_user.ai_preferences.user_context = data['user_context']
            
        current_user.save()
        
        return jsonify({
            'message': 'AI preferences updated successfully',
            'ai_preferences': current_user.ai_preferences.to_json()
        })
    except Exception as e:
        print(f"Error updating AI preferences: {str(e)}")
        return jsonify({'message': 'Failed to update AI preferences'}), 500