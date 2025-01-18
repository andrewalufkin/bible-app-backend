from mongoengine import Document, StringField, ReferenceField, DateTimeField, EnumField
from datetime import datetime
from enum import Enum
from .auth import AuthUser

class NoteType(str, Enum):
    STUDY = "study"
    QUICK = "quick"

class Note(Document):
    user = ReferenceField(AuthUser, required=True)
    book = StringField(required=True)
    chapter = StringField(required=True)
    verse = StringField(required=True)
    content = StringField(required=True)
    note_type = EnumField(NoteType, required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'notes',
        'indexes': [
            {
                'fields': ['user', 'book', 'chapter', 'verse', 'note_type'],
                'unique': True
            }
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Note, self).save(*args, **kwargs)

    def to_json(self):
        return {
            "id": str(self.id),
            "book": self.book,
            "chapter": self.chapter,
            "verse": self.verse,
            "content": self.content,
            "note_type": self.note_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 