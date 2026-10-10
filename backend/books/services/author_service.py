import hashlib
import logging

import requests
from django.utils.text import slugify

from books.models import Author

from .base import (
    DEFAULT_HEADERS,
    OPEN_LIBRARY_AUTHORS_URL,
    OPEN_LIBRARY_COVERS_URL,
    OPENLIBRARY_HEADERS,
    WIKIDATA_ENTITY_URL,
    WIKIDATA_SEARCH_URL,
    WIKIPEDIA_API_URL,
    WIKIPEDIA_OPENSEARCH_URL,
)
from .cover_service import download_and_attach_image

logger = logging.getLogger(__name__)


def maybe_enrich_author(author: Author) -> None:
    """
    Enriquece de forma exhaustiva al autor:
    1. Wikipedia (biografía detallada en español y foto en alta resolución)
    2. Wikidata (como alternativa para retrato o biografía adicional)
    3. OpenLibrary (para fotos adicionales si aún faltan)
    """
    if author.biography and author.photo:
        return

    # 1. Wikipedia primero (más fiable y sin caídas de SSL)
    maybe_enrich_author_from_wikipedia(author)

    # 2. Wikidata si falta foto o bio
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikidata(author)

    # 3. OpenLibrary si todavía falta algo
    if not author.biography or not author.photo:
        maybe_enrich_author_from_openlibrary(author)


def maybe_enrich_author_from_wikipedia(author: Author) -> None:
    """
    Enriquece la información del autor desde Wikipedia usando headers válidos.
    """
    if author.biography and author.photo:
        return

    name = author.name.strip()
    try:
        for lang in ('es', 'en'):
            data = None
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            r = requests.get(url, timeout=7, headers=DEFAULT_HEADERS)
            if r.ok:
                candidate = r.json()
                desc = candidate.get('description', '').lower()
                if 'desambiguación' not in desc and 'disambiguation' not in desc:
                    data = candidate

            # Si falló o fue desambiguación, buscar por autor/escritor
            if not data:
                search_queries = [f"{name} escritor", f"{name} autor", name]
                for query in search_queries:
                    sr = requests.get(
                        WIKIPEDIA_OPENSEARCH_URL.format(lang=lang),
                        params={'action': 'opensearch', 'search': query, 'limit': 4, 'format': 'json'},
                        timeout=7,
                        headers=DEFAULT_HEADERS,
                    )
                    if sr.ok:
                        titles = sr.json()[1] if len(sr.json()) > 1 else []
                        for t in titles:
                            sub_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(t)
                            sub_r = requests.get(sub_url, timeout=7, headers=DEFAULT_HEADERS)
                            if sub_r.ok:
                                sub_data = sub_r.json()
                                sub_desc = sub_data.get('description', '').lower()
                                if 'desambiguación' not in sub_desc and 'disambiguation' not in sub_desc:
                                    data = sub_data
                                    break
                    if data:
                        break

            if data:
                if not author.biography:
                    extract = data.get('extract')
                    if extract and len(extract.strip()) > 20:
                        author.biography = extract[:4000]

                if not author.photo:
                    img_data = data.get('originalimage') or data.get('thumbnail') or {}
                    img_url = img_data.get('source')
                    if img_url:
                        download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=img_url,
                            filename_hint=f"{slugify(author.name)}.jpg",
                        )

                if author.biography or author.photo:
                    author.save()
                    break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikipedia: {e}")


