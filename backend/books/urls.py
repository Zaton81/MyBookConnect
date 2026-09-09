from django.urls import path
from .views import (
    BookListCreateView, BookDetailView,
    UserBookListCreateView, UserBookDetailView, UserBookByBookView,
    ReviewListCreateView, AuthorListCreateView, AuthorDetailView,
    AuthorBooksView, ImportBookView, RecommendationView, AuthorBookRefreshView,
    ErrataListCreateView, ErrataDetailUpdateView,
    SocialFeedView, TrendingBooksView, ReadingMatchView,
)
from .ai_views import (
    AIAssistantView, AISemanticSearchView, AIBookSummaryView, AIStatusView,
)

urlpatterns = [
    # Rutas estándar limpias (/api/v1/books/...)
    path('', BookListCreateView.as_view(), name='books-list-root'),
    path('feed/', SocialFeedView.as_view(), name='books-social-feed'),
    path('trending/', TrendingBooksView.as_view(), name='books-trending'),
    path('match/<int:user_id>/', ReadingMatchView.as_view(), name='user-reading-match'),
    path('import/', ImportBookView.as_view(), name='books-import-root'),

    # Rutas de Inteligencia Artificial (OpenAI-compatible)
    path('ai/status/', AIStatusView.as_view(), name='book-ai-status'),
    path('ai/assistant/', AIAssistantView.as_view(), name='book-ai-assistant'),
    path('ai/semantic-search/', AISemanticSearchView.as_view(), name='book-ai-semantic-search'),
    path('<int:pk>/ai/summary/', AIBookSummaryView.as_view(), name='book-ai-summary'),

    path('<int:pk>/', BookDetailView.as_view(), name='books-detail-root'),
    path('<int:pk>/recommendations/', RecommendationView.as_view(), name='book-recommendations-root'),

    # Rutas heredadas para compatibilidad con código existente
    path('books/', BookListCreateView.as_view(), name='books-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='books-detail'),
    path('books/<int:pk>/recommendations/', RecommendationView.as_view(), name='book-recommendations'),
    path('books/import/', ImportBookView.as_view(), name='books-import'),

    path('authors/', AuthorListCreateView.as_view(), name='authors-list'),
    path('authors/<int:pk>/', AuthorDetailView.as_view(), name='authors-detail'),
    path('authors/<int:pk>/books/', AuthorBooksView.as_view(), name='author-books'),
    path('authors/<int:pk>/refresh-books/', AuthorBookRefreshView.as_view(), name='author-refresh-books'),
    path('user/books/', UserBookListCreateView.as_view(), name='user-books'),
    path('user/books/<int:pk>/', UserBookDetailView.as_view(), name='user-book-detail'),
    path('user/books/by-book/<int:book_id>/', UserBookByBookView.as_view(), name='user-book-by-book'),
    path('reviews/', ReviewListCreateView.as_view(), name='reviews'),
    path('erratas/', ErrataListCreateView.as_view(), name='erratas-list-create'),
    path('erratas/<int:pk>/', ErrataDetailUpdateView.as_view(), name='erratas-detail-update'),
]
