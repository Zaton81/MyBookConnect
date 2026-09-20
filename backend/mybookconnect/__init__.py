# Asegurar que la app de Celery siempre se importe cuando arranque Django
from .celery import app as celery_app
from .version import __version__, get_version

__all__ = ('celery_app', '__version__', 'get_version')
