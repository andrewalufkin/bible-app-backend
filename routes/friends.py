from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.auth import token_required
from database import get_db
import logging

friends_bp = Blueprint('friends', __name__)
logger = logging.getLogger(__name__)

@friends_bp.route('/friends', methods=['GET'])
@token_required
def get_friends(current_user):
    try:
        with get_db() as client:
            # Get all friendships where the current user is either user1 or user2
            response = client.table('friendships').select(
                'id',
                'user1_id',
                'user2_id',
                'status',
                'created_at',
                'users!friendships_user1_id_fkey(id, username, email)',
                'users!friendships_user2_id_fkey(id, username, email)'
            ).or_(f'user1_id.eq.{current_user.id},user2_id.eq.{current_user.id}').execute()
            
            friendships = response.data
            
            # Process friendships to get friend information
            friends = []
            for friendship in friendships:
                # Determine which user is the friend (not the current user)
                friend = None
                if friendship['user1_id'] == current_user.id:
                    friend = friendship['users!friendships_user2_id_fkey']
                else:
                    friend = friendship['users!friendships_user1_id_fkey']
                
                if friend:
                    friends.append({
                        'id': friend['id'],
                        'username': friend['username'],
                        'email': friend['email'],
                        'friendship_id': friendship['id'],
                        'status': friendship['status'],
                        'created_at': friendship['created_at']
                    })
            
            return jsonify(friends)
            
    except Exception as e:
        logger.error(f"Error fetching friends: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/requests', methods=['GET'])
@token_required
def get_friend_requests(current_user):
    try:
        with get_db() as client:
            # Get pending friend requests where current user is the recipient
            response = client.table('friendships').select(
                'id',
                'user1_id',
                'created_at',
                'users!friendships_user1_id_fkey(id, username, email)'
            ).eq('user2_id', current_user.id).eq('status', 'pending').execute()
            
            requests = response.data
            
            return jsonify([{
                'id': request['id'],
                'user': {
                    'id': request['users!friendships_user1_id_fkey']['id'],
                    'username': request['users!friendships_user1_id_fkey']['username'],
                    'email': request['users!friendships_user1_id_fkey']['email']
                },
                'created_at': request['created_at']
            } for request in requests])
            
    except Exception as e:
        logger.error(f"Error fetching friend requests: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/request', methods=['POST'])
@token_required
def send_friend_request(current_user):
    try:
        data = request.get_json()
        friend_email = data.get('email')

        if not friend_email:
            return jsonify({'error': 'Email is required'}), 400

        with get_db() as client:
            # Check if friend exists
            friend_response = client.table('users').select('id').eq('email', friend_email).execute()
            if not friend_response.data:
                return jsonify({'error': 'User not found'}), 404

            friend_id = friend_response.data[0]['id']

            # Check if friendship already exists
            existing_response = client.table('friendships').select('*').or_(
                f'user1_id.eq.{current_user.id},user2_id.eq.{current_user.id}'
            ).or_(
                f'user1_id.eq.{friend_id},user2_id.eq.{friend_id}'
            ).execute()

            if existing_response.data:
                return jsonify({'error': 'Friendship already exists'}), 400

            # Create friend request
            friendship_data = {
                'user1_id': current_user.id,
                'user2_id': friend_id,
                'status': 'pending',
                'created_at': datetime.utcnow()
            }

            response = client.table('friendships').insert(friendship_data).execute()
            
            if not response.data:
                return jsonify({'error': 'Failed to send friend request'}), 500

            return jsonify({
                'message': 'Friend request sent successfully',
                'friendship': response.data[0]
            }), 201

    except Exception as e:
        logger.error(f"Error sending friend request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/request/<request_id>', methods=['PUT'])
@token_required
def respond_to_friend_request(current_user, request_id):
    try:
        data = request.get_json()
        action = data.get('action')  # 'accept' or 'reject'

        if action not in ['accept', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400

        with get_db() as client:
            # Verify request exists and is pending
            request_response = client.table('friendships').select('*').eq('id', request_id).eq('user2_id', current_user.id).eq('status', 'pending').execute()
            
            if not request_response.data:
                return jsonify({'error': 'Friend request not found'}), 404

            if action == 'accept':
                # Update friendship status to accepted
                response = client.table('friendships').update({
                    'status': 'accepted',
                    'updated_at': datetime.utcnow()
                }).eq('id', request_id).execute()
            else:
                # Delete the friendship request
                response = client.table('friendships').delete().eq('id', request_id).execute()

            if not response.data:
                return jsonify({'error': f'Failed to {action} friend request'}), 500

            return jsonify({
                'message': f'Friend request {action}ed successfully'
            })

    except Exception as e:
        logger.error(f"Error responding to friend request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@friends_bp.route('/friends/<friendship_id>', methods=['DELETE'])
@token_required
def remove_friend(current_user, friendship_id):
    try:
        with get_db() as client:
            # Verify friendship exists and involves current user
            friendship_response = client.table('friendships').select('*').eq('id', friendship_id).or_(
                f'user1_id.eq.{current_user.id},user2_id.eq.{current_user.id}'
            ).execute()
            
            if not friendship_response.data:
                return jsonify({'error': 'Friendship not found'}), 404

            # Delete the friendship
            response = client.table('friendships').delete().eq('id', friendship_id).execute()
            
            if not response.data:
                return jsonify({'error': 'Failed to remove friend'}), 500

            return jsonify({
                'message': 'Friend removed successfully'
            })

    except Exception as e:
        logger.error(f"Error removing friend: {str(e)}")
        return jsonify({'error': str(e)}), 500 