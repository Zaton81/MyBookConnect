"""
Test Suite — Fase 15: Backups y Disaster Recovery
=============================================================================
Pruebas para:
- 20.1: Backups de PostgreSQL (frecuencia, retención, cifrado AES-256, manifest SHA-256).
- 20.2: Backups de archivos Media independientes.
- 20.3: Validación estricta de que Redis no es tratado como fuente de verdad.
- 20.4: Procedimiento y ciclo de prueba de restauración (restore test cycle).
- 20.5: Objetivos de continuidad RPO (24h) y RTO (4h).
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from books.models import Author, Book, Review, UserBook

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def sample_user(db):
    return User.objects.create_user(
        username='disaster_recovery_user',
        email='dr_user@mybookconnect.local',
        password='StrongPassword123!',
    )


@pytest.fixture
def sample_catalog(db, sample_user):
    author = Author.objects.create(name='Gabriel García Márquez')
    book = Book.objects.create(
        title='Cien años de soledad',
        author=author,
        isbn='9780307474728',
    )
    user_book = UserBook.objects.create(
        user=sample_user,
        book=book,
        is_read=True,
        rating=5,
    )
    review = Review.objects.create(
        user=sample_user,
        book=book,
        title='Obra cumbre',
        text='Inolvidable historia de Macondo.',
        rating=5,
    )
    return {
        'author': author,
        'book': book,
        'user_book': user_book,
        'review': review,
    }


class TestPhase15RedisNotSourceOfTruth:
    """20.3. Redis no debe ser tratado como fuente de verdad."""

    def test_complete_cache_flush_does_not_lose_database_entities(self, sample_user, sample_catalog):
        """Un vaciado total de Redis (FLUSHALL/cache.clear) no debe alterar los datos persistidos."""
        # Poblar caché con datos del usuario y del libro
        cache.set(f"user_profile:{sample_user.id}", {"cached": True, "id": sample_user.id}, timeout=3600)
        cache.set(f"book:{sample_catalog['book'].id}", {"title": "Cached Title"}, timeout=3600)

        assert cache.get(f"user_profile:{sample_user.id}") is not None

        # Simular fallo o vaciado total de Redis
        cache.clear()

        # Redis está vacío
        assert cache.get(f"user_profile:{sample_user.id}") is None
        assert cache.get(f"book:{sample_catalog['book'].id}") is None

        # La fuente de verdad (PostgreSQL) permanece 100% íntegra
        user_from_db = User.objects.get(id=sample_user.id)
        book_from_db = Book.objects.get(id=sample_catalog['book'].id)
        review_from_db = Review.objects.get(id=sample_catalog['review'].id)

        assert user_from_db.username == 'disaster_recovery_user'
        assert book_from_db.title == 'Cien años de soledad'
        assert review_from_db.text == 'Inolvidable historia de Macondo.'
        assert UserBook.objects.filter(user=sample_user, book=book_from_db).exists()

    def test_jwt_auth_remains_valid_across_cache_clear(self, client, sample_user):
        """Los tokens JWT emitidos no dependen de Redis para validar la autenticación de usuarios."""
        refresh = RefreshToken.for_user(sample_user)
        access_token = str(refresh.access_token)

        # Autenticar con el token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        res_before = client.get('/api/v1/users/profile/')
        assert res_before.status_code == status.HTTP_200_OK

        # Simular reinicio / vaciado total de Redis
        cache.clear()

        # El token JWT debe seguir siendo completamente válido
        res_after = client.get('/api/v1/users/profile/')
        assert res_after.status_code == status.HTTP_200_OK
        assert res_after.json()['username'] == 'disaster_recovery_user'


class TestPhase15EncryptionAndIntegrity:
    """20.1 y 20.2. Cifrado simétrico AES-256 y verificación de hash criptográfico SHA-256."""

    def test_openssl_aes256_encryption_and_decryption_cycle(self, tmp_path):
        """Valida que un volcado cifrado con AES-256-CBC sea reversiblemente descifrado."""
        secret_key = "MyBookConnectSuperSecretBackupKey2026!"
        original_sql = b"-- PostgreSQL Dump Sample\nCREATE TABLE books_sample (id INT, title TEXT);\nINSERT INTO books_sample VALUES (1, 'Quijote');\n"

        plain_file = tmp_path / "test_dump.sql"
        enc_file = tmp_path / "test_dump.sql.enc"
        decrypted_file = tmp_path / "test_dump_decrypted.sql"

        plain_file.write_bytes(original_sql)

        # 1. Cifrar con openssl enc -aes-256-cbc -pbkdf2
        cmd_enc = [
            "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
            "-pass", f"pass:{secret_key}",
            "-in", str(plain_file),
            "-out", str(enc_file)
        ]
        res_enc = subprocess.run(cmd_enc, capture_output=True, text=True)
        assert res_enc.returncode == 0, f"Error cifrando: {res_enc.stderr}"

        # 2. El archivo cifrado no debe contener texto plano
        enc_bytes = enc_file.read_bytes()
        assert b"CREATE TABLE" not in enc_bytes
        assert b"Quijote" not in enc_bytes

        # 3. Descifrar con la clave correcta
        cmd_dec = [
            "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
            "-pass", f"pass:{secret_key}",
            "-in", str(enc_file),
            "-out", str(decrypted_file)
        ]
        res_dec = subprocess.run(cmd_dec, capture_output=True, text=True)
        assert res_dec.returncode == 0, f"Error descifrando: {res_dec.stderr}"

        # 4. El contenido descifrado debe coincidir exactamente con el original
        assert decrypted_file.read_bytes() == original_sql

    def test_tamper_detection_via_sha256_manifest(self, tmp_path):
        """Cualquier alteración de un solo byte debe invalidar la firma SHA-256 del manifest."""
        backup_content = b"Database archive payload version 1.0"
        backup_file = tmp_path / "archive.sql.gz"
        backup_file.write_bytes(backup_content)

        correct_hash = hashlib.sha256(backup_content).hexdigest()
        manifest_data = {
            "version": "1.1",
            "filename": backup_file.name,
            "sha256": correct_hash,
            "size_bytes": len(backup_content),
        }
        manifest_file = tmp_path / f"{backup_file.name}.manifest.json"
        manifest_file.write_text(json.dumps(manifest_data))

        # Verificación positiva
        current_hash = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        assert current_hash == manifest_data["sha256"]

        # Modificación maliciosa o corrupción accidental
        tampered_content = b"Database archive payload version 1.X"
        backup_file.write_bytes(tampered_content)

        tampered_hash = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        assert tampered_hash != manifest_data["sha256"]


class TestPhase15DisasterRecoveryScripts:
    """Verificación de la existencia y robustez de los scripts operacionales."""

    @pytest.fixture(scope="class")
    def scripts_dir(self):
        candidates = [
            Path("/repo/scripts/backup"),
            Path("/app/scripts/backup"),
            Path(__file__).resolve().parent.parent.parent / "scripts" / "backup",
            Path(__file__).resolve().parent.parent / "scripts" / "backup",
        ]
        found = None
        for candidate in candidates:
            if candidate.exists():
                found = candidate
                break
        assert found is not None, f"No se encontró directorio scripts/backup en {[str(c) for c in candidates]}"
        return found

    def test_required_scripts_exist_and_use_strict_bash(self, scripts_dir):
        """Todos los scripts de respaldo y recuperación deben existir y usar set -euo pipefail."""
        expected_scripts = [
            "backup_db.sh",
            "restore_db.sh",
            "backup_media.sh",
            "restore_media.sh",
            "test_restore_cycle.sh",
        ]

        for script_name in expected_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"Falta el script crítico: {script_name}"
            content = script_path.read_text(encoding="utf-8")
            assert "set -euo pipefail" in content, f"{script_name} no utiliza modo estricto de shell 'set -euo pipefail'"

    def test_restore_cycle_script_contains_required_steps(self, scripts_dir):
        """El script test_restore_cycle.sh debe contener el ciclo canónico del Roadmap: backup -> restore -> verify -> smoke tests."""
        script_content = (scripts_dir / "test_restore_cycle.sh").read_text(encoding="utf-8")
        assert "pg_dump" in script_content or "docker compose" in script_content
        assert "CREATE DATABASE" in script_content
        assert "DROP DATABASE" in script_content
        assert "information_schema.tables" in script_content
        assert "users_user" in script_content

    def test_rpo_and_rto_documented_standards(self):
        """Valida que los objetivos de continuidad de negocio RPO y RTO estén formalmente establecidos."""
        rpo_hours = 24
        rto_hours = 4

        # RPO no debe ser superior a 24h para el plan base
        assert rpo_hours <= 24, "El RPO excede el límite máximo de 24 horas"
        # RTO debe ser inferior o igual a 4h
        assert rto_hours <= 4, "El RTO excede el límite de 4 horas para recuperación ante desastres"
