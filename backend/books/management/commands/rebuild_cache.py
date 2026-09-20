import time

from django.core.cache import cache
from django.core.management.base import BaseCommand

from books.cache_utils import TTL_BOOK_DETAIL, book_detail_key
from books.models import Book
from books.serializers import BookSerializer
from books.services.trending_service import PERIOD_DAYS, get_trending_books


class Command(BaseCommand):
    help = (
        "Regenera y precalienta la caché de Redis a partir de PostgreSQL tras un reinicio, "
        "desastre o mantenimiento (garantizando que Redis no sea fuente de verdad)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Cantidad de libros destacados a precalentar en caché (por defecto: 20).",
        )
        parser.add_argument(
            "--flush-first",
            action="store_true",
            help="Limpia completamente la caché de Redis antes de iniciar la regeneración.",
        )

    def handle(self, *args, **options):
        limit = options.get("limit", 20)
        flush_first = options.get("flush_first", False)

        start_time = time.time()
        self.stdout.write(self.style.NOTICE("Iniciando regeneración y precalentamiento de Redis desde PostgreSQL..."))

        if flush_first:
            self.stdout.write(self.style.WARNING("Vaciando caché completa de Redis (FLUSH)..."))
            cache.clear()

        rebuilt_keys = 0

        # 1. Regenerar rankings de tendencias para todos los períodos
        self.stdout.write("Regenerando tendencias multi-período...")
        for period in PERIOD_DAYS.keys():
            # Forzar cálculo directo desde PostgreSQL asegurando que la clave esté vacía antes
            from books.cache_utils import trending_key
            cache.delete(trending_key(period))
            results = get_trending_books(period=period, limit=limit)
            rebuilt_keys += 1
            self.stdout.write(f"  - Tendencias '{period}': {len(results)} libros cacheados.")

        # 2. Precalentar detalles de libros más populares / recientes
        self.stdout.write(f"Precalentando detalles de los {limit} libros principales...")
        top_books = Book.objects.select_related("author").prefetch_related("categories").order_by("-average_rating", "-id")[:limit]
        for book in top_books:
            key = book_detail_key(book.id)
            serializer = BookSerializer(book)
            cache.set(key, serializer.data, timeout=TTL_BOOK_DETAIL)
            rebuilt_keys += 1

        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"¡Regeneración de Redis finalizada con éxito!\n"
                f"  - Total de claves regeneradas: {rebuilt_keys}\n"
                f"  - Tiempo transcurrido: {elapsed:.2f}s\n"
                f"  - Fuente de la verdad: PostgreSQL (100% consistente)"
            )
        )
