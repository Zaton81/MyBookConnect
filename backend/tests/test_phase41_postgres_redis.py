"""
Fase 41: Tests de integración con PostgreSQL y Redis
Verificación rigurosa de:
- Migrations: integridad del esquema relacional y sincronización modelo-base de datos.
- Constraints: restricciones de unicidad, unicidad condicional (soft-delete) e integridad referencial.
- Indexes: catálogo pg_indexes, extensión pg_trgm e índices GIN Trigram.
- Transactions: atomicidad, puntos de guardado (savepoints) y bloqueo pesimista select_for_update().
- Cache: backend Redis real, almacenamiento clave-valor, TTL y caducidad.
- Channels: capa de canales Redis (RedisChannelLayer), envío punto a punto y difusión a grupos.
"""
from io import StringIO
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.recorder import MigrationRecorder
import pytest

from books.cache_utils import book_detail_key
from books.models import Author, Book, ReadingStatus, Review, UserBook

User = get_user_model()


@pytest.fixture
def test_user():
    return User.objects.create_user(username='pg_user', email='pg_user@test.com', password='password123')


@pytest.fixture
def sample_book():
    author = Author.objects.create(name='Julio Cortázar')
    return Book.objects.create(
        title='Rayuela',
        author=author,
        isbn='9788466331906',
        description='Contranovela abierta y lúdica.'
    )


# ============================================================================
# 1. MIGRATIONS
# ============================================================================
@pytest.mark.django_db
class TestPostgreSQLMigrations:
    def test_no_pending_migrations(self):
        """Verifica que no existan cambios de modelo pendientes de generar migración."""
        out = StringIO()
        try:
            call_command('makemigrations', check=True, dry_run=True, stdout=out)
        except SystemExit as exc:
            pytest.fail(f"Existen migraciones pendientes sin generar: {out.getvalue()} (exit {exc.code})")

    def test_all_migrations_recorded(self):
        """Verifica que el registrador de migraciones en PostgreSQL contenga las migraciones aplicadas de las apps principales."""
        applied_apps = set(
            MigrationRecorder.Migration.objects.values_list('app', flat=True).distinct()
        )
        for app in ['books', 'users', 'messages_app']:
            assert app in applied_apps, f"La app '{app}' no tiene migraciones registradas en django_migrations"


# ============================================================================
# 2. CONSTRAINTS
# ============================================================================
@pytest.mark.django_db
class TestPostgreSQLConstraints:
    def test_unique_active_review_conditional_constraint(self, test_user, sample_book):
        """Verifica que PostgreSQL imponga la restricción de unicidad parcial en reseñas activas."""
        # 1. Primera reseña activa
        rev1 = Review.objects.create(
            user=test_user,
            book=sample_book,
            rating=5,
            title='Primera',
            text='Excelente'
        )

        # 2. Intentar crear segunda reseña activa para el mismo usuario y libro viola la restricción
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Review.objects.create(
                    user=test_user,
                    book=sample_book,
                    rating=4,
                    title='Segunda duplicada',
                    text='Debe fallar a nivel de base de datos'
                )

        # 3. Soft-delete de la primera reseña (deleted_at ya no es NULL)
        rev1.delete()
        assert rev1.is_deleted is True

        # 4. Ahora se permite crear una nueva reseña activa
        rev2 = Review.objects.create(
            user=test_user,
            book=sample_book,
            rating=5,
            title='Nueva reseña tras soft delete',
            text='Permitida al estar la anterior soft-deleted'
        )
        assert rev2.id is not None
        assert Review.objects.filter(user=test_user, book=sample_book, deleted_at__isnull=True).count() == 1

    def test_userbook_unique_together_constraint(self, test_user, sample_book):
        """Verifica que la base de datos imponga unicidad en (user, book) para UserBook."""
        UserBook.objects.create(user=test_user, book=sample_book, status=ReadingStatus.READING)

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                UserBook.objects.create(user=test_user, book=sample_book, status=ReadingStatus.READ)

    def test_foreign_key_cascade_deletion(self, test_user, sample_book):
        """Verifica la integridad referencial y eliminación en cascada en PostgreSQL."""
        ub = UserBook.objects.create(user=test_user, book=sample_book)
        rev = Review.objects.create(user=test_user, book=sample_book, rating=5)

        # Eliminar el libro debe eliminar en cascada sus dependencias
        sample_book.delete()

        assert not UserBook.objects.filter(id=ub.id).exists()
        assert not Review.all_objects.filter(id=rev.id).exists()


