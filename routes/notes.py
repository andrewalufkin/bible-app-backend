from flask import Blueprint, jsonify, request
from models.note import Note, NoteType
from routes.auth import token_required
from mongoengine.errors import NotUniqueError, ValidationError
from models.auth import AuthUser

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