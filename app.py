# app.py
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from routes.bible import bible_bp
from routes.auth import auth_bp
from routes.friends import friends_bp
from routes.notes import notes_bp
from routes.highlight import highlight_bp
from routes.bookmarks_routes import bookmarks_bp
from database import get_supabase, get_db
from dotenv import load_dotenv
import os
import logging
import time
import sys
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import gc

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Use ProxyFix to handle proxy headers properly (important for Railway)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Scale down JSON settings to optimize memory usage
app.json.sort_keys = False  # Preserve order of keys in JSON responses
app.json.compact = True     # Use compact JSON to reduce memory usage 
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max request/response size (reduced from 100MB)
app.config['CORS_HEADERS'] = 'Content-Type'  # Add CORS headers configuration
app.config['CORS_SUPPORTS_CREDENTIALS'] = True  # Enable credentials support
app.config['CORS_EXPOSE_HEADERS'] = ['Content-Type', 'Authorization']  # Expose headers

# Configure CORS to allow requests from any origin
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Ensure URLs with or without trailing slashes are handled the same way
app.url_map.strict_slashes = False

# Initialize Supabase connection
try:
    logger.info("Initializing Supabase connection...")
    supabase = get_supabase()
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Error connecting to Supabase: {str(e)}")
    raise

# Register blueprints
app.register_blueprint(bible_bp, url_prefix='/api/bible')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(friends_bp, url_prefix='/api/friends')
app.register_blueprint(notes_bp, url_prefix='/api/notes')
app.register_blueprint(highlight_bp)
app.register_blueprint(bookmarks_bp)

# Request timeout middleware
def timeout_handler(seconds):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Set a timeout in g that can be used by long-running operations
            g.timeout = time.time() + seconds
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Register middleware that times out long-running requests
@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_timeout = 150  # 2.5 minutes

@app.after_request
def after_request(response):
    # Log request duration
    duration = time.time() - g.start_time
    logger.info(f"Request to {request.path} took {duration:.2f} seconds")
    
    # Clean up memory after each request
    try:
        # Import here to avoid circular imports
        from utils.rag import clear_model_cache
        
        # Clean any ML models loaded by the RAG module
        clear_model_cache()
        
        # Force Python garbage collection
        gc.collect()
        
        # Clean torch cache if available
        import torch
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        logger.info("Memory cleanup completed successfully")
    except Exception as e:
        logger.warning(f"Memory cleanup failed: {str(e)}")
    
    return response

@app.route('/test', methods=['GET'])
def test():
    return {'message': 'Flask server is working!'}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint that also verifies Supabase connection"""
    try:
        # Check if Supabase is connected by making a simple query
        with get_db() as client:
            response = client.table('bible_verses').select('id').limit(1).execute()
            db_status = len(response.data) >= 0
            
        return jsonify({
            'status': 'healthy',
            'supabase': 'connected' if db_status else 'error',
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)