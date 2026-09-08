"""
ASGI config for mybookconnect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


django_asgi_app = get_asgi_application()
# Importar rutas WebSocket después de inicializar Django para evitar Apps aren't loaded yet
from messages_app.routing import websocket_urlpatterns  # noqa: E402

# Aquí se agregarán las rutas websocket en el futuro
application = ProtocolTypeRouter({
	"http": django_asgi_app,
	"websocket": AuthMiddlewareStack(
		URLRouter(websocket_urlpatterns)
	),
})
