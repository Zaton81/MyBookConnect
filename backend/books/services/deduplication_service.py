import logging
from collections import defaultdict

from django.db import transaction
from django.db.models import Avg

from books.models import (
    Book,
    ReadingStatus,
    Review,
    UserBook,
    normalize_isbn,
    normalize_title,
)

logger = logging.getLogger(__name__)


def get_book_completeness_score(book: Book) -> int:
    """
    Calcula una puntuación de completitud para determinar la ficha canónica
    entre varios libros duplicados.
    """
    score = 0
    if book.cover:
        score += 50
    if book.description:
        score += min(len(book.description), 500) // 10
    if book.isbn:
        score += 25
    if book.additional_isbns:
        score += len(book.additional_isbns) * 10
    if book.average_rating:
        score += 15
    if book.published_date:
        score += 10
    if book.google_volume_id or book.openlibrary_work_id:
        score += 10

    # Actividad de lectores
    readers_count = book.user_entries.count()
    reviews_count = book.reviews.filter(deleted_at__isnull=True).count()
    score += readers_count * 5 + reviews_count * 10

    return score


def find_duplicate_books() -> list[dict]:
    """
    Identifica todos los grupos de libros duplicados en el catálogo basados en:
    - Mismo autor (o ambos sin autor)
    - Mismo título normalizado (insensible a mayúsculas, diacríticos y puntuación)
    """
    # Mapeo: (author_id, normalized_title) -> list[Book]
    grouped = defaultdict(list)
    books = Book.objects.select_related('author').prefetch_related('categories', 'authors', 'user_entries', 'reviews')

    for book in books:
        norm_title = normalize_title(book.title)
        if not norm_title:
            continue
        key = (book.author_id, norm_title)
        grouped[key].append(book)

    duplicate_groups = []
    for (author_id, norm_title), book_list in grouped.items():
        if len(book_list) > 1:
            # Seleccionar canónico por mayor puntuación; desempate por fecha más antigua (menor ID)
            sorted_books = sorted(
                book_list,
                key=lambda b: (get_book_completeness_score(b), -b.id),
                reverse=True,
            )
            canonical = sorted_books[0]
            duplicates = sorted_books[1:]
            duplicate_groups.append({
                'canonical': canonical,
                'duplicates': duplicates,
                'author_id': author_id,
                'normalized_title': norm_title,
                'count': len(book_list),
            })

    return duplicate_groups


