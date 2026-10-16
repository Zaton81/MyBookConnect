"""
Transitional re-exports for backwards compatibility.
All gamification serializers now reside in the standalone Django app `backend/gamification/`.
"""
from gamification.serializers import (
    BadgeSerializer,
    DailyReadingLogSerializer,
    GamificationPreferenceSerializer,
    ReadingChallengeSerializer,
    ReadingGoalSerializer,
)

__all__ = [
    'ReadingGoalSerializer',
    'DailyReadingLogSerializer',
    'BadgeSerializer',
    'ReadingChallengeSerializer',
    'GamificationPreferenceSerializer',
]
