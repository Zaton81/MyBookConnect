"""
Transitional re-exports for backwards compatibility.
All club urls now reside in the standalone Django app `backend/clubs/`.
"""
from clubs.urls import router, urlpatterns

__all__ = ['urlpatterns', 'router']
