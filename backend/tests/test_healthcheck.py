from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    def setup_method(self):
        self.client = APIClient()

    def test_healthcheck_returns_200_when_all_healthy(self):
        """Verifica que el healthcheck responda 200 OK con el estado de PostgreSQL y Redis."""
        res = self.client.get('/api/v1/health/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['status'] == 'healthy'
        assert data['services']['database'] == 'healthy'
        assert data['services']['cache'] == 'healthy'

    def test_healthcheck_accessible_without_auth(self):
        """Verifica que el endpoint sea público sin requerir tokens (necesario para Docker/K8s)."""
        res = self.client.get('/api/v1/health/')
        assert res.status_code == status.HTTP_200_OK

    def test_healthcheck_returns_503_when_database_fails(self):
        """Verifica que un fallo en la base de datos devuelva 503 SERVICE UNAVAILABLE."""
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('DB Connection Timeout')):
            res = self.client.get('/api/v1/health/')
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data['status'] == 'unhealthy'
            assert 'unhealthy' in data['services']['database']
            assert 'DB Connection Timeout' in data['services']['database']
            assert data['services']['cache'] == 'healthy'

    def test_healthcheck_returns_503_when_cache_fails(self):
        """Verifica que un fallo en Redis devuelva 503 SERVICE UNAVAILABLE."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis Error: Connection Refused')):
            res = self.client.get('/api/v1/health/')
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data['status'] == 'unhealthy'
            assert data['services']['database'] == 'healthy'
            assert 'unhealthy' in data['services']['cache']
            assert 'Redis Error' in data['services']['cache']
