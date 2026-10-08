"""
Servicio de Integración con Redes Sociales y Compartición Gráfica (Sprint 16).

Este módulo proporciona:
- Generación de textos optimizados para redes sociales con emojis y hashtags literarios.
- Generación de deep links para compartir en un clic en X/Twitter, WhatsApp, Telegram, LinkedIn, Facebook y Email.
- Generación de metadatos para tarjetas gráficas de previsualización (libros, estadísticas, retos, medallas, listas).
- Registro y tracking de métricas de compartición y viralidad.
"""

import logging
from typing import Any
import urllib.parse

from django.contrib.auth import get_user_model
from django.utils import timezone

from books.models import Badge, Book, ReadingChallenge, ReadingList, UserBook, UserChallenge
from books.services.stats_service import get_user_reading_stats

logger = logging.getLogger(__name__)
User = get_user_model()


def build_social_links(share_text: str, canonical_url: str, title: str = "MyBookConnect") -> dict[str, str]:
    """Genera las URLs directas de compartición con codificación segura de parámetros."""
    encoded_text = urllib.parse.quote(share_text)
    encoded_url = urllib.parse.quote(canonical_url)
    encoded_title = urllib.parse.quote(title)

    return {
        "twitter": f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}",
        "whatsapp": f"https://api.whatsapp.com/send?text={encoded_text}%20{encoded_url}",
        "telegram": f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        "email": f"mailto:?subject={encoded_title}&body={encoded_text}%0A%0A{encoded_url}",
    }


