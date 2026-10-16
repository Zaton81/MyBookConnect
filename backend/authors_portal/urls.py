from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthorAnnouncementCreateView,
    AuthorAnnouncementListView,
    AuthorClaimCreateView,
    AuthorClaimStatusView,
    AuthorClaimView,
    AuthorDashboardView,
    AuthorEventViewSet,
    AuthorNewsletterIssueViewSet,
    AuthorNewsletterViewSet,
    AuthorProfileMeView,
    AuthorPublicationViewSet,
)

router = DefaultRouter()
router.register('events', AuthorEventViewSet, basename='portal-author-events')
router.register('publications', AuthorPublicationViewSet, basename='portal-author-publications')
router.register('newsletters', AuthorNewsletterViewSet, basename='portal-author-newsletters')
router.register('newsletter-issues', AuthorNewsletterIssueViewSet, basename='portal-author-newsletter-issues')

urlpatterns = [
    path('me/', AuthorProfileMeView.as_view(), name='authors-me'),
    path('claim/', AuthorClaimView.as_view(), name='authors-claim'),
    path('dashboard/', AuthorDashboardView.as_view(), name='authors-dashboard'),
    path('announcements/', AuthorAnnouncementCreateView.as_view(), name='authors-announcement-create'),
    path('<int:pk>/announcements/', AuthorAnnouncementListView.as_view(), name='authors-announcements'),
    path('<int:pk>/claim/', AuthorClaimCreateView.as_view(), name='authors-claim-create'),
    path('<int:pk>/claim-status/', AuthorClaimStatusView.as_view(), name='authors-claim-status'),
    path('', include(router.urls)),
]
