"""
Test Suite — Fase B2: Backups, Restore y Disaster Recovery
=============================================================================
Pruebas exhaustivas para:
- B2.1: Backup automático diario de PostgreSQL y cifrado AES-256.
- B2.2: Backup de volumen Media y de configuración crítica (scripts y manifiestos).
- B2.3: Procedimiento y comando de verificación de integridad post-restore (verify_restore_integrity).
- B2.4: Monitorización de frescura de backups y alertas de RPO (check_backup_freshness).
- B2.5: Script maestro de orquestación (backup_all.sh).
"""
import io
import json
import os
from pathlib import Path
import tempfile
import time
from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from books.models import Author, Book, Review, UserBook
from books.services.backup_service import compute_sha256
from messages_app.models import Conversation, Message

User = get_user_model()


@pytest.fixture
def disaster_recovery_dataset(db):
    user = User.objects.create_user(
        username="dr_auditor",
        email="dr_auditor@mybookconnect.local",
        password="TestPassword123!",
    )
    author = Author.objects.create(name="Gabriel García Márquez")
    book = Book.objects.create(
        title="El amor en los tiempos del cólera",
        author=author,
        isbn="9780307389732",
        average_rating=4.5,
    )
    user_book = UserBook.objects.create(
        user=user,
        book=book,
        is_read=True,
        rating=5,
    )
    review = Review.objects.create(
        user=user,
        book=book,
        title="Excelente obra",
        text="Una de las mejores historias de amor.",
        rating=5,
    )
    conv = Conversation.objects.create()
    conv.participants.add(user)
    msg = Message.objects.create(
        conversation=conv,
        sender=user,
        text="Mensaje de prueba para integridad de DR",
    )
    return {
        "user": user,
        "author": author,
        "book": book,
        "user_book": user_book,
        "review": review,
        "conversation": conv,
        "message": msg,
    }


class TestVerifyRestoreIntegrityCommand:
    """Pruebas del comando django verify_restore_integrity."""

    def test_verify_restore_integrity_passes_on_valid_data(self, disaster_recovery_dataset):
        out = io.StringIO()
        call_command("verify_restore_integrity", "--json", stdout=out)
        data = json.loads(out.getvalue())

        assert data["status"] == "PASS"
        assert len(data["errors"]) == 0
        assert data["subsystems"]["users"]["total_users"] >= 1
        assert data["subsystems"]["catalog"]["total_books"] >= 1
        assert data["subsystems"]["interactions"]["total_reviews"] >= 1
        assert data["subsystems"]["messaging"]["total_messages"] >= 1

    def test_verify_restore_integrity_detects_corrupted_book_ratings(self, disaster_recovery_dataset):
        book = disaster_recovery_dataset["book"]
        Book.objects.filter(id=book.id).update(average_rating=9.9)

        out = io.StringIO()
        with pytest.raises(SystemExit):
            call_command("verify_restore_integrity", "--json", stdout=out)

        data = json.loads(out.getvalue())
        assert data["status"] == "FAIL"
        assert any("average_rating fuera del rango" in err for err in data["errors"])

    def test_verify_restore_integrity_min_users_threshold(self, disaster_recovery_dataset):
        out = io.StringIO()
        with pytest.raises(SystemExit):
            call_command("verify_restore_integrity", "--min-users=9999", "--json", stdout=out)

        data = json.loads(out.getvalue())
        assert data["status"] == "FAIL"
        assert any("inferior al umbral mínimo" in err for err in data["errors"])