def generate_social_share_card(
    share_type: str,
    object_id: int | str | None = None,
    year: int | str | None = None,
    user_id: int | str | None = None,
    base_url: str = "http://localhost:5173",
) -> dict[str, Any]:
    """
    Construye la tarjeta social y deep links según el tipo de recurso compartido.

    Tipos soportados:
    - 'book': Libro del catálogo.
    - 'reading_stats': Estadísticas de lectura (anuales o globales).
    - 'challenge': Reto literario de la comunidad.
    - 'badge': Insignia o logro literario.
    - 'reading_list': Lista de lectura pública.
    """
    clean_type = (share_type or "").strip().lower()
    base_url = base_url.rstrip("/")

    if clean_type == "book":
        try:
            book = Book.objects.select_related("author").get(id=int(object_id))
        except (Book.DoesNotExist, ValueError, TypeError):
            raise ValueError(f"Libro con id '{object_id}' no encontrado.")

        author_name = book.get_author_names()
        canonical_url = f"{base_url}/books/{book.id}"
        cover_url = book.cover.url if book.cover else None
        rating_str = f" ⭐ {book.average_rating:.1f}/5" if book.average_rating else ""

        share_text = f"📖 Descubre «{book.title}» de {author_name}{rating_str}. ¡Una lectura recomendada en @MyBookConnect!"
        hashtags = ["#MyBookConnect", "#LecturaRecomendada", "#Libros"]

        card_data = {
            "title": book.title,
            "subtitle": f"por {author_name}",
            "stat_highlight": f"{book.average_rating:.1f} ★" if book.average_rating else "Novedad",
            "stat_label": "Calificación media",
            "badge_or_icon": "📚",
            "image_url": cover_url,
            "theme_color": "teal",
            "site_name": "MyBookConnect",
        }

        return {
            "share_type": "book",
            "title": book.title,
            "description": book.description[:200] if book.description else f"Libro por {author_name}",
            "canonical_url": canonical_url,
            "hashtags": hashtags,
            "share_text": share_text,
            "share_urls": build_social_links(share_text, canonical_url, title=f"Descubre {book.title}"),
            "card_data": card_data,
        }

    elif clean_type in ("reading_stats", "stats"):
        target_user_id = user_id or object_id
        if not target_user_id:
            raise ValueError("Se requiere 'user_id' u 'object_id' para generar tarjeta de estadísticas.")

        stats = get_user_reading_stats(int(target_user_id), year=year)
        eval_year = stats.get("selected_year")
        year_label = str(eval_year) if eval_year else "Histórico"

        total_read = stats.get("total_read", 0)
        total_pages = stats.get("total_pages_read", 0)
        avg_days = stats.get("reading_pace", {}).get("avg_days_per_book")

        pace_extra = f" (media de {avg_days} días por libro)" if avg_days else ""
        share_text = f"🎯 ¡He completado {total_read} libros y {total_pages:,} páginas en {year_label}{pace_extra}! Descubre mi biblioteca en @MyBookConnect."
        canonical_url = f"{base_url}/statistics?user_id={target_user_id}" + (f"&year={eval_year}" if eval_year else "")
        hashtags = ["#MyBookConnect", "#RetoLector", "#EstadisticasDeLectura", f"#Lecturas{year_label}"]

        card_data = {
            "title": f"Memoria Lectora {year_label}",
            "subtitle": "Estadísticas y Ritmo de Lectura",
            "stat_highlight": f"{total_read} libros",
            "stat_label": f"{total_pages:,} páginas leídas",
            "badge_or_icon": "📊",
            "image_url": None,
            "theme_color": "indigo",
            "site_name": "MyBookConnect",
        }

        return {
            "share_type": "reading_stats",
            "title": f"Estadísticas de Lectura {year_label}",
            "description": f"{total_read} libros terminados y {total_pages:,} páginas leídas.",
            "canonical_url": canonical_url,
            "hashtags": hashtags,
            "share_text": share_text,
            "share_urls": build_social_links(share_text, canonical_url, title=f"Mis lecturas de {year_label}"),
            "card_data": card_data,
        }

    elif clean_type == "challenge":
        try:
            challenge = ReadingChallenge.objects.get(slug=str(object_id)) if not str(object_id).isdigit() else ReadingChallenge.objects.get(id=int(object_id))
        except (ReadingChallenge.DoesNotExist, ValueError):
            raise ValueError(f"Reto con id/slug '{object_id}' no encontrado.")

        user_progress_str = ""
        user_pct_str = ""
        if user_id:
            try:
                uc = UserChallenge.objects.get(user_id=int(user_id), challenge=challenge)
                prog = getattr(uc, 'current_progress', getattr(uc, 'current_count', 0))
                pct = round((prog / challenge.target_count) * 100, 1) if challenge.target_count else 0
                user_progress_str = f" ({prog}/{challenge.target_count})"
                user_pct_str = f" — {min(pct, 100)}% superado"
            except UserChallenge.DoesNotExist:
                pass

        share_text = f"🏆 ¡Participando en el reto literario «{challenge.title}»{user_progress_str}{user_pct_str} en @MyBookConnect! ¿Aceptas el desafío?"
        canonical_url = f"{base_url}/challenges"
        hashtags = ["#MyBookConnect", "#RetoLiterario", "#ClubDeLectura"]

        ctype_str = challenge.challenge_type.replace('_', ' ') if hasattr(challenge, 'challenge_type') else 'libros'
        card_data = {
            "title": challenge.title,
            "subtitle": f"Meta: {challenge.target_count} {ctype_str}",
            "stat_highlight": f"{challenge.participants_count if hasattr(challenge, 'participants_count') else 0} lectores",
            "stat_label": "Comunidad participando",
            "badge_or_icon": challenge.badge_reward.icon if getattr(challenge, 'badge_reward', None) else "🏆",
            "image_url": None,
            "theme_color": "amber",
            "site_name": "MyBookConnect",
        }

        return {
            "share_type": "challenge",
            "title": challenge.title,
            "description": challenge.description[:200] if challenge.description else "Reto literario",
            "canonical_url": canonical_url,
            "hashtags": hashtags,
            "share_text": share_text,
            "share_urls": build_social_links(share_text, canonical_url, title=challenge.title),
            "card_data": card_data,
        }

    elif clean_type == "badge":
        try:
            badge = Badge.objects.get(slug=str(object_id)) if not str(object_id).isdigit() else Badge.objects.get(id=int(object_id))
        except (Badge.DoesNotExist, ValueError):
            raise ValueError(f"Insignia con id/slug '{object_id}' no encontrada.")

        share_text = f"🎖️ ¡He desbloqueado la medalla «{badge.name}» (+{badge.points} pts) en @MyBookConnect! 🚀"
        canonical_url = f"{base_url}/challenges"
        hashtags = ["#MyBookConnect", "#LogroLector", "#MedalleroLiterario"]

        card_data = {
            "title": badge.name,
            "subtitle": badge.description,
            "stat_highlight": f"+{badge.points} pts",
            "stat_label": badge.category.capitalize(),
            "badge_or_icon": badge.icon or "🎖️",
            "image_url": None,
            "theme_color": "purple",
            "site_name": "MyBookConnect",
        }

        return {
            "share_type": "badge",
            "title": badge.name,
            "description": badge.description,
            "canonical_url": canonical_url,
            "hashtags": hashtags,
            "share_text": share_text,
            "share_urls": build_social_links(share_text, canonical_url, title=f"Medalla {badge.name}"),
            "card_data": card_data,
        }

    elif clean_type in ("reading_list", "list"):
        try:
            rlist = ReadingList.objects.select_related('user').get(id=int(object_id))
        except (ReadingList.DoesNotExist, ValueError):
            raise ValueError(f"Lista de lectura '{object_id}' no encontrada.")

        list_name = getattr(rlist, 'name', getattr(rlist, 'title', 'Colección'))
        books_count = getattr(rlist, 'books_count', rlist.items.count())
        creator_name = rlist.user.username if rlist.user else 'lector'
        share_text = f"📚 Echa un vistazo a la lista «{list_name}» ({books_count} libros) creada por @{creator_name} en @MyBookConnect."
        canonical_url = f"{base_url}/reading-lists?id={rlist.id}"
        hashtags = ["#MyBookConnect", "#ListaDeLectura", "#LibrosRecomendados"]

        card_data = {
            "title": list_name,
            "subtitle": f"por @{creator_name}",
            "stat_highlight": f"{books_count} libros",
            "stat_label": "Colección literaria",
            "badge_or_icon": "📑",
            "image_url": None,
            "theme_color": "teal",
            "site_name": "MyBookConnect",
        }

        return {
            "share_type": "reading_list",
            "title": list_name,
            "description": rlist.description[:200] if rlist.description else f"Colección con {books_count} libros",
            "canonical_url": canonical_url,
            "hashtags": hashtags,
            "share_text": share_text,
            "share_urls": build_social_links(share_text, canonical_url, title=list_name),
            "card_data": card_data,
        }

    else:
        raise ValueError(f"Tipo de compartición '{share_type}' no soportado.")


def track_social_share(
    share_type: str,
    object_id: str | int | None,
    platform: str,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Registra y audita un evento de compartición social para analítica de viralidad."""
    normalized_platform = (platform or "unknown").strip().lower()
    logger.info(
        f"[SocialShare] Usuario {user_id or 'anónimo'} compartió {share_type}:{object_id} en {normalized_platform}"
    )

    return {
        "status": "tracked",
        "share_type": share_type,
        "object_id": str(object_id) if object_id else None,
        "platform": normalized_platform,
        "timestamp": timezone.now().isoformat(),
    }
