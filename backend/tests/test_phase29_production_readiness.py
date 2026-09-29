from pathlib import Path
import pytest
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.test import RequestFactory, override_settings
from rest_framework import status
from rest_framework.test import APIClient


def _find_file(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Ninguno de los archivos candidatos existe: {[str(c) for c in candidates]}")


@pytest.mark.django_db
class TestPhase29ProductionReadiness:
    @pytest.fixture(autouse=True)
    def setup_fixture(self):
        self.client = APIClient()
        self.rf = RequestFactory()
        self.base_dir = Path(settings.BASE_DIR)
        self.repo_root = self.base_dir.parent if (self.base_dir.parent / 'docker-compose.yml').exists() else self.base_dir

    def test_session_and_csrf_cookie_hardening(self):
        """Verifica que las cookies de sesión y CSRF tienen configuración segura."""
        assert getattr(settings, 'SESSION_COOKIE_HTTPONLY', False) is True, (
            "SESSION_COOKIE_HTTPONLY debe ser True para mitigar ataques XSS."
        )
        assert getattr(settings, 'SESSION_COOKIE_SAMESITE', None) in ('Lax', 'Strict'), (
            "SESSION_COOKIE_SAMESITE debe ser Lax o Strict."
        )
        assert getattr(settings, 'CSRF_COOKIE_SAMESITE', None) in ('Lax', 'Strict'), (
            "CSRF_COOKIE_SAMESITE debe ser Lax o Strict."
        )

    def test_secure_proxy_ssl_header_detection(self):
        """Verifica que SECURE_PROXY_SSL_HEADER detecta correctamente peticiones HTTPS tras Nginx."""
        with override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')):
            request_https = self.rf.get('/health/live', HTTP_X_FORWARDED_PROTO='https')
            assert request_https.is_secure() is True, (
                "request.is_secure() debe retornar True cuando Nginx envía X-Forwarded-Proto: https."
            )

            request_http = self.rf.get('/health/live', HTTP_X_FORWARDED_PROTO='http')
            assert request_http.is_secure() is False, (
                "request.is_secure() debe retornar False cuando X-Forwarded-Proto es http."
            )

    def test_allowed_hosts_enforcement(self):
        """Valida que peticiones con host no permitido sean rechazadas con 400 y DisallowedHost."""
        with override_settings(ALLOWED_HOSTS=['mybookconnect.com', 'testserver']):
            client = APIClient()
            # Django Client captura DisallowedHost y responde HTTP 400 Bad Request
            response = client.get('/health/live', HTTP_HOST='malicious-domain.evil')
            assert response.status_code == status.HTTP_400_BAD_REQUEST

            # Request directo comprueba que get_host() lanza la excepción de seguridad
            req = self.rf.get('/health/live', HTTP_HOST='malicious-domain.evil')
            with pytest.raises(DisallowedHost):
                req.get_host()

    def test_production_env_example_completeness(self):
        """Valida que el archivo .env.production.example define todas las claves requeridas."""
        candidates = [
            Path('/repo/.env.production.example'),
            Path('/app/.env.production.example'),
            self.repo_root / '.env.production.example',
            Path(__file__).resolve().parent.parent.parent / '.env.production.example',
        ]
        env_example_path = _find_file(candidates)
        content = env_example_path.read_text(encoding='utf-8')
        required_keys = [
            'DEBUG=0',
            'SECRET_KEY=',
            'ALLOWED_HOSTS=',
            'CORS_ALLOWED_ORIGINS=',
            'CSRF_TRUSTED_ORIGINS=',
            'USE_X_FORWARDED_PROTO=1',
            'SECURE_SSL_REDIRECT=1',
            'POSTGRES_DB=',
            'POSTGRES_USER=',
            'REDIS_HOST=',
            'CELERY_BROKER_URL=',
            'MEDIA_STORAGE_BACKEND=',
            'REQUIRE_EMAIL_VERIFICATION=',
            'BACKUP_DIR=',
        ]
        for key in required_keys:
            assert key in content, f"La variable {key} debe estar presente en .env.production.example"

    def test_production_preflight_script_validity(self):
        """Comprueba que el script preflight_check.sh existe y realiza las auditorías clave."""
        candidates = [
            Path('/app/scripts/production/preflight_check.sh'),
            self.repo_root / 'scripts' / 'production' / 'preflight_check.sh',
            Path(__file__).resolve().parent.parent.parent / 'scripts' / 'production' / 'preflight_check.sh',
        ]
        script_path = _find_file(candidates)
        content = script_path.read_text(encoding='utf-8')
        assert 'set -eo pipefail' in content
        assert 'DEBUG' in content
        assert 'SECRET_KEY' in content
        assert 'showmigrations' in content
        assert 'check --deploy' in content
        assert '/health/live' in content
        assert '/health/ready' in content

    def test_nginx_production_config_hardening(self):
        """Comprueba que la configuración de Nginx cuenta con cabeceras de hardening y Let's Encrypt."""
        candidates = [
            Path('/repo/frontend_nginx.conf'),
            Path('/app/frontend_nginx.conf'),
            self.repo_root / 'frontend' / 'nginx.conf',
            Path(__file__).resolve().parent.parent.parent / 'frontend' / 'nginx.conf',
        ]
        nginx_conf_path = _find_file(candidates)
        content = nginx_conf_path.read_text(encoding='utf-8')
        assert 'Strict-Transport-Security' in content
        assert 'Content-Security-Policy' in content
        assert 'Permissions-Policy' in content
        assert 'X-Frame-Options' in content
        assert 'X-Content-Type-Options' in content
        assert '.well-known/acme-challenge' in content

    def test_docker_compose_production_ports(self):
        """Verifica que docker-compose.prod.yml expone puertos 80 y 443 para HTTPS."""
        candidates = [
            Path('/repo/docker-compose.prod.yml'),
            self.repo_root / 'docker-compose.prod.yml',
            Path(__file__).resolve().parent.parent.parent / 'docker-compose.prod.yml',
        ]
        compose_prod_path = _find_file(candidates)
        content = compose_prod_path.read_text(encoding='utf-8')
        assert '443:443' in content
        assert '80:80' in content

    def test_production_readiness_guide_exists_and_complete(self):
        """Verifica que la documentación técnica cubre los 20 aspectos clave de la Fase 29."""
        candidates = [
            Path('/app/docs/deployment/production_readiness_guide.md'),
            self.repo_root / 'docs' / 'deployment' / 'production_readiness_guide.md',
            Path(__file__).resolve().parent.parent.parent / 'docs' / 'deployment' / 'production_readiness_guide.md',
        ]
        guide_path = _find_file(candidates)
        content = guide_path.read_text(encoding='utf-8')
        key_sections = [
            'Topología y Arquitectura',
            'Dominio y DNS',
            'TLS 1.3',
            'Nginx',
            'Django',
            'PostgreSQL',
            'Redis',
            'Celery',
            'Almacenamiento Multimedia',
            'SMTP',
            'APM',
            'Disaster Recovery',
            'Rate Limiting',
            'Auditoría de Dependencias',
            'Pre-Flight Check',
            'Plan de Rollback',
        ]
        for section in key_sections:
            assert section in content, f"La sección '{section}' debe estar documentada en {guide_path.name}"

    def test_liveness_and_readiness_probes_healthy(self):
        """Valida que los endpoints de salud respondan 200 OK."""
        live_res = self.client.get('/health/live')
        assert live_res.status_code == status.HTTP_200_OK

        ready_res = self.client.get('/health/ready')
        assert ready_res.status_code == status.HTTP_200_OK
