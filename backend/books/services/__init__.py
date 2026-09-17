"""
Servicios modulares de importación, enriquecimiento y gestión de proveedores para libros y autores.
"""

from .author_service import (
    maybe_enrich_author,
    maybe_enrich_author_from_openlibrary,
    maybe_enrich_author_from_wikidata,
    maybe_enrich_author_from_wikipedia,
)
from .base import (
    DEFAULT_HEADERS,
    GOOGLE_BOOKS_API_URL,
    OPEN_LIBRARY_AUTHORS_URL,
    OPEN_LIBRARY_COVERS_URL,
    OPEN_LIBRARY_SEARCH_URL,
    OPENLIBRARY_HEADERS,
    WIKIDATA_ENTITY_URL,
    WIKIDATA_SEARCH_URL,
    WIKIPEDIA_API_URL,
    WIKIPEDIA_OPENSEARCH_URL,
    BookProvider,
    ProviderAuthorData,
    ProviderBookData,
    get_google_books_api_key,
)
from .cover_service import (
    _attach_best_cover,
    _download_and_attach_image,
    attach_best_cover,
    download_and_attach_image,
    ensure_book_cover,
)
from .enrichment_service import (
    enrich_book_metadata,
    maybe_enrich_book,
)
from .import_service import (
    _create_or_get_from_volume,
    _import_books_by_author_from_wikipedia,
    _import_from_openlibrary_by_title,
    _import_from_wikipedia_by_title,
    import_books_by_author,
    import_multiple_by_title,
    import_single_by_query,
)
from .providers import (
    GoogleBooksProvider,
    OpenLibraryProvider,
    WikipediaProvider,
)
from .recommendation_feedback_service import (
    get_recommendation_metrics,
    record_recommendation_event,
)
from .recommendation_service import (
    get_book_recommendations,
    get_similar_readers,
    get_user_recommendations,
)
from .recommendation_v1_service import (
    RecommendationEngineV1,
    RecommendationV1Item,
    ScoreBreakdownV1,
    recommend_books_v1,
)
from .recommendation_v2_service import (
    RecommendationEngineV2,
    RecommendationV2Item,
    ScoreBreakdownV2,
    SimilarUserPeer,
    get_similar_readers_v2,
    recommend_books_v2,
)
from .recommendation_v3_service import (
    RecommendationEngineV3,
    RecommendationV3Item,
    ScoreBreakdownV3,
    UserPreferenceVector,
    get_user_preference_vector,
    recommend_books_v3,
)
from .stats_service import get_user_reading_stats
from .trending_service import get_trending_books
from .unified_search_service import (
    SearchResultItem,
    UnifiedSearchEngine,
    unified_book_search,
)

__all__ = [
    # Funciones públicas principales
    'UnifiedSearchEngine',
    'SearchResultItem',
    'unified_book_search',
    'import_single_by_query',
    'import_multiple_by_title',
    'import_books_by_author',
    'get_trending_books',
    'get_user_recommendations',
    'recommend_books_v1',
    'RecommendationEngineV1',
    'recommend_books_v2',
    'RecommendationEngineV2',
    'recommend_books_v3',
    'RecommendationEngineV3',
    'get_user_preference_vector',
    'SimilarUserPeer',
    'get_similar_readers',
    'get_book_recommendations',
    'record_recommendation_event',
    'get_recommendation_metrics',
    'maybe_enrich_author',
    'maybe_enrich_author_from_wikipedia',
    'maybe_enrich_author_from_wikidata',
    'maybe_enrich_author_from_openlibrary',
    'ensure_book_cover',
    'enrich_book_metadata',
    'maybe_enrich_book',
    'get_user_reading_stats',
    'download_and_attach_image',
    '_download_and_attach_image',
    'attach_best_cover',
    '_attach_best_cover',
    '_create_or_get_from_volume',
    '_import_books_by_author_from_wikipedia',
    '_import_from_openlibrary_by_title',
    '_import_from_wikipedia_by_title',
    'get_google_books_api_key',
    # Constantes
    'GOOGLE_BOOKS_API_URL',
    'OPEN_LIBRARY_SEARCH_URL',
    'OPEN_LIBRARY_AUTHORS_URL',
    'OPEN_LIBRARY_COVERS_URL',
    'WIKIPEDIA_API_URL',
    'WIKIPEDIA_OPENSEARCH_URL',
    'WIKIDATA_SEARCH_URL',
    'WIKIDATA_ENTITY_URL',
    'DEFAULT_HEADERS',
    'OPENLIBRARY_HEADERS',
    # Tipos y DTOs
    'ProviderBookData',
    'ProviderAuthorData',
    'BookProvider',
    # Proveedores
    'GoogleBooksProvider',
    'OpenLibraryProvider',
    'WikipediaProvider',
]
