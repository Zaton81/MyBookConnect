"""
Tests de Verificación para Fase 1 Post-GA:
Higiene de Git, Activos Estáticos y Almacenamiento Multimedia.
"""

import hashlib
import io
import os
from pathlib import Path
from PIL import Image
import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command

from books.models import Author, Book
from mybookconnect.media_security import (
    UploadToHashedPath,
    sanitize_and_prepare_image,
    sanitize_image,
    upload_to_author_photos,
    upload_to_covers,
)
from mybookconnect.storage import DeduplicatedFileSystemStorage, DeduplicatedS3Storage


def _find_path(*relative_candidates) -> Path | None:
    """Busca una ruta relativa considerando la ejecución local y la ejecución containerizada (/app)."""
    for candidate in relative_candidates:
        # 1. Ruta absoluta directa
        p = Path(candidate)
        if p.exists():
            return p
        # 2. En contenedor Docker (/app /repo)
        for base in [Path("/app"), Path("/repo"), Path(settings.BASE_DIR)]:
            target = base / candidate
            if target.exists():
                return target
            # Probar sin prefijo "backend/"
            if candidate.startswith("backend/"):
                stripped = candidate[len("backend/"):]
                target_stripped = base / stripped
                if target_stripped.exists():
                    return target_stripped
        # 3. En máquina host local
        host_base = Path(__file__).resolve().parent.parent.parent
        target_host = host_base / candidate
        if target_host.exists():
            return target_host
    return None


