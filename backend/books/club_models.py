"""
Transitional re-exports for backwards compatibility.
All club models now reside in the standalone Django app `backend/clubs/`.
"""
from clubs.models import (
    ReadingClub,
    ReadingClubBook,
    ReadingClubDiscussion,
    ReadingClubDiscussionComment,
    ReadingClubMember,
)

__all__ = [
    'ReadingClub',
    'ReadingClubMember',
    'ReadingClubBook',
    'ReadingClubDiscussion',
    'ReadingClubDiscussionComment',
]
