"""
Servicios y cálculos matemáticos para vectores de embeddings semánticos.
"""

import math
from typing import Any

from ai.clients.base import AIProvider
from ai.clients.factory import get_ai_provider


def get_embedding_for_text(
    text: str,
    provider: AIProvider | None = None,
) -> list[float] | None:
    """
    Obtiene el vector de embeddings para un texto mediante el proveedor de IA activo.

    :param text: Texto a vectorizar.
    :param provider: Instancia opcional de AIProvider. Si es None, utiliza el proveedor por defecto.
    :return: Lista de floats con los componentes del vector o None si no fue posible generarlo.
    """
    if not text or not text.strip():
        return None

    client = provider or get_ai_provider()
    return client.get_embedding(text.strip())


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """
    Calcula la similitud coseno entre dos vectores numéricos.

    :param vector_a: Primer vector.
    :param vector_b: Segundo vector.
    :return: Valor de similitud en el rango [-1.0, 1.0]. Retorna 0.0 si las dimensiones no coinciden o la norma es nula.
    """
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def rank_items_by_semantic_similarity(
    query_embedding: list[float],
    items_with_embeddings: list[tuple[Any, list[float]]],
    top_k: int = 10,
) -> list[tuple[Any, float]]:
    """
    Ordena una colección de elementos según su similitud coseno con respecto a un vector de consulta.

    :param query_embedding: Vector de la consulta de búsqueda.
    :param items_with_embeddings: Lista de tuplas (objeto, vector_embedding).
    :param top_k: Cantidad máxima de resultados a retornar.
    :return: Lista de tuplas (objeto, score_similitud) ordenada descendentemente.
    """
    if not query_embedding or not items_with_embeddings:
        return []

    scored_items: list[tuple[Any, float]] = []
    for item, emb in items_with_embeddings:
        if emb and len(emb) == len(query_embedding):
            score = cosine_similarity(query_embedding, emb)
            scored_items.append((item, score))

    scored_items.sort(key=lambda x: x[1], reverse=True)
    return scored_items[:top_k]
