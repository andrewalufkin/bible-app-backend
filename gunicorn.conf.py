# gunicorn.conf.py
import os
import logging
import sys

# Configure logging to stdout
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Gunicorn config
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 2

def on_starting(server):
    logger = logging.getLogger('gunicorn.error')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    
timeout = 60  # increase from default 30
workers = 2
bind = "0.0.0.0:8080"

