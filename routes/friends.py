from flask import Blueprint, jsonify, request
from models.auth import AuthUser
from bson import ObjectId
from functools import wraps
from routes.auth import token_required

friends_bp = Blueprint('friends', __name__)

@friends_bp.route('/', methods=['GET'])
@token_required
def get_friends(current_user):
    try:
        print(f"\nFetching friends for user: {current_user.username}")
        # Extract IDs from friend objects
        friend_ids = [friend.id for friend in current_user.friends]
        print(f"Friend IDs: {[str(id) for id in friend_ids]}")
        
        friends = AuthUser.objects(id__in=friend_ids).only('username', 'online')
        friend_list = [{
            "id": str(friend.id),
            "username": friend.username,
            "online": friend.online
        } for friend in friends]
        
        print(f"Found {len(friend_list)} friends: {friend_list}")
        return jsonify(friend_list)
    except Exception as e:
        print(f"Error in get_friends: {str(e)}")
        return jsonify({"message": str(e)}), 500

@friends_bp.route('/requests', methods=['GET'])
@token_required
def get_friend_requests(current_user):
    try:
        pending_requests = []
        print(f"\nFetching friend requests for user: {current_user.username}")
        print(f"Total friend requests: {len(current_user.friend_requests)}")
        
        for request in current_user.get_pending_requests():
            print(f"Processing request: {request.to_json()}")
            from_user = AuthUser.objects(id=request.from_user.id).only('username').first()
            if from_user:
                request_data = {
                    "id": str(request.request_id),
                    "from": {
                        "username": from_user.username,
                        "id": str(from_user.id)
                    },
                    "status": request.status,
                    "created_at": request.created_at.isoformat()
                }
                print(f"Adding request to response: {request_data}")
                pending_requests.append(request_data)

        # Sort by creation date to ensure consistent order
        pending_requests.sort(key=lambda x: x['created_at'])
        print(f"Returning {len(pending_requests)} pending requests")
        return jsonify(pending_requests)
    except Exception as e:
        print(f"Error in get_friend_requests: {str(e)}")
        return jsonify({"message": str(e)}), 500

@friends_bp.route('/request/<username>', methods=['POST'])
@token_required
def send_friend_request(current_user, username):
    try:
        if current_user.username == username:
            return jsonify({"message": "Cannot send friend request to yourself"}), 400

        target_user = AuthUser.objects(username=username).first()
        if not target_user:
            return jsonify({"message": "User not found"}), 404

        # Check if they're already friends
        if target_user.id in [friend.id for friend in current_user.friends]:
            return jsonify({"message": "Already friends with this user"}), 400

        # Check if request already exists
        existing_request = any(
            str(req.from_user.id) == str(current_user.id) and req.status == 'pending'
            for req in target_user.friend_requests
        )
        if existing_request:
            return jsonify({"message": "Friend request already sent"}), 400

        # Check if there's a pending request from the target user
        reverse_request = any(
            str(req.from_user.id) == str(target_user.id) and req.status == 'pending'
            for req in current_user.friend_requests
        )
        if reverse_request:
            return jsonify({"message": "This user has already sent you a friend request"}), 400

        # Add friend request
        friend_request = target_user.add_friend_request(current_user)
        print(f"Created friend request: {friend_request.to_json()}")

        return jsonify({"message": "Friend request sent successfully"})
    except Exception as e:
        print(f"Error in send_friend_request: {str(e)}")
        return jsonify({"message": str(e)}), 500

@friends_bp.route('/accept/<request_id>', methods=['POST'])
@token_required
def accept_friend_request(current_user, request_id):
    try:
        # Clean the request_id by removing any trailing slashes
        request_id = request_id.rstrip('/')
        print(f"Looking for friend request with ID: {request_id}")
        print(f"Current user has {len(current_user.friend_requests)} friend requests")
        
        # Find the request
        request = current_user.get_friend_request_by_id(request_id)
        if not request:
            print(f"No friend request found with ID: {request_id}")
            print(f"Available request IDs: {[str(req.request_id) for req in current_user.friend_requests]}")
            return jsonify({"message": "Request not found"}), 404

        print(f"Found friend request: {request.to_json()}")
        
        # Update request status and add to friends lists
        request.status = "accepted"
        if request.from_user not in current_user.friends:
            current_user.friends.append(request.from_user)
        current_user.save()
        
        # Add current user to the requester's friends list
        from_user = AuthUser.objects(id=request.from_user.id).first()
        if from_user:
            if current_user not in from_user.friends:
                from_user.friends.append(current_user)
                from_user.save()

        return jsonify({"message": "Friend request accepted"})
    except Exception as e:
        print(f"Error in accept_friend_request: {str(e)}")
        return jsonify({"message": str(e)}), 500

@friends_bp.route('/reject/<request_id>', methods=['POST'])
@token_required
def reject_friend_request(current_user, request_id):
    try:
        # Find the request
        request = current_user.get_friend_request_by_id(request_id)
        if not request:
            return jsonify({"message": "Request not found"}), 404

        # Update request status
        request.status = "rejected"
        current_user.save()

        return jsonify({"message": "Friend request rejected"})
    except Exception as e:
        print(f"Error in reject_friend_request: {str(e)}")
        return jsonify({"message": str(e)}), 500

@friends_bp.route('/<friend_id>', methods=['DELETE'])
@token_required
def remove_friend(current_user, friend_id):
    try:
        # Remove from both users' friend lists
        current_user.update(
            pull__friends=ObjectId(friend_id)
        )
        AuthUser.objects(id=friend_id).update_one(
            pull__friends=current_user.id
        )

        return jsonify({"message": "Friend removed successfully"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500 