@pytest.mark.django_db
class TestPhasePostGAFase1HygieneAndStorage:
    """Suite de pruebas de higiene de repositorio, activos estáticos y almacenamiento deduplicado."""

    def test_git_media_hygiene_and_gitkeep(self):
        """Verifica que backend/media/.gitkeep existe y los archivos en media están ignorados."""
        gitkeep_path = _find_path("backend/media/.gitkeep", "media/.gitkeep")
        assert gitkeep_path is not None and gitkeep_path.is_file(), (
            "backend/media/.gitkeep debe existir para preservar la carpeta en Git"
        )

        gitignore_path = _find_path(".gitignore")
        if gitignore_path and gitignore_path.is_file():
            gitignore_content = gitignore_path.read_text(encoding="utf-8")
            assert "backend/media/*" in gitignore_content or "media/*" in gitignore_content
            assert "!backend/media/.gitkeep" in gitignore_content or "!media/.gitkeep" in gitignore_content

    def test_deduplicated_file_system_storage_reuses_existing(self, tmp_path):
        """Verifica que DeduplicatedFileSystemStorage no añade sufijos aleatorios si el archivo ya existe."""
        storage = DeduplicatedFileSystemStorage(location=str(tmp_path), base_url="/media/")
        content1 = b"test content for deduplication"
        filename = "covers/aa/aabbccdd11223344.webp"

        # Primera escritura
        saved_name1 = storage.save(filename, ContentFile(content1))
        assert saved_name1 == filename
        assert storage.exists(filename)

        # Segunda escritura con el mismo contenido o mismo nombre
        content2 = b"test content for deduplication"
        saved_name2 = storage.save(filename, ContentFile(content2))
        assert saved_name2 == filename, "El almacenamiento debe reutilizar el nombre exacto sin sufijos _XYZ"

    def test_upload_to_hashed_path_deterministic_structure(self):
        """Verifica que UploadToHashedPath genere la estructura jerárquica subfolder/hash[:2]/hash.ext."""
        uploader = UploadToHashedPath("covers")
        assert uploader.subfolder == "covers"

        # Simular filename con hash SHA-256
        sample_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        path = uploader(instance=None, filename=f"{sample_hash}.webp")
        expected_path = f"covers/{sample_hash[:2]}/{sample_hash}.webp"
        assert path == expected_path

    def test_sanitize_image_defaults_to_webp_and_attaches_hash(self):
        """Verifica que sanitize_image convierta a WebP por defecto y adjunte content_hash."""
        # Crear imagen sintética en memoria
        img = Image.new("RGB", (200, 300), color=(100, 150, 200))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        raw_bytes = buffer.getvalue()

        content_file = ContentFile(raw_bytes, name="portada_original.jpg")
        sanitized = sanitize_image(content_file, quality=82)

        assert sanitized.name.endswith(".webp"), "La imagen sanitizada debe tener extensión .webp"
        assert hasattr(sanitized, "content_hash"), "El ContentFile debe tener el atributo content_hash"
        assert len(sanitized.content_hash) == 64, "El content_hash debe ser un SHA-256 de 64 caracteres"
        assert sanitized.name == f"{sanitized.content_hash}.webp"

        # Verificar que el binario resultante es efectivamente un WebP válido
        reloaded = Image.open(sanitized)
        assert reloaded.format == "WEBP"

    def test_sanitize_and_prepare_image_preset_downscale(self):
        """Verifica que sanitize_and_prepare_image aplique downscaling conservando ratio."""
        # Imagen grande de 2000x3000 px
        img = Image.new("RGB", (2000, 3000), color=(50, 50, 50))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        content_file = ContentFile(buffer.getvalue(), name="large.png")
        preset = (800, 1200)
        sanitized = sanitize_and_prepare_image(content_file, preset=preset)

        reloaded = Image.open(sanitized)
        assert reloaded.width <= preset[0]
        assert reloaded.height <= preset[1]
        assert reloaded.format == "WEBP"

    def test_storage_backends_import_and_configuration(self):
        """Verifica que los backends de almacenamiento local y S3/R2 están definidos e integrados."""
        assert issubclass(DeduplicatedFileSystemStorage, object)
        assert hasattr(DeduplicatedFileSystemStorage, "get_available_name")
        assert issubclass(DeduplicatedS3Storage, object)
        assert hasattr(DeduplicatedS3Storage, "get_available_name")

        default_storage_backend = settings.STORAGES["default"]["BACKEND"]
        assert "mybookconnect.storage." in default_storage_backend

    def test_frontend_assets_budget(self):
        """Verifica que los activos frontend estén optimizados por debajo de los presupuestos de peso."""
        assets_dir = _find_path("frontend/src/assets")
        public_dir = _find_path("frontend/public")

        if not assets_dir and not public_dir:
            pytest.skip("Directorio frontend no montado en el contenedor; validación estática omitida en backend.")

        if assets_dir and assets_dir.exists():
            for name in ["logo-horizontal.png", "logo-libro.png", "logo-principal.png"]:
                path = assets_dir / name
                assert path.is_file(), f"Activo {name} debe existir"
                size_kb = path.stat().st_size / 1024
                assert size_kb < 50, f"Activo {name} excede el presupuesto ({size_kb:.1f} KB >= 50 KB)"

        if public_dir and public_dir.exists():
            favicon_path = public_dir / "favicon.ico"
            assert favicon_path.is_file(), "favicon.ico debe existir"
            favicon_kb = favicon_path.stat().st_size / 1024
            assert favicon_kb < 15, f"favicon.ico excede el presupuesto ({favicon_kb:.1f} KB >= 15 KB)"

            apple_icon = public_dir / "apple-touch-icon.png"
            assert apple_icon.is_file(), "apple-touch-icon.png debe existir"
            apple_kb = apple_icon.stat().st_size / 1024
            assert apple_kb < 25, f"apple-touch-icon.png excede el presupuesto ({apple_kb:.1f} KB >= 25 KB)"

    def test_scripts_consolidation(self):
        """Verifica que los scripts duplicados han sido consolidados según la Fase 1."""
        root_locust = _find_path("scripts/locustfile.py")
        assert root_locust is None or not root_locust.exists(), "scripts/locustfile.py raíz debe eliminarse"

        modular_locust = _find_path("scripts/load_testing/locustfile.py")
        assert modular_locust is not None and modular_locust.is_file(), (
            "scripts/load_testing/locustfile.py debe ser el archivo canónico"
        )

        preflight_check = _find_path("scripts/production/preflight_check.sh")
        assert preflight_check is None or not preflight_check.exists(), (
            "scripts/production/preflight_check.sh debe eliminarse tras fusión"
        )

        preflight_prod = _find_path("scripts/production/preflight_prod.sh")
        assert preflight_prod is not None and preflight_prod.is_file(), (
            "scripts/production/preflight_prod.sh debe existir y contener la lógica completa"
        )
        content = preflight_prod.read_text(encoding="utf-8")
        assert "showmigrations" in content
        assert "check --deploy" in content

    def test_seed_dev_catalog_command(self):
        """Verifica que el comando seed_dev_catalog genera registros y portadas sintéticas limpias."""
        call_command("seed_dev_catalog", count=2, clean=True)
        dev_books = Book.objects.filter(title__startswith="[DEV] ")
        assert dev_books.count() >= 2
        for book in dev_books:
            assert book.cover, f"El libro {book.title} debe tener portada asignada"
            assert book.cover.name.endswith(".webp")
