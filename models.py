# models.py
from dataclasses import dataclass

@dataclass
class Book:
    id: str
    name: str
    chapters: int
    testament: str

@dataclass
class Verse:
    id: int
    book_id: str
    chapter: int
    verse: int
    text: str
    translation: str