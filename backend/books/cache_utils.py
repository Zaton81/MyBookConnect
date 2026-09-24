import hashlib
import logging
import re
import time
from typing import Any, Callable

from django.core.cache import cache

logger = logging.getLogger(__name__)

# TTLs estandarizados en segundos (Fase 8 - 13.2)
TTL_BOOK_DETAIL = 900          # 15 minutos
TTL_USER_PROFILE = 900         # 15 minutos
TTL_RECOMMENDATIONS = 900      # 15 minutos
TTL_FEED = 300                 # 5 minutos
TTL_SEARCH = 300               # 5 minutos
TTL_TRENDING = 900             # 15 minutos
TTL_STATS = 900                # 15 minutos
TTL_EXTERNAL_API = 86400       # 24 horas
TTL_WIKIPEDIA_AUTHOR = 172800  # 48 horas


def safe_cache_get(key: str, default: Any = None) -> Any:
    """Acceso defensivo a caché; si Redis falla, no lanza excepción y retorna default (13.5)."""
    try:
        return cache.get(key, default)
    except Exception as exc:
        logger.warning(f"Fallo de Redis en safe_cache_get({key}): {exc}")
        return default


def safe_cache_set(key: str, value: Any, timeout: int | None = None) -> bool:
    """Escritura defensiva en caché; si Redis falla, registra warning sin romper ejecución (13.5)."""
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception as exc:
        logger.warning(f"Fallo de Redis en safe_cache_set({key}): {exc}")
        return False


def safe_cache_delete(key: str) -> bool:
    """Borrado defensivo en caché; si Redis falla, continúa sin interrumpir el flujo (13.5)."""
    try:
        cache.delete(key)
        return True
    except Exception as exc:
        logger.warning(f"Fallo de Redis en safe_cache_delete({key}): {exc}")
        return False


def _sanitize_key_part(value: str) -> str:
    """Normaliza texto para claves de caché seguras en Redis."""
    clean = re.sub(r'[\s:/?#\[\]@!$&\'()*+,;=]+', '_', value.strip().lower())
    return clean[:120]


def book_detail_key(book_id: int | str) -> str:
    """Namespace de detalle de libro: book:{id}"""
    return f"book:{book_id}"


def trending_key(period: str = 'week') -> str:
    """Namespace de libros populares/tendencias: trending:{period}"""
    return f"trending:{_sanitize_key_part(period)}"


def google_isbn_key(isbn: str) -> str:
    """Namespace de Google Books por ISBN: google:isbn:{isbn}"""
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip())
    return f"google:isbn:{clean_isbn}"


def google_search_key(query: str, offset: int = 0) -> str:
    """Namespace de búsqueda en Google Books: google:search:{query}:{offset}"""
    return f"google:search:{_sanitize_key_part(query)}:{offset}"


def openlibrary_isbn_key(isbn: str) -> str:
    """Namespace de OpenLibrary por ISBN: openlibrary:isbn:{isbn}"""
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip())
    return f"openlibrary:isbn:{clean_isbn}"


def openlibrary_work_key(work_id: str) -> str:
    """Namespace de OpenLibrary por Work ID: openlibrary:work:{id}"""
    return f"openlibrary:work:{_sanitize_key_part(work_id)}"


def openlibrary_search_key(query: str, page: int = 1) -> str:
    """Namespace de búsqueda en OpenLibrary: openlibrary:search:{query}:{page}"""
    return f"openlibrary:search:{_sanitize_key_part(query)}:{page}"


def wikipedia_author_key(author_name: str) -> str:
    """Namespace de autor en Wikipedia: wikipedia:author:{name}"""
    return f"wikipedia:author:{_sanitize_key_part(author_name)}"


def wikipedia_book_key(title: str) -> str:
    """Namespace de libro en Wikipedia: wikipedia:book:{title}"""
    return f"wikipedia:book:{_sanitize_key_part(title)}"


def invalidate_book_cache(book_id: int | str) -> None:
    """
    Invalida atómicamente la caché del detalle del libro y todos los rankings de tendencias dependientes.
    """
    try:
        key = book_detail_key(book_id)
        cache.delete(key)
        invalidate_trending_cache()
        logger.debug(f"Caché invalidada para libro {book_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando caché para libro {book_id}: {exc}")


def invalidate_trending_cache() -> None:
    """Invalida la caché de todos los periodos del ranking de tendencias ('week', 'month', 'year', 'all')."""
    try:
        for p in ('week', 'month', 'year', 'all'):
            cache.delete(trending_key(p))
    except Exception as exc:
        logger.warning(f"Error invalidando caché de tendencias: {exc}")


