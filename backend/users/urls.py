from django.urls import include, path
from rest_framework.routers import DefaultRouter

from messages_app.views import ConversationViewSet, MessageViewSet

from .auth_views import (
    EmailVerifyConfirmView,
    EmailVerifyRequestView,
    GoogleOAuthLoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RevokeAllSessionsView,
    WebSocketTicketView,
)
from .views import (
    BlockUserView,
    CheckFollowStatusView,
    FeedView,
    FollowUserView,
    LogoutView,
    MuteUserView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
    UnblockUserView,
    UnfollowUserView,
    UnmuteUserView,
    UserDetailView,
    UserFollowersListView,
    UserFollowingListView,
    UserProfileView,
    UserRegistrationView,
    UserSearchListView,
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
    path('<int:user_id>/mute/', MuteUserView.as_view(), name='user-mute'),
    path('<int:user_id>/unmute/', UnmuteUserView.as_view(), name='user-unmute'),
    path('<int:user_id>/follow-status/', CheckFollowStatusView.as_view(), name='follow-status'),
    path('<int:user_id>/toggle-editor/', toggle_editor, name='toggle-editor'),
]

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('email/verify-request/', EmailVerifyRequestView.as_view(), name='email-verify-request'),
    path('email/verify/', EmailVerifyConfirmView.as_view(), name='email-verify-confirm'),
    path('sessions/revoke-all/', RevokeAllSessionsView.as_view(), name='sessions-revoke-all'),
    path('ws-ticket/', WebSocketTicketView.as_view(), name='ws-ticket'),
    path('google/', GoogleOAuthLoginView.as_view(), name='google-oauth-login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
    path('search/', UserSearchListView.as_view(), name='user-search'),
    path('following/', UserFollowingListView.as_view(), name='following-list'),
    path('followers/', UserFollowersListView.as_view(), name='followers-list'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('notifications/read-all/', NotificationMarkAllReadView.as_view(), name='notification-read-all'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('feed/', FeedView.as_view(), name='social-feed'),
    *user_action_patterns,
    path('users/', include(user_action_patterns)),
] + router.urls
