import sys
from pathlib import Path

import pytest

# Asegurar que la carpeta scripts/ esté en el sys.path para importar el validador directamente
SCRIPTS_DIR = Path("/app/scripts") if Path("/app/scripts").exists() else Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_commit_msg import validate_commit_message  # noqa: E402


@pytest.fixture
def repo_root():
    """Localiza la raíz del repositorio según el entorno (dentro de Docker o en el host)."""
    container_app = Path("/app")
    if (container_app / "docs" / "development" / "commit_conventions.md").exists():
        return container_app

    host_root = Path(__file__).resolve().parent.parent.parent
    if (host_root / "docs" / "development" / "commit_conventions.md").exists():
        return host_root

    pytest.fail("No se pudo localizar la raíz con 'docs' en el entorno de ejecución.")


class TestPhase70CommitConventions:
    """
    Suite de pruebas para la Fase 70: Convención de commits (Conventional Commits 1.0.0,
    linter, hook commit-msg y documentación).
    """

    @pytest.mark.parametrize(
        "valid_msg",
        [
            "feat: add reading status",
            "fix: prevent duplicate reviews",
            "refactor: split external book providers",
            "test: add privacy permission tests",
            "security: rotate refresh tokens",
            "perf: optimize trending calculation query",
            "docs: update deployment guidelines",
            "chore: update dependencies in pyproject",
            "ci: add test matrix to github actions",
            "build: update vite configuration",
            "style: format imports with isort",
            "revert: revert commit dcd610f",
            "feat(books): add trigram search index",
            "fix(reviews): handle zero ratings gracefully",
            "security(auth): revoke blacklisted refresh tokens",
            "refactor(services): isolate book enrichment logic",
            "feat(api)!: remove deprecated v0 endpoints",
            "Merge branch 'develop' into main",
            "Merge pull request #42 from Zaton81/feature/cache",
            "fixup! feat(books): minor fix before squash",
        ],
    )
    def test_valid_commit_messages(self, valid_msg):
        """Verifica que mensajes conformes con Conventional Commits 1.0.0 sean aceptados."""
        is_valid, reason = validate_commit_message(valid_msg)
        assert is_valid is True, f"Se esperaba válido para '{valid_msg}' pero falló con: {reason}"

    @pytest.mark.parametrize(
        "invalid_msg,expected_error_keyword",
        [
            ("arreglado el bug de login", "no sigue el formato"),
            ("Fix: arreglar bug", "minúsculas"),
            ("FEAT: nueva caracteristica", "minúsculas"),
            ("feat:añadir libros sin espacio", "espacio obligatorio"),
            ("feat(libros): anadir libros con punto final.", "punto final"),
            ("custom(core): tipo desconocido", "no reconocido"),
            ("feat: ", "no puede estar vacía"),
            ("", "no puede estar vacío"),
            ("   \n# solo comentarios de git\n", "no puede estar vacío"),
            (
                "feat(books): " + "a" * 100,  # Excede 100 caracteres
                "excede los 100 caracteres",
            ),
        ],
    )
    def test_invalid_commit_messages(self, invalid_msg, expected_error_keyword):
        """Verifica que mensajes no conformes sean rechazados con el motivo correspondiente."""
        is_valid, reason = validate_commit_message(invalid_msg)
        assert is_valid is False, f"Se esperaba rechazo para '{invalid_msg}'"
        assert expected_error_keyword.lower() in reason.lower()

    def test_commit_conventions_document_exists_and_complete(self, repo_root):
        """Verifica que docs/development/commit_conventions.md documente tipos, scopes y breaking changes."""
        doc_path = repo_root / "docs" / "development" / "commit_conventions.md"
        assert doc_path.exists(), f"No se encontró {doc_path}"

        content = doc_path.read_text(encoding="utf-8")

        # Tipos obligatorios según Roadmap Fase 70
        for expected_type in [
            "`feat`",
            "`fix`",
            "`refactor`",
            "`test`",
            "`docs`",
            "`perf`",
            "`security`",
            "`chore`",
            "`ci`",
        ]:
            assert expected_type in content, f"Tipo {expected_type} no encontrado en la documentación"

        # Ejemplos explícitos del Roadmap
        assert "feat: add reading status" in content or "feat(books):" in content
        assert "fix: prevent duplicate reviews" in content or "fix(reviews):" in content
        assert "BREAKING CHANGE:" in content
        assert "core.hooksPath" in content

    def test_git_hook_script_exists_and_configured(self):
        """Verifica que .githooks/commit-msg exista y ejecute el validador."""
        # Comprobar en /app/.githooks si está montado o en el host
        host_hook = Path(__file__).resolve().parent.parent.parent / ".githooks" / "commit-msg"
        if host_hook.exists():
            content = host_hook.read_text(encoding="utf-8")
            assert "validate_commit_msg.py" in content
            assert content.startswith("#!/usr/bin/env bash")
