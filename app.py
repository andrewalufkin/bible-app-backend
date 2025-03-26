# app.py
from flask import Flask
from flask_cors import CORS
from routes.bible import bible_bp
from routes.auth import auth_bp
from routes.friends import friends_bp
from routes.notes import notes_bp
from database import init_db
from dotenv import load_dotenv
import os
import logging
import time
import sys
from mongoengine import connect
import certifi

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

# Increase limits to avoid any truncation issues
app.json.sort_keys = False  # Preserve order of keys in JSON responses
app.json.compact = False    # Ensure proper formatting
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request/response size
app.config['JSON_MAX_CONTENT_LENGTH'] = None  # No limit on JSON size
app.config['MAX_COOKIE_SIZE'] = 16384  # Set a large cookie size
app.config['APPLICATION_ROOT'] = '/'  # Set application root
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
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        logger.info(f"Database connection attempt {attempt + 1}/{MAX_RETRIES}")
        # Connect using MongoEngine
        connect(
            host=mongodb_uri,
            tlsCAFile=certifi.where(),
            alias='default'  # This sets up the default connection
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

@app.route('/test', methods=['GET'])
def test():
    return {'message': 'Flask server is working!'}

if __name__ == '__main__':
    print("Starting Flask server...")
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)