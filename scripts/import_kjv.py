# scripts/import_kjv.py
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the Python path properly
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

from models.bible import BibleVerse
from database import init_db

# Map of book names to their details
BOOKS_MAP = {
    'Genesis': ('GEN', 'old', 50),
    'Exodus': ('EXO', 'old', 40),
    'Leviticus': ('LEV', 'old', 27),
    'Numbers': ('NUM', 'old', 36),
    'Deuteronomy': ('DEU', 'old', 34),
    'Joshua': ('JOS', 'old', 24),
    'Judges': ('JDG', 'old', 21),
    'Ruth': ('RUT', 'old', 4),
    '1 Samuel': ('SA1', 'old', 31),
    '2 Samuel': ('SA2', 'old', 24),
    '1 Kings': ('KI1', 'old', 22),
    '2 Kings': ('KI2', 'old', 25),
    '1 Chronicles': ('CH1', 'old', 29),
    '2 Chronicles': ('CH2', 'old', 36),
    'Ezra': ('EZR', 'old', 10),
    'Nehemiah': ('NEH', 'old', 13),
    'Esther': ('EST', 'old', 10),
    'Job': ('JOB', 'old', 42),
    'Psalms': ('PSA', 'old', 150),
    'Proverbs': ('PRO', 'old', 31),
    'Ecclesiastes': ('ECC', 'old', 12),
    'Song of Solomon': ('SNG', 'old', 8),
    "Solomon's Song": ('SNG', 'old', 8),  # Added alternate name
    'Isaiah': ('ISA', 'old', 66),
    'Jeremiah': ('JER', 'old', 52),
    'Lamentations': ('LAM', 'old', 5),
    'Ezekiel': ('EZK', 'old', 48),
    'Daniel': ('DAN', 'old', 12),
    'Hosea': ('HOS', 'old', 14),
    'Joel': ('JOL', 'old', 3),
    'Amos': ('AMO', 'old', 9),
    'Obadiah': ('OBA', 'old', 1),
    'Jonah': ('JON', 'old', 4),
    'Micah': ('MIC', 'old', 7),
    'Nahum': ('NAH', 'old', 3),
    'Habakkuk': ('HAB', 'old', 3),
    'Zephaniah': ('ZEP', 'old', 3),
    'Haggai': ('HAG', 'old', 2),
    'Zechariah': ('ZEC', 'old', 14),
    'Malachi': ('MAL', 'old', 4),
    'Matthew': ('MAT', 'new', 28),
    'Mark': ('MRK', 'new', 16),
    'Luke': ('LUK', 'new', 24),
    'John': ('JHN', 'new', 21),
    'Acts': ('ACT', 'new', 28),
    'Romans': ('ROM', 'new', 16),
    '1 Corinthians': ('CO1', 'new', 16),
    '2 Corinthians': ('CO2', 'new', 13),
    'Galatians': ('GAL', 'new', 6),
    'Ephesians': ('EPH', 'new', 6),
    'Philippians': ('PHP', 'new', 4),
    'Colossians': ('COL', 'new', 4),
    '1 Thessalonians': ('TH1', 'new', 5),
    '2 Thessalonians': ('TH2', 'new', 3),
    '1 Timothy': ('TI1', 'new', 6),
    '2 Timothy': ('TI2', 'new', 4),
    'Titus': ('TIT', 'new', 3),
    'Philemon': ('PHM', 'new', 1),
    'Hebrews': ('HEB', 'new', 13),
    'James': ('JAS', 'new', 5),
    '1 Peter': ('PE1', 'new', 5),
    '2 Peter': ('PE2', 'new', 3),
    '1 John': ('JO1', 'new', 5),
    '2 John': ('JO2', 'new', 1),
    '3 John': ('JO3', 'new', 1),
    'Jude': ('JUD', 'new', 1),
    'Revelation': ('REV', 'new', 22)
}

def parse_reference(ref):
    """Parse a reference like 'Genesis 1:1' into (book_name, chapter, verse)"""
    book_chapter, verse = ref.rsplit(':', 1)
    book_parts = book_chapter.rsplit(' ', 1)
    chapter = book_parts[-1]
    book_name = ' '.join(book_parts[:-1])
    return book_name, int(chapter), int(verse)

def clean_verse_text(text):
    """Clean verse text by removing any leading '#' and trimming whitespace"""
    return text.lstrip('#').strip()

def import_kjv_data(json_path):
    """Import KJV Bible data from the JSON file into MongoDB"""
    print(f"Reading JSON file from: {json_path}")
    
    # Initialize MongoDB connection
    load_dotenv()
    init_db()
    
    # Clear existing verses
    BibleVerse.objects.delete()
    print("Cleared existing verses from database")
    
    # Read and insert verses
    with open(json_path, 'r', encoding='utf-8') as f:
        verses_data = json.load(f)
    
    verse_count = 0
    skipped_verses = []
    verses_to_insert = []
    
    for ref, text in verses_data.items():
        try:
            book_name, chapter, verse = parse_reference(ref)
            if book_name in BOOKS_MAP:
                clean_text = clean_verse_text(text)
                
                verse_doc = BibleVerse(
                    book_name=book_name,
                    chapter=chapter,
                    verse=verse,
                    text=clean_text,
                    translation='KJV'
                )
                verses_to_insert.append(verse_doc)
                
                verse_count += 1
                if verse_count % 1000 == 0:
                    print(f"Processed {verse_count} verses...")
                    # Batch insert every 1000 verses
                    BibleVerse.objects.insert(verses_to_insert)
                    verses_to_insert = []
            else:
                skipped_verses.append(ref)
                print(f"Warning: Unknown book '{book_name}' in reference '{ref}'")
        except Exception as e:
            print(f"Error processing reference '{ref}': {e}")
    
    # Insert any remaining verses
    if verses_to_insert:
        BibleVerse.objects.insert(verses_to_insert)
    
    print(f"\nImport complete!")
    print(f"Processed {verse_count} verses")
    if skipped_verses:
        print(f"Skipped {len(skipped_verses)} verses due to unknown book names")
    
    # Verify expected verse count
    expected_verses = sum(chapters for _, (_, _, chapters) in BOOKS_MAP.items())
    actual_verses = BibleVerse.objects.count()
    if actual_verses < expected_verses:
        print(f"\nWarning: Expected approximately {expected_verses} verses but only processed {actual_verses}")
        print("Some verses may be missing from the import.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_kjv.py <path_to_kjv.json>")
        sys.exit(1)
        
    json_path = sys.argv[1]
    import_kjv_data(json_path)