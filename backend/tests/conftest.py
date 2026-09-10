import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def enable_celery_always_eager():
    """Ejecuta tareas de Celery síncronamente durante los tests unitarios."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    yield
