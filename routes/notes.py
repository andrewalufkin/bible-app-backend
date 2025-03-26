from flask import Blueprint, jsonify, request
from models.note import Note, NoteType, ChapterNote, Insight
from routes.auth import token_required
from mongoengine.errors import NotUniqueError, ValidationError
from models.auth import AuthUser
from utils.rag import generate_verse_insights, clear_model_cache
from datetime import datetime
import json

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/verse/<book>/<chapter>/<verse>', methods=['GET'])
@token_required
def get_verse_notes(current_user, book, chapter, verse):
    """Get all notes (both study and quick) for a specific verse"""
    try:
        # Get the user's own notes
        own_notes = Note.objects(
            user=current_user.id,
            book=book,
            chapter=chapter,
            verse=verse
        )

        # Get notes from friends only if the user has permission to view them
        friend_notes = []
        if current_user.can_view_friend_notes:
            # Get friends who share their notes
            sharing_friends = AuthUser.objects(
                id__in=[friend.id for friend in current_user.friends],
                share_notes_with_friends=True
            )
            
            friend_notes = Note.objects(
                user__in=[f.id for f in sharing_friends],
                book=book,
                chapter=chapter,
                verse=verse,
                note_type='study'  # Only get study notes from friends
            )

        # Convert notes to JSON and include user information
        response_notes = []
        
        # Add own notes
        for note in own_notes:
            note_json = note.to_json()
            note_json['user'] = {
                'id': str(current_user.id),
                'username': current_user.username,
                'is_self': True
            }
            response_notes.append(note_json)
        
        # Add friend notes
        for note in friend_notes:
            note_json = note.to_json()
            friend = AuthUser.objects(id=note.user.id).first()
            if friend:  # Make sure friend still exists
                note_json['user'] = {
                    'id': str(friend.id),
                    'username': friend.username,
                    'is_self': False
                }
                response_notes.append(note_json)

        return jsonify(response_notes)
    except Exception as e:
        print(f"Error fetching notes: {str(e)}")
        return jsonify({"message": "Failed to fetch notes"}), 500

@notes_bp.route('/study', methods=['POST'])
@token_required
def create_or_update_study_note(current_user):
    """Create or update a study note for a verse"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['book', 'chapter', 'verse', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        # If content is empty or just whitespace, delete the note if it exists
        if not data['content'].strip():
            existing_note = Note.objects(
                user=current_user.id,
                book=data['book'],
                chapter=data['chapter'],
                verse=data['verse'],
                note_type=NoteType.STUDY
            ).first()
            
            if existing_note:
                existing_note.delete()
            
            return jsonify({"message": "Note deleted"}), 200

        # Try to find existing note
        existing_note = Note.objects(
            user=current_user.id,
            book=data['book'],
            chapter=data['chapter'],
            verse=data['verse'],
            note_type=NoteType.STUDY
        ).first()

        if existing_note:
            # Update existing note
            existing_note.content = data['content']
            existing_note.save()
            return jsonify(existing_note.to_json())
        else:
            # Create new note
            new_note = Note(
                user=current_user.id,
                book=data['book'],
                chapter=data['chapter'],
                verse=data['verse'],
                content=data['content'],
                note_type=NoteType.STUDY
            )
            new_note.save()
            return jsonify(new_note.to_json()), 201

    except NotUniqueError:
        return jsonify({"message": "Note already exists"}), 409
    except ValidationError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        print(f"Error saving note: {str(e)}")
        return jsonify({"message": "Failed to save note"}), 500

@notes_bp.route('/quick', methods=['POST'])
@token_required
def create_or_update_quick_note(current_user):
    """Create or update a quick note for a verse"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['book', 'chapter', 'verse', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        # Try to find existing note
        existing_note = Note.objects(
            user=current_user.id,
            book=data['book'],
            chapter=data['chapter'],
            verse=data['verse'],
            note_type=NoteType.QUICK
        ).first()

        if existing_note:
            # Update existing note
            existing_note.content = data['content']
            existing_note.save()
            return jsonify(existing_note.to_json())
        else:
            # Create new note
            new_note = Note(
                user=current_user.id,
                book=data['book'],
                chapter=data['chapter'],
                verse=data['verse'],
                content=data['content'],
                note_type=NoteType.QUICK
            )
            new_note.save()
            return jsonify(new_note.to_json()), 201

    except NotUniqueError:
        return jsonify({"message": "Note already exists"}), 409
    except ValidationError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        print(f"Error saving note: {str(e)}")
        return jsonify({"message": "Failed to save note"}), 500

