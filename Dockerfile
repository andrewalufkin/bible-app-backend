FROM python:3.11-slim

WORKDIR /app

# Set Python memory optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1  
ENV PYTHONHASHSEED=random
# Limit Python memory usage
ENV MALLOC_ARENA_MAX=2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set memory limit for gunicorn
ENV GUNICORN_CMD_ARGS="--worker-tmp-dir /dev/shm"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]