def maybe_enrich_author_from_wikidata(author: Author) -> None:
    """
    Enriquece autor desde Wikidata buscando retrato P18 y biografía.
    """
    if author.biography and author.photo:
        return

    try:
        search_params = {
            'action': 'wbsearchentities',
            'search': author.name,
            'language': 'es',
            'type': 'item',
            'format': 'json',
            'limit': 5,
        }
        search_resp = requests.get(WIKIDATA_SEARCH_URL, params=search_params, timeout=7, headers=DEFAULT_HEADERS)
        if not search_resp.ok:
            return

        results = search_resp.json().get('search', [])
        for item in results:
            entity_id = item.get('id')
            entity_url = WIKIDATA_ENTITY_URL.format(entity=entity_id)
            entity_resp = requests.get(entity_url, timeout=7, headers=DEFAULT_HEADERS)
            if not entity_resp.ok:
                continue

            entity_info = entity_resp.json().get('entities', {}).get(entity_id, {})
            claims = entity_info.get('claims', {})

            # Foto P18
            if not author.photo and 'P18' in claims:
                image_claims = claims['P18']
                if image_claims:
                    img_filename = image_claims[0].get('mainsnak', {}).get('datavalue', {}).get('value')
                    if img_filename:
                        clean_fn = img_filename.replace(' ', '_')
                        md5_hash = hashlib.md5(clean_fn.encode('utf-8'), usedforsecurity=False).hexdigest()  # nosec B324
                        image_url = f"https://upload.wikimedia.org/wikipedia/commons/{md5_hash[0]}/{md5_hash[0:2]}/{requests.utils.quote(clean_fn)}"
                        download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=image_url,
                            filename_hint=f"{slugify(author.name)}_wikidata.jpg",
                        )

            # Descripción / Biografía
            if not author.biography:
                descriptions = entity_info.get('descriptions', {})
                desc = descriptions.get('es', {}).get('value') or descriptions.get('en', {}).get('value')
                if desc:
                    author.biography = f"{author.name}: {desc}"

            if author.biography or author.photo:
                author.save()
                break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikidata: {e}")


def maybe_enrich_author_from_openlibrary(author: Author) -> None:
    """
    Enriquece autor desde OpenLibrary como fallback secundario.
    """
    if author.biography and author.photo:
        return

    try:
        rs = requests.get(
            OPEN_LIBRARY_AUTHORS_URL,
            params={'q': author.name},
            timeout=8,
            headers=OPENLIBRARY_HEADERS,
        )
        if not rs.ok:
            return

        docs = rs.json().get('docs') or []
        if not docs:
            return

        best = docs[0]
        for candidate in docs[:3]:
            olid = candidate.get('key')
            if olid and not author.biography:
                clean_olid = olid.split("/")[-1]
                detail_url = f'https://openlibrary.org/authors/{clean_olid}.json'
                rd = requests.get(detail_url, timeout=6, headers=OPENLIBRARY_HEADERS)
                if rd.ok:
                    bio = rd.json().get('bio')
                    if isinstance(bio, dict):
                        bio = bio.get('value')
                    if bio and len(str(bio).strip()) > 20:
                        author.biography = str(bio)[:4000]
                        break

        photos = best.get('photos') or []
        if photos and not author.photo:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photos[0]}-L.jpg'
            download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg",
            )

        if author.biography or author.photo:
            author.save()

    except Exception as e:
        logger.warning(f"OpenLibrary author enrichment skipped for {author.name}: {e}")


# ==============================================================================
# Plataforma y Hub de Autores (Fase 31 — RoadmapV2)
# ==============================================================================

