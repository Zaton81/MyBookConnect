from django.urls import path

from .views import (
    AudiobookCatalogView,
    BookAudiobookDetailView,
    BookAudiobookProgressView,
    UserAudiobookShelfView,
)

urlpatterns = [
    path('catalog/', AudiobookCatalogView.as_view(), name='audiobook-catalog'),
    path('in-progress/', UserAudiobookShelfView.as_view(), name='audiobook-in-progress'),
    path('books/<int:pk>/', BookAudiobookDetailView.as_view(), name='audiobook-detail'),
    path('books/<int:pk>/progress/', BookAudiobookProgressView.as_view(), name='audiobook-progress'),
]
