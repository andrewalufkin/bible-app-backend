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

# Initialize database connection
init_db()

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