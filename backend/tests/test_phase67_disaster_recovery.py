from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.cache_utils import (
    book_detail_key,
    trending_key,
)
from books.models import Author, Book, Category, Review
from books.services.backup_service import DatabaseBackupService

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestRedisNotSourceOfTruth:
    """
    Verifica el principio rector de la Fase 67:
    'Redis no debe ser fuente de verdad'.
    Si Redis se borra o corrompe por completo, PostgreSQL conserva toda la información
    y el patrón cache-aside recarga transparentemente los datos sin interrupción.
    """

    def test_redis_flush_resilience_and_cache_aside(self):
        client = APIClient()
        author = Author.objects.create(name="Resilient Author")
        category = Category.objects.create(name="Distributed Systems")
        book = Book.objects.create(
            title="Resilience in Distributed Systems",
            author=author,
            isbn="9780987654321",
            average_rating=4.8,
            cover="covers/sample.jpg",
            description="High availability and disaster recovery patterns",
            enrichment_attempted=True,
        )
        book.categories.add(category)
        user = User.objects.create_user(username="dr_user", password="password123")
        Review.objects.create(user=user, book=book, rating=5, text="Excelente para DR")

        with patch("books.tasks.download_cover_task.delay"), patch("books.tasks.enrich_book_task.delay"):
            # 1. Poblar la caché consultando detalle del libro y tendencias
            book_key = book_detail_key(book.id)
            assert cache.get(book_key) is None

            # Primera petición al endpoint de detalle
            res1 = client.get(f"/api/v1/books/{book.id}/")
            assert res1.status_code == 200
            assert res1.data["title"] == "Resilience in Distributed Systems"

            # La clave ahora debe estar en Redis
            assert cache.get(book_key) is not None

            # 2. Desastre total de Redis: FLUSHALL / cache.clear()
            cache.clear()

            # Comprobar que Redis está 100% vacío
            assert cache.get(book_key) is None
            for period in ("week", "month", "year", "all"):
                assert cache.get(trending_key(period)) is None

            # 3. Segunda petición: sin Redis, PostgreSQL responde sin error (cache-aside)
            res2 = client.get(f"/api/v1/books/{book.id}/")
            assert res2.status_code == 200
            assert res2.data["title"] == "Resilience in Distributed Systems"
            assert res2.data["author"]["name"] == "Resilient Author"

            # La caché se ha regenerado transparentemente desde PostgreSQL
            assert cache.get(book_key) is not None

    def test_rebuild_cache_management_command_populates_redis(self):
        """Verifica que el comando rebuild_cache regenera todas las tendencias y libros en Redis."""
        author = Author.objects.create(name="Trending Author")
        book1 = Book.objects.create(title="Book 1", author=author, average_rating=4.9)
        book2 = Book.objects.create(title="Book 2", author=author, average_rating=4.5)

        # Vaciar Redis
        cache.clear()
        for p in ("week", "month", "year", "all"):
            assert cache.get(trending_key(p)) is None
        assert cache.get(book_detail_key(book1.id)) is None
        assert cache.get(book_detail_key(book2.id)) is None

        # Ejecutar comando de regeneración
        call_command("rebuild_cache", limit=10, flush_first=True)

        # Verificar que las claves de tendencias están repobladas
        for p in ("week", "month", "year", "all"):
            cached_trending = cache.get(trending_key(p))
            assert cached_trending is not None, f"Clave trending_key('{p}') no fue repoblada en Redis"
            assert isinstance(cached_trending, list)

        # Verificar que el detalle del libro destacado está precalentado
        cached_book = cache.get(book_detail_key(book1.id))
        assert cached_book is not None
        assert cached_book["title"] == "Book 1"


@pytest.mark.django_db(transaction=True)
class TestDisasterRecoveryEndToEndDrill:
    """Simulacro integral de desastre: caída de BD, restauración fría y reconstrucción de caché."""

    def test_database_restore_and_cache_resilience(self, tmp_path):
        author = Author.objects.create(name="Primary Author")
        book = Book.objects.create(title="Mission Critical Manual", author=author, isbn="9781112223334")
        user = User.objects.create_user(username="dr_auditor", password="password123")
        Review.objects.create(user=user, book=book, rating=5, text="Crítico para auditoría")

        # 1. Generar backup de estado sano
        backup_res = DatabaseBackupService.backup_database(output_dir=tmp_path, force_django_dump=True)
        backup_file = Path(backup_res["backup_file"])

        # 2. Simular desastre: corrupción de registros y caída de caché
        book.title = "TITULO_CORRUPTO_POST_ATAQUE"
        book.save()
        cache.clear()

        assert Book.objects.get(id=book.id).title == "TITULO_CORRUPTO_POST_ATAQUE"

        # 3. Aplicar Runbook 1: Restaurar BD desde backup verificado
        DatabaseBackupService.restore_database(backup_file=backup_file, verify_checksum=True)

        # 4. Aplicar Runbook 3: Regenerar Redis desde PostgreSQL
        call_command("rebuild_cache", limit=10, flush_first=True)

        # 5. Comprobar que la base de datos y la caché son 100% coherentes y sanas
        restored_book = Book.objects.get(id=book.id)
        assert restored_book.title == "Mission Critical Manual"

        cached_detail = cache.get(book_detail_key(book.id))
        assert cached_detail is not None
        assert cached_detail["title"] == "Mission Critical Manual"


@pytest.mark.django_db
class TestSecretRotationAndTokenRevocation:
    """Verifica el protocolo de seguridad del Runbook 5: rotación de secretos y revocación de JWTs."""

    def test_token_revocation_on_security_incident(self):
        client = APIClient()
        user = User.objects.create_user(username="compromised_user", password="secure_pass_123")

        # Emitir tokens JWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        profile_res = client.get("/api/v1/auth/profile/")
        assert profile_res.status_code == 200

        # Incidente de seguridad: poner en lista negra el refresh token
        refresh.blacklist()

        # Un nuevo intento de refresco con el token revocado debe fallar con 401
        refresh_res = client.post("/api/v1/auth/token/refresh/", {"refresh": str(refresh)})
        assert refresh_res.status_code == 401
