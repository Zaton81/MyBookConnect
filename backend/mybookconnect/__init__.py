# Asegurar que la app de Celery siempre se importe cuando arranque Django
from .celery import app as celery_app

__all__ = ('celery_app',)
