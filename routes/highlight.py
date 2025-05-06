# backend/routes/highlight.py
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from database import get_db_session # Assuming a session getter for Flask context
from models import Highlight, User # Import models directly
from utils.auth import login_required # Assuming a decorator for protected routes
import logging

logger = logging.getLogger(__name__)

highlight_bp = Blueprint('highlight_bp', __name__)

# Pydantic models are not typically used directly in Flask request handling
# We'll parse JSON from the request body

@highlight_bp.route("/api/highlights", methods=['POST'])
@login_required # Protect the route
def create_highlight():
    """Creates a new highlight for the current user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    required_fields = ['book', 'chapter', 'verse', 'start_offset', 'end_offset']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Get user from g, assuming login_required adds it
    current_user_id = getattr(g, 'user_id', None)
    if not current_user_id:
         return jsonify({"error": "Authentication required"}), 401

    book = data['book']
    chapter = data['chapter']
    verse = data['verse']
    start_offset = data['start_offset']
    end_offset = data['end_offset']
    color = data.get('color', '#FFFF00') # Default color if not provided

    # Basic validation
    if not isinstance(start_offset, int) or not isinstance(end_offset, int) or \
       start_offset < 0 or end_offset <= start_offset:
        return jsonify({"error": "Invalid start or end offset"}), 400

    # More validation could be added here

    try:
        with get_db_session() as db: # Use the session context manager
            new_highlight = Highlight(
                user_id=current_user_id,
                book=book,
                chapter=chapter,
                verse=verse,
                start_offset=start_offset,
                end_offset=end_offset,
                color=color
            )
            db.add(new_highlight)
            db.commit()
            db.refresh(new_highlight)
            
            # Return the created object's details
            response_data = {
                "id": new_highlight.id,
                "user_id": new_highlight.user_id,
                "book": new_highlight.book,
                "chapter": new_highlight.chapter,
                "verse": new_highlight.verse,
                "start_offset": new_highlight.start_offset,
                "end_offset": new_highlight.end_offset,
                "color": new_highlight.color,
                # Add created_at/updated_at if needed, converting to string
                # "created_at": new_highlight.created_at.isoformat() if new_highlight.created_at else None,
            }
            return jsonify(response_data), 201 # HTTP 201 Created

    except Exception as e:
        logger.error(f"Error creating highlight: {str(e)}")
        # Consider rolling back the transaction if using a session context manager that doesn't auto-rollback
        # db.rollback() 
        return jsonify({"error": "Failed to create highlight"}), 500

# We will add GET and DELETE endpoints later 