class TestCheckBackupFreshnessCommand:
    """Pruebas del comando django check_backup_freshness."""

    def test_check_freshness_missing_backups_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out = io.StringIO()
            with pytest.raises(SystemExit):
                call_command(
                    "check_backup_freshness",
                    f"--backup-root={tmp_dir}",
                    "--subsystems=db",
                    "--json",
                    stdout=out,
                )

            data = json.loads(out.getvalue())
            assert data["status"] == "FAIL"
            assert data["subsystems"]["db"]["status"] == "MISSING"

    def test_check_freshness_valid_fresh_backup_passes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_dir = Path(tmp_dir) / "db"
            db_dir.mkdir(parents=True)

            backup_file = db_dir / "db_backup_test_20261012_100000.sql.gz"
            backup_file.write_bytes(b"GZIP_MOCK_CONTENT_FOR_TEST")
            sha256 = compute_sha256(backup_file)

            manifest_file = backup_file.with_name(f"{backup_file.name}.manifest.json")
            manifest_file.write_text(json.dumps({
                "filename": backup_file.name,
                "sha256": sha256,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }))

            out = io.StringIO()
            call_command(
                "check_backup_freshness",
                f"--backup-root={tmp_dir}",
                "--subsystems=db",
                "--max-age-hours=24",
                "--json",
                stdout=out,
            )

            data = json.loads(out.getvalue())
            assert data["status"] == "PASS"
            assert data["subsystems"]["db"]["status"] == "OK"
            assert data["subsystems"]["db"]["checksum_verified"] is True

    def test_check_freshness_stale_backup_fails_rpo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_dir = Path(tmp_dir) / "db"
            db_dir.mkdir(parents=True)

            backup_file = db_dir / "db_backup_old_20261001_000000.sql.gz"
            backup_file.write_bytes(b"OLD_CONTENT")
            sha256 = compute_sha256(backup_file)

            # Modificar timestamp para simular archivo con 48h de antigüedad
            old_time = time.time() - (48 * 3600)
            os.utime(backup_file, (old_time, old_time))

            manifest_file = backup_file.with_name(f"{backup_file.name}.manifest.json")
            manifest_file.write_text(json.dumps({
                "filename": backup_file.name,
                "sha256": sha256,
            }))
            os.utime(manifest_file, (old_time, old_time))

            out = io.StringIO()
            with pytest.raises(SystemExit):
                call_command(
                    "check_backup_freshness",
                    f"--backup-root={tmp_dir}",
                    "--subsystems=db",
                    "--max-age-hours=24",
                    "--json",
                    stdout=out,
                )

            data = json.loads(out.getvalue())
            assert data["status"] == "FAIL"
            assert data["subsystems"]["db"]["status"] == "STALE"

    def test_check_freshness_corrupted_checksum_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_dir = Path(tmp_dir) / "db"
            db_dir.mkdir(parents=True)

            backup_file = db_dir / "db_backup_corrupt.sql.gz"
            backup_file.write_bytes(b"ALTERED_DATA")

            manifest_file = backup_file.with_name(f"{backup_file.name}.manifest.json")
            manifest_file.write_text(json.dumps({
                "filename": backup_file.name,
                "sha256": "wrong_and_tampered_hash_0000000000000000000000000000000000000000",
            }))

            out = io.StringIO()
            with pytest.raises(SystemExit):
                call_command(
                    "check_backup_freshness",
                    f"--backup-root={tmp_dir}",
                    "--subsystems=db",
                    "--json",
                    stdout=out,
                )

            data = json.loads(out.getvalue())
            assert data["status"] == "FAIL"
            assert data["subsystems"]["db"]["status"] == "CORRUPTED"
            assert data["subsystems"]["db"]["checksum_verified"] is False


class TestDisasterRecoveryScriptsAndArchitecture:
    """Pruebas de presencia y sintaxis de los scripts operativos de DR."""

    def _find_repo_file(self, rel_path: str) -> Path:
        candidates = [
            Path("/repo") / rel_path,
            Path("/app") / rel_path,
            Path(os.getcwd()) / rel_path,
            Path(os.getcwd()).parent / rel_path,
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError(f"No se encontró {rel_path} en los candidatos evaluados.")

    def test_backup_and_restore_scripts_exist(self):
        required_scripts = [
            "scripts/backup/backup_db.sh",
            "scripts/backup/backup_media.sh",
            "scripts/backup/restore_db.sh",
            "scripts/backup/restore_media.sh",
            "scripts/backup/backup_config.sh",
            "scripts/backup/backup_all.sh",
            "scripts/backup/verify_restore_integrity.sh",
        ]
        for script_rel in required_scripts:
            script_path = self._find_repo_file(script_rel)
            assert script_path.is_file(), f"El script {script_rel} debe existir."
            content = script_path.read_text(encoding="utf-8")
            assert "set -euo pipefail" in content

    def test_disaster_recovery_plan_defines_rpo_and_rto(self):
        doc_path = self._find_repo_file("docs/deployment/disaster_recovery.md")
        content = doc_path.read_text(encoding="utf-8")
        assert "RPO (Recovery Point Objective)" in content
        assert "RTO (Recovery Time Objective)" in content
        assert "verify_restore_integrity" in content
        assert "check_backup_freshness" in content
        assert "backup_all.sh" in content
