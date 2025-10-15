from django.urls import path
from .views import (
    BookListCreateView, BookDetailView,
    UserBookListCreateView, UserBookDetailView,
    ReviewListCreateView, AuthorListCreateView, AuthorDetailView,
    ImportBookView
)

urlpatterns = [
    path('books/', BookListCreateView.as_view(), name='books-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='books-detail'),
    path('authors/', AuthorListCreateView.as_view(), name='authors-list'),
    path('authors/<int:pk>/', AuthorDetailView.as_view(), name='authors-detail'),
    path('user/books/', UserBookListCreateView.as_view(), name='user-books'),
    path('user/books/<int:pk>/', UserBookDetailView.as_view(), name='user-book-detail'),
    path('reviews/', ReviewListCreateView.as_view(), name='reviews'),
    path('books/import/', ImportBookView.as_view(), name='books-import'),
]
