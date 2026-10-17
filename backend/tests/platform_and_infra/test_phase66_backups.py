import gzip
import json
import os
import shutil
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from books.models import Author, Book, Review
from books.services.backup_service import (
    DatabaseBackupService,
    MediaBackupService,
    compute_sha256,
    prune_old_backups,
)

User = get_user_model()


@pytest.mark.django_db
class TestDatabaseBackupAndRetention:
    """Pruebas del servicio de backup de base de datos, firmas SHA-256 y política de retención."""

    def test_database_backup_creates_valid_archive_and_manifest(self, tmp_path):
        # Crear datos de prueba
        author = Author.objects.create(name="Author 1")
        User.objects.create_user(username="backup_user_1", password="password123")
        Book.objects.create(title="Backup Book 1", author=author)

        result = DatabaseBackupService.backup_database(
            output_dir=tmp_path,
            retention_days=7,
            force_django_dump=True,
        )

        backup_file = Path(result["backup_file"])
        manifest_file = Path(result["manifest_file"])

        assert backup_file.exists()
        assert manifest_file.exists()
        assert backup_file.stat().st_size > 0

        # Verificar manifest y firma SHA-256
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["type"] == "database"
        assert manifest["format"] == "django_dumpdata_gzip"
        assert manifest["sha256"] == compute_sha256(backup_file)
        assert manifest["size_bytes"] == backup_file.stat().st_size

    def test_database_backup_retention_policy(self, tmp_path):
        """Verifica que las copias que superen el límite de retención se eliminen pero se conserve la más reciente."""
        now = datetime.now(timezone.utc)

        # Crear 3 backups simulados: 1 de hace 20 días, 1 de hace 10 días, 1 de hace 1 día
        old_file_1 = tmp_path / "db_backup_old1.json.gz"
        old_file_2 = tmp_path / "db_backup_old2.json.gz"
        recent_file = tmp_path / "db_backup_recent.json.gz"

        for f in (old_file_1, old_file_2, recent_file):
            with gzip.open(f, "wb") as gz:
                gz.write(b'{"test": "data"}')

        # Ajustar timestamps de modificación
        time_20d_ago = (now - timedelta(days=20)).timestamp()
        time_10d_ago = (now - timedelta(days=10)).timestamp()
        time_1d_ago = (now - timedelta(days=1)).timestamp()

        os.utime(old_file_1, (time_20d_ago, time_20d_ago))
        os.utime(old_file_2, (time_10d_ago, time_10d_ago))
        os.utime(recent_file, (time_1d_ago, time_1d_ago))

        pruned = prune_old_backups(tmp_path, retention_days=7, file_pattern="db_backup_*", keep_minimum=1)

        pruned_names = [p.name for p in pruned]
        assert "db_backup_old1.json.gz" in pruned_names
        assert "db_backup_old2.json.gz" in pruned_names
        assert not old_file_1.exists()
        assert not old_file_2.exists()
        assert recent_file.exists()


class TestMediaBackupAndRetention:
    """Pruebas del servicio de empaquetado de archivos multimedia (Media) y retención."""

    def test_media_backup_creates_tarball_and_manifest(self, tmp_path):
        # Crear directorio temporal de media con archivos
        media_root = tmp_path / "source_media"
        media_root.mkdir(parents=True)
        avatars_dir = media_root / "avatars"
        avatars_dir.mkdir()
        covers_dir = media_root / "covers"
        covers_dir.mkdir()

        avatar_file = avatars_dir / "user_1.png"
        avatar_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRavatar_sample_bytes")
        cover_file = covers_dir / "book_1.jpg"
        cover_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIFcover_sample_bytes")

        output_dir = tmp_path / "backups_media"
        result = MediaBackupService.backup_media(
            output_dir=output_dir,
            retention_days=30,
            media_root=media_root,
        )

        backup_file = Path(result["backup_file"])
        manifest_file = Path(result["manifest_file"])

        assert backup_file.exists()
        assert manifest_file.exists()
        assert result["file_count"] == 2

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["type"] == "media"
        assert manifest["sha256"] == compute_sha256(backup_file)
        assert "avatars/user_1.png" in manifest["files"]
        assert "covers/book_1.jpg" in manifest["files"]
        assert manifest["files"]["avatars/user_1.png"]["sha256"] == compute_sha256(avatar_file)
        assert manifest["files"]["covers/book_1.jpg"]["sha256"] == compute_sha256(cover_file)

    def test_media_backup_retention_policy(self, tmp_path):
        media_dir = tmp_path / "media_backups"
        media_dir.mkdir(parents=True)
        now = datetime.now(timezone.utc)

        old_media = media_dir / "media_backup_old.tar.gz"
        recent_media = media_dir / "media_backup_recent.tar.gz"

        with tarfile.open(old_media, "w:gz"):
            pass
        with tarfile.open(recent_media, "w:gz"):
            pass

        time_40d_ago = (now - timedelta(days=40)).timestamp()
        time_2d_ago = (now - timedelta(days=2)).timestamp()

        os.utime(old_media, (time_40d_ago, time_40d_ago))
        os.utime(recent_media, (time_2d_ago, time_2d_ago))

        pruned = prune_old_backups(media_dir, retention_days=30, file_pattern="media_backup_*", keep_minimum=1)

        assert old_media in pruned
        assert not old_media.exists()
        assert recent_media.exists()


