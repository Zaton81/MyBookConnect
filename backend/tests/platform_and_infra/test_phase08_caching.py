"""
Suite de Pruebas de Calidad para la Fase 8 — Caché (Prioridad P1).

Cubre los requerimientos de la Sección 13 de RoadmapV2.md:
1. Inventario exhaustivo y namespaces estandarizados (13.1): book:{id}, user:{id}, recommendations:{user_id}, feed:{user_id}, search:{query}.
2. TTLs definidos por tipo de entidad (13.2).
3. Matriz de invalidación reactiva ante eventos clave (13.3):
   - Review created / updated
   - Follow created / deleted
   - User privacy changed
   - Book updated
   - Reading status changed
4. Protección contra estampidas (Cache Stampede Protection / mutex locking) (13.4).
5. Resiliencia y degradación elegante ante caídas de Redis (13.5).
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from books.cache_utils import (
    TTL_BOOK_DETAIL,
    TTL_FEED,
    TTL_RECOMMENDATIONS,
    TTL_SEARCH,
    TTL_STATS,
    TTL_TRENDING,
    TTL_USER_PROFILE,
    book_detail_key,
    book_recommendations_key,
    cascade_review_invalidation,
    feed_cache_key,
    get_or_set_stampede_protected,
    safe_cache_delete,
    safe_cache_get,
    safe_cache_set,
    search_cache_key,
    trending_key,
    user_profile_key,
    user_recommendations_key,
    user_stats_key,
)
from books.models import Author, Book, ReadingStatus, UserBook
from users.models import PrivacyChoices

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def cache_test_data(db):
    author = Author.objects.create(name="Stanislaw Lem")
    book = Book.objects.create(title="Solaris", author=author, isbn="9788439722748")

    alice = User.objects.create_user(
        username="alice_c8",
        email="alice_c8@example.com",
        password="password123",
        bio="Lector de ciencia ficción",
    )
    bob = User.objects.create_user(
        username="bob_c8",
        email="bob_c8@example.com",
        password="password123",
        bio="Lector apasionado",
    )

    return {
        'author': author,
        'book': book,
        'alice': alice,
        'bob': bob,
    }


@pytest.mark.django_db
class TestPhase08CacheInventoryAndTTLs:
    """Verifica el inventario de claves y TTLs definidos en el Roadmap (13.1 & 13.2)."""

    def test_cache_keys_namespaces(self, cache_test_data):
        book = cache_test_data['book']
        alice = cache_test_data['alice']

        # book:{id}
        b_key = book_detail_key(book.id)
        assert b_key == f"book:{book.id}"

        # user:{id}
        u_key = user_profile_key(alice.id)
        assert u_key == f"user:profile:{alice.id}"

        # recommendations:{user_id}:{strategy}
        r_key = user_recommendations_key(alice.id, strategy='hybrid')
        assert f"recommendations:user:{alice.id}:hybrid" == r_key

        # feed:{user_id}
        f_key = feed_cache_key(alice.id)
        assert f_key == f"feed:{alice.id}"

        # search:{query_hash}:{mode}:{page}
        s_key = search_cache_key("Solaris", mode='hybrid', page=1)
        assert s_key.startswith("search:")
        assert "hybrid:1" in s_key

    def test_ttl_definitions(self):
        assert TTL_BOOK_DETAIL == 900
        assert TTL_USER_PROFILE == 900
        assert TTL_RECOMMENDATIONS == 900
        assert TTL_FEED == 300
        assert TTL_SEARCH == 300
        assert TTL_TRENDING == 900
        assert TTL_STATS == 900


@pytest.mark.django_db(transaction=True)
class TestPhase08ReactiveInvalidationMatrix:
    """Verifica la invalidación reactiva ante los 5 eventos clave del Roadmap (13.3)."""

    def test_review_created_and_updated_invalidation(self, cache_test_data):
        alice = cache_test_data['alice']
        book = cache_test_data['book']

        # Calentar cachés
        cache.set(book_detail_key(book.id), {"title": book.title}, timeout=600)
        cache.set(user_profile_key(alice.id), {"user": alice.username}, timeout=600)
        cache.set(user_recommendations_key(alice.id, "hybrid"), ["rec1"], timeout=600)
        cache.set(trending_key("week"), ["dummy"], timeout=600)

        # 1. Review Created
        cascade_review_invalidation(book.id, alice.id)
        assert cache.get(book_detail_key(book.id)) is None
        assert cache.get(user_profile_key(alice.id)) is None
        assert cache.get(user_recommendations_key(alice.id, "hybrid")) is None
        assert cache.get(trending_key("week")) is None

    def test_follow_created_and_deleted_invalidation(self, api_client, cache_test_data):
        alice = cache_test_data['alice']
        bob = cache_test_data['bob']

        # Calentar cachés de feed, perfil y recomendaciones
        cache.set(feed_cache_key(alice.id), ["activity1"], timeout=600)
        cache.set(user_profile_key(alice.id), {"u": "alice"}, timeout=600)
        cache.set(user_profile_key(bob.id), {"u": "bob"}, timeout=600)
        cache.set(user_recommendations_key(alice.id, "social"), ["rec"], timeout=600)

        api_client.force_authenticate(user=alice)

        # Follow
        res = api_client.post(f"/api/v1/users/{bob.id}/follow/")
        assert res.status_code == status.HTTP_200_OK
        assert cache.get(feed_cache_key(alice.id)) is None
        assert cache.get(user_profile_key(alice.id)) is None
        assert cache.get(user_profile_key(bob.id)) is None
        assert cache.get(user_recommendations_key(alice.id, "social")) is None

        # Calentar de nuevo y Unfollow
        cache.set(feed_cache_key(alice.id), ["activity1"], timeout=600)
        cache.set(user_profile_key(alice.id), {"u": "alice"}, timeout=600)

        res_unfollow = api_client.post(f"/api/v1/users/{bob.id}/unfollow/")
        assert res_unfollow.status_code == status.HTTP_200_OK
        assert cache.get(feed_cache_key(alice.id)) is None
        assert cache.get(user_profile_key(alice.id)) is None

    def test_user_privacy_changed_invalidation(self, api_client, cache_test_data):
        alice = cache_test_data['alice']

        # Calentar cachés
        cache.set(user_profile_key(alice.id), {"u": "alice"}, timeout=600)
        cache.set(feed_cache_key(alice.id), ["feed1"], timeout=600)
        cache.set(user_recommendations_key(alice.id, "hybrid"), ["rec1"], timeout=600)

        api_client.force_authenticate(user=alice)
        res = api_client.patch("/api/v1/auth/profile/update/", {"privacy_level": PrivacyChoices.PRIVATE}, format="json")
        assert res.status_code == status.HTTP_200_OK

        assert cache.get(user_profile_key(alice.id)) is None
        assert cache.get(feed_cache_key(alice.id)) is None
        assert cache.get(user_recommendations_key(alice.id, "hybrid")) is None

    def test_book_updated_invalidation(self, cache_test_data):
        book = cache_test_data['book']

        cache.set(book_detail_key(book.id), {"title": book.title}, timeout=600)
        cache.set(book_recommendations_key(book.id), ["rec"], timeout=600)
        cache.set(trending_key("month"), ["trend"], timeout=600)

        book.title = "Solaris (Edición Definitiva)"
        book.save(update_fields=["title"])

        assert cache.get(book_detail_key(book.id)) is None
        assert cache.get(book_recommendations_key(book.id)) is None
        assert cache.get(trending_key("month")) is None

    def test_reading_status_changed_invalidation(self, cache_test_data):
        alice = cache_test_data['alice']
        book = cache_test_data['book']

        cache.set(user_profile_key(alice.id), {"u": "alice"}, timeout=600)
        cache.set(user_stats_key(alice.id), {"stats": 1}, timeout=600)
        cache.set(user_recommendations_key(alice.id, "hybrid"), ["rec"], timeout=600)
        cache.set(feed_cache_key(alice.id), ["feed"], timeout=600)
        cache.set(book_detail_key(book.id), {"b": "solaris"}, timeout=600)

        # Mutación de lectura
        UserBook.objects.create(user=alice, book=book, status=ReadingStatus.READING)

        assert cache.get(user_profile_key(alice.id)) is None
        assert cache.get(user_stats_key(alice.id)) is None
        assert cache.get(user_recommendations_key(alice.id, "hybrid")) is None
        assert cache.get(feed_cache_key(alice.id)) is None
        assert cache.get(book_detail_key(book.id)) is None


@pytest.mark.django_db
class TestPhase08StampedeProtection:
    """Verifica la protección contra estampidas de caché (13.4)."""

    def test_get_or_set_stampede_protected_computes_once(self):
        call_count = 0

        def expensive_computation():
            nonlocal call_count
            call_count += 1
            return {"data": 42}

        test_key = "test:stampede:key_1"
        cache.delete(test_key)
        cache.delete(f"lock:{test_key}")

        # Primer acceso: computa y almacena
        val1 = get_or_set_stampede_protected(test_key, expensive_computation, ttl=60)
        assert val1 == {"data": 42}
        assert call_count == 1

        # Segundo acceso: lee de caché directamente sin recomputar
        val2 = get_or_set_stampede_protected(test_key, expensive_computation, ttl=60)
        assert val2 == {"data": 42}
        assert call_count == 1  # No se volvió a llamar a la función costosa

        cache.delete(test_key)


@pytest.mark.django_db
class TestPhase08RedisFailureResilience:
    """Verifica la resiliencia y degradación elegante ante caídas de Redis (13.5)."""

    def test_safe_cache_wrappers_handle_redis_exceptions(self):
        # Simular fallo total de Redis en django.core.cache.cache
        with patch.object(cache, 'get', side_effect=Exception("Redis Connection Refused")):
            result = safe_cache_get("any_key", default="fallback_val")
            assert result == "fallback_val"

        with patch.object(cache, 'set', side_effect=Exception("Redis Connection Refused")):
            success = safe_cache_set("any_key", "value")
            assert success is False

        with patch.object(cache, 'delete', side_effect=Exception("Redis Connection Refused")):
            success = safe_cache_delete("any_key")
            assert success is False

    def test_user_profile_view_operates_in_degraded_mode_without_redis(self, api_client, cache_test_data):
        alice = cache_test_data['alice']
        api_client.force_authenticate(user=alice)

        # Cuando Redis no está disponible, la vista no debe arrojar error 500, sino responder 200 desde BD
        with patch('books.cache_utils.cache.get', side_effect=Exception("Redis Connection Timeout")):
            with patch('books.cache_utils.cache.set', side_effect=Exception("Redis Connection Timeout")):
                res = api_client.get("/api/v1/auth/profile/")
                assert res.status_code == status.HTTP_200_OK
                assert res.data['username'] == alice.username
