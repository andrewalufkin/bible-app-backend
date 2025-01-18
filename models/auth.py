from mongoengine import Document, StringField, BooleanField, ListField, ReferenceField, EmbeddedDocument, EmbeddedDocumentField, DateTimeField, ObjectIdField
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson import ObjectId

class FriendRequest(EmbeddedDocument):
    request_id = ObjectIdField(default=lambda: ObjectId(), required=True)
    from_user = ReferenceField('AuthUser', required=True)
    status = StringField(choices=['pending', 'accepted', 'rejected'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)

    def to_json(self):
        return {
            "id": str(self.request_id),
            "from_user": str(self.from_user.id),
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

    def __eq__(self, other):
        if isinstance(other, FriendRequest):
            return str(self.request_id) == str(other.request_id)
        return False

    def __hash__(self):
        return hash(str(self.request_id))

class AuthUser(Document):
    username = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    is_premium = BooleanField(default=False)
    friends = ListField(ReferenceField('self'), default=list)
    friend_requests = ListField(EmbeddedDocumentField(FriendRequest), default=list)
    online = BooleanField(default=False)
    can_view_friend_notes = BooleanField(default=True)
    share_notes_with_friends = BooleanField(default=True)
    
    meta = {
        'collection': 'users'
    }
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_json(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_premium": self.is_premium,
            "online": self.online,
            "can_view_friend_notes": self.can_view_friend_notes,
            "share_notes_with_friends": self.share_notes_with_friends
        }

    def add_friend_request(self, from_user):
        friend_request = FriendRequest(
            from_user=from_user,
            status='pending'
        )
        self.friend_requests.append(friend_request)
        self.save()
        return friend_request

    def get_friend_request_by_id(self, request_id):
        for request in self.friend_requests:
            if str(request.request_id) == str(request_id):
                return request
        return None

    def get_pending_requests(self):
        return [req for req in self.friend_requests if req.status == 'pending'] 