import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root():
    """Localiza la raíz del repositorio con soporte tanto en Docker (/app) como en el host local."""
    container_app = Path("/app")
    if (container_app / "docs" / "development" / "definition_of_done.md").exists():
        return container_app

    host_root = Path(__file__).resolve().parent.parent.parent
    if (host_root / "docs" / "development" / "definition_of_done.md").exists():
        return host_root

    pytest.fail("No se pudo localizar el directorio de documentación en el entorno de pruebas.")


class TestPhase71DefinitionOfDone:
    """
    Suite de pruebas para la Fase 71: Definition of Done (DoD formal,
    plantilla de Pull Request, herramienta scripts/verify_dod.sh y calidad).
    """

    def test_definition_of_done_document_exists_and_contains_all_13_criteria(self, repo_root):
        """Verifica que docs/development/definition_of_done.md contenga los 13 criterios obligatorios."""
        dod_path = repo_root / "docs" / "development" / "definition_of_done.md"
        assert dod_path.exists(), f"No se encontró {dod_path}"

        content = dod_path.read_text(encoding="utf-8")

        # 13 criterios de aceptación obligatorios de la Fase 71
        expected_criteria = [
            "1. Modelo",
            "2. Migración",
            "3. Serializer",
            "4. API",
            "5. Permisos",
            "6. Tests backend",
            "7. Cliente frontend",
            "8. UI",
            "9. Tests frontend",
            "10. Documentación",
            "11. OpenAPI",
            "12. CI",
            "13. Logs si son necesarios",
        ]

        for criterion in expected_criteria:
            assert criterion in content, f"Criterio '{criterion}' no encontrado en definition_of_done.md"

        # Validar conceptos clave de calidad y seguridad dentro de la guía
        assert "UniqueConstraint" in content
        assert "makemigrations --check" in content
        assert "nh3" in content or "sanitize_html" in content
        assert "HasObjectPermission" in content
        assert "pytest-django" in content
        assert "TanStack Query" in content or "api.ts" in content
        assert "TailwindCSS" in content
        assert "Vitest" in content
        assert "spectacular" in content.lower()
        assert "verify_dod.sh" in content

    def test_pull_request_template_exists_and_has_dod_checklist(self, repo_root):
        """Verifica que .github/pull_request_template.md contenga la checklist interactiva de DoD."""
        # En contenedor /app o host
        pr_template_path = repo_root / ".github" / "pull_request_template.md"
        if not pr_template_path.exists():
            # Buscar en host si .github no se montó en /app
            host_template = Path(__file__).resolve().parent.parent.parent / ".github" / "pull_request_template.md"
            if host_template.exists():
                pr_template_path = host_template

        assert pr_template_path.exists(), f"No se encontró {pr_template_path}"

        content = pr_template_path.read_text(encoding="utf-8")
        assert "Checklist de Definition of Done (DoD)" in content
        assert "- [ ] **1. Modelo:" in content
        assert "- [ ] **2. Migración:" in content
        assert "- [ ] **3. Serializer:" in content
        assert "- [ ] **4. API:" in content
        assert "- [ ] **5. Permisos:" in content
        assert "- [ ] **6. Tests backend:" in content
        assert "- [ ] **7. Cliente frontend:" in content
        assert "- [ ] **8. UI:" in content
        assert "- [ ] **9. Tests frontend:" in content
        assert "- [ ] **10. Documentación:" in content
        assert "- [ ] **11. OpenAPI:" in content
        assert "- [ ] **12. CI:" in content
        assert "- [ ] **13. Logs si son necesarios:" in content
        assert "Conventional Commits" in content

    def test_verify_dod_script_exists_and_syntax(self, repo_root):
        """Verifica que scripts/verify_dod.sh tenga shebang, sintaxis bash válida y comprobaciones clave."""
        script_path = repo_root / "scripts" / "verify_dod.sh"
        assert script_path.exists(), f"No se encontró {script_path}"

        content = script_path.read_text(encoding="utf-8")
        assert content.startswith("#!/usr/bin/env bash")

        # Comprobaciones automáticas implementadas
        assert "makemigrations" in content
        assert "spectacular" in content
        assert "ruff check" in content
        assert "typecheck" in content
        assert "verify_release.sh" in content

        # Sintaxis con bash -n
        res = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Error de sintaxis en verify_dod.sh: {res.stderr}"
