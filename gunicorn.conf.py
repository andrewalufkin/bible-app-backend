# gunicorn.conf.py
import os
import logging
import sys
import multiprocessing

# Configure logging to stdout
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Get PORT from environment or use default
port = os.getenv('PORT', '8080')
bind = f"0.0.0.0:{port}"

# Reduce workers and threads to minimize memory usage
workers = 1  # Use a single worker to minimize memory usage
threads = 2  # Reduce threads to minimize memory usage

# Log configuration on startup
def on_starting(server):
    logger = logging.getLogger('gunicorn.error')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.info(f"Starting gunicorn with {workers} workers on port {port}")
    logger.info(f"Worker timeout set to 180 seconds")

# Extended timeouts for Railway
timeout = 180  # 3 minutes timeout for slow operations
keepalive = 120  # Keep connections alive for 2 minutes
worker_class = "sync"  # Use sync workers for Flask
worker_connections = 100  # Reduced from 1000 to save memory

# Process naming
proc_name = "bible_app"
default_proc_name = "bible_app" 

# Graceful server restart
graceful_timeout = 30  # Give workers 30 seconds to finish serving requests

