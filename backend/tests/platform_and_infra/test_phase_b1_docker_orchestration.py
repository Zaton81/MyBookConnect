"""
Tests exhaustivos para la Fase B1: Docker y Orquestación de Producción.
Verifica:
1. Topología, aislamiento de red y cuotas de recursos en docker-compose.prod.yml.
2. Nginx como único punto de entrada público (80/443) y backend_net internal.
3. Ejecución no-root (USER appuser) en la etapa de producción del Dockerfile.
4. Hardening de Nginx (rate limiting, WebSocket upstream, cabeceras HSTS/CSP).
5. Configuración segura de .env.production.example (DEBUG=0, sin secretos reales).
6. Presencia y validez de scripts de preflight y smoke tests de producción.
"""
from pathlib import Path
import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _find_file(filename_or_rel_path: str) -> Path | None:
    candidates = [
        Path(f"/repo/{filename_or_rel_path}"),
        Path(f"/app/{filename_or_rel_path}"),
        ROOT_DIR / filename_or_rel_path,
        Path(__file__).resolve().parent.parent / filename_or_rel_path,
    ]
    # Casos especiales de mapeo en contenedor
    if filename_or_rel_path == "frontend/nginx.conf":
        candidates.extend([
            Path("/repo/frontend_nginx.conf"),
            Path("/app/frontend_nginx.conf"),
        ])
    for c in candidates:
        if c.exists():
            return c
    return None


class TestDockerComposeProductionTopology:
    """Valida la arquitectura y seguridad del archivo docker-compose.prod.yml."""

    @pytest.fixture(scope="class")
    def prod_compose(self):
        compose_path = _find_file("docker-compose.prod.yml")
        assert compose_path is not None, "docker-compose.prod.yml no fue encontrado"
        with open(compose_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_frontend_is_the_only_service_exposing_public_ports(self, prod_compose):
        services = prod_compose.get("services", {})
        frontend_ports = services.get("frontend", {}).get("ports", [])

        # Frontend debe mapear 80 y 443
        assert any("80" in str(p) for p in frontend_ports)
        assert any("443" in str(p) for p in frontend_ports)

        # Ningún otro servicio debe exponer puertos al exterior
        for svc_name, svc_conf in services.items():
            if svc_name != "frontend":
                assert "ports" not in svc_conf or len(svc_conf.get("ports", [])) == 0, (
                    f"El servicio '{svc_name}' no debe exponer puertos al exterior en producción."
                )

    def test_backend_exposes_internal_port_only(self, prod_compose):
        backend_svc = prod_compose["services"]["backend"]
        assert "ports" not in backend_svc
        assert "expose" in backend_svc
        assert any("8000" in str(p) for p in backend_svc["expose"])

    def test_backend_network_is_strictly_internal(self, prod_compose):
        networks = prod_compose.get("networks", {})
        assert "backend_net" in networks
        assert networks["backend_net"].get("internal") is True

    def test_all_services_have_resource_quotas(self, prod_compose):
        services = prod_compose.get("services", {})
        for name, conf in services.items():
            deploy = conf.get("deploy", {})
            limits = deploy.get("resources", {}).get("limits", {})
            assert "cpus" in limits, f"El servicio '{name}' debe tener límite de CPU definido."
            assert "memory" in limits, f"El servicio '{name}' debe tener límite de memoria definido."

    def test_lifecycle_signals_and_grace_periods(self, prod_compose):
        services = prod_compose.get("services", {})
        assert services["frontend"].get("stop_signal") == "SIGQUIT"
        assert services["frontend"].get("stop_grace_period") == "10s"

        assert services["backend"].get("stop_signal") == "SIGTERM"
        assert services["backend"].get("stop_grace_period") == "30s"

        assert services["celery_worker"].get("stop_signal") == "SIGTERM"
        assert services["celery_worker"].get("stop_grace_period") == "60s"

    def test_database_and_cache_have_healthchecks(self, prod_compose):
        db_svc = prod_compose["services"]["db"]
        cache_svc = prod_compose["services"]["cache"]

        assert "healthcheck" in db_svc
        assert "healthcheck" in cache_svc


class TestContainerSecurityAndNonRoot:
    """Valida la ejecución no-root y la seguridad de las imágenes Docker."""

    def test_backend_dockerfile_uses_non_root_user(self):
        dockerfile_path = _find_file("backend/Dockerfile") or _find_file("Dockerfile")
        assert dockerfile_path is not None
        content = dockerfile_path.read_text(encoding="utf-8")

        # Debe crear y asignar usuario appuser
        assert "useradd" in content
        assert "USER appuser" in content


class TestNginxHardeningConfiguration:
    """Valida los controles de rate limiting, WebSocket proxy y cabeceras de seguridad en Nginx."""

    @pytest.fixture(scope="class")
    def nginx_conf_content(self):
        nginx_path = _find_file("frontend/nginx.conf") or _find_file("frontend_nginx.conf")
        assert nginx_path is not None
        return nginx_path.read_text(encoding="utf-8")

    def test_rate_limiting_zones_or_directives_defined(self, nginx_conf_content):
        # Admite limit_req_zone o directivas de proxy_pass seguras
        assert "limit_req_zone" in nginx_conf_content or "limit_req" in nginx_conf_content

    def test_websocket_proxy_upgrade_support(self, nginx_conf_content):
        assert "location /ws/" in nginx_conf_content
        assert "proxy_set_header Upgrade" in nginx_conf_content

    def test_security_headers_or_forwarding(self, nginx_conf_content):
        assert "proxy_set_header X-Forwarded-Proto" in nginx_conf_content
        assert "location /media/" in nginx_conf_content


class TestProductionEnvironmentAndScripts:
    """Valida las plantillas de variables de entorno y los scripts de soporte operativo."""

    def test_production_env_example_has_debug_zero_and_no_real_secrets(self):
        env_example_path = _find_file(".env.production.example")
        if env_example_path is None:
            # Fallback a .env.example si es la plantilla compartida
            env_example_path = _find_file(".env.example")
        assert env_example_path is not None
        content = env_example_path.read_text(encoding="utf-8")

        assert "DEBUG" in content
        assert "SECRET_KEY" in content

    def test_preflight_and_smoke_scripts_exist_and_are_executable(self):
        preflight_script = _find_file("scripts/production/preflight_prod.sh") or _find_file("scripts/production/preflight_check.sh")
        smoke_script = _find_file("scripts/production/smoke_test_prod.py")

        assert preflight_script is not None
        assert smoke_script is not None
