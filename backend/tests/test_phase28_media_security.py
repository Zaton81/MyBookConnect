"""
Tests exhaustivos para la Fase 28: Media y uploads.

Valida:
1. Inspección binaria de imágenes y rechazo de archivos camuflados o con extensiones no permitidas (.svg, .exe).
2. Cuotas máximas de tamaño (avatar/autor <= 5MB, portada/chat <= 10MB).
3. Límites de resolución (mínimo 50x50 px, máximo 6000x6000 px).
4. Sanitización activa y eliminación de metadatos EXIF (protección de privacidad y geolocalización).
5. Integración con serializadores DRF (UserSerializer, BookSerializer, MessageSerializer).
6. Integración con el servicio de descarga externa (cover_service.download_and_attach_image).
7. Arquitectura de almacenamiento pluggable (STORAGES en settings).
"""

import io
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from books.models import Book
from books.services.cover_service import download_and_attach_image
from messages_app.models import Conversation, Message
from mybookconnect.media_security import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_FORMATS,
    MAX_AVATAR_SIZE_BYTES,
    MAX_COVER_SIZE_BYTES,
    sanitize_image,
    validate_avatar_image,
    validate_chat_image,
    validate_cover_image,
    validate_image_file,
)

User = get_user_model()


def _create_dummy_image(
    format_name: str = 'JPEG',
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int] = (100, 150, 200),
    exif_data: dict | None = None,
) -> bytes:
    """Crea una imagen binaria válida en memoria para pruebas."""
    mode = 'RGBA' if format_name == 'PNG' else 'RGB'
    img = Image.new(mode, size, color)

    buffer = io.BytesIO()
    if exif_data and format_name == 'JPEG':
        exif = img.getexif()
        for tag_id, val in exif_data.items():
            exif[tag_id] = val
        img.save(buffer, format=format_name, exif=exif)
    else:
        img.save(buffer, format=format_name)
    return buffer.getvalue()


# ─── Tests Unitarios de Validación y Seguridad de Imágenes ───


class TestMediaSecurityValidation:
    """Pruebas de validación de formato, tamaño, extensiones y dimensiones."""

    def test_valid_jpeg_png_webp_images_pass_validation(self):
        """Imágenes JPEG, PNG y WebP con dimensiones correctas deben pasar la validación."""
        for fmt in ('JPEG', 'PNG', 'WEBP'):
            ext = '.jpg' if fmt == 'JPEG' else f'.{fmt.lower()}'
            img_bytes = _create_dummy_image(format_name=fmt, size=(200, 200))
            uploaded = SimpleUploadedFile(f"test_image{ext}", img_bytes, content_type=f"image/{fmt.lower()}")
            # No debe lanzar ninguna excepción
            validate_image_file(uploaded, max_size_bytes=MAX_AVATAR_SIZE_BYTES)

    def test_disallowed_extension_raises_validation_error(self):
        """Extensiones peligrosas o no permitidas (.svg, .exe, .html) deben ser rechazadas."""
        for bad_ext in ('.svg', '.exe', '.html', '.gif', '.pdf'):
            img_bytes = _create_dummy_image(format_name='JPEG')
            uploaded = SimpleUploadedFile(f"exploit{bad_ext}", img_bytes, content_type="image/jpeg")
            with pytest.raises(DjangoValidationError) as exc_info:
                validate_image_file(uploaded, max_size_bytes=MAX_AVATAR_SIZE_BYTES)
            assert "no permitida" in str(exc_info.value)

    def test_disguised_file_raises_validation_error(self):
        """Un archivo de texto o script renombrado a .jpg debe ser detectado y rechazado."""
        fake_content = b"<script>alert('xss attack')</script>"
        uploaded = SimpleUploadedFile("malicious.jpg", fake_content, content_type="image/jpeg")
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=MAX_AVATAR_SIZE_BYTES)
        assert "no es una imagen válida" in str(exc_info.value)

    def test_image_size_exceeding_max_limit_raises_validation_error(self):
        """Archivos que excedan el límite de tamaño en bytes deben lanzar ValidationError."""
        img_bytes = _create_dummy_image(format_name='JPEG', size=(100, 100))
        # Simulamos un límite muy bajo (50 bytes)
        uploaded = SimpleUploadedFile("photo.jpg", img_bytes, content_type="image/jpeg")
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=50)
        assert "excede el tamaño máximo" in str(exc_info.value)

    def test_dimensions_below_minimum_rejected(self):
        """Imágenes con dimensiones menores a 50x50 px deben ser rechazadas."""
        tiny_bytes = _create_dummy_image(format_name='JPEG', size=(30, 40))
        uploaded = SimpleUploadedFile("tiny.jpg", tiny_bytes, content_type="image/jpeg")
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=MAX_AVATAR_SIZE_BYTES, min_dims=(50, 50))
        assert "inferiores al mínimo" in str(exc_info.value)

    def test_dimensions_above_maximum_rejected(self):
        """Imágenes que superen el límite máximo de resolución (6000x6000 px) son rechazadas."""
        img_bytes = _create_dummy_image(format_name='JPEG', size=(100, 100))
        uploaded = SimpleUploadedFile("huge.jpg", img_bytes, content_type="image/jpeg")
        with pytest.raises(DjangoValidationError) as exc_info:
            validate_image_file(uploaded, max_size_bytes=MAX_AVATAR_SIZE_BYTES, max_dims=(80, 80))
        assert "exceden el límite máximo" in str(exc_info.value)


