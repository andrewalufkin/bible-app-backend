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

# Determine appropriate worker count based on CPU cores
# For Railway, we want to be conservative with resources
cores = multiprocessing.cpu_count()
workers = min(cores * 2 + 1, 6)  # Use standard formula but cap at 6 workers
threads = 4  # Use threading for I/O bound applications

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
worker_connections = 1000  # Maximum number of connections each worker can handle

# Process naming
proc_name = "bible_app"
default_proc_name = "bible_app" 

# Graceful server restart
graceful_timeout = 30  # Give workers 30 seconds to finish serving requests

