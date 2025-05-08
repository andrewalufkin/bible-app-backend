from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class BookmarkBase(BaseModel):
    book: str = Field(..., max_length=100)
    chapter: int
    verse: int
    text_preview: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class BookmarkCreate(BookmarkBase):
    pass

class BookmarkRead(BookmarkBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True # For compatibility with SQLAlchemy models 