# app.py
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from routes.bible import bible_bp
from routes.auth import auth_bp
from routes.friends import friends_bp
from routes.notes import notes_bp
from database import init_db
from models.bible import BibleVerse
from dotenv import load_dotenv
import os
import logging
import time
import sys
from mongoengine import connect
import certifi
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps

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
        "expose_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Ensure URLs with or without trailing slashes are handled the same way
app.url_map.strict_slashes = False

# Initialize MongoDB connection with MongoEngine
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("MONGODB_URI not found in environment variables")

# Try to connect to the database with retries
MAX_RETRIES = 5  # Increased from 3
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        logger.info(f"Database connection attempt {attempt + 1}/{MAX_RETRIES}")
        # Connect using MongoEngine with optimized settings for Railway with reduced memory usage
        connect(
            host=mongodb_uri,
            tlsCAFile=certifi.where(),
            alias='default',  # This sets up the default connection
            serverSelectionTimeoutMS=25000,  # 25 seconds timeout for server selection
            connectTimeoutMS=45000,  # 45 seconds timeout for initial connection
            socketTimeoutMS=90000,  # 90 seconds timeout for socket operations
            maxPoolSize=2,   # Reduced from 10 to minimize memory usage
            minPoolSize=1,   # Keep at least one connection alive
            waitQueueTimeoutMS=30000,  # Wait queue timeout
            retryWrites=True,  # Retry write operations
            heartbeatFrequencyMS=15000  # More frequent heartbeats to keep connection alive
        )
        logger.info("Successfully connected to MongoDB Atlas")
        break
    except Exception as e:
        logger.error(f"Error during database connection: {str(e)}")
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            logger.error("Max retries reached. Starting app without database connection.")
            raise

# Register blueprints
app.register_blueprint(bible_bp, url_prefix='/api/bible')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(friends_bp, url_prefix='/api/friends')
app.register_blueprint(notes_bp, url_prefix='/api/notes')

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
    return response

@app.route('/test', methods=['GET'])
def test():
    return {'message': 'Flask server is working!'}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint that also verifies MongoDB connection"""
    try:
        # Check if MongoDB is connected
        db_status = BibleVerse.objects().limit(1).count() >= 0
        return jsonify({
            'status': 'healthy',
            'mongodb': 'connected' if db_status else 'error',
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