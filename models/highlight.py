# backend/models/highlight.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Highlight(Base):
    __tablename__ = 'highlights'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    book = Column(String, nullable=False, index=True)
    chapter = Column(Integer, nullable=False, index=True)
    verse = Column(Integer, nullable=False, index=True)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    color = Column(String, nullable=False, default='#FFFF00') # Default yellow
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="highlights") # Add back_populates

    def __repr__(self):
        return f'<Highlight {self.user_id} {self.book} {self.chapter}:{self.verse} [{self.start_offset}-{self.end_offset}] {self.color}>' 