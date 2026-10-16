"""
Transitional re-exports for backwards compatibility.
All gamification urls now reside in the standalone Django app `backend/gamification/`.
"""
from gamification.urls import urlpatterns

__all__ = ['urlpatterns']
