# gunicorn.conf.py
timeout = 60  # increase from default 30
workers = 2
bind = "0.0.0.0:8080"