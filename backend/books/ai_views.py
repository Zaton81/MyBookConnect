"""
Módulo de re-exports para compatibilidad retrospectiva con backend/books/ai_views.py.
La implementación canónica de las vistas de IA reside en `backend/ai/views.py`.
"""

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
