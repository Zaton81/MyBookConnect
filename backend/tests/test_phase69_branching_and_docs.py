import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def doc_paths():
    """Localiza los archivos de documentación y scripts tanto en local como dentro del contenedor Docker."""
    # 1. Dentro del contenedor Docker (/app/docs, /app/scripts)
    container_app = Path("/app")
    if (container_app / "docs" / "development" / "branching_strategy.md").exists():
        return {
            "branching": container_app / "docs" / "development" / "branching_strategy.md",
            "troubleshooting": container_app / "docs" / "development" / "troubleshooting_and_runbooks.md",
            "doctor": container_app / "scripts" / "doctor.sh",
        }

    # 2. En el host local (raíz del repositorio dos niveles arriba de tests/)
    host_root = Path(__file__).resolve().parent.parent.parent
    if (host_root / "docs" / "development" / "branching_strategy.md").exists():
        return {
            "branching": host_root / "docs" / "development" / "branching_strategy.md",
            "troubleshooting": host_root / "docs" / "development" / "troubleshooting_and_runbooks.md",
            "doctor": host_root / "scripts" / "doctor.sh",
        }

    pytest.fail("No se pudieron localizar los directorios 'docs' y 'scripts' en el entorno de ejecución.")


class TestPhase69BranchingAndTroubleshootingDocs:
    """
    Suite de pruebas para la Fase 69: Estrategia de ramas y Guía Integral de
    Resolución de Problemas (Troubleshooting Runbook).
    """

    def test_branching_strategy_document_exists_and_valid(self, doc_paths):
        """Verifica que docs/development/branching_strategy.md exista y contenga el modelo GitFlow oficial."""
        doc_path = doc_paths["branching"]
        assert doc_path.exists(), f"No se encontró {doc_path}"

        content = doc_path.read_text(encoding="utf-8")

        # Ramas principales y de soporte requeridas
        assert "`main`" in content
        assert "`develop`" in content
        assert "`feature/*`" in content
        assert "`fix/*`" in content
        assert "`refactor/*`" in content
        assert "`hotfix/*`" in content
        assert "`release/*`" in content

        # Diagrama de flujo Mermaid
        assert "```mermaid" in content
        assert "gitGraph" in content

        # Políticas de merge y rebase
        assert "--no-ff" in content
        assert "rebase" in content

        # Checklist de Pull Request
        assert "Checklist para Pull Requests" in content

    def test_troubleshooting_document_exists_and_comprehensive(self, doc_paths):
        """Verifica que docs/development/troubleshooting_and_runbooks.md cubra todas las áreas clave."""
        doc_path = doc_paths["troubleshooting"]
        assert doc_path.exists(), f"No se encontró {doc_path}"

        content = doc_path.read_text(encoding="utf-8")

        # 1. Git
        assert "Conflictos durante un Merge o Rebase" in content
        assert "Detached HEAD" in content
        assert "git reflog" in content
        assert "git stash" in content
        assert "git revert" in content

        # 2. Docker
        assert "Puertos en Conflicto" in content
        assert "docker compose exec -it backend" in content
        assert "docker compose down -v" in content

        # 3. Base de Datos / Migraciones
        assert "InconsistentMigrationHistory" in content
        assert "pg_stat_activity" in content
        assert "pg_terminate_backend" in content
        assert "restore_db" in content

        # 4. Redis y Celery
        assert "rebuild_cache" in content
        assert "celery -A mybookconnect purge" in content

        # 5. Frontend
        assert "node_modules/.vite" in content
        assert "typecheck" in content

        # 6. Runbook de diagnóstico
        assert "scripts/doctor.sh" in content

    def test_doctor_script_exists_and_syntax(self, doc_paths):
        """Verifica que scripts/doctor.sh exista, tenga shebang y sintaxis bash correcta."""
        doctor_path = doc_paths["doctor"]
        assert doctor_path.exists(), f"No se encontró {doctor_path}"

        content = doctor_path.read_text(encoding="utf-8")
        assert content.startswith("#!/usr/bin/env bash")

        # Verificaciones obligatorias en el script
        assert "verify_release.sh" in content
        assert "docker compose" in content
        assert "PostgreSQL" in content
        assert "Redis" in content
        assert "showmigrations" in content

        # Comprobar sintaxis bash usando bash -n
        res = subprocess.run(
            ["bash", "-n", str(doctor_path)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Error de sintaxis en doctor.sh: {res.stderr}"
