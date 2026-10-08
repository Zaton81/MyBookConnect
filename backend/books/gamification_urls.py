from django.urls import path

from books.gamification_views import (
    BadgeListView,
    DailyReadingLogView,
    GamificationOverviewView,
    GamificationPreferenceView,
    JoinChallengeView,
    LeaveChallengeView,
    ReadingChallengeListView,
    ReadingGoalView,
)

urlpatterns = [
    path('overview/', GamificationOverviewView.as_view(), name='gamification-overview'),
    path('goals/', ReadingGoalView.as_view(), name='gamification-goals'),
    path('log/', DailyReadingLogView.as_view(), name='gamification-log'),
    path('badges/', BadgeListView.as_view(), name='gamification-badges'),
    path('challenges/', ReadingChallengeListView.as_view(), name='gamification-challenges'),
    path('challenges/<slug:slug>/join/', JoinChallengeView.as_view(), name='gamification-challenge-join'),
    path('challenges/<slug:slug>/leave/', LeaveChallengeView.as_view(), name='gamification-challenge-leave'),
    path('preferences/', GamificationPreferenceView.as_view(), name='gamification-preferences'),
]
