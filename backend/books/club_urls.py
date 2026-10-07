from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .club_views import ReadingClubViewSet, ReadingClubDiscussionViewSet

router = DefaultRouter()
router.register(r'', ReadingClubViewSet, basename='club')

urlpatterns = [
    # Hilos de debate y comentarios por club
    path(
        '<slug:club_slug>/discussions/',
        ReadingClubDiscussionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='club-discussions-list',
    ),
    path(
        '<slug:club_slug>/discussions/<int:pk>/',
        ReadingClubDiscussionViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='club-discussions-detail',
    ),
    path(
        '<slug:club_slug>/discussions/<int:pk>/comments/',
        ReadingClubDiscussionViewSet.as_view({'get': 'comments', 'post': 'comments'}),
        name='club-discussions-comments',
    ),
    path(
        '<slug:slug>/members/<int:user_id>/',
        ReadingClubViewSet.as_view({'patch': 'manage_member'}),
        name='club-manage-member',
    ),
    # Router principal de clubs (list, create, retrieve, update, join, leave, members, books)
    path('', include(router.urls)),
]
