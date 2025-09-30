from django.urls import path
from .views import (
    BookListCreateView, BookDetailView,
    UserBookListCreateView, UserBookDetailView,
    ReviewListCreateView
)
from .views import AuthorListCreateView

urlpatterns = [
    path('books/', BookListCreateView.as_view(), name='books-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='books-detail'),
    path('authors/', AuthorListCreateView.as_view(), name='authors-list'),
    path('user/books/', UserBookListCreateView.as_view(), name='user-books'),
    path('user/books/<int:pk>/', UserBookDetailView.as_view(), name='user-book-detail'),
    path('reviews/', ReviewListCreateView.as_view(), name='reviews'),
]
