from django.urls import path
from .views import (
    UserRegistrationView, UserProfileView, UserUpdateView, UserDetailView,
    FollowUserView, UnfollowUserView, BlockUserView, UnblockUserView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
    path('<int:id>/', UserDetailView.as_view(), name='user-detail'),
    path('<int:id>/follow/', FollowUserView.as_view(), name='user-follow'),
    path('<int:id>/unfollow/', UnfollowUserView.as_view(), name='user-unfollow'),
    path('<int:id>/block/', BlockUserView.as_view(), name='user-block'),
    path('<int:id>/unblock/', UnblockUserView.as_view(), name='user-unblock'),
]