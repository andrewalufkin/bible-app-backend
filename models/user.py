from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from database import Base # Change to direct import
from datetime import datetime

# Association table for the many-to-many relationship between users (friends)
# This might be needed if you keep the friends relationship similar to the MongoEngine version.
# We can refine this later.
friends_association_table = Table('friends_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('friend_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    # Supabase Auth typically handles email and password, so we might not need them here
    # email = Column(String, unique=True, index=True, nullable=True) # If storing email separately
    # hashed_password = Column(String, nullable=True) # If managing passwords outside Supabase Auth
    
    online = Column(Boolean, default=False)
    # Assuming created_at and updated_at are handled by Supabase or existing table defaults
    # created_at = Column(DateTime, default=datetime.utcnow)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    highlights = relationship("Highlight", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

    # Example for friends relationship (many-to-many)
    # We need to define how this works. The Mongo `friends = ListField(ReferenceField('User'))` implies a direct list.
    # SQLAlchemy requires an association table for many-to-many.
    # friends = relationship(
    #     "User",
    #     secondary=friends_association_table,
    #     primaryjoin=(friends_association_table.c.user_id == id),
    #     secondaryjoin=(friends_association_table.c.friend_id == id),
    #     backref="friend_of"
    # )

    # FriendRequests would likely become a separate table/model with a ForeignKey to User
    # friend_requests_received = relationship("FriendRequest", foreign_keys="[FriendRequest.to_user_id]", back_populates="to_user")
    # friend_requests_sent = relationship("FriendRequest", foreign_keys="[FriendRequest.from_user_id]", back_populates="from_user")

    def __repr__(self):
        return f'<User {self.username} (ID: {self.id})>'

# If you need a separate FriendRequest model:
# class FriendRequest(Base):
#     __tablename__ = 'friend_requests'
#     id = Column(Integer, primary_key=True, index=True)
#     from_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     to_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     status = Column(String, default='pending') # pending, accepted, rejected
#     created_at = Column(DateTime, default=datetime.utcnow)

#     from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_friend_requests")
#     to_user = relationship("User", foreign_keys=[to_user_id], backref="received_friend_requests")

#     def __repr__(self):
#         return f'<FriendRequest from {self.from_user_id} to {self.to_user_id} ({self.status})>' 