# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SQLITE_DB_PATH = os.path.join(BASE_DIR, 'bible.db')