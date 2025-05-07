from supabase import create_client
from supabase.client import ClientOptions
from dotenv import load_dotenv
import os
import logging
import asyncio
import asyncpg
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define Base for SQLAlchemy models BEFORE SupabaseClient class
# DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = os.getenv("SUPABASE_POSTGRES_CONNECTION") # Use the existing env var
if not DATABASE_URL:
    logger.error("SUPABASE_POSTGRES_CONNECTION environment variable not set.")
    # Decide how to handle this - raise error, exit, etc.
    # For now, let's allow Base to be defined, but engine creation might fail later
    # raise ValueError("SUPABASE_POSTGRES_CONNECTION environment variable not set.")
    DATABASE_URL = "postgresql://user:pass@host/db" # Dummy for Base definition

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Supabase Client Logic ---
_supabase_client_instance = None

class SupabaseClient:
    def __init__(self):
        self._client = None
        self._pg_pool = None
        # Defer initialization to first access or explicit call

    def _get_or_init_client(self):
        if self._client is None:
            try:
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
                
                if not supabase_url or not supabase_key:
                    raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY not found")
                if not supabase_key.startswith('eyJ'):
                    raise ValueError("SUPABASE_SERVICE_KEY appears invalid (use service_role key)")
                
                logger.info("Initializing Supabase client...")
                
                # Initialize client without explicit options, relying on environment for proxy settings
                self._client = create_client(supabase_url, supabase_key)
                
                logger.info("Successfully initialized Supabase client")
            except Exception as e:
                logger.error(f"Error initializing Supabase client: {str(e)}")
                self._client = None
                raise
        return self._client

    async def init_pg_pool(self):
        """Initialize PostgreSQL connection pool for direct queries"""
        if self._pg_pool is not None:
            return
        
        try:
            pg_conn_string = os.getenv('SUPABASE_POSTGRES_CONNECTION')
            if not pg_conn_string:
                raise ValueError("SUPABASE_POSTGRES_CONNECTION not found in environment variables")
            
            logger.info("Initializing PostgreSQL connection pool...")
            self._pg_pool = await asyncpg.create_pool(
                pg_conn_string,
                min_size=1,
                max_size=10
            )
            logger.info("Successfully initialized PostgreSQL connection pool")
            
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL connection pool: {str(e)}")
            self._pg_pool = None
            raise
    
    @property
    def client(self):
        """Get the Supabase client, initializing if needed."""
        return self._get_or_init_client()
    
    @property
    def pg_pool(self):
        """Get the PostgreSQL connection pool"""
        if not self._pg_pool:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.init_pg_pool())
            else:
                loop.run_until_complete(self.init_pg_pool())
        return self._pg_pool
    
    @contextmanager
    def db_connection(self):
        """Context manager for Supabase client usage"""
        try:
            yield self.client # Accessing .client ensures initialization
        except Exception as e:
            logger.error(f"Error in Supabase client operation: {str(e)}")
            raise
    
    async def close(self):
        """Close PostgreSQL connection pool"""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
            logger.info("PostgreSQL connection pool closed")

# Function to get the singleton instance
def _get_supabase_instance():
    global _supabase_client_instance
    if _supabase_client_instance is None:
        _supabase_client_instance = SupabaseClient()
    return _supabase_client_instance

# Public getter for the Supabase client API
def get_supabase():
    """Get the Supabase client API instance."""
    instance = _get_supabase_instance()
    return instance.client # Return the actual client API object

@contextmanager
def get_db():
    """DEPRECATED? Context manager for Supabase client operations.
       Consider using get_db_session() for SQLAlchemy operations.
    """
    logger.warning("get_db() called - consider using get_db_session() for SQLAlchemy.")
    instance = _get_supabase_instance()
    with instance.db_connection() as client:
        yield client

# Context manager for SQLAlchemy sessions (needed for Flask routes)
@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of SQLAlchemy operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy Session Error: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"General Session Error: {e}")
        raise
    finally:
        db.close()


async def get_pg_conn():
    """Get a PostgreSQL connection from the pool"""
    instance = _get_supabase_instance()
    if not instance.pg_pool:
        await instance.init_pg_pool()
    
    # Assuming pg_pool exists after init
    if instance.pg_pool:
      async with instance.pg_pool.acquire() as conn:
          yield conn
    else:
      # Handle case where pool init failed or wasn't awaited properly
      logger.error("Failed to acquire PG connection, pool not available.")
      yield None # Or raise an error

# Function to close pool on app shutdown (if needed)
async def close_pg_pool():
    instance = _get_supabase_instance()
    await instance.close()