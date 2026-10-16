"""
Transitional re-exports for backwards compatibility.
All gamification models now reside in the standalone Django app `backend/gamification/`.
"""
from gamification.models import (
    Badge,
    BadgeCategory,
    ChallengeType,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)

__all__ = [
    'Badge',
    'BadgeCategory',
    'ChallengeType',
    'DailyReadingLog',
    'ReadingChallenge',
    'ReadingGoal',
    'ReadingStreak',
    'UserBadge',
    'UserChallenge',
]
