import os

from celery import Celery

# Establecer la configuración por defecto de Django para celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')

app = Celery('mybookconnect')

# Usar cadenas para evitar serializar el objeto de configuración en procesos secundarios
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar automáticamente módulos tasks.py de todas las aplicaciones registradas en INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
