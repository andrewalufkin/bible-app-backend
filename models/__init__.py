# This file makes the models directory a Python package 
from .user import User
from .highlight import Highlight
from .bookmark import Bookmark

__all__ = [
    'User',
    'Highlight',
    'Bookmark',
] 