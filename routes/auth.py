# routes/auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
import os
from database import get_db
import logging
import time

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            with get_db() as client:
                # Verify the JWT token with Supabase
                user = client.auth.get_user(token)
                if not user:
                    return jsonify({'message': 'Invalid token!'}), 401
                return f(user, *args, **kwargs)
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return jsonify({'message': 'Invalid token!'}), 401

    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')

        if not all([email, password, username]):
            return jsonify({'error': 'Missing required fields'}), 400

        with get_db() as client:
            # Check if user exists
            existing_user = client.table('users').select('*').eq('email', email).execute()
            
            if existing_user.data:
                return jsonify({'error': 'User already exists'}), 400

            # Create new user
            try:
                auth_response = client.auth.sign_up({
                    'email': email,
                    'password': password
                })
            except Exception as e:
                if 'User already registered' in str(e):
                    return jsonify({'error': 'User already exists'}), 400
                raise e

            if not auth_response.user:
                return jsonify({'error': 'Failed to create user'}), 500

            # Create user profile in users table
            user_data = {
                'id': auth_response.user.id,
                'email': email,
                'username': username,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            try:
                response = client.table('users').insert(user_data).execute()
            except Exception as e:
                # If user profile creation fails, we should clean up the auth user
                try:
                    client.auth.admin.delete_user(auth_response.user.id)
                except:
                    pass
                raise e
            
            if not response.data:
                return jsonify({'error': 'Failed to create user profile'}), 500

            return jsonify({
                'message': 'Registration successful! Please check your email to confirm your account.',
                'user': {
                    'id': auth_response.user.id,
                    'email': email,
                    'username': username
                },
                'needsConfirmation': True
            }), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'error': 'Missing email or password'}), 400

        with get_db() as client:
            try:
                # Sign in with Supabase Auth
                auth_response = client.auth.sign_in_with_password({
                    'email': email,
                    'password': password
                })

                if not auth_response.user:
                    return jsonify({'error': 'Invalid credentials'}), 401

                # Get user profile
                response = client.table('users').select('*').eq('id', auth_response.user.id).execute()
                user = response.data[0] if response.data else None

                if not user:
                    return jsonify({'error': 'User profile not found'}), 404

                return jsonify({
                    'token': auth_response.session.access_token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'username': user['username']
                    }
                })

            except Exception as e:
                error_message = str(e)
                if 'Email not confirmed' in error_message:
                    return jsonify({
                        'error': 'Please check your email to confirm your account before logging in.',
                        'needsConfirmation': True,
                        'email': email
                    }), 401
                elif 'Invalid login credentials' in error_message:
                    return jsonify({'error': 'Invalid email or password'}), 401
                raise e

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    try:
        with get_db() as client:
            response = client.table('users').select('*').eq('id', current_user.id).execute()
            user = response.data[0] if response.data else None

            if not user:
                return jsonify({'error': 'User not found'}), 404

            return jsonify({
                'id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'created_at': user['created_at'],
                'updated_at': user['updated_at']
            })

    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    try:
        data = request.get_json()
        username = data.get('username')

        if not username:
            return jsonify({'error': 'Username is required'}), 400

        with get_db() as client:
            response = client.table('users').update({
                'username': username,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', current_user.id).execute()

            if not response.data:
                return jsonify({'error': 'Failed to update profile'}), 500

            return jsonify({
                'message': 'Profile updated successfully',
                'user': {
                    'id': current_user.id,
                    'email': current_user.email,
                    'username': username
                }
            })

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@auth_bp.route('/resend-confirmation', methods=['POST'])
def resend_confirmation():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        with get_db() as client:
            # Resend confirmation email
            response = client.auth.resend({
                'type': 'signup',
                'email': email
            })

            return jsonify({
                'message': 'Confirmation email has been resent. Please check your inbox.'
            }), 200

    except Exception as e:
        logger.error(f"Error resending confirmation email: {str(e)}")
        return jsonify({'error': str(e)}), 500