def user_profile_key(user_id: int | str) -> str:
    """Namespace de perfil de usuario: user:profile:{user_id}"""
    return f"user:profile:{user_id}"


def invalidate_user_profile_cache(user_id: int | str) -> None:
    """
    Invalida atómicamente la caché del perfil y de las estadísticas del usuario.
    """
    try:
        cache.delete(user_profile_key(user_id))
        cache.delete(user_stats_key(user_id))
        logger.debug(f"Caché de perfil y estadísticas invalidada para usuario {user_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando caché de perfil para usuario {user_id}: {exc}")


def user_stats_key(user_id: int | str) -> str:
    """Namespace de estadísticas de lectura del usuario: stats:user:{user_id}"""
    return f"stats:user:{user_id}"


def invalidate_user_stats_cache(user_id: int | str) -> None:
    """
    Invalida atómicamente la caché de estadísticas de lectura de un usuario
    cuando se modifican sus lecturas o valoraciones.
    """
    try:
        cache.delete(user_stats_key(user_id))
        logger.debug(f"Caché de estadísticas invalidada para usuario {user_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando caché de estadísticas para usuario {user_id}: {exc}")


def user_recommendations_key(user_id: int | str, strategy: str = 'hybrid') -> str:
    """Namespace de recomendaciones de usuario: recommendations:user:{user_id}:{strategy}"""
    return f"recommendations:user:{user_id}:{_sanitize_key_part(strategy)}"


def book_recommendations_key(book_id: int | str) -> str:
    """Namespace de recomendaciones contextuales de un libro: recommendations:book:{book_id}"""
    return f"recommendations:book:{book_id}"


def invalidate_user_recommendations_cache(user_id: int | str) -> None:
    """
    Invalida la caché de recomendaciones de un usuario para todas sus estrategias y embeddings.
    """
    try:
        for strat in ('hybrid', 'rules', 'social', 'semantic', 'v1', 'v2', 'v3', 'all'):
            cache.delete(user_recommendations_key(user_id, strat))
        cache.delete(f"user_pref_embedding_{user_id}")
        cache.delete(f"user_pref_vector_{user_id}")
        logger.debug(f"Caché de recomendaciones y vectores invalidada para usuario {user_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando caché de recomendaciones para usuario {user_id}: {exc}")


def invalidate_book_recommendations_cache(book_id: int | str) -> None:
    """
    Invalida la caché de recomendaciones contextuales de un libro específico y libros similares.
    """
    try:
        cache.delete(book_recommendations_key(book_id))
        cache.delete(f"similar_books_{book_id}")
        logger.debug(f"Caché de recomendaciones contextuales invalidada para libro {book_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando recomendaciones para libro {book_id}: {exc}")


def cascade_review_invalidation(book_id: int | str, user_id: int | str) -> None:
    """
    Cascada reactiva completa ante mutación de reseña (Roadmap Fase 65):
    new review
     ↓
    invalidate book rating & book cache
     ↓
    invalidate recommendations (book & user)
     ↓
    invalidate trending (all periods)
     ↓
    invalidate user profile & stats
    """
    try:
        # 1. Invalida libro y desencadena recálculo de promedio
        invalidate_book_cache(book_id)
        try:
            from books.tasks import recalculate_book_rating_task
            recalculate_book_rating_task.delay(int(book_id))
        except Exception:
            pass

        # 2. Invalida recomendaciones de libro y usuario
        invalidate_book_recommendations_cache(book_id)
        invalidate_user_recommendations_cache(user_id)

        # 3. Invalida ranking de tendencias
        invalidate_trending_cache()

        # 4. Invalida perfil y estadísticas del autor de la reseña
        invalidate_user_profile_cache(user_id)
        logger.debug(f"Cascada de invalidación completada para review (libro={book_id}, user={user_id})")
    except Exception as exc:
        logger.warning(f"Error en cascada de invalidación de reseña: {exc}")


def feed_cache_key(user_id: int | str) -> str:
    """Namespace de feed social de usuario (13.1): feed:{user_id}"""
    return f"feed:{user_id}"


def invalidate_feed_cache(user_id: int | str) -> None:
    """Invalida la caché del feed social de un usuario."""
    safe_cache_delete(feed_cache_key(user_id))


def search_cache_key(query: str, mode: str = 'hybrid', page: int = 1) -> str:
    """Namespace de búsqueda unificada (13.1): search:{query_hash}:{mode}:{page}"""
    norm = query.strip().lower().encode('utf-8')
    q_hash = hashlib.sha256(norm).hexdigest()[:16]
    return f"search:{q_hash}:{_sanitize_key_part(mode)}:{page}"