class AuthorService:
    @classmethod
    def get_or_create_profile(cls, user):
        """Obtiene o crea un perfil de autor para el usuario indicado."""
        from books.models import AuthorProfile
        profile, _ = AuthorProfile.objects.get_or_create(user=user)
        return profile

    @classmethod
    def claim_author(cls, user, author_id: int, pen_name: str = "", verification_notes: str = ""):
        """
        Inicia el proceso de reclamación y vinculación de un autor del catálogo
        con la cuenta del usuario.
        """
        author = Author.objects.filter(id=author_id).first()
        if not author:
            raise ValueError(f"El autor #{author_id} no existe en el catálogo.")

        profile = cls.get_or_create_profile(user)
        profile.author = author
        if pen_name:
            profile.pen_name = pen_name
        elif not profile.pen_name:
            profile.pen_name = author.name

        profile.verification_notes = verification_notes
        if user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'EDITOR'):
            profile.is_verified = True
        profile.save()
        logger.info(f"Usuario {user.username} reclamó autor #{author_id} ({author.name})")
        return profile

    @classmethod
    def get_author_dashboard_metrics(cls, author_profile) -> dict:
        """
        Genera el resumen de métricas e impacto de las obras del autor para su panel privado.
        """
        from django.db.models import Avg, Count

        from books.models import Book, Review, UserBook

        author = author_profile.author
        if not author:
            return {
                "author_id": None,
                "author_name": author_profile.pen_name or author_profile.user.username,
                "is_verified": author_profile.is_verified,
                "books_count": 0,
                "readers_total": 0,
                "readers_by_status": {"want_to_read": 0, "reading": 0, "read": 0, "abandoned": 0},
                "average_rating": None,
                "recent_reviews": [],
            }

        books = Book.objects.filter(author=author)
        book_ids = list(books.values_list('id', flat=True))
        books_count = len(book_ids)

        # Lectores totales y por estado
        user_books = UserBook.objects.filter(book_id__in=book_ids)
        readers_total = user_books.count()

        status_counts = user_books.values('status').annotate(total=Count('id'))
        readers_by_status = {"want_to_read": 0, "reading": 0, "read": 0, "abandoned": 0}
        for sc in status_counts:
            st = sc.get('status')
            if st in readers_by_status:
                readers_by_status[st] = sc.get('total', 0)

        # Valoración media agregada de todas las obras del autor
        avg_rating = Review.objects.filter(
            book_id__in=book_ids,
            rating__isnull=False,
            deleted_at__isnull=True,
            is_moderated=False,
        ).aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 2)

        # Últimas reseñas sobre libros del autor
        recent_reviews_qs = (
            Review.objects.filter(
                book_id__in=book_ids,
                deleted_at__isnull=True,
                is_moderated=False,
            )
            .select_related('user', 'book')
            .order_by('-created_at')[:10]
        )
        recent_reviews = [
            {
                "id": rev.id,
                "book_id": rev.book_id,
                "book_title": rev.book.title,
                "username": rev.user.username,
                "rating": rev.rating,
                "title": rev.title or "",
                "content": rev.text[:200] if rev.text else "",
                "created_at": rev.created_at.isoformat() if rev.created_at else None,
            }
            for rev in recent_reviews_qs
        ]

        return {
            "author_id": author.id,
            "author_name": author.name,
            "pen_name": author_profile.pen_name or author.name,
            "is_verified": author_profile.is_verified,
            "books_count": books_count,
            "readers_total": readers_total,
            "readers_by_status": readers_by_status,
            "average_rating": avg_rating,
            "recent_reviews": recent_reviews,
        }

    @classmethod
    def create_announcement(
        cls,
        author_profile,
        title: str,
        content: str,
        book_id: int | None = None,
        is_pinned: bool = False,
        publication_type: str = "ANNOUNCEMENT",
        excerpt: str = "",
        has_spoilers: bool = False,
        spoiler_warning: str = "",
        estimated_reading_time: int | None = None,
        is_draft: bool = False,
        author_id: int | None = None,
        is_paid: bool = False,
        price: float | None = None,
    ):
        """Crea una publicación oficial o comunicado emitido por el autor."""
        from django.utils import timezone
        from books.models import Author, AuthorAnnouncement, Book

        book = Book.objects.filter(id=book_id).first() if book_id else None
        author = Author.objects.filter(id=author_id).first() if author_id else (author_profile.author if author_profile else None)

        announcement = AuthorAnnouncement(
            author_profile=author_profile,
            author=author,
            book=book,
            title=title.strip(),
            content=content.strip(),
            excerpt=excerpt.strip(),
            publication_type=publication_type,
            has_spoilers=has_spoilers,
            spoiler_warning=spoiler_warning.strip(),
            is_pinned=is_pinned,
            is_draft=is_draft,
            is_paid=is_paid,
            price=price,
            created_at=timezone.now(),
        )
        if estimated_reading_time:
            announcement.estimated_reading_time = estimated_reading_time
        announcement.save()
        return announcement

    @classmethod
    def get_announcements_for_author(
        cls,
        author_id: int,
        include_drafts: bool = False,
        publication_type: str | None = None,
        include_moderated: bool = False,
    ):
        """Obtiene las publicaciones asociadas a un autor del catálogo."""
        from django.db.models import Q
        from books.models import AuthorAnnouncement
        qs = AuthorAnnouncement.objects.filter(
            Q(author_id=author_id) | Q(author_profile__author_id=author_id)
        ).select_related('author_profile', 'author', 'book')
        if not include_moderated:
            qs = qs.filter(is_moderated=False)
        if not include_drafts:
            qs = qs.filter(is_draft=False)
        if publication_type:
            qs = qs.filter(publication_type=publication_type)
        return qs.order_by('-is_pinned', '-created_at')
