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

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Ensure URLs with or without trailing slashes are handled the same way
app.url_map.strict_slashes = False

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to connect to the database with retries
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        logger.info(f"Database connection attempt {attempt + 1}/{MAX_RETRIES}")
        if init_db():
            logger.info("Database connection successful")
            break
        else:
            logger.error(f"Failed to connect to database (attempt {attempt + 1}/{MAX_RETRIES})")
    except Exception as e:
        logger.error(f"Error during database connection: {str(e)}")
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            logger.error("Max retries reached. Starting app without database connection.")

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