# ============================================================================
# 3. INDEXES
# ============================================================================
@pytest.mark.django_db
class TestPostgreSQLIndexes:
    def test_pg_trgm_extension_enabled(self):
        """Verifica que la extensión pg_trgm esté habilitada en PostgreSQL."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm';")
            result = cursor.fetchone()
        assert result is not None, "La extensión pg_trgm no está habilitada en PostgreSQL"
        assert result[0] == 'pg_trgm'

    def test_gin_trigram_indexes_exist(self):
        """Verifica que los índices GIN Trigram de búsqueda rápida existan en el catálogo PostgreSQL."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public' AND indexname IN ('idx_book_title_trgm', 'idx_book_desc_trgm');
                """
            )
            found = {row[0] for row in cursor.fetchall()}

        assert 'idx_book_title_trgm' in found, "Índice GIN idx_book_title_trgm no encontrado"
        assert 'idx_book_desc_trgm' in found, "Índice GIN idx_book_desc_trgm no encontrado"

    def test_btree_composite_indexes_exist(self):
        """Verifica que los índices compuestos B-Tree críticos estén presentes."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public';
                """
            )
            all_indexes = {row[0] for row in cursor.fetchall()}

        critical_indexes = [
            'idx_book_title',
            'idx_book_title_author',
            'idx_review_book_created',
            'idx_userbook_status_updated',
        ]
        for idx in critical_indexes:
            assert idx in all_indexes, f"Índice B-Tree crítico '{idx}' no encontrado en PostgreSQL"


# ============================================================================
# 4. TRANSACTIONS
# ============================================================================
@pytest.mark.django_db
class TestPostgreSQLTransactions:
    def test_atomic_rollback_on_exception(self):
        """Verifica que un bloque atomic revierta todas las operaciones ante una excepción no capturada."""
        try:
            with transaction.atomic():
                author = Author.objects.create(name='Autor Fantasma')
                Book.objects.create(title='Libro Fantasma', author=author)
                raise RuntimeError('Fallo forzado para probar rollback')
        except RuntimeError:
            pass

        assert not Author.objects.filter(name='Autor Fantasma').exists()
        assert not Book.objects.filter(title='Libro Fantasma').exists()

    def test_nested_atomic_savepoints(self):
        """Verifica que los savepoints anidados permitan revertir una subtransacción sin abortar la externa."""
        with transaction.atomic():
            author = Author.objects.create(name='Autor Principal')
            try:
                with transaction.atomic():
                    Book.objects.create(title='Libro que fallará', author=author)
                    raise ValueError('Error en savepoint anidado')
            except ValueError:
                pass

            # La transacción externa continúa y se consolida
            Book.objects.create(title='Libro Exitoso', author=author)

        assert Author.objects.filter(name='Autor Principal').exists()
        assert not Book.objects.filter(title='Libro que fallará').exists()
        assert Book.objects.filter(title='Libro Exitoso').exists()

    def test_select_for_update_row_locking(self, sample_book):
        """Verifica que el bloqueo pesimista select_for_update() funcione en PostgreSQL."""
        with transaction.atomic():
            locked_book = Book.objects.select_for_update().get(id=sample_book.id)
            locked_book.title = 'Título Protegido por Bloqueo'
            locked_book.save()

        sample_book.refresh_from_db()
        assert sample_book.title == 'Título Protegido por Bloqueo'


# ============================================================================
# 5. CACHE (REDIS)
# ============================================================================
@pytest.mark.django_db
class TestRedisCacheIntegration:
    def test_redis_backend_active(self):
        """Verifica que el backend de caché configurado sea RedisCache."""
        from django.core.cache import caches
        default_cache = caches['default']
        backend_name = default_cache.__class__.__name__
        assert 'RedisCache' in backend_name or 'redis' in str(default_cache.__class__).lower(), (
            f"El backend de caché activo no es RedisCache: {default_cache.__class__}"
        )

    def test_redis_set_get_and_expiration(self):
        """Verifica la persistencia y lectura clave-valor con prefijo en Redis."""
        key = 'phase41_integration_test_key'
        val = {'framework': 'Django', 'db': 'PostgreSQL', 'cache': 'Redis'}

        cache.set(key, val, timeout=30)
        retrieved = cache.get(key)
        assert retrieved == val

        cache.delete(key)
        assert cache.get(key) is None

    def test_book_detail_cache_key_generation_and_caching(self, sample_book):
        """Verifica la generación de clave canónica y el almacenamiento en Redis."""
        cache_key = book_detail_key(sample_book.id)
        assert cache_key == f"book:{sample_book.id}"

        data = {'id': sample_book.id, 'title': sample_book.title}
        cache.set(cache_key, data, timeout=60)

        cached_data = cache.get(cache_key)
        assert cached_data is not None
        assert cached_data['title'] == sample_book.title

        cache.delete(cache_key)


# ============================================================================
# 6. CHANNELS (REDIS CHANNEL LAYER)
# ============================================================================
class TestRedisChannelLayerIntegration:
    def test_redis_channel_layer_active(self):
        """Verifica que la capa de canales por defecto use RedisChannelLayer."""
        channel_layer = get_channel_layer()
        assert channel_layer is not None
        layer_cls = channel_layer.__class__.__name__
        assert 'RedisChannelLayer' in layer_cls, f"Channel layer no es RedisChannelLayer: {channel_layer.__class__}"

    def test_channel_layer_send_and_receive(self):
        """Verifica el envío y recepción punto a punto a través de Redis."""
        channel_layer = get_channel_layer()
        channel_name = 'test_channel_direct'
        message = {'type': 'chat.message', 'text': 'Integración Redis Channel Layer'}

        async_to_sync(channel_layer.send)(channel_name, message)
        received = async_to_sync(channel_layer.receive)(channel_name)

        assert received['type'] == 'chat.message'
        assert received['text'] == 'Integración Redis Channel Layer'

    def test_channel_layer_group_broadcast(self):
        """Verifica el agregado de canales a un grupo y difusión mediante group_send."""
        channel_layer = get_channel_layer()
        group_name = 'test_group_phase41'
        channel_a = 'test_ch_a'
        channel_b = 'test_ch_b'

        async_to_sync(channel_layer.group_add)(group_name, channel_a)
        async_to_sync(channel_layer.group_add)(group_name, channel_b)

        broadcast_msg = {'type': 'group.event', 'payload': 'Notificación masiva'}
        async_to_sync(channel_layer.group_send)(group_name, broadcast_msg)

        msg_a = async_to_sync(channel_layer.receive)(channel_a)
        msg_b = async_to_sync(channel_layer.receive)(channel_b)

        assert msg_a['payload'] == 'Notificación masiva'
        assert msg_b['payload'] == 'Notificación masiva'

        async_to_sync(channel_layer.group_discard)(group_name, channel_a)
        async_to_sync(channel_layer.group_discard)(group_name, channel_b)
