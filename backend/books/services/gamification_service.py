"""
Transitional re-exports for backwards compatibility.
The gamification service and helpers now reside in `backend/gamification/services.py`.
"""
from gamification.services import (
    DEFAULT_BADGES,
    GamificationService,
    ensure_default_badges,
    ensure_default_challenges,
)

__all__ = [
    'DEFAULT_BADGES',
    'ensure_default_badges',
    'ensure_default_challenges',
    'GamificationService',
]
