from django.urls import path
from .views import UserRegistrationView, UserProfileView, UserUpdateView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
]