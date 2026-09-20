import csv
import io
import logging
import re
from datetime import date, datetime
from typing import Any

from django.db import transaction

from books.models import Author, Book, ReadingStatus, Review, UserBook, normalize_isbn
from books.services.enrichment_service import attach_categories_to_book

logger = logging.getLogger(__name__)


class CSVFormatDetector:
    GOODREADS = 'goodreads'
    CALIBRE = 'calibre'
    GENERIC = 'generic'

    @classmethod
    def detect_format(cls, fieldnames: list[str]) -> str:
        lower_headers = {h.strip().lower() for h in fieldnames if h}
        if 'exclusive shelf' in lower_headers or 'book id' in lower_headers or 'my rating' in lower_headers:
            return cls.GOODREADS
        if 'identifiers' in lower_headers or ('authors' in lower_headers and 'tags' in lower_headers):
            return cls.CALIBRE
        return cls.GENERIC


def _clean_goodreads_value(val: str | None) -> str:
    """Limpia fórmulas de texto de Excel/Goodreads como =\"9788445077528\"."""
    if not val:
        return ''
    cleaned = str(val).strip()
    if cleaned.startswith('="') and cleaned.endswith('"'):
        cleaned = cleaned[2:-1]
    return cleaned.strip()


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%d/%m/%Y', '%Y'):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _map_goodreads_status(shelf: str | None, has_date_read: bool = False) -> str:
    shelf_clean = (shelf or '').strip().lower()
    if shelf_clean == 'read':
        return ReadingStatus.READ
    if shelf_clean == 'currently-reading':
        return ReadingStatus.READING
    if shelf_clean in ('to-read', 'want-to-read', 'wishlist'):
        return ReadingStatus.WANT_TO_READ
    if shelf_clean in ('abandoned', 'did-not-finish', 'dnf'):
        return ReadingStatus.ABANDONED
    return ReadingStatus.READ if has_date_read else ReadingStatus.WANT_TO_READ


def _map_generic_status(status_val: str | None) -> str:
    s = (status_val or '').strip().lower()
    if s in ('read', 'leido', 'leído', 'terminado', 'finished'):
        return ReadingStatus.READ
    if s in ('reading', 'leyendo', 'en progreso', 'in_progress'):
        return ReadingStatus.READING
    if s in ('want_to_read', 'por leer', 'quiero leer', 'pendiente', 'to_read', 'wishlist'):
        return ReadingStatus.WANT_TO_READ
    if s in ('abandoned', 'abandonado', 'dnf'):
        return ReadingStatus.ABANDONED
    return ReadingStatus.WANT_TO_READ


