"""
Transitional re-exports for backwards compatibility.
All gamification views now reside in the standalone Django app `backend/gamification/`.
"""
from gamification.views import (
    BadgeListView,
    DailyReadingLogView,
    GamificationOverviewView,
    GamificationPreferenceView,
    JoinChallengeView,
    LeaveChallengeView,
    ReadingChallengeListView,
    ReadingGoalView,
)

__all__ = [
    'GamificationOverviewView',
    'ReadingGoalView',
    'DailyReadingLogView',
    'BadgeListView',
    'ReadingChallengeListView',
    'JoinChallengeView',
    'LeaveChallengeView',
    'GamificationPreferenceView',
]
