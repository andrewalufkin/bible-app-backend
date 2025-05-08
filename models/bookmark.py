from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base # Assuming Base is in a 'database.py' at the root of 'backend'

class Bookmark(Base):
    __tablename__ = 'bookmarks'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    book = Column(String(100), nullable=False, index=True) # E.g., "Genesis", "Revelation"
    chapter = Column(Integer, nullable=False, index=True)  # E.g., 1, 23
    verse = Column(Integer, nullable=False, index=True)    # E.g., 1, 15

    text_preview = Column(String(255), nullable=True) # Store a short preview of the verse
    notes = Column(Text, nullable=True) # Optional user notes for the bookmark

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at can be added if bookmarks are editable beyond simple notes

    # Relationship to User
    user = relationship("User", back_populates="bookmarks")

    def __repr__(self):
        return f'<Bookmark {self.id} User: {self.user_id} - {self.book} {self.chapter}:{self.verse}>' 