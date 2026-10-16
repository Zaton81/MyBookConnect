"""
Transitional re-exports for backwards compatibility.
All audiobook services now reside in `backend/audiobooks/services.py`.
"""
from audiobooks.services import (
    format_seconds,
    get_audiobook_catalog,
    get_book_audiobook_details,
    get_user_listening_shelf,
    save_audiobook_progress,
)

__all__ = [
    'format_seconds',
    'get_book_audiobook_details',
    'save_audiobook_progress',
    'get_user_listening_shelf',
    'get_audiobook_catalog',
]
