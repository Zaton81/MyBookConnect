from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    def setup_method(self):
        self.client = APIClient()

    def test_health_liveness_returns_200(self):
        """Verifica que la sonda de liveness responda 200 OK con process: alive."""
        res = self.client.get('/api/v1/health/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['status'] == 'healthy'
        assert data['process'] == 'alive'

    def test_healthcheck_accessible_without_auth(self):
        """Verifica que los endpoints sean públicos sin requerir tokens (necesario para Docker/K8s)."""
        res_health = self.client.get('/api/v1/health/')
        assert res_health.status_code == status.HTTP_200_OK

        res_ready = self.client.get('/api/v1/ready/')
        assert res_ready.status_code == status.HTTP_200_OK

    def test_readiness_returns_200_when_all_healthy(self):
        """Verifica que la sonda de readiness responda 200 OK con el estado de PostgreSQL y Redis."""
        res = self.client.get('/api/v1/ready/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['status'] == 'ready'
        assert data['services']['database'] == 'ready'
        assert data['services']['cache'] == 'ready'

    def test_readiness_returns_503_when_database_fails(self):
        """Verifica que un fallo en la base de datos devuelva 503 SERVICE UNAVAILABLE en /ready/."""
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('DB Connection Timeout')):
            res = self.client.get('/api/v1/ready/')
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data['status'] == 'not_ready'
            assert 'unhealthy' in data['services']['database']
            assert 'DB Connection Timeout' in data['services']['database']
            assert data['services']['cache'] == 'ready'

    def test_readiness_returns_503_when_cache_fails(self):
        """Verifica que un fallo en Redis devuelva 503 SERVICE UNAVAILABLE en /ready/."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis Error: Connection Refused')):
            res = self.client.get('/api/v1/ready/')
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data['status'] == 'not_ready'
            assert data['services']['database'] == 'ready'
            assert 'unhealthy' in data['services']['cache']
            assert 'Redis Error' in data['services']['cache']
