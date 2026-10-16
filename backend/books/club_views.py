"""
Transitional re-exports for backwards compatibility.
All club views now reside in the standalone Django app `backend/clubs/`.
"""
from clubs.views import (
    IsClubAdminOrReadOnly,
    ReadingClubDiscussionViewSet,
    ReadingClubViewSet,
)

__all__ = [
    'IsClubAdminOrReadOnly',
    'ReadingClubViewSet',
    'ReadingClubDiscussionViewSet',
]
