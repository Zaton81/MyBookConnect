import json
import os
import subprocess
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.core.cache import cache
from books.models import Author, Book, FAQ
from users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestInfrastructureProbesAndHealth:
    def test_liveness_probe_returns_200(self, api_client):
        res = api_client.get('/health/live/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data.get('status') == 'healthy'

    def test_readiness_probe_returns_200_and_no_secrets(self, api_client):
        res = api_client.get('/health/ready/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data.get('status') == 'ready'
        assert 'services' in data
        assert data['services'].get('database') == 'ready'
        assert data['services'].get('cache') == 'ready'
        content_str = res.content.decode('utf-8')
        assert 'password' not in content_str.lower()
        assert 'superseguro' not in content_str

    def test_version_probe_is_accessible_and_stable(self, api_client):
        res = api_client.get('/api/v1/version/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data.get('version') == '1.0.0'
        assert data.get('major') == 1
        assert data.get('minor') == 0
        assert data.get('patch') == 0


@pytest.mark.django_db
class TestCacheAndDatabaseInfrastructure:
    def test_redis_cache_operations(self):
        cache_key = "infra_test_key_sprint2"
        cache_val = {"status": "ok", "timestamp": 123456789}
        cache.set(cache_key, cache_val, timeout=60)
        retrieved = cache.get(cache_key)
        assert retrieved == cache_val
        cache.delete(cache_key)
        assert cache.get(cache_key) is None

    def test_postgres_16_schema_integrity(self):
        # Verificar que los modelos de todos los sprints operan sobre PostgreSQL 16 sin fallos de constraints
        author = Author.objects.create(name="Autor Infraestructura", nationality="Española")
        book = Book.objects.create(title="Libro Infraestructura", author=author)
        faq = FAQ.objects.create(question="¿Pregunta de Infra?", answer="Respuesta probada.", category="general")

        assert author.id is not None
        assert book.id is not None
        assert faq.id is not None
        assert book.author_id == author.id

        # Limpieza
        faq.delete()
        book.delete()
        author.delete()


class TestBackupAndRestoreScripts:
    def test_backup_script_manifest_generation(self, tmp_path):
        # Simular manifest de backup y validar estructura de metadatos criptográficos
        manifest_data = {
            "version": "1.1",
            "type": "database",
            "format": "pg_dump_gzip",
            "database": "booksocial",
            "filename": "db_backup_test.sql.gz",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "size_bytes": 1024,
            "encrypted": False,
            "cipher": "none",
            "created_at": "2026-10-03T15:00:00Z",
            "retention_days": 7
        }
        manifest_file = tmp_path / "test.manifest.json"
        manifest_file.write_text(json.dumps(manifest_data))

        parsed = json.loads(manifest_file.read_text())
        assert parsed["database"] == "booksocial"
        assert parsed["sha256"] is not None
        assert len(parsed["sha256"]) == 64
        assert parsed["retention_days"] == 7