def merge_books(canonical: Book, duplicates: list[Book]) -> Book:
    """
    Fusiona de forma atómica uno o más libros duplicados en el libro canónico,
    reubicando todas las relaciones dependientes (UserBook, Review, Listas, Actividades)
    y preservando todos los ISBNs (físicos, digitales, etc.) en additional_isbns.
    """
    with transaction.atomic():
        # Bloquear registro canónico para actualización
        canonical = Book.objects.select_for_update().get(id=canonical.id)

        for dup in duplicates:
            if dup.id == canonical.id:
                continue

            # 1. Unificar ISBNs en additional_isbns
            if dup.isbn:
                canonical.add_isbn(dup.isbn)
            if isinstance(dup.additional_isbns, list):
                for extra_isbn in dup.additional_isbns:
                    canonical.add_isbn(extra_isbn)

            # 2. Portada
            if not canonical.cover and dup.cover:
                canonical.cover = dup.cover

            # 3. Descripción más rica
            if not canonical.description and dup.description:
                canonical.description = dup.description
            elif dup.description and len(dup.description) > len(canonical.description or ""):
                canonical.description = dup.description

            # 4. Metadatos e identificadores externos
            if not canonical.google_volume_id and dup.google_volume_id:
                canonical.google_volume_id = dup.google_volume_id
            if not canonical.openlibrary_work_id and dup.openlibrary_work_id:
                canonical.openlibrary_work_id = dup.openlibrary_work_id
            if not canonical.openlibrary_edition_id and dup.openlibrary_edition_id:
                canonical.openlibrary_edition_id = dup.openlibrary_edition_id
            if not canonical.published_date and dup.published_date:
                canonical.published_date = dup.published_date

            # 5. Categorías y Autores (M2M)
            canonical.categories.add(*dup.categories.all())
            canonical.authors.add(*dup.authors.all())
            if not canonical.author_id and dup.author_id:
                canonical.author = dup.author

            # 6. Migrar UserBook (Estantería del lector)
            status_order = {
                ReadingStatus.READ: 4,
                ReadingStatus.READING: 3,
                ReadingStatus.WANT_TO_READ: 2,
                ReadingStatus.ABANDONED: 1,
            }
            for dup_ub in dup.user_entries.all():
                canon_ub = canonical.user_entries.filter(user=dup_ub.user).first()
                if canon_ub:
                    if status_order.get(dup_ub.status, 0) > status_order.get(canon_ub.status, 0):
                        canon_ub.status = dup_ub.status
                        canon_ub.is_read = dup_ub.is_read
                    if dup_ub.rating and not canon_ub.rating:
                        canon_ub.rating = dup_ub.rating
                    if dup_ub.notes and not canon_ub.notes:
                        canon_ub.notes = dup_ub.notes
                    if dup_ub.progress > canon_ub.progress:
                        canon_ub.progress = dup_ub.progress
                        canon_ub.current_page = dup_ub.current_page
                    if dup_ub.finished_at and not canon_ub.finished_at:
                        canon_ub.finished_at = dup_ub.finished_at
                    canon_ub.save()
                    dup_ub.delete()
                else:
                    dup_ub.book = canonical
                    dup_ub.save(update_fields=['book'])

            # 7. Migrar Reviews
            for dup_rev in dup.reviews.all():
                canon_rev = canonical.reviews.filter(user=dup_rev.user, deleted_at__isnull=True).first()
                if canon_rev:
                    # El usuario ya tiene una reseña activa en la ficha canónica
                    dup_rev.delete()
                else:
                    dup_rev.book = canonical
                    dup_rev.save(update_fields=['book'])

            # 8. Migrar ReadingListItems
            for rl_item in dup.reading_list_items.all():
                if canonical.reading_list_items.filter(reading_list=rl_item.reading_list).exists():
                    rl_item.delete()
                else:
                    rl_item.book = canonical
                    rl_item.save(update_fields=['book'])

            # 9. Migrar Erratas, Clics de Afiliado y Recomendaciones
            dup.erratas.all().update(book=canonical)
            dup.affiliate_clicks.all().update(book=canonical)
            dup.recommendation_feedbacks.all().update(book=canonical)
            dup.author_announcements.all().update(book=canonical)

            # 10. Migrar UserPost y Actividades Sociales
            try:
                from users.models import Activity, UserPost
                UserPost.objects.filter(book=dup).update(book=canonical)
                Activity.objects.filter(book=dup).update(book=canonical)
            except Exception as e:
                logger.warning(f"Error reasignando actividades de libro duplicado {dup.id}: {e}")

            # 11. Eliminar libro duplicado
            dup.delete()

        # Guardar canónico y recalcular valoraciones
        canonical.save()

        review_avg = canonical.reviews.filter(
            deleted_at__isnull=True, is_moderated=False, rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg']
        if review_avg is not None:
            canonical.average_rating = round(review_avg, 2)
        else:
            ub_avg = canonical.user_entries.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
            canonical.average_rating = round(ub_avg, 2) if ub_avg else None
        canonical.save(update_fields=['average_rating'])

        return canonical


def deduplicate_all_books() -> dict:
    """
    Ejecuta el ciclo completo de deduplicación en todo el catálogo.
    Devuelve un resumen con el número de grupos procesados y libros eliminados.
    """
    groups = find_duplicate_books()
    merged_groups = 0
    duplicates_removed = 0

    for group in groups:
        canonical = group['canonical']
        duplicates = group['duplicates']
        num_dups = len(duplicates)
        merge_books(canonical, duplicates)
        merged_groups += 1
        duplicates_removed += num_dups
        logger.info(
            f"Fusión completada para '{canonical.title}' (ID {canonical.id}): {num_dups} duplicados absorbidos."
        )

    return {
        'groups_merged': merged_groups,
        'duplicates_removed': duplicates_removed,
    }
