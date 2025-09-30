from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.register_user, name='register'),
    path('auth/token/', views.obtain_token, name='token'),
    path('auth/profile/', views.get_profile, name='profile'),
    path('auth/profile/update/', views.update_profile, name='update_profile'),
]