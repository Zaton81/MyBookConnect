"""
Transitional re-exports for backwards compatibility.
All club serializers now reside in the standalone Django app `backend/clubs/`.
"""
from clubs.serializers import (
    ClubBookMiniSerializer,
    ClubUserMiniSerializer,
    ReadingClubBookSerializer,
    ReadingClubDetailSerializer,
    ReadingClubDiscussionCommentSerializer,
    ReadingClubDiscussionSerializer,
    ReadingClubListSerializer,
    ReadingClubMemberSerializer,
)

__all__ = [
    'ClubUserMiniSerializer',
    'ClubBookMiniSerializer',
    'ReadingClubMemberSerializer',
    'ReadingClubBookSerializer',
    'ReadingClubDiscussionCommentSerializer',
    'ReadingClubDiscussionSerializer',
    'ReadingClubListSerializer',
    'ReadingClubDetailSerializer',
]
