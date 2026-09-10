from django.urls import include, path
from rest_framework.routers import DefaultRouter

from messages_app.views import ConversationViewSet, MessageViewSet

from .views import (
    BlockUserView,
    CheckFollowStatusView,
    FollowUserView,
    LogoutView,
    UnblockUserView,
    UnfollowUserView,
    UserDetailView,
    UserFollowersListView,
    UserFollowingListView,
    UserProfileView,
    UserRegistrationView,
    UserUpdateView,
    toggle_editor,
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

# Alias para /api/v1/auth/users/<id>/ (el mismo urls.py se incluye también en /api/v1/users/).
user_action_patterns = [
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('<int:user_id>/follow/', FollowUserView.as_view(), name='user-follow'),
    path('<int:user_id>/unfollow/', UnfollowUserView.as_view(), name='user-unfollow'),
    path('<int:user_id>/block/', BlockUserView.as_view(), name='user-block'),
    path('<int:user_id>/unblock/', UnblockUserView.as_view(), name='user-unblock'),
    path('<int:user_id>/follow-status/', CheckFollowStatusView.as_view(), name='follow-status'),
    path('<int:user_id>/toggle-editor/', toggle_editor, name='toggle-editor'),
]

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
    path('following/', UserFollowingListView.as_view(), name='following-list'),
    path('followers/', UserFollowersListView.as_view(), name='followers-list'),
    *user_action_patterns,
    path('users/', include(user_action_patterns)),
] + router.urls
