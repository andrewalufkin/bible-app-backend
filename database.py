# database.py
from mongoengine import connect, get_db
from dotenv import load_dotenv
import os
import certifi

# Load environment variables
load_dotenv()

def init_db():
    try:
        # Get MongoDB URI from environment variables
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
        
        print(f"Connecting to MongoDB...")
        # Connect to MongoDB with SSL certificate verification
        connect(
            host=mongodb_uri,
            ssl=True,
            tlsCAFile=certifi.where()  # Use certifi's certificate bundle
        )
        
        # Verify connection by getting database
        db = get_db()
        collections = db.list_collection_names()
        print(f"Connected to database. Available collections: {collections}")
        
        # Count verses
        verses_count = db.verses.count_documents({})
        print(f"Found {verses_count} verses in the database")
        
        print("Successfully connected to MongoDB Atlas")
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise e