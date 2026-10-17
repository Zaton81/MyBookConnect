import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def enable_celery_always_eager():
    """Ejecuta tareas de Celery síncronamente durante los tests unitarios."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    yield


@pytest.fixture
def api_client():
    """Cliente API anónimo de DRF."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Usuario estándar de pruebas tipo lector."""
    return User.objects.create_user(
        username="standard_reader",
        email="reader@mybooksocial.test",
        password="ValidPassword123!",
        account_type="reader",
    )


@pytest.fixture
def auth_client(api_client, test_user):
    """Cliente API autenticado con usuario lector estándar."""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def admin_user(db):
    """Usuario administrador con permisos staff y superuser."""
    return User.objects.create_superuser(
        username="admin_super",
        email="admin@mybooksocial.test",
        password="AdminPassword123!",
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    """Cliente API autenticado con usuario administrador."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def author_user(db):
    """Usuario con rol de autor registrado y verificado."""
    return User.objects.create_user(
        username="verified_author",
        email="author@mybooksocial.test",
        password="AuthorPassword123!",
        account_type="author",
    )


@pytest.fixture
def author_client(api_client, author_user):
    """Cliente API autenticado con usuario autor."""
    api_client.force_authenticate(user=author_user)
    return api_client
