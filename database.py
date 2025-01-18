from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging
import ssl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def init_db():
    try:
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
        
        logger.info("Connecting to MongoDB...")
        
        # Create client with minimal SSL config
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False  
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas")
        return client
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        return None