# routes/bible.py
from flask import Blueprint, jsonify, request
import logging
import sys
import traceback
import os
import json
import anthropic
# from utils.auth import token_required # Remove this import
from .auth import token_required # Import from sibling auth module
from database import get_db, get_pg_conn
import asyncio

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
            with get_db() as client:
                response = client.table('bible_verses').select('book_name').limit(1).execute()
                if response.data:
                    logger.info("Database connection check: found sample records")
                    # We can use the static list since DB is available and has data
                    logger.info("Using static book list since database has data")
                    return jsonify(biblical_books)
                
        except Exception as db_err:
            logger.error(f"Error checking database status: {str(db_err)}")
            # Continue with regular query approach as fallback
        
        # Fall back to the original implementation
        try:
            # Log Supabase connection info
            logger.info(f"Supabase connection status check")
            
            # Get unique book names
            with get_db() as client:
                response = client.table('bible_verses').select('book_name').execute()
                books = list(set(item['book_name'] for item in response.data))
            
            logger.info(f"Found {len(books)} books in database")
            
            if not books:
                logger.warning("No books found in database")
                # Try to get a count of all documents to check if any data exists
                try:
                    with get_db() as client:
                        response = client.table('bible_verses').select('id', count='exact').execute()
                        count = response.count
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
        # Get unique chapter numbers for the given book
        with get_db() as client:
            response = client.table('bible_verses').select('chapter').eq('book_name', book).execute()
            chapters = list(set(item['chapter'] for item in response.data))
            
        if not chapters:
            return jsonify({"error": "Book not found"}), 404
            
        return jsonify(sorted(chapters))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bible_bp.route('/verses/<book>/<int:chapter>', methods=['GET'])
def get_verses(book, chapter):
    try:
        # Get all verses for the given book and chapter
        with get_db() as client:
            response = client.table('bible_verses').select('*').eq('book_name', book).eq('chapter', chapter).order('verse').execute()
            verses = response.data
            
        if not verses:
            return jsonify({"error": "Chapter not found"}), 404
            
        return jsonify([{
            "id": verse['id'],
            "book": verse['book_name'],
            "chapter": verse['chapter'],
            "verse": verse['verse'],
            "text": verse['text']
        } for verse in verses])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bible_bp.route('/search', methods=['GET'])
@token_required
def search_bible(current_user):
    try:
        # Note: current_user object is available here if needed, e.g., current_user.id
        query_str = request.args.get('q', '')
        if not query_str:
            return jsonify([])
            
        # Simple word matching: split query and filter by each word
        words = [word for word in query_str.split() if word] # Basic split, could add stopword filtering
        
        with get_db() as client:
            # Start the query
            supabase_query = client.table('bible_verses').select('*')
            
            # Add an 'ilike' filter for each word
            for word in words:
                supabase_query = supabase_query.ilike('text', f'%{word}%')
                
            # Execute the query
            response = supabase_query.limit(20).execute()
            results = response.data
            
        return jsonify([{
            "id": verse['id'],
            "book": verse['book_name'],
            "chapter": verse['chapter'],
            "verse": verse['verse'],
            "text": verse['text']
        } for verse in results])
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bible_bp.route('/ai-search', methods=['GET'])
@token_required
def ai_search_bible(current_user):
    logger.info("AI Search endpoint called")
    # Note: current_user object is available here if needed, e.g., current_user.id
    query_str = request.args.get('q', '')
    if not query_str:
        logger.warning("AI Search called with empty query")
        return jsonify([])

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Anthropic API key not found in environment variables.")
            return jsonify({"error": "AI search configuration error."}), 500

        client = anthropic.Anthropic(api_key=api_key)
        
        # Define the prompt for the LLM
        prompt = f"""Analyze the following query and identify the specific Bible book and chapter it refers to. 
        Query: "{query_str}"
        
        Respond ONLY with a JSON object containing the book name (full name, e.g., '1 Corinthians') and the chapter number. Use the key "book" for the book name and "chapter" for the chapter number (as an integer).
        Example format: {{"book": "John", "chapter": 4}}
        
        If the query does not clearly refer to a specific Bible passage or is too ambiguous, respond with: {{"book": null, "chapter": null}}
        """
        
        logger.info(f"Sending prompt to Anthropic for query: '{query_str}'")
        
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            temperature=0.0, # Low temperature for deterministic output
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract and parse the JSON response from the LLM
        llm_response_text = message.content[0].text
        logger.info(f"Received response from Anthropic: {llm_response_text}")
        
        try:
            # The response might be wrapped in ```json ... ```, try to extract if needed
            if llm_response_text.strip().startswith('```json'):
                llm_response_text = llm_response_text.split('```json')[1].split('```')[0].strip()
                
            llm_data = json.loads(llm_response_text)
            book = llm_data.get('book')
            chapter = llm_data.get('chapter')
            
            if not book or not chapter:
                logger.info(f"LLM could not identify a specific reference for query: '{query_str}'")
                return jsonify({"message": "Could not identify a specific Bible reference for your query.", "type": "info"}), 200

        except (json.JSONDecodeError, IndexError, AttributeError) as parse_err:
            logger.error(f"Failed to parse LLM response: {llm_response_text}. Error: {parse_err}")
            return jsonify({"error": "Failed to process AI response."}), 500

        # Fetch verses for the identified book and chapter
        logger.info(f"Fetching verses for {book} {chapter} based on LLM response")
        try:
            with get_db() as db_client:
                response = db_client.table('bible_verses')\
                                    .select('*')\
                                    .eq('book_name', book)\
                                    .eq('chapter', chapter)\
                                    .order('verse')\
                                    .execute()
                verses = response.data
            
            if not verses:
                logger.warning(f"No verses found for {book} {chapter} despite LLM suggestion.")
                # This could happen if the LLM hallucinates a non-existent chapter
                return jsonify({"message": f"AI suggested {book} {chapter}, but no verses were found.", "type": "warning"}), 200
            
            logger.info(f"Successfully fetched {len(verses)} verses for {book} {chapter}")
            # Format the response similarly to the standard verse endpoint
            formatted_verses = [{
                "id": verse['id'],
                "book": verse['book_name'],
                "chapter": verse['chapter'],
                "verse": verse['verse'],
                "text": verse['text'],
                "ai_suggestion": True # Add a flag indicating this came from AI search
            } for verse in verses]
            
            return jsonify(formatted_verses)

        except Exception as db_err:
            logger.error(f"Database error fetching verses for {book} {chapter}: {db_err}", exc_info=True)
            return jsonify({"error": "Failed to retrieve verses from database."}), 500

    except anthropic.APIError as api_err:
        logger.error(f"Anthropic API error: {api_err}", exc_info=True)
        return jsonify({'error': 'AI service communication error.'}), 500
    except Exception as e:
        logger.error(f"AI Search error: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred during AI search.'}), 500

@bible_bp.route('/verse/<book>/<int:chapter>/<int:verse>', methods=['GET'])
def get_single_verse(book, chapter, verse):
    try:
        with get_db() as client:
            response = client.table('bible_verses').select('*').eq('book_name', book).eq('chapter', chapter).eq('verse', verse).execute()
            verse_obj = response.data[0] if response.data else None
        
        if not verse_obj:
            return jsonify({"error": "Verse not found"}), 404
            
        return jsonify({
            "id": verse_obj['id'],
            "book": verse_obj['book_name'],
            "chapter": verse_obj['chapter'],
            "verse": verse_obj['verse'],
            "text": verse_obj['text']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500