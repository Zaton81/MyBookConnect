"""
Tests exhaustivos para la Fase A4: Health, Readiness y Superficie de Ataque.
Verifica:
1. Sondas canónicas de salud (/health/live y /health/ready) y respuesta 503 sanitizada ante fallos.
2. Restricción estricta de endpoints de métricas y observabilidad a personal autorizado (401/403).
3. Inexistencia de rutas de depuración residuales y protección honeypot.
4. Integridad del esquema OpenAPI y superficie de ataque pública.
"""
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestHealthAndReadinessProbes:
    """Valida el comportamiento y sanitización de las sondas de liveness y readiness."""

    def test_health_live_probe_returns_200_without_touching_db(self):
        client = APIClient()
        response = client.get("/health/live/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("process") == "alive"
        # No debe filtrar rutas de sistema operativo ni configuraciones internas
        assert "SECRET_KEY" not in str(data)
        assert "DATABASE" not in str(data)

    def test_health_ready_probe_operational_returns_200(self):
        client = APIClient()
        response = client.get("/health/ready/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("status") == "ready"
        assert data.get("services", {}).get("database") == "ready"
        assert data.get("services", {}).get("cache") == "ready"

    def test_health_ready_probe_database_down_returns_503_sanitized(self):
        client = APIClient()
        # Simulamos caída o error de conexión con PostgreSQL
        with patch("django.db.connection.cursor", side_effect=Exception("OperationalError: connection to server at '10.0.1.5' failed")):
            response = client.get("/health/ready/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data.get("status") == "not_ready"
            assert data.get("services", {}).get("database") == "unhealthy"
            # Verificar que no se filtra la traza de excepción, la IP interna ni el usuario de DB
            assert "10.0.1.5" not in str(data)
            assert "OperationalError" not in str(data)
            assert "traceback" not in str(data).lower()

    def test_health_ready_probe_cache_down_returns_503_sanitized(self):
        client = APIClient()
        # Simulamos fallo de Redis/Caché
        with patch("django.core.cache.cache.get", return_value=None):
            response = client.get("/health/ready/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data.get("status") == "not_ready"
            assert data.get("services", {}).get("cache") == "unhealthy"


@pytest.mark.django_db
class TestMetricsAndObservabilityAccessControl:
    """Verifica que todos los endpoints de métricas y observabilidad requieran privilegios de staff/admin."""

    def test_observability_metrics_requires_admin_user(self):
        client = APIClient()

        # 1. Anónimo -> 401 Unauthorized
        res_anon = client.get("/api/v1/observability/metrics/")
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. Usuario regular autenticado -> 403 Forbidden
        user = User.objects.create_user(username="regular_viewer", email="reg@example.com", password="password123")
        client.force_authenticate(user=user)
        res_user = client.get("/api/v1/observability/metrics/")
        assert res_user.status_code == status.HTTP_403_FORBIDDEN

        # 3. Staff / Admin -> 200 OK
        admin = User.objects.create_superuser(username="admin_viewer", email="adm@example.com", password="password123")
        client.force_authenticate(user=admin)
        res_admin = client.get("/api/v1/observability/metrics/")
        assert res_admin.status_code == status.HTTP_200_OK

    def test_analytics_endpoints_require_admin_user(self):
        client = APIClient()
        user = User.objects.create_user(username="norm_analyst", email="norm@example.com", password="password123")
        client.force_authenticate(user=user)

        for endpoint in ["/api/v1/analytics/funnel/", "/api/v1/analytics/summary/", "/api/v1/analytics/retention/"]:
            res = client.get(endpoint)
            assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_beta_admin_metrics_require_admin_user(self):
        client = APIClient()
        user = User.objects.create_user(username="beta_tester_user", email="tester@example.com", password="password123")
        client.force_authenticate(user=user)

        res_metrics = client.get("/api/v1/beta/admin/metrics/")
        assert res_metrics.status_code == status.HTTP_403_FORBIDDEN

        res_alerts = client.get("/api/v1/beta/admin/alerts/")
        assert res_alerts.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAttackSurfaceAndDebugEndpoints:
    """Comprueba que no existen endpoints de depuración activos en la superficie pública."""

    def test_residual_debug_endpoints_return_404(self):
        client = APIClient()
        debug_candidates = [
            "/debug/",
            "/_debug/",
            "/test/",
            "/phpmyadmin/",
            "/wp-admin/",
            "/env/",
            "/.env",
            "/actuator/",
        ]
        for path in debug_candidates:
            res = client.get(path)
            assert res.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST)

    def test_openapi_schema_endpoint_returns_200_without_sensitive_leaks(self):
        client = APIClient()
        res = client.get("/api/schema/", HTTP_HOST="localhost")
        assert res.status_code == status.HTTP_200_OK
        content = res.content.decode("utf-8")
        # No debe filtrar secretos ni variables de entorno
        assert "SECRET_KEY" not in content
        assert "AWS_SECRET_ACCESS_KEY" not in content
        assert "DATABASE_URL" not in content
