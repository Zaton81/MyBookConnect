"""
Módulo de re-exports para compatibilidad retrospectiva con backend/books/ai_views.py.
La implementación canónica de las vistas de IA reside en `backend/ai/views.py`.
"""

from ai.services import (  # noqa: F401
    compare_books_ai,
    execute_assistant_tool,
    explain_book_ai,
    get_ai_status,
    get_assistant_reply,
    get_available_assistant_tools,
    get_book_ai_summary,
    semantic_search_books,
)
from ai.views import (  # noqa: F401
    AIAssistantView,
    AIBookSummaryView,
    AIBookVisualInsightsView,
    AICompareBooksView,
    AIEmbeddingStatsView,
    AIExplainBookView,
    AIGenerateBookEmbeddingView,
    AIMultimodalAssistantView,
    AIMultimodalCoverAnalysisView,
    AISemanticSearchView,
    AIStatusView,
    AIToolExecuteView,
    AIToolsListView,
)

