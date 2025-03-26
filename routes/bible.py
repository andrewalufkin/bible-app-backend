# routes/bible.py
from flask import Blueprint, jsonify, request
from models.bible import BibleVerse
import logging
import sys
import traceback
from utils.auth import token_required
from utils.search import BibleSearchEngine

bible_bp = Blueprint('bible', __name__)
search_engine = BibleSearchEngine()

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
        # Log request details
        logger.info(f"Request headers: {request.headers}")
        logger.info(f"Request path: {request.path}")
        
        # Define a static list of books to avoid database query when possible
        # This is a common optimization for static data
        biblical_books = [
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
        
        # First try a quick check to confirm database connectivity
        try:
            # Use count with a limit as a lightweight query to check connectivity
            sample_count = BibleVerse.objects().limit(1).count()
            logger.info(f"Database connection check: found {sample_count} sample records")
            
            if sample_count > 0:
                # We can use the static list since DB is available and has data
                logger.info("Using static book list since database has data")
                return jsonify(biblical_books)
                
        except Exception as db_err:
            logger.error(f"Error checking database status: {str(db_err)}")
            # Continue with regular query approach as fallback
        
        # Fall back to the original implementation
        try:
            # Log MongoDB connection info (without sensitive data)
            logger.info(f"MongoDB connection status check")
            
            # Get unique book names
            books = BibleVerse.objects().distinct('book_name')
            logger.info(f"Found {len(books)} books in database")
            
            if not books:
                logger.warning("No books found in database")
                # Try to get a count of all documents to check if any data exists
                try:
                    count = BibleVerse.objects.count()
                    logger.info(f"Total documents in collection: {count}")
                except Exception as count_err:
                    logger.error(f"Error counting documents: {str(count_err)}")
                return jsonify([])
            
            # Log the first few books to verify data
            logger.info(f"Sample of books found: {books[:5]}")
            
            # Sort books in biblical order
            sorted_books = sorted(books, key=lambda x: biblical_books.index(x) if x in biblical_books else len(biblical_books))
            logger.info(f"Returning sorted books: {sorted_books}")
            
            return jsonify(sorted_books)
        except Exception as inner_e:
            logger.error(f"Error in database query: {str(inner_e)}")
            # Return static list as last resort
            logger.info("Returning static book list as fallback")
            return jsonify(biblical_books)
            
    except Exception as e:
        logger.error(f"Error in get_books: {str(e)}", exc_info=True)
        # Log detailed stack trace for better debugging
        logger.error(f"Stack trace: {traceback.format_exc()}")
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
        # Validate book and chapter exist
        if not BibleVerse.objects(book_name=book, chapter=chapter).first():
            return jsonify({"error": "Chapter not found"}), 404
            
        # Get all verses for the given book and chapter
        verses = BibleVerse.objects(
            book_name=book,
            chapter=chapter
        ).order_by('verse')
        
        return jsonify([{
            "id": str(verse.id),
            "book": verse.book_name,
            "chapter": verse.chapter,
            "verse": verse.verse,
            "text": verse.text
        } for verse in verses])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bible_bp.route('/search', methods=['GET'])
@token_required
def search_bible(current_user):
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
            
        # Get search results using the search engine
        results = search_engine.search(query)
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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