class CSVImportService:
    """
    Servicio de importación avanzada e idempotente de bibliotecas (Fase 55 y 56).
    """

    @classmethod
    def parse_and_preview_csv(cls, file_content: bytes | str, user) -> dict[str, Any]:
        """
        Analiza el archivo CSV, detecta su formato y genera una previsualización
        exhaustiva clasificando cada fila por estado (nuevo, en catálogo, en biblioteca, error).
        """
        if isinstance(file_content, bytes):
            # Probar decodificaciones comunes
            decoded = None
            for encoding in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
                try:
                    decoded = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                raise ValueError("No se pudo descifrar la codificación del archivo CSV.")
        else:
            decoded = file_content

        f = io.StringIO(decoded)
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("El archivo CSV está vacío o no contiene encabezados válidos.")

        detected_format = CSVFormatDetector.detect_format(reader.fieldnames)
        preview_items = []
        valid_count = 0
        existing_in_catalog_count = 0
        existing_in_library_count = 0
        invalid_count = 0

        # Cache local de libros de la biblioteca del usuario para evitar N+1 en preview
        user_books = set(
            UserBook.objects.filter(user=user).values_list('book__isbn', 'book__title', 'book_id')
        )
        user_book_isbns = {item[0] for item in user_books if item[0]}
        user_book_titles = {item[1].strip().lower() for item in user_books if item[1]}

        row_idx = 0
        for row in reader:
            row_idx += 1
            item = cls._normalize_row(row, detected_format, row_idx)
            if not item['is_valid']:
                invalid_count += 1
                preview_items.append(item)
                continue

            valid_count += 1

            # Comprobar coincidencia en catálogo existente
            matched_book = None
            if item['isbn']:
                matched_book = Book.objects.filter(isbn=item['isbn']).first()
            if not matched_book and item['title'] and item['author']:
                matched_book = Book.objects.filter(
                    title__iexact=item['title'],
                    author__name__iexact=item['author'],
                ).first()
            elif not matched_book and item['title']:
                matched_book = Book.objects.filter(title__iexact=item['title']).first()

            # Comprobar si ya está en la biblioteca personal
            in_library = False
            if item['isbn'] and item['isbn'] in user_book_isbns:
                in_library = True
            elif item['title'].lower() in user_book_titles:
                in_library = True
            elif matched_book and UserBook.objects.filter(user=user, book=matched_book).exists():
                in_library = True

            if in_library:
                item['match_status'] = 'in_library'
                existing_in_library_count += 1
            elif matched_book:
                item['match_status'] = 'in_catalog'
                item['catalog_book_id'] = matched_book.id
                existing_in_catalog_count += 1
            else:
                item['match_status'] = 'new'

            preview_items.append(item)

        return {
            'format_detected': detected_format,
            'total_rows': row_idx,
            'valid_count': valid_count,
            'existing_in_catalog_count': existing_in_catalog_count,
            'existing_in_library_count': existing_in_library_count,
            'invalid_count': invalid_count,
            'preview_items': preview_items,
        }

    @classmethod
    def _normalize_row(cls, row: dict[str, Any], fmt: str, row_index: int) -> dict[str, Any]:
        """Normaliza una fila independientemente del dialecto CSV de origen."""
        # Limpieza de claves
        clean_row = {k.strip().lower() if k else '': v for k, v in row.items()}

        title = ''
        author = ''
        isbn = None
        status = ReadingStatus.WANT_TO_READ
        rating = None
        review_text = ''
        date_read = None
        categories = []

        if fmt == CSVFormatDetector.GOODREADS:
            title = clean_row.get('title', '').strip()
            author = clean_row.get('author', '').strip()
            isbn_raw = _clean_goodreads_value(clean_row.get('isbn13') or clean_row.get('isbn'))
            isbn = normalize_isbn(isbn_raw)

            date_read_str = clean_row.get('date read')
            date_read = _parse_date(date_read_str)

            shelf = clean_row.get('exclusive shelf')
            status = _map_goodreads_status(shelf, has_date_read=bool(date_read))

            try:
                r_val = int(clean_row.get('my rating', 0) or 0)
                if 1 <= r_val <= 5:
                    rating = r_val
            except (ValueError, TypeError):
                pass

            review_text = clean_row.get('my review', '').strip()

        elif fmt == CSVFormatDetector.CALIBRE:
            title = clean_row.get('title', '').strip()
            author = clean_row.get('authors', '').strip()
            if '&' in author:
                author = author.split('&')[0].strip()

            isbn_raw = clean_row.get('isbn', '').strip()
            if not isbn_raw and 'identifiers' in clean_row:
                m = re.search(r'isbn:([0-9X-]+)', clean_row.get('identifiers') or '', re.IGNORECASE)
                if m:
                    isbn_raw = m.group(1)
            isbn = normalize_isbn(isbn_raw)

            try:
                r_val = int(float(clean_row.get('rating', 0) or 0))
                if 1 <= r_val <= 5:
                    rating = r_val
            except (ValueError, TypeError):
                pass

            tags = clean_row.get('tags', '')
            if tags:
                categories = [t.strip() for t in tags.split(',') if t.strip()]

            status = ReadingStatus.READ

        else:
            # Generic CSV
            for t_key in ('title', 'titulo', 'título', 'nombre'):
                if t_key in clean_row and clean_row[t_key]:
                    title = clean_row[t_key].strip()
                    break

            for a_key in ('author', 'autor', 'autores', 'authors'):
                if a_key in clean_row and clean_row[a_key]:
                    author = clean_row[a_key].strip()
                    break

            for i_key in ('isbn', 'isbn13', 'isbn10', 'isbn_13'):
                if i_key in clean_row and clean_row[i_key]:
                    isbn = normalize_isbn(clean_row[i_key])
                    break

            for s_key in ('status', 'estado', 'shelf'):
                if s_key in clean_row and clean_row[s_key]:
                    status = _map_generic_status(clean_row[s_key])
                    break

            for r_key in ('rating', 'puntuacion', 'puntuación', 'calificacion', 'calificación'):
                if r_key in clean_row and clean_row[r_key]:
                    try:
                        r_val = int(float(clean_row[r_key]))
                        if 1 <= r_val <= 5:
                            rating = r_val
                    except (ValueError, TypeError):
                        pass
                    break

        is_valid = bool(title)
        error_message = None
        if not is_valid:
            error_message = 'Falta el título obligatorio de la obra.'

        return {
            'row_index': row_index,
            'title': title,
            'author': author,
            'isbn': isbn,
            'status': status,
            'rating': rating,
            'review_text': review_text,
            'date_read': str(date_read) if date_read else None,
            'categories': categories,
            'is_valid': is_valid,
            'error_message': error_message,
            'match_status': 'unknown',
        }

    @classmethod
    def execute_csv_import(
        cls,
        items: list[dict[str, Any]],
        user,
        update_existing: bool = True,
    ) -> dict[str, Any]:
        """
        Ejecuta la importación masiva de los libros previsualizados dentro de una
        transacción atómica con deduplicación e idempotencia estricta.
        """
        imported_books_count = 0
        added_to_library_count = 0
        updated_in_library_count = 0
        reviews_created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for item in items:
                if not item.get('is_valid', True):
                    skipped_count += 1
                    continue

                title = (item.get('title') or '').strip()
                if not title:
                    skipped_count += 1
                    continue

                author_name = (item.get('author') or '').strip()
                isbn = normalize_isbn(item.get('isbn'))
                status_val = item.get('status') or ReadingStatus.WANT_TO_READ
                rating_val = item.get('rating')
                review_text = (item.get('review_text') or '').strip()
                date_read = _parse_date(item.get('date_read'))
                categories = item.get('categories') or []

                # 1. Resolver Autor
                author_obj = None
                if author_name:
                    author_obj, _ = Author.objects.get_or_create(name=author_name)

                # 2. Resolver o Crear Libro (Deduplicación multi-nivel)
                book = None
                if isbn:
                    book = Book.objects.filter(isbn=isbn).first()

                if not book and author_obj:
                    book = Book.objects.filter(title__iexact=title, author=author_obj).first()
                elif not book:
                    book = Book.objects.filter(title__iexact=title).first()

                if not book:
                    book = Book.objects.create(
                        title=title,
                        author=author_obj,
                        isbn=isbn,
                    )
                    imported_books_count += 1
                    if categories:
                        attach_categories_to_book(book, categories)
                else:
                    # Enriquecer libro existente si le faltaba autor o isbn
                    updated_fields = []
                    if isbn and not book.isbn:
                        book.isbn = isbn
                        updated_fields.append('isbn')
                    if author_obj and not book.author:
                        book.author = author_obj
                        updated_fields.append('author')
                    if updated_fields:
                        book.save(update_fields=updated_fields)

                # 3. Vincular a la biblioteca personal UserBook
                user_book, ub_created = UserBook.objects.get_or_create(
                    user=user,
                    book=book,
                    defaults={
                        'status': status_val,
                        'rating': rating_val,
                        'finished_at': date_read,
                        'is_read': status_val == ReadingStatus.READ,
                    },
                )

                if ub_created:
                    added_to_library_count += 1
                elif update_existing:
                    # Actualizar estado o calificación si se solicitó
                    user_book.status = status_val
                    if rating_val is not None:
                        user_book.rating = rating_val
                    if date_read is not None:
                        user_book.finished_at = date_read
                    user_book.is_read = (status_val == ReadingStatus.READ)
                    user_book.save()
                    updated_in_library_count += 1
                else:
                    skipped_count += 1

                # 4. Crear Reseña si hay calificación y texto o si rating >= 1
                if rating_val and 1 <= rating_val <= 5:
                    existing_rev = Review.objects.filter(user=user, book=book, deleted_at__isnull=True).first()
                    if not existing_rev and review_text:
                        Review.objects.create(
                            user=user,
                            book=book,
                            rating=rating_val,
                            text=review_text,
                        )
                        reviews_created_count += 1
                    elif existing_rev and review_text and update_existing:
                        existing_rev.text = review_text
                        existing_rev.rating = rating_val
                        existing_rev.save()

            # Disparar evaluación de gamificación (racha, insignias, retos) si el usuario la tiene activa
            if getattr(user, 'gamification_enabled', True):
                try:
                    from books.services.gamification_service import GamificationService
                    GamificationService.evaluate_user_badges(user)
                except Exception as e:
                    logger.debug(f"Error evaluando gamificación tras importación: {e}")

        return {
            'success': True,
            'imported_books_count': imported_books_count,
            'added_to_library_count': added_to_library_count,
            'updated_in_library_count': updated_in_library_count,
            'reviews_created_count': reviews_created_count,
            'skipped_count': skipped_count,
        }
