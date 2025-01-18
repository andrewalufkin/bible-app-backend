from mongoengine import Document, StringField, ListField, ReferenceField, BooleanField, EmbeddedDocument, EmbeddedDocumentField, DateTimeField
from datetime import datetime

class FriendRequest(EmbeddedDocument):
    from_user = ReferenceField('User', required=True)
    status = StringField(choices=['pending', 'accepted', 'rejected'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)

class User(Document):
    username = StringField(required=True, unique=True)
    friends = ListField(ReferenceField('User'))
    friend_requests = ListField(EmbeddedDocumentField(FriendRequest))
    online = BooleanField(default=False)

    meta = {
        'collection': 'users'
    } 