from django.urls import path

from .views import (
    AuthorAnnouncementCreateView,
    AuthorAnnouncementListView,
    AuthorClaimCreateView,
    AuthorClaimStatusView,
    AuthorClaimView,
    AuthorDashboardView,
    AuthorProfileMeView,
)

urlpatterns = [
    path('me/', AuthorProfileMeView.as_view(), name='authors-me'),
    path('claim/', AuthorClaimView.as_view(), name='authors-claim'),
    path('dashboard/', AuthorDashboardView.as_view(), name='authors-dashboard'),
    path('announcements/', AuthorAnnouncementCreateView.as_view(), name='authors-announcement-create'),
    path('<int:pk>/announcements/', AuthorAnnouncementListView.as_view(), name='authors-announcements'),
    path('<int:pk>/claim/', AuthorClaimCreateView.as_view(), name='authors-claim-create'),
    path('<int:pk>/claim-status/', AuthorClaimStatusView.as_view(), name='authors-claim-status'),
]
