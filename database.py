# database.py
from mongoengine import connect, get_db
from dotenv import load_dotenv
import os
import certifi
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
        
        # Connect with explicit TLS/SSL settings
        connect(
            host=mongodb_uri,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=certifi.where(),
            tlsAllowInvalidCertificates=False,  # Ensure strict certificate validation
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test connection
        db = get_db()
        db.client.server_info()
        
        logger.info("Successfully connected to MongoDB Atlas")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        return False