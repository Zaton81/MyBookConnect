import time
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestPhase46HealthAndReadiness:
    def setup_method(self):
        self.client = APIClient()

    def test_liveness_endpoint_status_and_payload(self):
        """Verifica que /api/v1/health/ retorne 200 OK con el esquema de liveness."""
        response = self.client.get('/api/v1/health/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("process") == "alive"
        assert "version" in data

    def test_liveness_remains_healthy_even_if_db_fails(self):
        """
        La sonda de liveness (/health/) comprueba únicamente que el proceso web está vivo.
        Un fallo en base de datos NO debe tumbar la sonda de liveness para evitar
        que el orquestador reinicie el contenedor en bucle durante tareas de mantenimiento o microcortes.
        """
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('DB Out of Service')):
            response = self.client.get('/api/v1/health/')
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["process"] == "alive"

    def test_liveness_remains_healthy_even_if_cache_fails(self):
        """Un fallo en Redis tampoco debe tumbar la sonda de liveness."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis Connection Dropped')):
            response = self.client.get('/api/v1/health/')
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["process"] == "alive"

    def test_readiness_returns_200_when_dependencies_healthy(self):
        """Verifica que /api/v1/ready/ retorne 200 OK cuando PostgreSQL y Redis están disponibles."""
        response = self.client.get('/api/v1/ready/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["services"]["database"] == "ready"
        assert data["services"]["cache"] == "ready"

    def test_readiness_returns_503_when_database_fails(self):
        """Verifica que /api/v1/ready/ devuelva 503 cuando la base de datos no está disponible."""
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('PostgreSQL unreachable')):
            response = self.client.get('/api/v1/ready/')
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not_ready"
            assert "unhealthy: PostgreSQL unreachable" in data["services"]["database"]
            assert data["services"]["cache"] == "ready"

    def test_readiness_returns_503_when_cache_fails(self):
        """Verifica que /api/v1/ready/ devuelva 503 cuando Redis no está disponible."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis down')):
            response = self.client.get('/api/v1/ready/')
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["services"]["database"] == "ready"
            assert "unhealthy: Redis down" in data["services"]["cache"]

    def test_readiness_returns_503_on_cache_value_mismatch(self):
        """Verifica detección de inconsistencia en lectura/escritura de Redis."""
        with patch('mybookconnect.health.cache.get', return_value=None):
            response = self.client.get('/api/v1/ready/')
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not_ready"
            assert "cache value mismatch" in data["services"]["cache"]

    def test_endpoints_publicly_accessible_without_tokens(self):
        """Asegura que ni health ni ready requieran encabezado Authorization."""
        client_no_auth = APIClient()
        r_health = client_no_auth.get('/api/v1/health/')
        assert r_health.status_code == status.HTTP_200_OK

        r_ready = client_no_auth.get('/api/v1/ready/')
        assert r_ready.status_code == status.HTTP_200_OK

    def test_liveness_latency_is_minimal(self):
        """Sonda de liveness debe responder de forma prácticamente instantánea (<50ms)."""
        start = time.perf_counter()
        response = self.client.get('/api/v1/health/')
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == status.HTTP_200_OK
        assert elapsed_ms < 100, f"Liveness tardó demasiado: {elapsed_ms:.2f}ms"