def invalidate_search_cache(query: str | None = None) -> None:
    """
    Invalida caché de búsqueda para una query específica o limpia versiones de búsqueda.
    """
    if query:
        for m in ('hybrid', 'text', 'fuzzy', 'semantic'):
            for p in range(1, 5):
                safe_cache_delete(search_cache_key(query, mode=m, page=p))


def cascade_follow_invalidation(follower_id: int | str, following_id: int | str) -> None:
    """
    Cascada reactiva ante creación o eliminación de relación de seguimiento (13.3):
    - Invalida feed del seguidor
    - Invalida perfil del seguidor y del seguido
    - Invalida recomendaciones sociales del seguidor
    """
    try:
        invalidate_feed_cache(follower_id)
        invalidate_user_profile_cache(follower_id)
        invalidate_user_profile_cache(following_id)
        invalidate_user_recommendations_cache(follower_id)
        logger.debug(f"Cascada de seguimiento completada (follower={follower_id}, following={following_id})")
    except Exception as exc:
        logger.warning(f"Error en cascada de invalidación de follow: {exc}")


def cascade_privacy_invalidation(user_id: int | str) -> None:
    """
    Cascada reactiva ante cambio de privacidad de usuario (13.3):
    - Invalida perfil y stats del usuario
    - Invalida recomendaciones del usuario
    - Invalida feed del usuario
    """
    try:
        invalidate_user_profile_cache(user_id)
        invalidate_user_recommendations_cache(user_id)
        invalidate_feed_cache(user_id)
        logger.debug(f"Cascada de privacidad completada para user={user_id}")
    except Exception as exc:
        logger.warning(f"Error en cascada de invalidación de privacidad: {exc}")


def cascade_reading_status_invalidation(user_id: int | str, book_id: int | str) -> None:
    """
    Cascada reactiva ante mutación de estado de lectura en UserBook (13.3):
    - Invalida perfil del usuario
    - Invalida recomendaciones del usuario y vectores derivados
    - Invalida estadísticas del usuario
    - Invalida detalle del libro (contadores de lecturas)
    - Invalida feed del usuario
    """
    try:
        invalidate_user_profile_cache(user_id)
        invalidate_user_recommendations_cache(user_id)
        invalidate_user_stats_cache(user_id)
        invalidate_book_cache(book_id)
        invalidate_feed_cache(user_id)
        logger.debug(f"Cascada de lectura completada (user={user_id}, book={book_id})")
    except Exception as exc:
        logger.warning(f"Error en cascada de invalidación de reading status: {exc}")


def cascade_book_invalidation(book_id: int | str) -> None:
    """
    Cascada reactiva ante actualización de metadatos de un libro (13.3):
    - Invalida caché de detalle de libro
    - Invalida rankings de tendencias
    - Invalida recomendaciones contextuales del libro
    """
    try:
        invalidate_book_cache(book_id)
        invalidate_book_recommendations_cache(book_id)
        invalidate_trending_cache()
        logger.debug(f"Cascada de libro completada para book={book_id}")
    except Exception as exc:
        logger.warning(f"Error en cascada de invalidación de libro: {exc}")


def get_or_set_stampede_protected(
    key: str,
    fetch_fn: Callable[[], Any],
    ttl: int = 900,
    lock_timeout: int = 10,
) -> Any:
    """
    Protección contra avalancha o estampida de caché (Cache Stampede Protection - 13.4).
    Implementa el patrón Mutex distribuido con double-checked locking:
    Si la clave no existe, un único hilo/proceso adquiere el lock para calcular el resultado,
    mientras los demás esperan un breve intervalo para leer el valor recién cacheado.
    """
    val = safe_cache_get(key)
    if val is not None:
        return val

    lock_key = f"lock:{key}"
    acquired = False
    try:
        # cache.add() en Django/Redis actúa como SETNX atómico
        acquired = bool(cache.add(lock_key, "1", timeout=lock_timeout))
    except Exception as exc:
        logger.warning(f"Error adquiriendo lock distribuido para {key}: {exc}")
        return fetch_fn()

    if acquired:
        try:
            # Double check tras adquisición de lock
            val = safe_cache_get(key)
            if val is not None:
                return val
            computed = fetch_fn()
            safe_cache_set(key, computed, timeout=ttl)
            return computed
        finally:
            safe_cache_delete(lock_key)
    else:
        # Espera activa controlada para que el worker que tiene el lock concluya
        for _ in range(15):
            time.sleep(0.08)
            val = safe_cache_get(key)
            if val is not None:
                return val
        # Si transcurrió el tiempo máximo sin que se poblase la caché, calcular directamente
        computed = fetch_fn()
        safe_cache_set(key, computed, timeout=ttl)
        return computed


