# backend/routes/highlight.py
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from sqlalchemy import and_ # Added for complex queries
from database import get_db_session # Assuming a session getter for Flask context
from models import Highlight, User # Import models directly
# from utils.auth import login_required
from utils.auth import token_required # Corrected import name
import logging
import uuid # Import the uuid module

logger = logging.getLogger(__name__)

highlight_bp = Blueprint('highlight_bp', __name__)

# Pydantic models are not typically used directly in Flask request handling
# We'll parse JSON from the request body

@highlight_bp.route("/api/highlights", methods=['POST'])
# @login_required
@token_required # Use the correct decorator name
def create_highlight(current_user_id_str): # Renamed to indicate it's a string
    """
    Creates or updates highlights for a verse based on a new highlight submission.
    Implements a "paint over" logic: new highlights can split, truncate, or
    overwrite existing highlights. Returns the complete, updated set of
    non-overlapping highlight segments for the affected verse.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # Convert current_user_id_str to UUID object
    try:
        current_user_id = uuid.UUID(current_user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID format for user_id: {current_user_id_str}")
        return jsonify({"error": "Invalid user identifier format"}), 400

    required_fields = ['book', 'chapter', 'verse', 'start_offset', 'end_offset', 'color']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    book = data['book']
    chapter = data['chapter']
    verse = data['verse']
    new_start_offset = data['start_offset']
    new_end_offset = data['end_offset']
    new_color = data['color']

    if not all(isinstance(val, str) for val in [book, new_color]):
        return jsonify({"error": "Book and color must be strings"}), 400
    if not all(isinstance(val, int) for val in [chapter, verse, new_start_offset, new_end_offset]):
        return jsonify({"error": "Chapter, verse, start_offset, and end_offset must be integers"}), 400

    if new_start_offset < 0 or new_end_offset <= new_start_offset:
        return jsonify({"error": "Invalid start or end offset"}), 400

    try:
        with get_db_session() as db:
            existing_highlights = db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).order_by(Highlight.start_offset).all()

            final_segments = []

            # 1. Calculate remaining parts of existing highlights
            for ex_hl in existing_highlights:
                ex_start, ex_end, ex_color = ex_hl.start_offset, ex_hl.end_offset, ex_hl.color

                # If existing highlight is entirely to the left of the new one
                if ex_end <= new_start_offset:
                    final_segments.append({'start': ex_start, 'end': ex_end, 'color': ex_color})
                # If existing highlight is entirely to the right of the new one
                elif ex_start >= new_end_offset:
                    final_segments.append({'start': ex_start, 'end': ex_end, 'color': ex_color})
                # Else, there is an overlap
                else:
                    # Part of existing highlight to the left of the new highlight
                    if ex_start < new_start_offset:
                        final_segments.append({'start': ex_start, 'end': new_start_offset, 'color': ex_color})
                    # Part of existing highlight to the right of the new highlight
                    if ex_end > new_end_offset:
                        final_segments.append({'start': new_end_offset, 'end': ex_end, 'color': ex_color})
            
            # 2. Add the new highlight itself
            final_segments.append({'start': new_start_offset, 'end': new_end_offset, 'color': new_color})

            # 3. Sort and Merge segments
            # Sort by start offset, then by end offset
            final_segments.sort(key=lambda s: (s['start'], s['end']))

            merged_segments = []
            if not final_segments:
                # If there are no segments (e.g. first highlight, or new highlight covered all old ones)
                # and the new highlight itself was valid.
                # This case is handled by the loop below if final_segments has the new highlight.
                # If final_segments is truly empty, merged_segments remains empty.
                pass


            for seg in final_segments:
                # Skip zero-length or invalid segments that might have been created
                if seg['start'] >= seg['end']:
                    continue

                if not merged_segments or seg['color'] != merged_segments[-1]['color'] or seg['start'] > merged_segments[-1]['end']:
                    # If merged_segments is empty, or current segment has a different color,
                    # or current segment does not touch/overlap the last merged segment,
                    # then add it as a new segment.
                    merged_segments.append(seg.copy()) # Use copy to avoid modifying original in final_segments
                else:
                    # Merge with the last segment (it has the same color and touches or overlaps)
                    merged_segments[-1]['end'] = max(merged_segments[-1]['end'], seg['end'])
            
            # 4. Database Update
            # Delete old highlights for this verse for this user
            db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).delete(synchronize_session=False) # synchronize_session=False is typical for bulk deletes

            # Add new merged segments
            new_db_highlights = []
            for seg_data in merged_segments:
                new_hl = Highlight(
                    user_id=current_user_id,
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    start_offset=seg_data['start'],
                    end_offset=seg_data['end'],
                    color=seg_data['color']
                )
                db.add(new_hl)
                new_db_highlights.append(new_hl)
            
            db.commit() # Commit changes: deletions and additions

            # Refresh objects to get IDs and timestamps
            # Instead of refreshing (which might be tricky with new_db_highlights if they weren't flushed for IDs),
            # it's safer to re-query. But for performance, if IDs are populated after add and before commit,
            # we might not need a full re-query. SQLAlchemy populates PKs on flush, which happens before commit.
            # However, timestamps like created_at, updated_at with server_default/onupdate might need refresh.
            # Let's re-fetch for safety and to ensure all fields are current.

            # 5. Fetch and Return all highlights for the verse
            final_verse_highlights = db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).order_by(Highlight.start_offset).all()

            response_data = [{
                "id": hl.id,
                "user_id": hl.user_id,
                "book": hl.book,
                "chapter": hl.chapter,
                "verse": hl.verse,
                "start_offset": hl.start_offset,
                "end_offset": hl.end_offset,
                "color": hl.color,
                "created_at": hl.created_at.isoformat() if hl.created_at else None,
                "updated_at": hl.updated_at.isoformat() if hl.updated_at else None,
            } for hl in final_verse_highlights]
            
            return jsonify(response_data), 200

    except Exception as e:
        db.rollback() # Rollback in case of error during transaction
        logger.error(f"Error processing highlight for verse {book} {chapter}:{verse}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to process highlight"}), 500

# We will add GET and DELETE endpoints later

@highlight_bp.route("/api/highlights/chapter/<string:book_name>/<int:chapter_number>", methods=['GET'])
@token_required
def get_highlights_by_chapter(current_user_id, book_name, chapter_number):
    """Fetches all highlights for a given book and chapter for the current user."""
    logger.info(f"Attempting to fetch highlights for user: {current_user_id}, book: {book_name}, chapter: {chapter_number}")
    try:
        logger.debug("Attempting to get DB session.")
        with get_db_session() as db:
            logger.debug(f"DB session acquired. Querying highlights for user_id: {current_user_id}, book: {book_name}, chapter: {chapter_number}")
            highlights = db.query(Highlight).filter_by(
                user_id=current_user_id,
                book=book_name,
                chapter=chapter_number
            ).order_by(Highlight.verse, Highlight.start_offset).all()
            logger.info(f"Successfully fetched {len(highlights)} highlights from DB.")

            results = [{
                "id": h.id,
                "user_id": h.user_id,
                "book": h.book,
                "chapter": h.chapter,
                "verse": h.verse,
                "start_offset": h.start_offset,
                "end_offset": h.end_offset,
                "color": h.color,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "updated_at": h.updated_at.isoformat() if h.updated_at else None
            } for h in highlights]
            
            logger.debug("Successfully serialized highlights results.")
            return jsonify(results), 200
            
    except Exception as e:
        logger.error(f"Error fetching highlights for {book_name} chapter {chapter_number}. User ID: {current_user_id}. Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch highlights"}), 500 

@highlight_bp.route("/api/highlights/range", methods=['DELETE'])
@token_required
def delete_highlights_in_range(current_user_id_str):
    """
    Deletes highlights within a specified range for a verse.
    Recalculates segments similar to create_highlight, but removes the specified range.
    Returns the complete, updated set of non-overlapping highlight segments for the affected verse.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    try:
        current_user_id = uuid.UUID(current_user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID format for user_id: {current_user_id_str}")
        return jsonify({"error": "Invalid user identifier format"}), 400

    required_fields = ['book', 'chapter', 'verse', 'start_offset', 'end_offset']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields for deletion"}), 400

    book = data['book']
    chapter = data['chapter']
    verse = data['verse']
    del_start_offset = data['start_offset']
    del_end_offset = data['end_offset']

    if not isinstance(book, str):
        return jsonify({"error": "Book must be a string"}), 400
    if not all(isinstance(val, int) for val in [chapter, verse, del_start_offset, del_end_offset]):
        return jsonify({"error": "Chapter, verse, start_offset, and end_offset must be integers"}), 400

    if del_start_offset < 0 or del_end_offset <= del_start_offset:
        return jsonify({"error": "Invalid start or end offset for deletion range"}), 400

    try:
        with get_db_session() as db:
            existing_highlights = db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).order_by(Highlight.start_offset).all()

            final_segments = []

            # Calculate remaining parts of existing highlights after deletion range is applied
            for ex_hl in existing_highlights:
                ex_start, ex_end, ex_color = ex_hl.start_offset, ex_hl.end_offset, ex_hl.color

                # Case 1: Existing highlight is entirely to the left of the deletion range
                if ex_end <= del_start_offset:
                    final_segments.append({'start': ex_start, 'end': ex_end, 'color': ex_color})
                # Case 2: Existing highlight is entirely to the right of the deletion range
                elif ex_start >= del_end_offset:
                    final_segments.append({'start': ex_start, 'end': ex_end, 'color': ex_color})
                # Case 3: Overlap exists
                else:
                    # Part of existing highlight to the left of the deletion range
                    if ex_start < del_start_offset:
                        final_segments.append({'start': ex_start, 'end': del_start_offset, 'color': ex_color})
                    # Part of existing highlight to the right of the deletion range
                    if ex_end > del_end_offset:
                        final_segments.append({'start': del_end_offset, 'end': ex_end, 'color': ex_color})
            
            # Sort and Merge segments (same logic as create_highlight, but without adding a new highlight segment)
            final_segments.sort(key=lambda s: (s['start'], s['end']))

            merged_segments = []
            for seg in final_segments:
                if seg['start'] >= seg['end']: # Skip zero-length or invalid segments
                    continue
                if not merged_segments or seg['color'] != merged_segments[-1]['color'] or seg['start'] > merged_segments[-1]['end']:
                    merged_segments.append(seg.copy())
                else:
                    merged_segments[-1]['end'] = max(merged_segments[-1]['end'], seg['end'])
            
            # Database Update: Delete old highlights for this verse, then add new merged segments
            db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).delete(synchronize_session=False)

            new_db_highlights = []
            for seg_data in merged_segments:
                new_hl = Highlight(
                    user_id=current_user_id,
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    start_offset=seg_data['start'],
                    end_offset=seg_data['end'],
                    color=seg_data['color']
                )
                db.add(new_hl)
                new_db_highlights.append(new_hl)
            
            db.commit()

            # Fetch and Return all highlights for the verse
            final_verse_highlights = db.query(Highlight).filter(
                Highlight.user_id == current_user_id,
                Highlight.book == book,
                Highlight.chapter == chapter,
                Highlight.verse == verse
            ).order_by(Highlight.start_offset).all()

            response_data = [{
                "id": hl.id, "user_id": hl.user_id, "book": hl.book,
                "chapter": hl.chapter, "verse": hl.verse,
                "start_offset": hl.start_offset, "end_offset": hl.end_offset,
                "color": hl.color,
                "created_at": hl.created_at.isoformat() if hl.created_at else None,
                "updated_at": hl.updated_at.isoformat() if hl.updated_at else None,
            } for hl in final_verse_highlights]
            
            return jsonify(response_data), 200

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting highlights in range for verse {book} {chapter}:{verse}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete highlights in range"}), 500 