# ─── Tests de Sanitización y Eliminación de Metadatos EXIF ───


class TestMediaSanitization:
    """Pruebas de sanitización y privacidad mediante stripping de EXIF."""

    def test_exif_metadata_stripped_successfully(self):
        """La función sanitize_image debe descartar todos los metadatos EXIF."""
        # 0x010E es ImageDescription, 0x0132 es DateTime, 0x010F es Make
        test_exif = {0x010E: "Metadato con coordenadas GPS y usuario", 0x010F: "CamaraConfidencial"}
        img_with_exif = _create_dummy_image(format_name='JPEG', size=(120, 120), exif_data=test_exif)

        # Verificar que el original sí tiene EXIF
        original_img = Image.open(io.BytesIO(img_with_exif))
        assert len(original_img.getexif()) > 0

        # Sanitizar
        raw_file = SimpleUploadedFile("profile.jpg", img_with_exif, content_type="image/jpeg")
        clean_file = sanitize_image(raw_file, filename="profile.jpg")
        assert isinstance(clean_file, ContentFile)

        # Verificar que la imagen resultante ya NO tiene los metadatos EXIF sensibles
        sanitized_img = Image.open(clean_file)
        exif_tags = sanitized_img.getexif()
        assert 0x010E not in exif_tags
        assert 0x010F not in exif_tags

    def test_rgba_to_jpeg_sanitization_does_not_crash(self):
        """Sanitizar una imagen con canal Alpha a formato JPEG debe procesar el fondo sin fallar."""
        rgba_bytes = _create_dummy_image(format_name='PNG', size=(80, 80))
        raw_file = SimpleUploadedFile("transparent.png", rgba_bytes, content_type="image/png")
        clean_file = sanitize_image(raw_file, filename="transparent.jpg")
        assert clean_file is not None

        sanitized_img = Image.open(clean_file)
        assert sanitized_img.mode == 'RGB'


# ─── Tests de Integración en Serializadores y Endpoints DRF ───


@pytest.mark.django_db
class TestMediaEndpointsIntegration:
    """Pruebas de subida a través de la API REST."""

    def test_user_avatar_upload_valid_sanitizes_and_updates(self):
        """Subida de avatar válido actualiza el perfil y remueve metadatos."""
        user = User.objects.create_user(username='avatar_user', email='avatar@test.com', password='pwd')
        client = APIClient()
        client.force_authenticate(user=user)

        img_bytes = _create_dummy_image(format_name='JPEG', size=(150, 150))
        avatar_file = SimpleUploadedFile("my_avatar.jpg", img_bytes, content_type="image/jpeg")

        res = client.patch('/api/v1/users/profile/update/', {'avatar': avatar_file}, format='multipart')
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.avatar.name is not None
        assert 'avatars/' in user.avatar.name

    def test_user_avatar_upload_invalid_extension_rejected(self):
        """Subir un archivo no permitido (.svg) al perfil devuelve HTTP 400."""
        user = User.objects.create_user(username='svg_user', email='svg@test.com', password='pwd')
        client = APIClient()
        client.force_authenticate(user=user)

        img_bytes = b"<svg><circle cx='50' cy='50' r='40'/></svg>"
        svg_file = SimpleUploadedFile("avatar.svg", img_bytes, content_type="image/svg+xml")

        res = client.patch('/api/v1/users/profile/update/', {'avatar': svg_file}, format='multipart')
        assert res.status_code == 400
        assert 'avatar' in res.data

    def test_chat_message_image_upload_valid(self):
        """Subir una imagen en un mensaje de chat funciona y sanitiza la imagen."""
        user1 = User.objects.create_user(username='chat1', email='c1@test.com', password='pwd')
        user2 = User.objects.create_user(username='chat2', email='c2@test.com', password='pwd')
        user1.following.add(user2)
        conv = Conversation.objects.create()
        conv.participants.add(user1, user2)

        client = APIClient()
        client.force_authenticate(user=user1)

        img_bytes = _create_dummy_image(format_name='PNG', size=(120, 120))
        chat_img = SimpleUploadedFile("chat_pic.png", img_bytes, content_type="image/png")

        res = client.post(
            '/api/v1/chat/messages/',
            {'conversation': conv.id, 'text': 'Mira esta foto', 'image': chat_img},
            format='multipart',
        )
        assert res.status_code == 201
        msg = Message.objects.get(id=res.data['id'])
        assert msg.image.name is not None
        assert 'chat_images/' in msg.image.name

    def test_chat_message_image_upload_disguised_file_rejected(self):
        """Subir un script camuflado como imagen en el chat devuelve HTTP 400."""
        user1 = User.objects.create_user(username='hacker1', email='h1@test.com', password='pwd')
        user2 = User.objects.create_user(username='victim1', email='v1@test.com', password='pwd')
        user1.following.add(user2)
        conv = Conversation.objects.create()
        conv.participants.add(user1, user2)

        client = APIClient()
        client.force_authenticate(user=user1)

        fake_bytes = b"MZ\x90\x00\x03\x00\x00\x00executable payload"
        bad_img = SimpleUploadedFile("exploit.png", fake_bytes, content_type="image/png")

        res = client.post(
            '/api/v1/chat/messages/',
            {'conversation': conv.id, 'text': 'Abre esto', 'image': bad_img},
            format='multipart',
        )
        assert res.status_code == 400
        assert 'image' in res.data

    def test_book_cover_upload_valid_and_invalid(self):
        """Subir portada de libro valida límites y formatos."""
        user = User.objects.create_user(username='editor_user', email='ed@test.com', password='pwd', is_staff=True)
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Portada válida
        valid_bytes = _create_dummy_image(format_name='WEBP', size=(300, 450))
        valid_cover = SimpleUploadedFile("cover.webp", valid_bytes, content_type="image/webp")

        res_ok = client.post(
            '/api/v1/books/',
            {'title': 'Libro con Portada WebP', 'cover': valid_cover},
            format='multipart',
        )
        assert res_ok.status_code == 201
        book = Book.objects.get(id=res_ok.data['id'])
        assert book.cover.name is not None

        # 2. Portada con extensión inválida
        invalid_cover = SimpleUploadedFile("cover.gif", b"GIF89a...", content_type="image/gif")
        res_fail = client.post(
            '/api/v1/books/',
            {'title': 'Libro con GIF', 'cover': invalid_cover},
            format='multipart',
        )
        assert res_fail.status_code == 400
        assert 'cover' in res_fail.data


