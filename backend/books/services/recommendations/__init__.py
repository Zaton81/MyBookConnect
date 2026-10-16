"""
Subpaquete de Recomendaciones de MyBookConnect:
Pipeline modular en 4 etapas (Candidates, Filtering, Reranking MMR, Explanations).
"""

from .candidates import CandidateGenerator
from .explanations import BatchExplanationEngine
from .filtering import RecommendationFilter
from .pipeline import RecommendationPipeline
from .reranking import MMRReranker

__all__ = [
    'CandidateGenerator',
    'RecommendationFilter',
    'MMRReranker',
    'BatchExplanationEngine',
    'RecommendationPipeline',
]
