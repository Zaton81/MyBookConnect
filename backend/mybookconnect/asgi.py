"""
ASGI config for mybookconnect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()
if settings.DEBUG:
    django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)
# Importar rutas WebSocket después de inicializar Django para evitar Apps aren't loaded yet
from messages_app.routing import websocket_urlpatterns  # noqa: E402
from mybookconnect.middleware import JwtAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
