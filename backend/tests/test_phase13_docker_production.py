"""
Test Suite — Fase 13: Docker y Producción
=============================================================================
Pruebas de verificación de arquitectura de contenedores, sondas canónicas
de liveness y readiness, configuración de aislamiento de redes en Docker
y proxy inverso Nginx.
"""
from pathlib import Path
from unittest.mock import patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient
import yaml


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestPhase13Healthchecks:
    """Verificación de sondas canónicas /health/live y /health/ready."""

    def test_canonical_liveness_returns_200(self, client):
        """La sonda /health/live debe retornar 200 con el estado del proceso."""
        response = client.get('/health/live')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('status') == 'healthy'
        assert data.get('process') == 'alive'
        assert 'version' in data

    def test_canonical_liveness_with_slash_returns_200(self, client):
        """La sonda /health/live/ con barra final también debe responder 200."""
        response = client.get('/health/live/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('status') == 'healthy'

    def test_liveness_resilient_to_database_failure(self, client):
        """La sonda de liveness no debe fallar si la base de datos se interrumpe."""
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('DB Connection Refused')):
            response = client.get('/health/live')
            assert response.status_code == status.HTTP_200_OK
            assert response.json().get('status') == 'healthy'

    def test_liveness_resilient_to_cache_failure(self, client):
        """La sonda de liveness no debe fallar si Redis se interrumpe."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis Error: Connection Dropped')):
            response = client.get('/health/live')
            assert response.status_code == status.HTTP_200_OK
            assert response.json().get('status') == 'healthy'

    def test_canonical_readiness_healthy(self, client):
        """La sonda /health/ready debe retornar 200 cuando DB y Redis están operativos."""
        response = client.get('/health/ready')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('status') == 'ready'
        assert data.get('services', {}).get('database') == 'ready'
        assert data.get('services', {}).get('cache') == 'ready'

    def test_canonical_readiness_with_slash_healthy(self, client):
        """La sonda /health/ready/ con barra final también responde 200."""
        response = client.get('/health/ready/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get('status') == 'ready'

    def test_readiness_returns_503_on_database_failure(self, client):
        """La sonda de readiness debe retornar 503 si PostgreSQL no está disponible."""
        with patch('mybookconnect.health.connection.cursor', side_effect=Exception('PostgreSQL unreachable')):
            response = client.get('/health/ready')
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data.get('status') == 'not_ready'
            assert 'unhealthy' in data.get('services', {}).get('database', '')

    def test_readiness_returns_503_on_cache_failure(self, client):
        """La sonda de readiness debe retornar 503 si Redis no responde."""
        with patch('mybookconnect.health.cache.set', side_effect=Exception('Redis connection refused')):
            response = client.get('/health/ready')
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data.get('status') == 'not_ready'
            assert 'unhealthy' in data.get('services', {}).get('cache', '')

    def test_healthchecks_publicly_accessible_without_token(self, client):
        """Ambas sondas deben ser públicas para monitoreo sin exigir cabeceras de auth."""
        res_live = client.get('/health/live')
        res_ready = client.get('/health/ready')
        assert res_live.status_code == status.HTTP_200_OK
        assert res_ready.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


class TestPhase13DockerProductionArchitecture:
    """Verificación de arquitectura, redes, puertos y graceful shutdown en docker-compose.prod.yml."""

    @pytest.fixture(scope="class")
    def prod_compose_data(self):
        """Carga y parsea el archivo docker-compose.prod.yml."""
        candidates = [
            Path("/repo/docker-compose.prod.yml"),
            Path("/app/docker-compose.prod.yml"),
            Path(__file__).resolve().parent.parent.parent / "docker-compose.prod.yml",
            Path(__file__).resolve().parent.parent / "docker-compose.prod.yml",
        ]
        compose_file = None
        for candidate in candidates:
            if candidate.exists():
                compose_file = candidate
                break

        assert compose_file is not None, f"No se encontró docker-compose.prod.yml en {[str(c) for c in candidates]}"

        with open(compose_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_only_frontend_exposes_ports_to_host(self, prod_compose_data):
        """Solo el reverse proxy (frontend) debe tener puertos publicados al exterior en producción."""
        services = prod_compose_data.get("services", {})
        for name, svc in services.items():
            if name != "frontend":
                assert "ports" not in svc, f"El servicio {name} NO debe exponer puertos hacia el host en producción"
        # Frontend debe tener puertos mapeados (por ejemplo 80:80)
        assert "ports" in services["frontend"]
        assert any("80" in str(p) for p in services["frontend"]["ports"])

    def test_backend_does_not_publish_host_ports(self, prod_compose_data):
        """El backend de Django no debe tener puertos mapeados al host, solo expose interno."""
        backend_svc = prod_compose_data["services"]["backend"]
        assert "ports" not in backend_svc, "Django backend tiene puertos expuestos al host"
        assert "expose" in backend_svc, "Django backend debe usar 'expose' interno en lugar de 'ports'"
        assert "8000" in str(backend_svc["expose"])

    def test_db_and_cache_are_not_published_to_internet(self, prod_compose_data):
        """Ni PostgreSQL ni Redis deben tener puertos expuestos al exterior."""
        services = prod_compose_data["services"]
        assert "ports" not in services["db"], "PostgreSQL tiene puertos expuestos al exterior"
        assert "ports" not in services["cache"], "Redis tiene puertos expuestos al exterior"

    def test_isolated_networks_defined(self, prod_compose_data):
        """Deben existir las redes frontend_net y backend_net, con backend_net marcada como internal."""
        networks = prod_compose_data.get("networks", {})
        assert "frontend_net" in networks, "Falta la red frontend_net"
        assert "backend_net" in networks, "Falta la red backend_net"
        assert networks["backend_net"].get("internal") is True, "backend_net debe ser internal: true"

    def test_network_isolation_assignment(self, prod_compose_data):
        """El frontend solo debe estar en frontend_net, mientras db y cache solo en backend_net."""
        services = prod_compose_data["services"]
        assert services["frontend"]["networks"] == ["frontend_net"]
        assert "backend_net" not in services["frontend"]["networks"], "Frontend Nginx no debe tener acceso directo a la red de datos"
        assert "frontend_net" in services["backend"]["networks"]
        assert "backend_net" in services["backend"]["networks"]
        assert services["db"]["networks"] == ["backend_net"]
        assert services["cache"]["networks"] == ["backend_net"]

    def test_graceful_shutdown_configured(self, prod_compose_data):
        """Gunicorn/Daphne, Celery y Nginx deben tener stop_signal y stop_grace_period configurados."""
        backend = prod_compose_data["services"]["backend"]
        celery = prod_compose_data["services"]["celery_worker"]
        frontend = prod_compose_data["services"]["frontend"]

        assert "stop_signal" in backend
        assert "stop_grace_period" in backend
        assert backend["stop_signal"] == "SIGTERM"

        assert "stop_signal" in celery
        assert "stop_grace_period" in celery

        assert "stop_signal" in frontend
        assert frontend["stop_signal"] == "SIGQUIT"

    def test_persistent_volumes_declared(self, prod_compose_data):
        """Deben declararse volúmenes persistentes para db, media, estáticos y backups."""
        volumes = prod_compose_data.get("volumes", {})
        expected_volumes = ["db_prod_data", "backend_media", "backend_static", "backups_data"]
        for vol in expected_volumes:
            assert vol in volumes, f"Falta declarar el volumen {vol} en docker-compose.prod.yml"


class TestPhase13NginxReverseProxyConfig:
    """Verificación de directivas en frontend/nginx.conf."""

    @pytest.fixture(scope="class")
    def nginx_config_content(self):
        candidates = [
            Path("/repo/frontend_nginx.conf"),
            Path("/app/frontend_nginx.conf"),
            Path(__file__).resolve().parent.parent.parent / "frontend" / "nginx.conf",
            Path(__file__).resolve().parent.parent / "frontend" / "nginx.conf",
        ]
        nginx_conf = None
        for candidate in candidates:
            if candidate.exists():
                nginx_conf = candidate
                break

        assert nginx_conf is not None, f"No se encontró nginx.conf en {[str(c) for c in candidates]}"
        return nginx_conf.read_text(encoding="utf-8")

    def test_api_proxy_pass_configured(self, nginx_config_content):
        """Debe existir directiva proxy_pass hacia backend para la ruta /api/."""
        assert "location /api/" in nginx_config_content
        assert "proxy_pass http://backend:8000/api/;" in nginx_config_content
        assert "proxy_set_header Host $host;" in nginx_config_content
        assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in nginx_config_content

    def test_websocket_proxy_pass_configured(self, nginx_config_content):
        """Debe existir directiva proxy_pass con Upgrade y Connection para WebSockets /ws/."""
        assert "location /ws/" in nginx_config_content
        assert "proxy_pass http://backend:8000/ws/;" in nginx_config_content
        assert "proxy_set_header Upgrade $http_upgrade;" in nginx_config_content
        assert "proxy_set_header Connection \"upgrade\";" in nginx_config_content

    def test_health_proxy_pass_configured(self, nginx_config_content):
        """Debe existir directiva proxy_pass para sondas /health/."""
        assert "location /health/" in nginx_config_content
        assert "proxy_pass http://backend:8000/health/;" in nginx_config_content

    def test_static_and_media_aliases_configured(self, nginx_config_content):
        """Debe servir /media/ y estáticos con cabeceras de seguridad."""
        assert "location /media/" in nginx_config_content
        assert "alias /app/media/;" in nginx_config_content
        assert "location /django_static/" in nginx_config_content
        assert "alias /app/staticfiles/;" in nginx_config_content

    def test_spa_try_files_present(self, nginx_config_content):
        """Debe incluir soporte para React Router con try_files."""
        assert "try_files $uri $uri/ /index.html;" in nginx_config_content