@pytest.mark.django_db(transaction=True)
class TestRestorationDrillAndIntegrity:
    """
    Simulacros automatizados de restauración para validar la regla del Roadmap:
    'Un backup que nunca se ha restaurado no se considera validado'.
    """

    def test_database_restoration_drill(self, tmp_path):
        """Simulacro completo: crear datos, hacer backup, modificar/eliminar datos, restaurar y verificar."""
        author = Author.objects.create(name="Drill Author")
        user = User.objects.create_user(username="drill_author", email="drill@example.com", password="password123")
        book = Book.objects.create(title="Drill Master Book", author=author, isbn="9780123456789")
        review = Review.objects.create(user=user, book=book, rating=5, text="Excelente lectura para simulacro")

        # 1. Generar backup
        backup_result = DatabaseBackupService.backup_database(
            output_dir=tmp_path,
            retention_days=7,
            force_django_dump=True,
        )
        backup_file = Path(backup_result["backup_file"])

        # 2. Simular pérdida o corrupción de datos
        review_id = review.id
        book_id = book.id
        review.delete(hard=True)
        book.title = "Libro Modificado con Título Corrupto"
        book.save()

        assert not Review.objects.filter(id=review_id).exists()
        assert Book.objects.get(id=book_id).title == "Libro Modificado con Título Corrupto"

        # 3. Restaurar desde backup
        restore_result = DatabaseBackupService.restore_database(
            backup_file=backup_file,
            verify_checksum=True,
        )

        assert restore_result["status"] == "success"

        # 4. Verificar que todos los datos han sido restaurados íntegramente
        restored_book = Book.objects.get(id=book_id)
        assert restored_book.title == "Drill Master Book"

        restored_review = Review.objects.get(id=review_id)
        assert restored_review.rating == 5
        assert restored_review.text == "Excelente lectura para simulacro"
        assert restored_review.user_id == user.id

    def test_media_restoration_drill(self, tmp_path):
        """Simulacro completo de media: crear archivos, hacer backup, borrarlos, restaurar y verificar hashes."""
        source_media = tmp_path / "drill_source_media"
        source_media.mkdir(parents=True)
        avatar = source_media / "avatar_drill.png"
        avatar.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdrill_avatar_bytes")
        cover = source_media / "cover_drill.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIFdrill_cover_bytes")

        original_avatar_hash = compute_sha256(avatar)
        original_cover_hash = compute_sha256(cover)

        # 1. Backup de media
        backup_dir = tmp_path / "drill_backups"
        backup_result = MediaBackupService.backup_media(
            output_dir=backup_dir,
            media_root=source_media,
        )
        backup_file = Path(backup_result["backup_file"])

        # 2. Simular pérdida total de archivos de media
        shutil.rmtree(source_media)
        assert not source_media.exists()

        # 3. Restaurar media
        restore_result = MediaBackupService.restore_media(
            backup_file=backup_file,
            target_dir=source_media,
            verify_checksum=True,
        )

        assert restore_result["status"] == "success"
        assert restore_result["restored_files_count"] == 2

        # 4. Verificar integridad y coincidencia exacta de hashes
        restored_avatar = source_media / "avatar_drill.png"
        restored_cover = source_media / "cover_drill.jpg"

        assert restored_avatar.exists()
        assert restored_cover.exists()
        assert compute_sha256(restored_avatar) == original_avatar_hash
        assert compute_sha256(restored_cover) == original_cover_hash

    def test_corrupted_backup_refuses_restore(self, tmp_path):
        """Verifica que un archivo manipulado o corrupto sea detectado por SHA-256 y rechazado."""
        source_media = tmp_path / "tamper_media"
        source_media.mkdir(parents=True)
        sample = source_media / "sample.txt"
        sample.write_text("archivo de prueba")

        backup_result = MediaBackupService.backup_media(
            output_dir=tmp_path / "tamper_backups",
            media_root=source_media,
        )
        backup_file = Path(backup_result["backup_file"])

        # Corromper el archivo alterando bytes sin actualizar el manifest
        with open(backup_file, "ab") as f:
            f.write(b"CORRUPTED_BYTES_INJECTED")

        # Intentar restaurar debe lanzar ValueError por discrepancia de firma
        with pytest.raises(ValueError, match="¡Firma de seguridad de media inválida!"):
            MediaBackupService.restore_media(backup_file, target_dir=tmp_path / "restored")


@pytest.mark.django_db(transaction=True)
class TestDjangoManagementCommands:
    """Prueba la ejecución de los 4 comandos de gestión de backup y restauración."""

    def test_management_commands_execution(self, tmp_path):
        db_dir = tmp_path / "mgmt_db"
        media_dir = tmp_path / "mgmt_media"

        # 1. backup_db command
        call_command(
            "backup_db",
            output_dir=str(db_dir),
            retention_days=5,
            force_django_dump=True,
        )
        db_backups = list(db_dir.glob("*.json.gz"))
        assert len(db_backups) == 1

        # 2. restore_db command
        call_command("restore_db", str(db_backups[0]))

        # 3. backup_media command
        src_media = tmp_path / "src_media"
        src_media.mkdir(parents=True)
        (src_media / "sample.jpg").write_bytes(b"\xff\xd8\xffsample_bytes")

        call_command(
            "backup_media",
            output_dir=str(media_dir),
            media_root=str(src_media),
            retention_days=10,
        )
        media_backups = list(media_dir.glob("*.tar.gz"))
        assert len(media_backups) == 1

        # 4. restore_media command
        call_command(
            "restore_media",
            str(media_backups[0]),
            target_dir=str(tmp_path / "mgmt_restored_media"),
        )
        assert (tmp_path / "mgmt_restored_media").exists()
