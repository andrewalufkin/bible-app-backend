# routes/bible.py
from flask import Blueprint, jsonify, request
from models.bible import BibleVerse
import logging
import sys

bible_bp = Blueprint('bible', __name__)

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@bible_bp.route('/books', methods=['GET'])
def get_books():
    try:
        logger.info("Attempting to fetch books from database")
        # Log MongoDB connection info (without sensitive data)
        logger.info(f"MongoDB connection status: {BibleVerse._get_db().client.is_primary}")
        
        # Get unique book names
        books = BibleVerse.objects().distinct('book_name')
        logger.info(f"Found {len(books)} books in database")
        
        if not books:
            logger.warning("No books found in database")
            return jsonify([])
        
        # Log the first few books to verify data
        logger.info(f"Sample of books found: {books[:5]}")
        
        # Sort books in biblical order (Old Testament first, then New Testament)
        biblical_order = [
            'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
            'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel', '1 Kings',
            '2 Kings', '1 Chronicles', '2 Chronicles', 'Ezra', 'Nehemiah',
            'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes',
            'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations',
            'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Obadiah',
            'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai',
            'Zechariah', 'Malachi',
            'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
            '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
            'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
            '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews',
            'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John',
            'Jude', 'Revelation'
        ]
        sorted_books = sorted(books, key=lambda x: biblical_order.index(x) if x in biblical_order else len(biblical_order))
        print(f"Returning sorted books: {sorted_books}")
        
        # Let's also check a sample verse to make sure data exists
        sample_verse = BibleVerse.objects.first()
        print(f"Sample verse from DB: {sample_verse.to_json() if sample_verse else 'No verses found'}")
        
        return jsonify(sorted_books)
    except Exception as e:
        logger.error(f"Error in get_books: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bible_bp.route('/chapters/<book>', methods=['GET'])
def get_chapters(book):
    try:
        # Validate book exists
        if not BibleVerse.objects(book_name=book).first():
            return jsonify({"error": "Book not found"}), 404
            
        # Get unique chapter numbers for the given book
        chapters = BibleVerse.objects(book_name=book).distinct('chapter')
        return jsonify(sorted(chapters))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bible_bp.route('/verses/<book>/<int:chapter>', methods=['GET'])
def get_verses(book, chapter):
    try:
        print(f"Fetching verses for {book} chapter {chapter}")
        
        # First check if the book exists
        if not BibleVerse.objects(book_name=book).first():
            print(f"Book not found: {book}")
            return jsonify({"error": f"Book '{book}' not found"}), 404
            
        # Then check if the chapter exists
        if not BibleVerse.objects(book_name=book, chapter=chapter).first():
            print(f"Chapter {chapter} not found in {book}")
            return jsonify({"error": f"Chapter {chapter} not found in {book}"}), 404
            
        verses = BibleVerse.objects(book_name=book, chapter=chapter).order_by('verse')
        results = [verse.to_json() for verse in verses]
        
        print(f"Found {len(results)} verses")
        return jsonify(results)
    except Exception as e:
        print(f"Error fetching verses: {str(e)}")
        return jsonify({"error": "Failed to fetch verses"}), 500

@bible_bp.route('/search', methods=['GET'])
def search_verses():
    try:
        query = request.args.get('q')
        if not query:
            return jsonify({"error": "No search query provided"}), 400

        print(f"Searching for: {query}")
        
        # Try text search first
        verses = BibleVerse.objects.search_text(query).order_by('-text_score')
        results = [verse.to_json() for verse in verses]
        
        # If no results found, try a case-insensitive contains search
        if not results:
            print("No text search results, trying contains search")
            verses = BibleVerse.objects(text__icontains=query).limit(50)
            results = [verse.to_json() for verse in verses]
        
        print(f"Found {len(results)} results")
        return jsonify(results)
    except Exception as e:
        print(f"Error in search: {str(e)}")
        return jsonify({"error": "Failed to perform search"}), 500

@bible_bp.route('/verse/<book>/<int:chapter>/<int:verse>', methods=['GET'])
def get_single_verse(book, chapter, verse):
    try:
        verse_obj = BibleVerse.objects(
            book_name=book,
            chapter=chapter,
            verse=verse
        ).first()
        
        if not verse_obj:
            return jsonify({"error": "Verse not found"}), 404
            
        return jsonify({
            "id": str(verse_obj.id),
            "book": verse_obj.book_name,
            "chapter": verse_obj.chapter,
            "verse": verse_obj.verse,
            "text": verse_obj.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add to_json method to BibleVerse model for debugging
def to_json(self):
    return {
        "id": str(self.id),
        "book_name": self.book_name,
        "chapter": self.chapter,
        "verse": self.verse,
        "text": self.text
    }