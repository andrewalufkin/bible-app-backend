from mongoengine import Document, StringField, IntField

class BibleVerse(Document):
    book_name = StringField(required=True)
    chapter = IntField(required=True)
    verse = IntField(required=True)
    text = StringField(required=True)
    translation = StringField(default='KJV')

    meta = {
        'collection': 'bible_verses',
        'indexes': [
            'book_name',
            ('book_name', 'chapter'),
            ('book_name', 'chapter', 'verse'),
            {
                'fields': [('text', 'text')],
                'default_language': 'english'
            }
        ]
    }
    
    def to_json(self):
        return {
            "id": str(self.id),
            "book_name": self.book_name,
            "chapter": self.chapter,
            "verse": self.verse,
            "text": self.text,
            "translation": self.translation
        } 