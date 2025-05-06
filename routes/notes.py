from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.auth import token_required
from database import get_db
import logging
from functools import wraps

notes_bp = Blueprint('notes', __name__)
logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            with get_db() as client:
                # Verify the JWT token with Supabase
                user_response = client.auth.get_user(token)
                if not user_response:
                    return jsonify({'message': 'Invalid token!'}), 401
                
                # Extract user ID from the response
                user_id = user_response.user.id
                return f(user_id, *args, **kwargs)
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return jsonify({'message': 'Invalid token!'}), 401

    return decorated

@notes_bp.route('/notes', methods=['GET'])
@token_required
def get_notes(current_user):
    try:
        with get_db() as client:
            response = client.table('notes').select('*').eq('user_id', current_user).order('created_at', desc=True).execute()
            notes = response.data
            
        return jsonify([{
            'id': note['id'],
            'user_id': note['user_id'],
            'verse_id': note['verse_id'],
            'content': note['content'],
            'created_at': note['created_at'],
            'updated_at': note['updated_at']
        } for note in notes])
        
    except Exception as e:
        logger.error(f"Error fetching notes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/notes', methods=['POST'])
@token_required
def create_note(current_user):
    try:
        data = request.get_json()
        verse_id = data.get('verse_id')
        content = data.get('content')

        if not all([verse_id, content]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify verse exists
        with get_db() as client:
            verse_response = client.table('bible_verses').select('id').eq('id', verse_id).execute()
            if not verse_response.data:
                return jsonify({'error': 'Verse not found'}), 404

            # Create note
            current_time = datetime.utcnow().isoformat()
            note_data = {
                'user_id': current_user,
                'verse_id': verse_id,
                'content': content,
                'created_at': current_time,
                'updated_at': current_time
            }

            response = client.table('notes').insert(note_data).execute()
            
            if not response.data:
                return jsonify({'error': 'Failed to create note'}), 500

            return jsonify({
                'message': 'Note created successfully',
                'note': response.data[0]
            }), 201

    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/notes/<note_id>', methods=['PUT'])
@token_required
def update_note(current_user, note_id):
    try:
        data = request.get_json()
        content = data.get('content')

        if not content:
            return jsonify({'error': 'Content is required'}), 400

        with get_db() as client:
            # Verify note exists and belongs to user
            response = client.table('notes').select('*').eq('id', note_id).eq('user_id', current_user).execute()
            if not response.data:
                return jsonify({'error': 'Note not found'}), 404

            # Update note
            update_response = client.table('notes').update({
                'content': content,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', note_id).execute()

            if not update_response.data:
                return jsonify({'error': 'Failed to update note'}), 500

            return jsonify({
                'message': 'Note updated successfully',
                'note': update_response.data[0]
            })

    except Exception as e:
        logger.error(f"Error updating note: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/notes/<note_id>', methods=['DELETE'])
@token_required
def delete_note(current_user, note_id):
    try:
        with get_db() as client:
            # Verify note exists and belongs to user
            response = client.table('notes').select('*').eq('id', note_id).eq('user_id', current_user).execute()
            if not response.data:
                return jsonify({'error': 'Note not found'}), 404

            # Delete note
            delete_response = client.table('notes').delete().eq('id', note_id).execute()
            
            if not delete_response.data:
                return jsonify({'error': 'Failed to delete note'}), 500

            return jsonify({
                'message': 'Note deleted successfully'
            })

    except Exception as e:
        logger.error(f"Error deleting note: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/notes/verse/<verse_id>', methods=['GET'])
@token_required
def get_notes_for_verse(current_user, verse_id):
    try:
        with get_db() as client:
            response = client.table('notes').select('*').eq('user_id', current_user).eq('verse_id', verse_id).order('created_at', desc=True).execute()
            notes = response.data
            
        return jsonify([{
            'id': note['id'],
            'user_id': note['user_id'],
            'verse_id': note['verse_id'],
            'content': note['content'],
            'created_at': note['created_at'],
            'updated_at': note['updated_at']
        } for note in notes])
        
    except Exception as e:
        logger.error(f"Error fetching notes for verse: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/chapter/<book>/<chapter>/notes', methods=['GET'])
@token_required
def get_chapter_notes(current_user, book, chapter):
    try:
        with get_db() as client:
            response = client.table('notes').select('*').eq('user_id', current_user).eq('book', book).eq('chapter', chapter).order('created_at', desc=True).execute()
            notes = response.data
            
        # Format the notes to include the nested user object expected by the frontend
        formatted_notes = []
        for note in notes:
            formatted_notes.append({
                'id': note['id'],
                # Add the nested user object
                'user': {
                    'id': note['user_id'],
                    'is_self': True # Since we query by current_user, these are always self
                },
                'book': note['book'],
                'chapter': note['chapter'],
                'verse': note['verse'],
                'content': note['content'],
                'note_type': note['note_type'],
                'created_at': note['created_at'],
                'updated_at': note['updated_at']
            })
            
        return jsonify(formatted_notes)
        
    except Exception as e:
        logger.error(f"Error fetching chapter notes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/chapter/<book>/<chapter>', methods=['GET'])
@token_required
def get_single_chapter_note(current_user, book, chapter):
    """
    Fetches the single chapter-level note for a given user, book, and chapter.
    """
    try:
        with get_db() as client:
            response = client.table('notes').select('id, content, created_at, updated_at') \
                .eq('user_id', current_user) \
                .eq('book', book) \
                .eq('chapter', chapter) \
                .eq('note_type', 'chapter') \
                .limit(1) \
                .execute()

            # Check if data exists and is not empty
            if response.data:
                note = response.data[0] # Get the first (and only) note
                return jsonify(note)
            else:
                # Return an empty object with null/default values if no note exists,
                # consistent with how fetchSingleChapterNote handles 404 in the frontend.
                return jsonify({
                    'id': None,
                    'content': '',
                    'created_at': None,
                    'updated_at': None
                }), 200 # Return 200 OK even if note doesn't exist yet

    except Exception as e:
        logger.exception(f"Error fetching single chapter note for user {current_user}, book {book}, chapter {chapter}: {str(e)}")
        return jsonify({'error': 'An internal server error occurred while fetching the chapter note.'}), 500

@notes_bp.route('/study', methods=['POST'])
@token_required
def create_study_note(current_user):
    try:
        data = request.get_json()
        book = data.get('book')
        chapter = data.get('chapter')
        verse = data.get('verse')
        content = data.get('content')

        if not all([book, chapter, verse, content]):
            return jsonify({'error': 'Missing required fields (book, chapter, verse, content)'}), 400

        with get_db() as client:
            current_time = datetime.utcnow().isoformat()
            note_type = 'study'

            # 1. Check if a study note already exists for this verse
            existing_note_response = client.table('notes') \
                .select('id') \
                .eq('user_id', current_user) \
                .eq('book', book) \
                .eq('chapter', chapter) \
                .eq('verse', verse) \
                .eq('note_type', note_type) \
                .limit(1) \
                .execute()

            if existing_note_response.data:
                # 2a. Update existing note
                existing_note_id = existing_note_response.data[0]['id']
                update_data = {
                    'content': content,
                    'updated_at': current_time
                }
                response = client.table('notes') \
                    .update(update_data) \
                    .eq('id', existing_note_id) \
                    .execute()
                operation = 'updated'
            else:
                # 2b. Insert new note
                insert_data = {
                    'user_id': current_user,
                    'book': book,
                    'chapter': chapter,
                    'verse': verse,
                    'content': content,
                    'note_type': note_type,
                    'created_at': current_time, # Set created_at on initial insert
                    'updated_at': current_time
                }
                response = client.table('notes') \
                    .insert(insert_data) \
                    .execute()
                operation = 'created'

            # Check for success
            if not response.data:
                logger.error(f"Failed to {operation} study note. User: {current_user}, Ref: {book} {chapter}:{verse}. Response: {response}")
                return jsonify({'error': f'Failed to save study note ({operation} operation)'}), 500

            # Return the created/updated note data
            return jsonify({
                'message': f'Study note {operation} successfully',
                'note': response.data[0]
            }), 200 if operation == 'updated' else 201 # 200 for update, 201 for create

    except Exception as e:
        logger.exception(f"Error saving study note for user {current_user}, ref {book} {chapter}:{verse}: {str(e)}")
        return jsonify({'error': 'An internal server error occurred while saving the note.'}), 500

@notes_bp.route('/quick', methods=['POST'])
@token_required
def create_quick_note(current_user):
    try:
        data = request.get_json()
        book = data.get('book')
        chapter = data.get('chapter')
        verse = data.get('verse')
        content = data.get('content')

        if not all([book, chapter, verse, content]):
            return jsonify({'error': 'Missing required fields'}), 400

        with get_db() as client:
            # Create quick note
            current_time = datetime.utcnow().isoformat()
            note_data = {
                'user_id': current_user,
                'book': book,
                'chapter': chapter,
                'verse': verse,
                'content': content,
                'note_type': 'quick',
                'created_at': current_time,
                'updated_at': current_time
            }

            response = client.table('notes').insert(note_data).execute()
            
            if not response.data:
                return jsonify({'error': 'Failed to create quick note'}), 500

            return jsonify({
                'message': 'Quick note created successfully',
                'note': response.data[0]
            }), 201

    except Exception as e:
        logger.error(f"Error creating quick note: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/chapter', methods=['POST'])
@token_required
def create_chapter_note(current_user):
    try:
        data = request.get_json()
        book = data.get('book')
        chapter = data.get('chapter')
        content = data.get('content')

        if not all([book, chapter, content]):
            return jsonify({'error': 'Missing required fields (book, chapter, content)'}), 400

        with get_db() as client:
            current_time = datetime.utcnow().isoformat()
            note_type = 'chapter'

            # 1. Check if a chapter note already exists
            existing_note_response = client.table('notes') \
                .select('id') \
                .eq('user_id', current_user) \
                .eq('book', book) \
                .eq('chapter', chapter) \
                .eq('note_type', note_type) \
                .limit(1) \
                .execute()

            if existing_note_response.data:
                # 2a. Update existing note
                existing_note_id = existing_note_response.data[0]['id']
                update_data = {
                    'content': content,
                    'updated_at': current_time
                }
                response = client.table('notes') \
                    .update(update_data) \
                    .eq('id', existing_note_id) \
                    .execute()
                operation = 'updated'
            else:
                # 2b. Insert new note
                insert_data = {
                    'user_id': current_user,
                    'book': book,
                    'chapter': chapter,
                    'content': content,
                    'note_type': note_type, 
                    'created_at': current_time,
                    'updated_at': current_time
                }
                response = client.table('notes') \
                    .insert(insert_data) \
                    .execute()
                operation = 'created'
            
            # Check for success
            if not response.data:
                logger.error(f"Failed to {operation} chapter note. User: {current_user}, Book: {book}, Chapter: {chapter}. Response: {response}")
                return jsonify({'error': f'Failed to save chapter note ({operation} operation)'}), 500

            # Return the created/updated note data
            return jsonify({
                'message': f'Chapter note {operation} successfully',
                'note': response.data[0]
            }), 200 if operation == 'updated' else 201 # 200 for update, 201 for create

    except Exception as e:
        logger.exception(f"Error saving chapter note for user {current_user}, book {book}, chapter {chapter}: {str(e)}")
        return jsonify({'error': 'An internal server error occurred while saving the note.'}), 500 