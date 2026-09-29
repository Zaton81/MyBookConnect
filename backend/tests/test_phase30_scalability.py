from pathlib import Path
from unittest.mock import patch
import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings

from mybookconnect.db_routers import PrimaryReplicaRouter
from users.tasks import send_notification_email_task, send_transactional_email_task


def _find_file(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Ninguno de los archivos candidatos existe: {[str(c) for c in candidates]}")


@pytest.mark.django_db
class TestPhase30Scalability:
    @pytest.fixture(autouse=True)
    def setup_fixture(self):
        self.base_dir = Path(settings.BASE_DIR)
        self.repo_root = self.base_dir.parent if (self.base_dir.parent / 'docker-compose.yml').exists() else self.base_dir

    def test_celery_queues_and_default_queue_registered(self):
        """Verifica que las 5 colas canónicas de Celery están declaradas en settings."""
        queues = getattr(settings, 'CELERY_TASK_QUEUES', {})
        expected_queues = {'default', 'books', 'ai', 'recommendations', 'emails'}

        assert expected_queues.issubset(set(queues.keys())), (
            f"Faltan colas en CELERY_TASK_QUEUES. Esperadas: {expected_queues}, Actuales: {set(queues.keys())}"
        )
        assert getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', None) == 'default', (
            "CELERY_TASK_DEFAULT_QUEUE debe ser 'default'."
        )

    def test_celery_task_routes_mapping(self):
        """Verifica que las tareas críticas están correctamente enrutadas a sus colas especializadas."""
        routes = getattr(settings, 'CELERY_TASK_ROUTES', {})

        # Cola 'books'
        assert routes.get('books.tasks.enrich_book_task', {}).get('queue') == 'books'
        assert routes.get('books.tasks.download_cover_task', {}).get('queue') == 'books'
        assert routes.get('books.tasks.recalculate_book_rating_task', {}).get('queue') == 'books'

        # Cola 'ai'
        assert routes.get('books.tasks.generate_book_embedding_task', {}).get('queue') == 'ai'
        assert routes.get('books.tasks.batch_reindex_embeddings_task', {}).get('queue') == 'ai'

        # Cola 'recommendations'
        assert routes.get('books.tasks.precompute_trending_task', {}).get('queue') == 'recommendations'
        assert routes.get('books.tasks.precompute_user_recommendations_task', {}).get('queue') == 'recommendations'

        # Cola 'emails'
        assert routes.get('users.tasks.send_transactional_email_task', {}).get('queue') == 'emails'
        assert routes.get('users.tasks.send_notification_email_task', {}).get('queue') == 'emails'

        # Cola 'default'
        assert routes.get('analytics.tasks.record_analytics_event_task', {}).get('queue') == 'default'

    def test_users_send_transactional_email_task_execution(self):
        """Verifica la ejecución exitosa de la tarea asíncrona de email transaccional."""
        mail.outbox.clear()
        result = send_transactional_email_task(
            subject="Bienvenido a MyBookConnect",
            message="Tu cuenta ha sido creada exitosamente.",
            recipient_list=["testuser@example.com"],
            from_email="registro@mybookconnect.com",
        )

        assert result is True
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert sent_email.subject == "Bienvenido a MyBookConnect"
        assert sent_email.to == ["testuser@example.com"]
        assert sent_email.from_email == "registro@mybookconnect.com"
        assert "creada exitosamente" in sent_email.body

    def test_users_send_notification_email_task_execution(self):
        """Verifica el envío asíncrono de notificaciones por correo."""
        mail.outbox.clear()
        result = send_notification_email_task(
            recipient_email="reader@example.com",
            subject="Nueva interacción en tu reseña",
            message="A un usuario le ha gustado tu reseña.",
            notification_id=42,
        )

        assert result is True
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert sent_email.subject == "Nueva interacción en tu reseña"
        assert sent_email.to == ["reader@example.com"]
        assert "le ha gustado tu reseña" in sent_email.body

    def test_primary_replica_router_logic(self):
        """Valida que PrimaryReplicaRouter dirige escrituras a master y lecturas a réplica."""
        router = PrimaryReplicaRouter()

        # Sin réplica configurada: lecturas van a 'default'
        assert router.db_for_read(None) == 'default'
        assert router.db_for_write(None) == 'default'

        # Con réplica configurada en DATABASES: lecturas van a 'replica'
        with override_settings(DATABASES={
            'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'test_db'},
            'replica': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'test_replica'},
        }):
            assert router.db_for_read(None) == 'replica'
            assert router.db_for_write(None) == 'default'

        # Migraciones sólo en 'default'
        assert router.allow_migrate('default', 'books') is True
        assert router.allow_migrate('replica', 'books') is False

    def test_database_routers_setting_registered(self):
        """Verifica que PrimaryReplicaRouter está registrado en settings.DATABASE_ROUTERS."""
        routers = getattr(settings, 'DATABASE_ROUTERS', [])
        assert 'mybookconnect.db_routers.PrimaryReplicaRouter' in routers

    def test_nginx_upstream_load_balancing_configuration(self):
        """Comprueba que nginx.conf cuenta con el bloque upstream django_cluster y least_conn."""
        candidates = [
            Path('/repo/frontend_nginx.conf'),
            Path('/app/frontend_nginx.conf'),
            self.repo_root / 'frontend' / 'nginx.conf',
            Path(__file__).resolve().parent.parent.parent / 'frontend' / 'nginx.conf',
        ]
        nginx_conf = _find_file(candidates)
        content = nginx_conf.read_text(encoding='utf-8')

        assert 'upstream django_cluster' in content
        assert 'least_conn;' in content
        assert 'server backend:8000' in content

    def test_docker_compose_prod_celery_queues_declared(self):
        """Verifica que docker-compose.prod.yml declara las colas en el comando del worker."""
        candidates = [
            Path('/repo/docker-compose.prod.yml'),
            self.repo_root / 'docker-compose.prod.yml',
            Path(__file__).resolve().parent.parent.parent / 'docker-compose.prod.yml',
        ]
        compose_conf = _find_file(candidates)
        content = compose_conf.read_text(encoding='utf-8')

        assert '-Q default,books,ai,recommendations,emails' in content

    def test_scalability_guide_exists_and_complete(self):
        """Comprueba que la documentación técnica cubre las 4 etapas y tuning de infraestructura."""
        candidates = [
            Path('/app/docs/architecture/scalability_and_performance_tuning.md'),
            self.repo_root / 'docs' / 'architecture' / 'scalability_and_performance_tuning.md',
            Path(__file__).resolve().parent.parent.parent / 'docs' / 'architecture' / 'scalability_and_performance_tuning.md',
        ]
        guide = _find_file(candidates)
        content = guide.read_text(encoding='utf-8')

        assert 'Etapa 1' in content
        assert 'Etapa 2' in content
        assert 'Etapa 3' in content
        assert 'Etapa 4' in content
        assert 'pgvector' in content
        assert 'HNSW' in content
        assert 'PrimaryReplicaRouter' in content
        assert 'Matriz de Decisiones' in content
