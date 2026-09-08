from django.urls import path
from .views import (
    BookListCreateView, BookDetailView,
    UserBookListCreateView, UserBookDetailView, UserBookByBookView,
    ReviewListCreateView, AuthorListCreateView, AuthorDetailView,
    AuthorBooksView, ImportBookView, RecommendationView, AuthorBookRefreshView,
    ErrataListCreateView, ErrataDetailUpdateView,
)

urlpatterns = [
    path('books/', BookListCreateView.as_view(), name='books-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='books-detail'),
    path('books/<int:pk>/recommendations/', RecommendationView.as_view(), name='book-recommendations'),
    path('authors/', AuthorListCreateView.as_view(), name='authors-list'),
    path('authors/<int:pk>/', AuthorDetailView.as_view(), name='authors-detail'),
    path('authors/<int:pk>/books/', AuthorBooksView.as_view(), name='author-books'),
    path('authors/<int:pk>/refresh-books/', AuthorBookRefreshView.as_view(), name='author-refresh-books'),
    path('user/books/', UserBookListCreateView.as_view(), name='user-books'),
    path('user/books/<int:pk>/', UserBookDetailView.as_view(), name='user-book-detail'),
    path('user/books/by-book/<int:book_id>/', UserBookByBookView.as_view(), name='user-book-by-book'),
    path('reviews/', ReviewListCreateView.as_view(), name='reviews'),
    path('books/import/', ImportBookView.as_view(), name='books-import'),
    path('erratas/', ErrataListCreateView.as_view(), name='erratas-list-create'),
    path('erratas/<int:pk>/', ErrataDetailUpdateView.as_view(), name='erratas-detail-update'),
]