@notes_bp.route('/all', methods=['GET'])
@token_required
def get_all_notes(current_user):
    """Get all notes for the current user with pagination"""
    try:
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=10, type=int)
        
        # Cap limit to reasonable values
        if limit > 50:
            limit = 50
            
        # Calculate skip for pagination
        skip = (page - 1) * limit
        
        # Get total count of notes
        total_count = Note.objects(user=current_user.id).count()
        
        # Get the user's notes ordered by updated_at in descending order
        notes = Note.objects(user=current_user.id).order_by('-updated_at').skip(skip).limit(limit)
        
        # Convert notes to JSON with reference data
        response_notes = []
        for note in notes:
            note_json = note.to_json()
            note_json['user'] = {
                'id': str(current_user.id),
                'username': current_user.username
            }
            response_notes.append(note_json)
        
        # Create response with pagination metadata
        response = {
            'notes': response_notes,
            'pagination': {
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit  # Ceiling division
            }
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching all notes: {str(e)}")
        return jsonify({"message": "Failed to fetch notes"}), 500

@notes_bp.route('/chapter', methods=['POST'])
@token_required
def create_or_update_chapter_note(current_user):
    """Create or update a chapter note"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['book', 'chapter', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        # Try to find existing note
        existing_note = ChapterNote.objects(
            user=current_user.id,
            book=data['book'],
            chapter=data['chapter']
        ).first()

        if existing_note:
            # Update existing note
            existing_note.content = data['content']
            existing_note.save()
            return jsonify(existing_note.to_json())
        else:
            # Create new note
            new_note = ChapterNote(
                user=current_user.id,
                book=data['book'],
                chapter=data['chapter'],
                content=data['content']
            )
            new_note.save()
            return jsonify(new_note.to_json()), 201

    except Exception as e:
        print(f"Error saving chapter note: {str(e)}")
        return jsonify({"message": f"Failed to save chapter note: {str(e)}"}), 500

@notes_bp.route('/chapter/<book>/<chapter>', methods=['GET'])
@token_required
def get_chapter_note(current_user, book, chapter):
    """Get chapter note for a specific chapter"""
    try:
        # Get the user's own chapter note
        note = ChapterNote.objects(
            user=current_user.id,
            book=book,
            chapter=chapter
        ).first()
        
        if note:
            note_json = note.to_json()
            note_json['user'] = {
                'id': str(current_user.id),
                'username': current_user.username,
                'is_self': True
            }
            return jsonify(note_json)
        else:
            return jsonify({"message": "No chapter note found"}), 404
    except Exception as e:
        print(f"Error fetching chapter note: {str(e)}")
        return jsonify({"message": "Failed to fetch chapter note"}), 500

@notes_bp.route('/chapter/<book>/<chapter>/notes', methods=['GET'])
@token_required
def get_all_chapter_notes(current_user, book, chapter):
    """Get all notes for all verses in a specific chapter in a single request"""
    try:
        # Get the user's own notes for all verses in this chapter
        own_notes = Note.objects(
            user=current_user.id,
            book=book,
            chapter=chapter
        )

        # Get notes from friends only if the user has permission to view them
        friend_notes = []
        if current_user.can_view_friend_notes:
            # Get friends who share their notes
            sharing_friends = AuthUser.objects(
                id__in=[friend.id for friend in current_user.friends],
                share_notes_with_friends=True
            )
            
            friend_notes = Note.objects(
                user__in=[f.id for f in sharing_friends],
                book=book,
                chapter=chapter,
                note_type='study'  # Only get study notes from friends
            )

        # Convert notes to JSON and include user information
        response_notes = []
        
        # Add own notes
        for note in own_notes:
            note_json = note.to_json()
            note_json['user'] = {
                'id': str(current_user.id),
                'username': current_user.username,
                'is_self': True
            }
            response_notes.append(note_json)
        
        # Add friend notes
        for note in friend_notes:
            note_json = note.to_json()
            friend = AuthUser.objects(id=note.user.id).first()
            if friend:  # Make sure friend still exists
                note_json['user'] = {
                    'id': str(friend.id),
                    'username': friend.username,
                    'is_self': False
                }
                response_notes.append(note_json)

        return jsonify(response_notes)
    except Exception as e:
        print(f"Error fetching chapter notes: {str(e)}")
        return jsonify({"message": "Failed to fetch chapter notes"}), 500

@notes_bp.route('/insights', methods=['GET', 'POST'])
@token_required
def generate_insights(current_user):
    """Generate insights based on Bible verses and user notes using RAG or retrieve existing insights"""
    try:
        if request.method == 'GET':
            # Get book and chapter from query parameters
            book = request.args.get('book')
            chapter = request.args.get('chapter')
            
            if not book or not chapter:
                return jsonify({"message": "Missing 'book' or 'chapter' parameters"}), 400
                
            # Check if insights already exist
            existing_insight = Insight.objects(
                user=current_user.id,
                book=book,
                chapter=chapter
            ).first()
            
            if existing_insight:
                # Convert to JSON and return
                insight_json = existing_insight.to_json()
                return jsonify(insight_json)
            else:
                return jsonify({"message": "No insights found for this chapter"}), 404
        
        # Handle POST request
        data = request.get_json()
        
        # Validate required fields
        if 'verses' not in data or not isinstance(data['verses'], list):
            return jsonify({"message": "Missing or invalid 'verses' array"}), 400
            
        if not data['verses']:
            return jsonify({"message": "Verses array cannot be empty"}), 400
            
        # Get optional fields with defaults
        verse_notes = data.get('verse_notes', [])
        chapter_note = data.get('chapter_note', {})
        
        # If user has custom AI preferences, use those; otherwise use defaults
        if hasattr(current_user, 'ai_preferences') and current_user.ai_preferences:
            ai_preferences = current_user.ai_preferences.to_json()
        else:
            ai_preferences = {
                "model_temperature": 0.7,
                "response_length": 200,
                "writing_style": "devotional",
                "preferred_topics": []
            }
            
        # Override with any preferences passed in the request
        if 'ai_preferences' in data and isinstance(data['ai_preferences'], dict):
            ai_preferences.update(data['ai_preferences'])
        
        # Generate insights
        insights = generate_verse_insights(
            verses=data['verses'],
            verse_notes=verse_notes,
            chapter_note=chapter_note,
            ai_preferences=ai_preferences
        )
        
        # Clean up model memory after generating insights
        clear_model_cache()
        
        # Check if there was an error in generating insights
        if 'error' in insights:
            # Return the error but with a 200 status so the frontend can access the error message
            return jsonify(insights), 200
        
        # Save insights to database
        # Extract book and chapter from the first verse
        book = data['verses'][0]['book']
        chapter = data['verses'][0]['chapter']
        
        # Check if insights already exist for this book and chapter
        existing_insight = Insight.objects(
            user=current_user.id,
            book=book,
            chapter=chapter
        ).first()
        
        if existing_insight:
            # Update existing insight
            existing_insight.content = insights['insights']
            existing_insight.preferences_used = insights['preferences_used']
            existing_insight.created_at = datetime.utcnow()
            existing_insight.save()
        else:
            # Create new insight
            new_insight = Insight(
                user=current_user.id,
                book=book,
                chapter=chapter,
                content=insights['insights'],
                preferences_used=insights['preferences_used']
            )
            new_insight.save()
        
        # Convert to consistent structure with the GET endpoint
        response_data = {
            "chapter_reference": f"{book} {chapter}",
            "content": insights['insights'],
            "preferences_used": insights['preferences_used'],
            "created_at": datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        return jsonify({"message": f"Failed to generate insights: {str(e)}"}), 500 