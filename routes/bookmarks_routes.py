# backend/routes/bookmarks_routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database import get_db_session
from models import Bookmark, User # Assuming models are accessible like this
from schemas.bookmark_schemas import BookmarkCreate, BookmarkRead # For potential internal use or future migration
from utils.auth import token_required
import logging
import uuid

logger = logging.getLogger(__name__)
bookmarks_bp = Blueprint('bookmarks_bp', __name__, url_prefix='/api/bookmarks')

@bookmarks_bp.route("/", methods=['POST'])
@token_required
def create_bookmark(current_user_id_str):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    try:
        current_user_id = uuid.UUID(current_user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID format for user_id: {current_user_id_str}")
        return jsonify({"error": "Invalid user identifier format"}), 400

    required_fields = ['book', 'chapter', 'verse']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields (book, chapter, verse)"}), 400
    
    # Basic type validation (can be expanded or use Pydantic models if preferred internally)
    if not isinstance(data.get('book'), str) or \
       not isinstance(data.get('chapter'), int) or \
       not isinstance(data.get('verse'), int):
        return jsonify({"error": "Invalid data types for book, chapter, or verse"}), 400
    if data.get('text_preview') is not None and not isinstance(data.get('text_preview'), str):
        return jsonify({"error": "Invalid data type for text_preview"}), 400
    if data.get('notes') is not None and not isinstance(data.get('notes'), str):
         return jsonify({"error": "Invalid data type for notes"}), 400

    try:
        with get_db_session() as db:
            # Check if bookmark already exists for this user and verse
            existing_bookmark = db.query(Bookmark).filter_by(
                user_id=current_user_id,
                book=data['book'],
                chapter=data['chapter'],
                verse=data['verse']
            ).first()

            if existing_bookmark:
                return jsonify({"error": "Bookmark already exists for this verse"}), 409 # Conflict

            new_bookmark = Bookmark(
                user_id=current_user_id,
                book=data['book'],
                chapter=data['chapter'],
                verse=data['verse'],
                text_preview=data.get('text_preview'),
                notes=data.get('notes')
            )
            db.add(new_bookmark)
            db.commit()
            db.refresh(new_bookmark) # To get ID and created_at
            
            # Convert to a dictionary for JSON response, similar to BookmarkRead schema
            response_data = {
                "id": new_bookmark.id,
                "user_id": new_bookmark.user_id,
                "book": new_bookmark.book,
                "chapter": new_bookmark.chapter,
                "verse": new_bookmark.verse,
                "text_preview": new_bookmark.text_preview,
                "notes": new_bookmark.notes,
                "created_at": new_bookmark.created_at.isoformat() if new_bookmark.created_at else None
            }
            return jsonify(response_data), 201

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bookmark: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to create bookmark"}), 500

@bookmarks_bp.route("/", methods=['GET'])
@token_required
def get_bookmarks(current_user_id_str):
    try:
        current_user_id = uuid.UUID(current_user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID format for user_id: {current_user_id_str}")
        return jsonify({"error": "Invalid user identifier format"}), 400

    try:
        with get_db_session() as db:
            bookmarks = db.query(Bookmark).filter_by(user_id=current_user_id).order_by(Bookmark.created_at.desc()).all()
            
            results = [{
                "id": b.id,
                "user_id": b.user_id,
                "book": b.book,
                "chapter": b.chapter,
                "verse": b.verse,
                "text_preview": b.text_preview,
                "notes": b.notes,
                "created_at": b.created_at.isoformat() if b.created_at else None
            } for b in bookmarks]
            return jsonify(results), 200
    except Exception as e:
        logger.error(f"Error fetching bookmarks: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to fetch bookmarks"}), 500

@bookmarks_bp.route("/<int:bookmark_id>", methods=['DELETE'])
@token_required
def delete_bookmark(current_user_id_str, bookmark_id):
    try:
        current_user_id = uuid.UUID(current_user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID format for user_id: {current_user_id_str}")
        return jsonify({"error": "Invalid user identifier format"}), 400

    try:
        with get_db_session() as db:
            bookmark_to_delete = db.query(Bookmark).filter_by(id=bookmark_id, user_id=current_user_id).first()

            if not bookmark_to_delete:
                return jsonify({"error": "Bookmark not found or not owned by user"}), 404

            db.delete(bookmark_to_delete)
            db.commit()
            return jsonify({"message": "Bookmark deleted successfully"}), 200 # Or 204 No Content with empty body

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting bookmark {bookmark_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete bookmark"}), 500 