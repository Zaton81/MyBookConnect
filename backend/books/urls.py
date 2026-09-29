from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import FeedView

from .admin_views import PublicLegalDocumentListView, PublicLegalDocumentView
from .ai_views import (
    AIAssistantView,
    AIBookSummaryView,
    AICompareBooksView,
    AIEmbeddingStatsView,
    AIExplainBookView,
    AIGenerateBookEmbeddingView,
    AISemanticSearchView,
    AIStatusView,
    AIToolExecuteView,
    AIToolsListView,
)
from .discovery_views import BookDiscoveryView
from .import_views import CSVImportConfirmView, CSVImportPreviewView
from .views import (
    AuthorAnnouncementCreateView,
    AuthorAnnouncementListView,
    AuthorBookRefreshView,
    AuthorBooksView,
    AuthorClaimView,
    AuthorDashboardView,
    AuthorDetailView,
    AuthorListCreateView,
    AuthorProfileMeView,
    BookAffiliateClickView,
    BookAffiliateLinksView,
    BookDetailView,
    BookListCreateView,
    BookRecommendationExplainView,
    ErrataDetailUpdateView,
    ErrataListCreateView,
    ExternalSyncView,
    ImportBookView,
    ReadingListViewSet,
    ReadingMatchView,
    ReadingStatsView,
    RecommendationFeedbackView,
    RecommendationMetricsView,
    RecommendationView,
    SimilarReadersView,
    TrendingBooksView,
    UnifiedBookSearchView,
    UserBookByBookView,
    UserBookDetailView,
    UserBookListCreateView,
    UserPreferenceEmbeddingView,
    UserRecommendationsView,
)

router = DefaultRouter()
router.register('reading-lists', ReadingListViewSet, basename='reading-lists')

urlpatterns = [
    path('legal/', PublicLegalDocumentListView.as_view(), name='books-legal-list'),
    path('legal/<slug:slug>/', PublicLegalDocumentView.as_view(), name='books-legal-document'),
    # Rutas estándar limpias (/api/v1/books/...)
    path('', BookListCreateView.as_view(), name='books-list-root'),
    path('search/', UnifiedBookSearchView.as_view(), name='books-unified-search'),
    path('feed/', FeedView.as_view(), name='books-social-feed'),
    path('discover/', BookDiscoveryView.as_view(), name='books-discover'),
    path('trending/', TrendingBooksView.as_view(), name='books-trending'),
    path('recommendations/', UserRecommendationsView.as_view(), name='user-recommendations'),
    path('recommendations/<int:book_id>/explain/', BookRecommendationExplainView.as_view(), name='book-recommendation-explain'),
    path('recommendations/user-embedding/', UserPreferenceEmbeddingView.as_view(), name='user-recommendations-embedding'),
    path('recommendations/similar-readers/', SimilarReadersView.as_view(), name='user-recommendations-similar-readers'),
    path('recommendations/feedback/', RecommendationFeedbackView.as_view(), name='recommendation-feedback'),
    path('recommendations/metrics/', RecommendationMetricsView.as_view(), name='recommendation-metrics'),
    path('statistics/', ReadingStatsView.as_view(), name='books-statistics'),
    path('gamification/', include('books.gamification_urls')),
    path('match/<int:user_id>/', ReadingMatchView.as_view(), name='user-reading-match'),
    path('import/', ImportBookView.as_view(), name='books-import-root'),
    path('import/csv/preview/', CSVImportPreviewView.as_view(), name='books-import-csv-preview'),
    path('import/csv/confirm/', CSVImportConfirmView.as_view(), name='books-import-csv-confirm'),
    path('sync/external/', ExternalSyncView.as_view(), name='books-external-sync'),

    # Rutas de Inteligencia Artificial (OpenAI-compatible)
    path('ai/status/', AIStatusView.as_view(), name='book-ai-status'),
    path('ai/assistant/', AIAssistantView.as_view(), name='book-ai-assistant'),
    path('ai/semantic-search/', AISemanticSearchView.as_view(), name='book-ai-semantic-search'),
    path('ai/compare/', AICompareBooksView.as_view(), name='book-ai-compare'),
    path('ai/embeddings/stats/', AIEmbeddingStatsView.as_view(), name='book-ai-embeddings-stats'),
    path('ai/tools/', AIToolsListView.as_view(), name='book-ai-tools'),
    path('ai/tools/execute/', AIToolExecuteView.as_view(), name='book-ai-tools-execute'),
    path('<int:pk>/ai/summary/', AIBookSummaryView.as_view(), name='book-ai-summary'),
    path('<int:pk>/ai/explain/', AIExplainBookView.as_view(), name='book-ai-explain'),
    path('<int:pk>/ai/embeddings/generate/', AIGenerateBookEmbeddingView.as_view(), name='book-ai-embeddings-generate'),

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
    path('reviews/', include('books.review_urls')),
    path('erratas/', ErrataListCreateView.as_view(), name='erratas-list-create'),
    path('erratas/<int:pk>/', ErrataDetailUpdateView.as_view(), name='erratas-detail-update'),

    # Afiliación y Monetización (Fase 31)
    path('<int:pk>/affiliate-links/', BookAffiliateLinksView.as_view(), name='book-affiliate-links'),
    path('<int:pk>/affiliate-click/', BookAffiliateClickView.as_view(), name='book-affiliate-click'),
    path('books/<int:pk>/affiliate-links/', BookAffiliateLinksView.as_view(), name='book-affiliate-links-legacy'),
    path('books/<int:pk>/affiliate-click/', BookAffiliateClickView.as_view(), name='book-affiliate-click-legacy'),

    # Plataforma de Autores (Fase 31)
    path('authors/me/', AuthorProfileMeView.as_view(), name='authors-me'),
    path('authors/claim/', AuthorClaimView.as_view(), name='authors-claim'),
    path('authors/dashboard/', AuthorDashboardView.as_view(), name='authors-dashboard'),
    path('authors/announcements/', AuthorAnnouncementCreateView.as_view(), name='authors-announcement-create'),
    path('authors/<int:pk>/announcements/', AuthorAnnouncementListView.as_view(), name='authors-announcements'),
] + router.urls
