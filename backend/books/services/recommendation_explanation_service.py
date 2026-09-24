"""
Motor de Explicabilidad de Recomendaciones para MyBookConnect.

Fase 52 del Roadmap: Recomendaciones Explicables (Explainable Recommendations):
Cada recomendación debe poder responder con rigor empírico y transparencia:
    "¿Por qué te recomendamos este libro?"

Ejemplo canónico:
    Te recomendamos Dune porque:
    ✓ Te han gustado 5 libros de Ciencia Ficción
    ✓ Has valorado 1984 con 5 estrellas
    ✓ Tiene similitud semántica alta con Fundación (88%)
    ✓ 3 usuarios que sigues lo han leído (@lector1, @lector2)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q

from ai.embeddings import cosine_similarity
from books.cache_utils import TTL_RECOMMENDATIONS
from books.models import Book, ReadingStatus, UserBook

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class ExplanationBullet:
    """Representa una viñeta/evidencia concreta que justifica una recomendación."""
    type: str  # 'genre', 'author', 'semantic', 'social', 'collaborative', 'wishlist', 'community'
    text: str
    confidence: float = 1.0
    icon: str = 'check'
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': self.type,
            'text': self.text,
            'confidence': round(self.confidence, 4),
            'icon': self.icon,
            'metadata': self.metadata,
        }


@dataclass
class RecommendationExplanation:
    """Estructura completa de explicabilidad para una recomendación de libro."""
    headline: str
    primary_reason: str
    reasons: list[ExplanationBullet] = field(default_factory=list)
    algorithm_version: str = "v3"

    def to_dict(self) -> dict[str, Any]:
        return {
            'headline': self.headline,
            'primary_reason': self.primary_reason,
            'reasons': [b.to_dict() for b in self.reasons],
            'total_signals': len(self.reasons),
            'algorithm_version': self.algorithm_version,
        }


class RecommendationExplanationEngine:
    """
    Motor multi-señal de explicabilidad de recomendaciones literarias.
    Extrae y clasifica evidencias transparentes basadas en interacciones reales del usuario.
    """

    def explain(
        self,
        user,
        book: Book,
        breakdown: dict[str, Any] | None = None,
        algorithm_version: str = "v3",
        existing_reason: str | None = None,
    ) -> RecommendationExplanation:
        """Genera la explicación completa y estructurada para un libro y usuario dados."""
        if not user or not user.is_authenticated:
            return self._build_anonymous_explanation(book, algorithm_version)

        cache_key = f"rec_explain_{user.id}_{book.id}_{algorithm_version}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        bullets: list[ExplanationBullet] = []

        # 1. Evidencia temático-literaria (Género)
        genre_bullet = self._extract_genre_evidence(user, book)
        if genre_bullet:
            bullets.append(genre_bullet)

        # 2. Evidencia de autor y obras ancla valoradas
        author_bullet = self._extract_author_evidence(user, book)
        if author_bullet:
            bullets.append(author_bullet)

        # 3. Evidencia semántico-conceptual (Vectorial / Embeddings)
        semantic_bullet = self._extract_semantic_evidence(user, book)
        if semantic_bullet:
            bullets.append(semantic_bullet)

        # 4. Evidencia de red social (Usuarios seguidos que han leído el libro)
        social_bullet = self._extract_social_evidence(user, book)
        if social_bullet:
            bullets.append(social_bullet)

        # 5. Evidencia colaborativa comunitaria (Lectores afines / gemelos)
        collab_bullet = self._extract_collaborative_evidence(user, book, breakdown)
        if collab_bullet:
            bullets.append(collab_bullet)

        # 6. Evidencia de lista de deseos
        wishlist_bullet = self._extract_wishlist_evidence(user, book)
        if wishlist_bullet:
            bullets.append(wishlist_bullet)

        # 7. Si hay pocas evidencias personalizadas, añadir aclamación comunitaria
        if len(bullets) < 2 and (book.average_rating or 0.0) >= 4.0:
            community_bullet = self._extract_community_evidence(book)
            if community_bullet:
                bullets.append(community_bullet)

        # Si aún no hay viñetas (usuario 100% novel sin ninguna señal previa)
        if not bullets:
            bullets.append(
                ExplanationBullet(
                    type='community',
                    text=f"Lectura recomendada y destacada dentro de nuestro catálogo ({book.average_rating or 4.5} ★)",
                    confidence=0.8,
                    icon='star',
                    metadata={'rating': book.average_rating},
                )
            )

        # Determinar motivo principal para síntesis y compatibilidad
        primary_reason = existing_reason if existing_reason else self._determine_primary_reason(bullets, breakdown)
        headline = f"Te recomendamos {book.title} porque:"

        explanation = RecommendationExplanation(
            headline=headline,
            primary_reason=primary_reason,
            reasons=bullets,
            algorithm_version=algorithm_version,
        )

        cache.set(cache_key, explanation, timeout=TTL_RECOMMENDATIONS)
        return explanation

    def _extract_genre_evidence(self, user, book: Book) -> ExplanationBullet | None:
        """
        Calcula cuántos libros de la misma categoría ha leído o valorado positivamente el usuario.
        Ejemplo: "Te han gustado 5 libros de Ciencia Ficción"
        """
        book_categories = list(book.categories.all())
        if not book_categories:
            return None

        cat_ids = [c.id for c in book_categories]
        user_books_in_genre = (
            UserBook.objects.filter(
                user=user,
                book__categories__id__in=cat_ids,
            )
            .filter(Q(status=ReadingStatus.READ) | Q(rating__gte=4))
            .distinct()
        )
        count = user_books_in_genre.count()

        if count > 0:
            # Encontrar el nombre de la categoría más leída de las compartidas
            top_cat_name = book_categories[0].name
            if count == 1:
                text = f"Te ha gustado 1 libro de {top_cat_name}"
            else:
                text = f"Te han gustado {count} libros de {top_cat_name}"

            return ExplanationBullet(
                type='genre',
                text=text,
                confidence=min(1.0, 0.5 + (count * 0.1)),
                icon='book-open',
                metadata={'category_name': top_cat_name, 'liked_count': count},
            )
        return None

    def _extract_author_evidence(self, user, book: Book) -> ExplanationBullet | None:
        """
        Verifica si el usuario ha leído o calificado obras previas del mismo autor.
        Ejemplo: "Has valorado 1984 con 5 estrellas" o "Has leído 2 libros de George Orwell"
        """
        if not book.author:
            return None

        author_entries = list(
            UserBook.objects.filter(
                user=user,
                book__author=book.author,
            )
            .exclude(book=book)
            .select_related('book')
        )

        if not author_entries:
            return None

        # Priorizar libros con alta calificación (5 estrellas, 4 estrellas)
        five_star = next((e for e in author_entries if e.rating and e.rating >= 5), None)
        if five_star:
            return ExplanationBullet(
                type='author',
                text=f"Has valorado {five_star.book.title} con 5 estrellas",
                confidence=0.98,
                icon='pen-tool',
                metadata={'author': book.author.name, 'anchor_book': five_star.book.title, 'rating': 5},
            )

        four_star = next((e for e in author_entries if e.rating and e.rating >= 4), None)
        if four_star:
            return ExplanationBullet(
                type='author',
                text=f"Has valorado {four_star.book.title} con 4 estrellas",
                confidence=0.90,
                icon='pen-tool',
                metadata={'author': book.author.name, 'anchor_book': four_star.book.title, 'rating': 4},
            )

        read_entry = next((e for e in author_entries if e.status == ReadingStatus.READ), None)
        if read_entry:
            return ExplanationBullet(
                type='author',
                text=f"Has leído {read_entry.book.title} de {book.author.name}",
                confidence=0.85,
                icon='pen-tool',
                metadata={'author': book.author.name, 'anchor_book': read_entry.book.title},
            )

        return ExplanationBullet(
            type='author',
            text=f"Tienes obras de {book.author.name} en tu biblioteca personal",
            confidence=0.75,
            icon='pen-tool',
            metadata={'author': book.author.name},
        )

    def _extract_semantic_evidence(self, user, book: Book) -> ExplanationBullet | None:
        """
        Calcula la similitud semántica coseno contra los libros leídos o favoritos del lector.
        Ejemplo: "Tiene similitud semántica alta con Fundación (88%)"
        """
        def _get_emb(b):
            try:
                e = getattr(b, 'embedding', None)
                if e is not None:
                    if hasattr(e, 'vector') and isinstance(e.vector, list):
                        return e.vector
                    if isinstance(e, list):
                        return e
                rec = getattr(b, 'embedding_record', None)
                if rec is not None and hasattr(rec, 'vector') and isinstance(rec.vector, list):
                    return rec.vector
                return None
            except Exception:
                return None

        cand_emb = _get_emb(book)
        if not cand_emb or not isinstance(cand_emb, list) or len(cand_emb) == 0:
            return None

        user_books = list(
            UserBook.objects.filter(user=user)
            .filter(Q(status=ReadingStatus.READ) | Q(rating__gte=4))
            .select_related('book')
        )

        best_sim = -1.0
        best_book = None

        for entry in user_books:
            b_emb = _get_emb(entry.book)
            if b_emb and isinstance(b_emb, list) and len(b_emb) == len(cand_emb):
                sim = float(cosine_similarity(cand_emb, b_emb))
                if sim > best_sim:
                    best_sim = sim
                    best_book = entry.book

        if best_book and best_sim >= 0.70:
            pct = int(round(best_sim * 100))
            return ExplanationBullet(
                type='semantic',
                text=f"Tiene similitud semántica alta con {best_book.title} ({pct}%)",
                confidence=best_sim,
                icon='sparkles',
                metadata={
                    'anchor_book_id': best_book.id,
                    'anchor_book_title': best_book.title,
                    'similarity': round(best_sim, 4),
                    'percentage': pct,
                },
            )
        elif best_book and best_sim >= 0.50:
            pct = int(round(best_sim * 100))
            return ExplanationBullet(
                type='semantic',
                text=f"Afinidad temática y estilística con {best_book.title} ({pct}%)",
                confidence=best_sim,
                icon='sparkles',
                metadata={
                    'anchor_book_id': best_book.id,
                    'anchor_book_title': best_book.title,
                    'similarity': round(best_sim, 4),
                    'percentage': pct,
                },
            )
        return None

    def _extract_social_evidence(self, user, book: Book) -> ExplanationBullet | None:
        """
        Consulta usuarios a los que sigue el lector que hayan leído o calificado este libro,
        filtrando estrictamente usuarios bloqueados o con perfiles/bibliotecas privadas.
        Ejemplo: "3 usuarios que sigues lo han leído (@amigo1, @amigo2)"
        """
        followed_users = list(user.following.all()[:50])
        if not followed_users:
            return None

        from users.policies import filter_visible_user_books
        followed_ids = [u.id for u in followed_users]

        # Primero probar con libros completados (READ)
        visible_ubs_read = filter_visible_user_books(
            user,
            UserBook.objects.filter(
                user_id__in=followed_ids,
                book=book,
                status=ReadingStatus.READ,
            )
        )
        read_user_ids = list(visible_ubs_read.values_list('user_id', flat=True).distinct()[:5])
        readers = list(User.objects.filter(id__in=read_user_ids))

        count = len(readers)
        if count == 0:
            # Probar si lo tienen en cualquier estado de lectura visible
            visible_ubs_any = filter_visible_user_books(
                user,
                UserBook.objects.filter(
                    user_id__in=followed_ids,
                    book=book,
                )
            )
            any_user_ids = list(visible_ubs_any.values_list('user_id', flat=True).distinct()[:5])
            readers = list(User.objects.filter(id__in=any_user_ids))
            count = len(readers)

        if count > 0:
            usernames = [f"@{u.username}" for u in readers[:2]]
            names_str = ", ".join(usernames)
            if count == 1:
                text = f"{names_str} (a quien sigues) ha leído este libro"
            elif count == 2:
                text = f"{names_str} (a quienes sigues) han leído este libro"
            else:
                remaining = count - 2
                text = f"{count} usuarios que sigues lo han leído ({names_str} y {remaining} más)"

            return ExplanationBullet(
                type='social',
                text=text,
                confidence=0.92,
                icon='users',
                metadata={
                    'followed_count': count,
                    'followed_usernames': [u.username for u in readers],
                },
            )
        return None

    def _extract_collaborative_evidence(
        self,
        user,
        book: Book,
        breakdown: dict[str, Any] | None,
    ) -> ExplanationBullet | None:
        """
        Verifica recomendaciones de lectores con gustos gemelos (filtrado colaborativo v2).
        Ejemplo: "Recomendado por lectores con alta afinidad hacia tus gustos literarios"
        """
        if breakdown and breakdown.get('collaborative', 0.0) > 0.3:
            shared_peers = breakdown.get('shared_peers', 1)
            top_peer = breakdown.get('top_peer')
            if top_peer:
                text = f"Leído y aclamado por lectores con gustos muy similares a los tuyos como @{top_peer}"
            elif shared_peers > 1:
                text = f"Recomendado por {shared_peers} lectores con alta coincidencia en lecturas compartidas"
            else:
                text = "Recomendado por lectores con alta afinidad hacia tus gustos literarios"

            return ExplanationBullet(
                type='collaborative',
                text=text,
                confidence=float(breakdown['collaborative']),
                icon='user-check',
                metadata={'collaborative_score': breakdown['collaborative'], 'shared_peers': shared_peers},
            )
        return None

    def _extract_wishlist_evidence(self, user, book: Book) -> ExplanationBullet | None:
        """
        Verifica si se alinea con lecturas pendientes en la lista de deseos del usuario.
        """
        # Comprobar si el usuario tiene libros del mismo autor o categoría en su lista de deseos
        cand_cats = list(book.categories.all())
        if cand_cats:
            wl_count = UserBook.objects.filter(
                user=user,
                status=ReadingStatus.WANT_TO_READ,
                book__categories__in=cand_cats,
            ).distinct().count()

            if wl_count > 0:
                return ExplanationBullet(
                    type='wishlist',
                    text=f"Alineado con los {wl_count} libros pendientes en tu lista de deseos",
                    confidence=0.78,
                    icon='bookmark',
                    metadata={'pending_wishlist_count': wl_count},
                )
        return None

    def _extract_community_evidence(self, book: Book) -> ExplanationBullet | None:
        """Genera evidencia de prestigio o aclamación comunitaria para el libro."""
        rating = book.average_rating or 0.0
        if rating >= 4.0:
            return ExplanationBullet(
                type='community',
                text=f"Obra destacada y aclamada por la comunidad de lectores ({rating} ★)",
                confidence=min(1.0, rating / 5.0),
                icon='star',
                metadata={'average_rating': rating},
            )
        return None

    def _determine_primary_reason(
        self,
        bullets: list[ExplanationBullet],
        breakdown: dict[str, Any] | None,
    ) -> str:
        """Determina la razón principal en una sola frase concisa para retrocompatibilidad."""
        if not bullets:
            return "Recomendado para ti basado en tu perfil lector"

        # Prioridad 1: Autor dominante
        author_bullet = next((b for b in bullets if b.type == 'author'), None)
        if author_bullet and author_bullet.confidence >= 0.90:
            return author_bullet.text

        # Prioridad 2: Semántica alta
        semantic_bullet = next((b for b in bullets if b.type == 'semantic'), None)
        if semantic_bullet and semantic_bullet.confidence >= 0.80:
            return semantic_bullet.text

        # Prioridad 3: Género con varios libros
        genre_bullet = next((b for b in bullets if b.type == 'genre'), None)
        if genre_bullet and genre_bullet.metadata.get('liked_count', 0) >= 2:
            return genre_bullet.text

        # Prioridad 4: Social
        social_bullet = next((b for b in bullets if b.type == 'social'), None)
        if social_bullet:
            return social_bullet.text

        # Fallback: Primera viñeta
        return bullets[0].text

    def _build_anonymous_explanation(self, book: Book, algorithm_version: str) -> RecommendationExplanation:
        """Explicación predeterminada para usuarios no autenticados o llamadas genéricas."""
        bullets = [
            ExplanationBullet(
                type='community',
                text=f"Obra aclamada por la comunidad ({book.average_rating or 4.5} ★)",
                confidence=0.9,
                icon='star',
                metadata={'average_rating': book.average_rating},
            )
        ]
        first_cat = book.categories.first()
        if first_cat:
            bullets.append(
                ExplanationBullet(
                    type='genre',
                    text=f"Referencia destacada dentro del género {first_cat.name}",
                    confidence=0.85,
                    icon='book-open',
                    metadata={'category_name': first_cat.name},
                )
            )

        return RecommendationExplanation(
            headline=f"Te recomendamos {book.title} porque:",
            primary_reason=bullets[0].text,
            reasons=bullets,
            algorithm_version=algorithm_version,
        )


def explain_recommendation(
    user,
    book: Book,
    breakdown: dict[str, Any] | None = None,
    algorithm_version: str = "v3",
    existing_reason: str | None = None,
) -> dict[str, Any]:
    """Función de conveniencia para obtener la explicación estructurada de una recomendación."""
    engine = RecommendationExplanationEngine()
    return engine.explain(
        user=user,
        book=book,
        breakdown=breakdown,
        algorithm_version=algorithm_version,
        existing_reason=existing_reason,
    ).to_dict()
