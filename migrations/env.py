from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to sys.path
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..')) # Go up two levels from env.py

# Import Base from your database setup and all models
from backend.database import Base # Adjust import path if necessary
from backend.models import * # Import all models to ensure they are registered with Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line reads the section named [loggers] from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata # Use your Base metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:-
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Ensure DATABASE_URL is loaded from .env if not already set
    from dotenv import load_dotenv
    import os
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env')) # Adjust path to .env if needed
    
    # Get database URL from environment
    db_url = os.getenv('SUPABASE_POSTGRES_CONNECTION') # Use the existing env var
    if not db_url:
        raise ValueError("SUPABASE_POSTGRES_CONNECTION environment variable not set or loaded")

    # Create a configuration dictionary programmatically
    # overriding the sqlalchemy.url from the ini file
    ini_config = config.get_section(config.config_ini_section, {})
    ini_config['sqlalchemy.url'] = db_url

    connectable = engine_from_config(
        # config.get_section(config.config_ini_section, {}),
        ini_config, # Use the modified config dictionary
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
