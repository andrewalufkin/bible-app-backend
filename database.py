# database.py
from mongoengine import connect, get_db
from dotenv import load_dotenv
import os
import certifi
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def init_db():
    try:
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
        
        logger.info("Connecting to MongoDB...")
        
        # Connect with timeout settings
        connect(
            host=mongodb_uri,
            ssl=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
            connectTimeoutMS=5000,          # 5 second timeout for initial connection
            socketTimeoutMS=5000            # 5 second timeout for socket operations
        )
        
        # Test connection immediately
        db = get_db()
        db.client.server_info()  # This will raise an exception if connection fails
        
        logger.info("Successfully connected to MongoDB Atlas")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        # Don't raise the error, just return False
        return False