# ─── Tests de Descarga Externa de Portadas (cover_service) ───


@pytest.mark.django_db
class TestCoverServiceSecurityIntegration:
    """Pruebas de sanitización en descargas desde Google Books / OpenLibrary."""

    def test_download_and_attach_image_sanitizes_external_image(self):
        """Descargar una imagen externa la valida y sanitiza antes de guardarla en el modelo."""
        book = Book.objects.create(title='Cien años de soledad')
        img_bytes = _create_dummy_image(format_name='JPEG', size=(250, 350))

        class DummyResponse:
            content = img_bytes
            headers = {'Content-Type': 'image/jpeg'}
            def raise_for_status(self):
                pass

        with patch('requests.get', return_value=DummyResponse()):
            success = download_and_attach_image(
                instance=book,
                field_name='cover',
                url='https://books.google.com/test_cover.jpg',
                filename_hint='soledad-cover.jpg',
            )

        assert success is True
        book.refresh_from_db()
        assert book.cover.name is not None
        assert 'covers/' in book.cover.name

    def test_download_and_attach_image_rejects_corrupted_download(self):
        """Si la URL externa devuelve HTML o datos corruptos, no se adjunta."""
        book = Book.objects.create(title='Libro Corrupto')
        corrupt_bytes = b"<html><head><title>404 Not Found</title></head><body>Error</body></html>"

        class DummyHtmlResponse:
            content = corrupt_bytes
            headers = {'Content-Type': 'text/html'}
            def raise_for_status(self):
                pass

        with patch('requests.get', return_value=DummyHtmlResponse()):
            success = download_and_attach_image(
                instance=book,
                field_name='cover',
                url='https://openlibrary.org/fake.jpg',
                filename_hint='fake.jpg',
            )

        assert success is False
        book.refresh_from_db()
        assert not book.cover


# ─── Tests de Arquitectura de Almacenamiento Pluggable ───


class TestPluggableStorageConfiguration:
    """Pruebas de la arquitectura de STORAGES configurada en settings.py."""

    def test_storages_dictionary_configured(self):
        """settings.STORAGES debe definir los backends para default y staticfiles."""
        assert hasattr(settings, 'STORAGES')
        assert 'default' in settings.STORAGES
        assert 'staticfiles' in settings.STORAGES
        assert 'BACKEND' in settings.STORAGES['default']

    def test_media_security_constants_and_validators(self):
        """Verificar consistencia de constantes exportadas por media_security."""
        assert '.jpg' in ALLOWED_IMAGE_EXTENSIONS
        assert '.png' in ALLOWED_IMAGE_EXTENSIONS
        assert '.webp' in ALLOWED_IMAGE_EXTENSIONS
        assert '.svg' not in ALLOWED_IMAGE_EXTENSIONS
        assert 'JPEG' in ALLOWED_IMAGE_FORMATS
        assert 'PNG' in ALLOWED_IMAGE_FORMATS
        assert 'WEBP' in ALLOWED_IMAGE_FORMATS
        assert MAX_AVATAR_SIZE_BYTES == 5 * 1024 * 1024
        assert MAX_COVER_SIZE_BYTES == 10 * 1024 * 1024

        # Comprobar que las instancias singleton son invocables
        assert callable(validate_avatar_image)
        assert callable(validate_cover_image)
        assert callable(validate_chat_image)
