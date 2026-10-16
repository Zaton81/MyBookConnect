"""
Rutas de API para el módulo de Inteligencia Artificial (backend/ai/).
Expone endpoints canónicos para BookAI, análisis multimodal, búsqueda semántica y herramientas de IA.
"""

from django.urls import path

from .views import (
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

urlpatterns = [
    path('status/', AIStatusView.as_view(), name='ai-status'),
    path('assistant/', AIAssistantView.as_view(), name='ai-assistant'),
    path('semantic-search/', AISemanticSearchView.as_view(), name='ai-semantic-search'),
    path('compare/', AICompareBooksView.as_view(), name='ai-compare'),
    path('embeddings/stats/', AIEmbeddingStatsView.as_view(), name='ai-embeddings-stats'),
    path('tools/', AIToolsListView.as_view(), name='ai-tools'),
    path('tools/execute/', AIToolExecuteView.as_view(), name='ai-tools-execute'),
    path('multimodal/analyze-cover/', AIMultimodalCoverAnalysisView.as_view(), name='ai-multimodal-analyze-cover'),
    path('multimodal/assistant/', AIMultimodalAssistantView.as_view(), name='ai-multimodal-assistant'),
    # Rutas por libro
    path('<int:pk>/summary/', AIBookSummaryView.as_view(), name='ai-book-summary'),
    path('<int:pk>/explain/', AIExplainBookView.as_view(), name='ai-book-explain'),
    path('<int:pk>/visual-insights/', AIBookVisualInsightsView.as_view(), name='ai-book-visual-insights'),
    path('<int:pk>/embeddings/generate/', AIGenerateBookEmbeddingView.as_view(), name='ai-book-embeddings-generate'),
]
