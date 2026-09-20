import logging
from django.core.management.base import BaseCommand
from django.db.models import Count

from books.models import Book, Category
from books.services.enrichment_service import enrich_book_metadata

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Enriquece e hidrata categorías y géneros faltantes en los libros del catálogo."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Límite de libros a procesar (0 para todos los libros sin categorías).',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        books_without_cats = (
            Book.objects.annotate(cat_count=Count('categories'))
            .filter(cat_count=0)
            .order_by('-id')
        )

        total_pending = books_without_cats.count()
        self.stdout.write(f"Libros pendientes de categorías: {total_pending}")

        if limit > 0:
            target_books = list(books_without_cats[:limit])
        else:
            target_books = list(books_without_cats)

        enriched_count = 0
        for i, book in enumerate(target_books, 1):
            try:
                enrich_book_metadata(book)
                book.refresh_from_db()
                cat_names = list(book.categories.values_list('name', flat=True))
                if cat_names:
                    enriched_count += 1
                if i % 25 == 0 or i == len(target_books):
                    self.stdout.write(
                        f"[{i}/{len(target_books)}] Procesados. Enriquecidos con éxito: {enriched_count}"
                    )
            except Exception as e:
                logger.warning(f"Error enriqueciendo libro {book.id} ({book.title}): {e}")

        total_with_cats = (
            Book.objects.annotate(cat_count=Count('categories'))
            .filter(cat_count__gt=0)
            .count()
        )
        total_categories = Category.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompletado. Libros con categorías ahora: {total_with_cats} | Total de categorías en catálogo: {total_categories}"
            )
        )
