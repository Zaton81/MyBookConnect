import logging

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponseNotFound
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenRefreshView

from users.auth_views import CustomTokenObtainPairView
from users.moderation_views import ReportCreateView, UserReportsListView

from .health import HealthCheckView, ReadinessCheckView, VersionView
from .observability import ObservabilityMetricsView

logger = logging.getLogger('mybookconnect.security')


def admin_probe_trap_view(request):
    """
    Señuelo y trampa de seguridad para peticiones dirigidas a la ruta predecible /admin/.
    Registra la dirección IP atacante y devuelve 404 para no revelar la existencia del panel.
    """
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'desconocida'))
    logger.warning("Intento de acceso o escaneo a ruta de administración deshabilitada /admin/ desde IP %s", client_ip)
    return HttpResponseNotFound("Página no encontrada.")


admin_path = getattr(settings, 'ADMIN_URL', 'admin/').strip('/') + '/'

urlpatterns = [
    # Panel de administración seguro con ruta ofuscada
    path(admin_path, admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/health/', HealthCheckView.as_view(), name='health_check'),
    path('api/v1/ready/', ReadinessCheckView.as_view(), name='readiness_check'),
    path('api/v1/version/', VersionView.as_view(), name='api-version'),
    path('api/v1/', include([
        path('version/', VersionView.as_view(), name='api-version-nested'),
        path('auth/', include([
            path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
            path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
            path('', include('users.urls')),
        ])),
        path('books/', include('books.urls')),
        path('gamification/', include('books.gamification_urls')),
        path('users/', include('users.urls')),
        path('notifications/', include('users.urls')),
        path('reviews/', include('books.review_urls')),
        path('', include('messages_app.urls')),
        path('chat/', include('messages_app.urls')),
        path('admin/', include('books.admin_urls')),
        path('observability/metrics/', ObservabilityMetricsView.as_view(), name='observability-metrics'),
        path('reports/', include([
            path('', ReportCreateView.as_view(), name='report-create'),
            path('my/', UserReportsListView.as_view(), name='user-reports-list'),
        ])),
    ])),
]

# Si la ruta del admin está ofuscada, proteger /admin/ registrando la anomalía
if admin_path != 'admin/':
    urlpatterns.append(path('admin/', admin_probe_trap_view, name='admin_probe_trap'))

# Archivos estáticos y multimedia
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

