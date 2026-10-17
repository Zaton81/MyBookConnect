"""
Suite de pruebas exhaustiva para la Fase 60: Seguridad de imágenes.

Valida:
1. Redimensionamiento inteligente (resize/downscale) conservando aspect ratio según presets.
2. Eliminación profunda de metadatos (EXIF, XMP, IPTC, comentarios, chunks de texto).
3. Validación estricta de tipos MIME HTTP y coherencia con el formato binario real.
4. Inspección binaria de firmas de cabecera (Magic Bytes) para JPEG, PNG y WebP.
5. Arquitectura de escáner antivirus y bloqueo de firmas de prueba EICAR y ejecutables.
6. Integración en serializadores y endpoints de la API (avatares, chat, portadas).
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from messages_app.models import Conversation, Message
from mybookconnect.media_scanner import EICAR_SIGNATURE, scan_media_file
from mybookconnect.media_security import (
    AVATAR_PRESET,
    CHAT_IMAGE_PRESET,
    COVER_PRESET,
    detect_magic_format,
    sanitize_image,
    validate_avatar_image,
    validate_image_file,
)

User = get_user_model()


def _create_test_image(
    format_name: str = "JPEG",
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int] = (120, 150, 180),
    exif_data: dict | None = None,
) -> bytes:
    """Genera bytes de una imagen válida en memoria para pruebas."""
    mode = "RGBA" if format_name == "PNG" else "RGB"
    img = Image.new(mode, size, color)
    buffer = io.BytesIO()

    if exif_data and format_name == "JPEG":
        exif = img.getexif()
        for tag_id, val in exif_data.items():
            exif[tag_id] = val
        img.save(buffer, format=format_name, exif=exif)
    else:
        img.save(buffer, format=format_name)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# 1. Pruebas de Redimensionamiento Inteligente (Resize / Downscale)
# ---------------------------------------------------------------------------
class TestImageResizing:
    def test_oversized_avatar_downscales_to_preset(self):
        """Una imagen de avatar de 2000x1500 debe reducirse al preset (512, 512) conservando ratio."""
        raw_bytes = _create_test_image("JPEG", size=(2000, 1500))
        cleaned = sanitize_image(raw_bytes, filename="avatar.jpg", max_dimensions=AVATAR_PRESET)

        img = Image.open(cleaned)
        assert img.width <= AVATAR_PRESET[0]
        assert img.height <= AVATAR_PRESET[1]
        # Aspect ratio 2000:1500 = 4:3 -> 512 x 384
        assert img.width == 512
        assert img.height == 384

    def test_oversized_cover_downscales_to_preset(self):
        """Una portada de 3000x2000 debe reducirse al preset de portada (1200, 1800) conservando ratio."""
        raw_bytes = _create_test_image("JPEG", size=(3000, 2000))
        cleaned = sanitize_image(raw_bytes, filename="cover.jpg", max_dimensions=COVER_PRESET)

        img = Image.open(cleaned)
        assert img.width <= COVER_PRESET[0]
        assert img.height <= COVER_PRESET[1]
        # Ratio 3:2 -> 1200 x 800
        assert img.width == 1200
        assert img.height == 800

    def test_oversized_chat_image_downscales_to_preset(self):
        """Una imagen de chat de 2400x2400 debe reducirse a máximo 1920x1920."""
        raw_bytes = _create_test_image("PNG", size=(2400, 2400))
        cleaned = sanitize_image(raw_bytes, filename="chat.png", max_dimensions=CHAT_IMAGE_PRESET)

        img = Image.open(cleaned)
        assert img.width == 1920
        assert img.height == 1920

    def test_smaller_image_remains_unchanged_in_dimensions(self):
        """Una imagen más pequeña que el preset (p.ej. 300x200) no debe aumentarse innecesariamente."""
        raw_bytes = _create_test_image("JPEG", size=(300, 200))
        cleaned = sanitize_image(raw_bytes, filename="small.jpg", max_dimensions=AVATAR_PRESET)

        img = Image.open(cleaned)
        assert img.width == 300
        assert img.height == 200


# ---------------------------------------------------------------------------
# 2. Pruebas de Eliminación Profunda de Metadatos (Strip Metadata)
# ---------------------------------------------------------------------------
class TestMetadataStripping:
    def test_exif_metadata_stripped_completely(self):
        """Verifica que los metadatos EXIF sean purgados en su totalidad."""
        # 0x010E es ImageDescription, 0x0131 es Software
        exif_tags = {0x010E: "Metadato con posible inyeccion", 0x0131: "Camera Software v1.0"}
        raw_bytes = _create_test_image("JPEG", size=(200, 200), exif_data=exif_tags)

        # Confirmar que el origen tiene EXIF
        original_img = Image.open(io.BytesIO(raw_bytes))
        orig_exif = original_img.getexif()
        assert orig_exif.get(0x010E) == "Metadato con posible inyeccion"

        # Sanitizar
        cleaned = sanitize_image(raw_bytes, filename="photo.jpg")
        cleaned_img = Image.open(cleaned)
        cleaned_exif = cleaned_img.getexif()
        assert not cleaned_exif or len(cleaned_exif) == 0
        assert 0x010E not in cleaned_exif
        assert 0x0131 not in cleaned_exif

    def test_webp_and_png_clean_metadata(self):
        """Verifica que imágenes WebP y PNG no contengan información residual en info."""
        for fmt in ("PNG", "WEBP"):
            raw_bytes = _create_test_image(fmt, size=(150, 150))
            cleaned = sanitize_image(raw_bytes, filename=f"image.{fmt.lower()}")
            cleaned_img = Image.open(cleaned)
            assert "exif" not in cleaned_img.info
            assert "comment" not in cleaned_img.info
            assert "xmp" not in cleaned_img.info


# ---------------------------------------------------------------------------
# 3. Pruebas de Validación MIME y Magic Bytes
# ---------------------------------------------------------------------------
class TestMimeAndMagicBytes:
    def test_detect_magic_format_valid(self):
        """Identifica correctamente las firmas Magic Bytes para JPEG, PNG y WebP."""
        jpeg_bytes = _create_test_image("JPEG")
        png_bytes = _create_test_image("PNG")
        webp_bytes = _create_test_image("WEBP")

        assert detect_magic_format(io.BytesIO(jpeg_bytes)) == "JPEG"
        assert detect_magic_format(io.BytesIO(png_bytes)) == "PNG"
        assert detect_magic_format(io.BytesIO(webp_bytes)) == "WEBP"

    def test_detect_magic_format_rejects_fake_header(self):
        """Rechaza archivos con contenido de texto plano o scripts camuflados."""
        fake_bytes = io.BytesIO(b"#!/bin/bash\necho 'hacked'\n")
        assert detect_magic_format(fake_bytes) is None

        html_bytes = io.BytesIO(b"<html><body><script>alert(1)</script></body></html>")
        assert detect_magic_format(html_bytes) is None

    def test_mime_type_mismatch_rejected(self):
        """Si el content_type declarado no coincide con el formato binario real, debe fallar."""
        # Archivo binario PNG con content_type declarado como image/jpeg
        png_bytes = _create_test_image("PNG")
        uploaded = SimpleUploadedFile(
            "fake.jpg",
            png_bytes,
            content_type="image/jpeg",
        )
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=5 * 1024 * 1024)
        assert "Discrepancia" in str(exc_info.value)

    def test_disallowed_mime_type_rejected(self):
        """Tipos MIME no permitidos como application/pdf o image/gif deben ser rechazados."""
        jpeg_bytes = _create_test_image("JPEG")
        uploaded = SimpleUploadedFile(
            "document.jpg",
            jpeg_bytes,
            content_type="application/pdf",
        )
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=5 * 1024 * 1024)
        assert "Tipo MIME 'application/pdf' no permitido" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Pruebas de Escáner Antivirus y Malware
# ---------------------------------------------------------------------------
class TestAntivirusScanner:
    def test_eicar_virus_signature_blocked(self):
        """Un archivo que contenga la firma estándar EICAR debe ser bloqueado con ValidationError."""
        infected_buffer = io.BytesIO(EICAR_SIGNATURE)
        with pytest.raises(DjangoValidationError) as exc_info:
            scan_media_file(infected_buffer)
        assert "inspección de seguridad antivirus" in str(exc_info.value)
        assert "Eicar-Test-Signature" in str(exc_info.value)

    def test_eicar_signature_in_image_payload_blocked(self):
        """Una imagen con una carga útil EICAR concatenada debe ser bloqueada por la validación."""
        jpeg_bytes = _create_test_image("JPEG")
        payload = jpeg_bytes + b"\n" + EICAR_SIGNATURE
        uploaded = SimpleUploadedFile("infected.jpg", payload, content_type="image/jpeg")

        with pytest.raises(DjangoValidationError) as exc_info:
            validate_avatar_image(uploaded)
        assert "antivirus" in str(exc_info.value)

    def test_clean_file_passes_scanner(self):
        """Un archivo de imagen limpio pasa el escaneo antivirus sin excepciones."""
        clean_buffer = io.BytesIO(_create_test_image("JPEG"))
        # No debe lanzar ninguna excepción
        scan_media_file(clean_buffer)


# ---------------------------------------------------------------------------
# 5. Integración con Endpoints de la API
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestImageEndpointsIntegration:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="imagetester",
            email="imagetester@example.com",
            password="StrongPassword123!",
        )

    @pytest.fixture
    def client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_avatar_upload_downscales_and_saves_clean(self, client, user):
        """Subida de un avatar de 1600x1200 px vía API; debe guardarse redimensionado a máx 512x512."""
        raw_bytes = _create_test_image("JPEG", size=(1600, 1200))
        avatar_file = SimpleUploadedFile("my_large_avatar.jpg", raw_bytes, content_type="image/jpeg")

        res = client.patch(
            "/api/v1/auth/profile/update/",
            {"avatar": avatar_file},
            format="multipart",
        )
        assert res.status_code == 200, res.data

        user.refresh_from_db()
        assert bool(user.avatar) is True
        saved_img = Image.open(user.avatar.path)
        assert saved_img.width <= AVATAR_PRESET[0]
        assert saved_img.height <= AVATAR_PRESET[1]
        assert saved_img.width == 512
        assert saved_img.height == 384

    def test_chat_message_image_upload_downscales_and_saves_clean(self, client, user):
        """Subida de imagen de chat de 2400x1800 px; debe guardarse redimensionada a máx 1920x1920."""
        friend = User.objects.create_user(
            username="chat_recipient",
            email="recipient@example.com",
            password="StrongPassword123!",
        )
        user.following.add(friend)
        conv, _ = Conversation.get_or_create_direct(user, friend)

        chat_bytes = _create_test_image("PNG", size=(2400, 1800))
        chat_file = SimpleUploadedFile("big_photo.png", chat_bytes, content_type="image/png")

        res = client.post(
            "/api/v1/messages/",
            {"conversation": conv.id, "image": chat_file, "text": "Mira esta foto"},
            format="multipart",
        )
        assert res.status_code == 201, res.data

        msg = Message.objects.get(id=res.data["id"])
        assert bool(msg.image) is True
        saved_img = Image.open(msg.image.path)
        assert saved_img.width <= CHAT_IMAGE_PRESET[0]
        assert saved_img.height <= CHAT_IMAGE_PRESET[1]
        # 2400x1800 ratio 4:3 -> 1920 x 1440
        assert saved_img.width == 1920
        assert saved_img.height == 1440
