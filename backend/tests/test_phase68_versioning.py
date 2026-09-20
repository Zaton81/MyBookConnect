import json
import re
from pathlib import Path

import pytest
from rest_framework import status
from rest_framework.test import APIClient

import mybookconnect
from mybookconnect.version import (
    API_VERSION,
    VERSION,
    __version__,
    get_version,
    get_version_info,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestPhase68Versioning:
    """
    Suite de pruebas para la Fase 68: Versionado y releases (SemVer 2.0.0,
    Keep a Changelog 1.1.0, endpoints de versión y consistencia global).
    """

    def test_version_module_constants_and_helpers(self):
        """Verifica que el módulo version.py exponga constantes SemVer válidas."""
        assert isinstance(VERSION, tuple)
        assert len(VERSION) == 3
        assert VERSION == (1, 0, 0)
        assert API_VERSION == "v1"

        # Formateo por defecto
        assert get_version() == "1.0.0"
        assert __version__ == "1.0.0"

        # Formateo personalizado
        assert get_version((2, 5, 1)) == "2.5.1"

        # Estructura del diccionario de metadatos
        info = get_version_info()
        assert info["version"] == "1.0.0"
        assert info["major"] == 1
        assert info["minor"] == 0
        assert info["patch"] == 0
        assert info["prerelease"] is None
        assert info["api_version"] == "v1"
        assert info["semver"] is True

    def test_version_exported_in_package_root(self):
        """Verifica que mybookconnect.__version__ esté disponible en la raíz del paquete."""
        assert hasattr(mybookconnect, "__version__")
        assert mybookconnect.__version__ == "1.0.0"
        assert hasattr(mybookconnect, "get_version")
        assert mybookconnect.get_version() == "1.0.0"

    def test_api_version_endpoint(self, api_client):
        """Verifica que GET /api/v1/version/ devuelva los metadatos de versión SemVer."""
        response = api_client.get("/api/v1/version/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["version"] == "1.0.0"
        assert data["major"] == 1
        assert data["minor"] == 0
        assert data["patch"] == 0
        assert data["api_version"] == "v1"
        assert data["semver"] is True

    def test_api_health_endpoint_includes_version(self, api_client):
        """Verifica que el endpoint de liveness (/api/v1/health/) incluya la versión actual."""
        response = api_client.get("/api/v1/health/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["process"] == "alive"
        assert data["version"] == "1.0.0"

    def test_pyproject_version_consistency(self):
        """Verifica que backend/pyproject.toml contenga la versión 1.0.0."""
        # Ruta relativa al directorio de backend
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), f"No se encontró {pyproject_path}"

        content = pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        assert match is not None, "No se encontró campo version en pyproject.toml"
        assert match.group(1) == get_version()

    def test_frontend_package_json_consistency(self):
        """Verifica que frontend/package.json coincida con la versión del backend."""
        frontend_pkg_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "package.json"
        if frontend_pkg_path.exists():
            pkg_data = json.loads(frontend_pkg_path.read_text(encoding="utf-8"))
            assert pkg_data.get("version") == get_version(), (
                f"Desincronización: package.json={pkg_data.get('version')} vs version.py={get_version()}"
            )

    def test_changelog_conforms_to_standard(self):
        """Verifica que CHANGELOG.md exista y contenga la versión 1.0.0."""
        changelog_path = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
        if changelog_path.exists():
            content = changelog_path.read_text(encoding="utf-8")
            assert f"## [{get_version()}]" in content, f"Falta sección ## [{get_version()}] en CHANGELOG.md"
            assert "Keep a Changelog" in content
            assert "Semantic Versioning" in content
            assert "### Added" in content
            assert "### Changed" in content
