from mongoengine import Document, StringField, BooleanField, ListField, ReferenceField, EmbeddedDocument, EmbeddedDocumentField, DateTimeField, ObjectIdField, IntField, FloatField, DictField
from datetime import datetime
from bson import ObjectId
import bcrypt
import re

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

class AIPreferences(EmbeddedDocument):
    model_temperature = FloatField(default=0.7, min_value=0, max_value=1)
    response_length = IntField(default=200, min_value=50, max_value=500)
    writing_style = StringField(choices=['academic', 'casual', 'devotional'], default='devotional')
    preferred_topics = ListField(StringField(), default=list)
    challenge_level = FloatField(default=0.5, min_value=0, max_value=1)
    depth_level = StringField(choices=['beginner', 'intermediate', 'scholarly'], default='intermediate')
    time_orientation = FloatField(default=0.5, min_value=0, max_value=1)
    user_context = DictField(default=dict)
    
    def to_json(self):
        return {
            "model_temperature": self.model_temperature,
            "response_length": self.response_length,
            "writing_style": self.writing_style,
            "preferred_topics": self.preferred_topics,
            "challenge_level": self.challenge_level,
            "depth_level": self.depth_level,
            "time_orientation": self.time_orientation,
            "user_context": self.user_context or {}
        }

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
    ai_preferences = EmbeddedDocumentField(AIPreferences, default=AIPreferences)
    
    meta = {
        'collection': 'users'
    }
    
    def set_password(self, password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        self.password_hash = hashed.decode('utf-8')
        
    def check_password(self, password):
        # First try bcrypt
        try:
            if bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8')):
                return True
        except Exception:
            pass  # Not a bcrypt hash, try legacy method next
            
        # Check if it's a Werkzeug hash (pbkdf2:sha256:...)
        if self.password_hash.startswith(('pbkdf2:', 'scrypt:')):
            try:
                from werkzeug.security import check_password_hash
                if check_password_hash(self.password_hash, password):
                    # Migrate to bcrypt
                    self.set_password(password)
                    self.save()
                    return True
            except Exception:
                pass
                
        return False
        
    def to_json(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_premium": self.is_premium,
            "online": self.online,
            "can_view_friend_notes": self.can_view_friend_notes,
            "share_notes_with_friends": self.share_notes_with_friends,
            "ai_preferences": self.ai_preferences.to_json() if self.ai_preferences else None
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