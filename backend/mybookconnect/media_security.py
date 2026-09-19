"""
Módulo centralizado de seguridad, validación y sanitización de archivos multimedia.

Este módulo implementa las directrices de la Fase 28 del Roadmap:
- Validación rigurosa de formato MIME y tipo binario real (vía Pillow) para evitar
  archivos camuflados (polyglots, scripts o ejecutables renombrados a .jpg/.png).
- Restricción estricta de extensiones permitidas (.jpg, .jpeg, .png, .webp),
  rechazando explícitamente formatos con vector de ataque XSS como SVG.
- Control estricto de cuotas en bytes (avatars y autores <= 5MB; portadas y chat <= 10MB).
- Control de resolución mínima (50x50 px) para evitar imágenes corruptas o píxeles invisibles,
  y resolución máxima (6000x6000 px) para prevenir ataques de descompresión (decompression bombs / DoS).
- Sanitización activa eliminando metadatos EXIF (coordenadas GPS, identificación de dispositivos)
  para proteger la privacidad de los usuarios y eliminar posibles payloads incrustados.
"""

import io
import logging
import os
from typing import Tuple

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Extensiones de archivo permitidas (en minúsculas)
ALLOWED_IMAGE_EXTENSIONS: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.webp')

# Formatos binarios reconocidos por Pillow permitidos
ALLOWED_IMAGE_FORMATS: Tuple[str, ...] = ('JPEG', 'PNG', 'WEBP')

# Tipos MIME permitidos
ALLOWED_MIME_TYPES: Tuple[str, ...] = ('image/jpeg', 'image/png', 'image/webp')

# Mapeo MIME a Formato Pillow
MIME_TO_FORMAT_MAP = {
    'image/jpeg': 'JPEG',
    'image/pjpeg': 'JPEG',
    'image/png': 'PNG',
    'image/webp': 'WEBP',
}

# Límites de tamaño en bytes
MAX_AVATAR_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_AUTHOR_PHOTO_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_COVER_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
MAX_CHAT_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

# Límites de dimensiones en píxeles (ancho, alto)
MIN_IMAGE_DIMENSIONS: Tuple[int, int] = (50, 50)
MAX_IMAGE_DIMENSIONS: Tuple[int, int] = (6000, 6000)

# Presets de dimensiones de destino para redimensionamiento optimizado (Fase 60)
AVATAR_PRESET: Tuple[int, int] = (512, 512)
AUTHOR_PHOTO_PRESET: Tuple[int, int] = (800, 1200)
COVER_PRESET: Tuple[int, int] = (1200, 1800)
CHAT_IMAGE_PRESET: Tuple[int, int] = (1920, 1920)


def detect_magic_format(file_obj) -> str | None:
    """
    Inspecciona los primeros bytes del archivo para identificar su firma binaria (Magic Bytes).
    Soporta firmas estándar para JPEG, PNG y WebP.
    """
    if not file_obj:
        return None
    current_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
    try:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        header = file_obj.read(16) if hasattr(file_obj, 'read') else b""
        if header.startswith(b"\xff\xd8\xff"):
            return "JPEG"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "PNG"
        if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "WEBP"
        return None
    finally:
        if hasattr(file_obj, 'seek'):
            try:
                file_obj.seek(current_pos)
            except Exception:
                pass


def validate_image_file(
    file_obj,
    max_size_bytes: int,
    min_dims: Tuple[int, int] = MIN_IMAGE_DIMENSIONS,
    max_dims: Tuple[int, int] = MAX_IMAGE_DIMENSIONS,
    allowed_formats: Tuple[str, ...] = ALLOWED_IMAGE_FORMATS,
    allowed_extensions: Tuple[str, ...] = ALLOWED_IMAGE_EXTENSIONS,
) -> None:
    """
    Valida un archivo de imagen asegurando extensión, tamaño, formato binario e integridad.
    Implementa validación estricta de MIME, firmas Magic Bytes e inspección antivirus (Fase 60).
    """
    if not file_obj:
        return

    # 1. Validación de tamaño en bytes
    file_size = getattr(file_obj, 'size', None)
    if file_size is None:
        try:
            pos = file_obj.tell()
            file_obj.seek(0, os.SEEK_END)
            file_size = file_obj.tell()
            file_obj.seek(pos)
        except Exception:
            file_size = 0

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        current_mb = round(file_size / (1024 * 1024), 2)
        raise ValidationError(
            f"El archivo excede el tamaño máximo permitido de {max_mb:.0f} MB (tamaño actual: {current_mb} MB)."
        )

    # 2. Validación de extensión declarada en el nombre
    file_name = getattr(file_obj, 'name', '') or ''
    _, ext = os.path.splitext(file_name.lower())
    if ext:
        if ext not in allowed_extensions:
            raise ValidationError(
                f"Extensión '{ext}' no permitida. Formatos válidos: {', '.join(allowed_extensions)}."
            )

    # 3. Validación de tipo MIME declarado en HTTP request
    declared_mime = getattr(file_obj, 'content_type', None)
    if declared_mime:
        declared_mime = declared_mime.lower().strip()
        if declared_mime not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Tipo MIME '{declared_mime}' no permitido. Formatos aceptados: {', '.join(ALLOWED_MIME_TYPES)}."
            )

    # 4. Inspección de seguridad y antivirus (Fase 60)
    from mybookconnect.media_scanner import scan_media_file
    scan_media_file(file_obj)

    # 5. Validación de firma binaria (Magic Bytes)
    magic_fmt = detect_magic_format(file_obj)
    if not magic_fmt or magic_fmt not in allowed_formats:
        raise ValidationError(
            "El archivo no es una imagen válida: firma binaria (magic bytes) inválida o no coincide con un formato permitido."
        )

    # 6. Validación de contenido binario mediante Pillow
    try:
        current_pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

        img = Image.open(file_obj)

        detected_format = img.format
        if not detected_format or detected_format.upper() not in allowed_formats:
            raise ValidationError(
                f"Formato de imagen '{detected_format}' no permitido. Formatos aceptados: {', '.join(allowed_formats)}."
            )

        # Comprobar consistencia estricta entre Magic Bytes y Pillow
        if magic_fmt != detected_format.upper():
            raise ValidationError(
                f"Discrepancia entre firma binaria ('{magic_fmt}') y formato detectado ('{detected_format}')."
            )

        # Comprobar concordancia entre MIME declarado y formato binario real
        if declared_mime:
            expected_format = MIME_TO_FORMAT_MAP.get(declared_mime)
            if expected_format and expected_format != detected_format.upper():
                raise ValidationError(
                    f"Discrepancia entre tipo MIME declarado ('{declared_mime}') y formato binario real ('{detected_format}')."
                )

        # Verificar dimensiones
        width, height = img.size
        min_w, min_h = min_dims
        max_w, max_h = max_dims

        if width < min_w or height < min_h:
            raise ValidationError(
                f"Las dimensiones ({width}x{height} px) son inferiores al mínimo requerido ({min_w}x{min_h} px)."
            )

        if width > max_w or height > max_h:
            raise ValidationError(
                f"Las dimensiones ({width}x{height} px) exceden el límite máximo permitido ({max_w}x{max_h} px)."
            )

        # Verificar integridad estructural del archivo
        img.verify()

        if hasattr(file_obj, 'seek'):
            file_obj.seek(current_pos)

    except UnidentifiedImageError as err:
        raise ValidationError("El archivo no es una imagen válida o contiene datos corruptos.") from err
    except Image.DecompressionBombError as err:
        raise ValidationError("La imagen es excesivamente grande o contiene una bomba de descompresión.") from err
    except ValidationError:
        raise
    except Exception as exc:
        logger.warning(f"Error durante validación de imagen: {exc}")
        raise ValidationError(f"Error procesando la imagen: {str(exc)}") from exc
    finally:
        if hasattr(file_obj, 'seek'):
            try:
                file_obj.seek(0)
            except Exception:
                pass


def sanitize_image(
    file_or_bytes,
    filename: str | None = None,
    output_format: str | None = None,
    strip_exif: bool = True,
    quality: int = 85,
    max_dimensions: Tuple[int, int] | None = None,
) -> ContentFile:
    """
    Sanitiza una imagen abriéndola en Pillow, eliminando metadatos EXIF/IPTC/XMP/comentarios,
    redimensionando si excede max_dimensions preservando el aspect ratio (Fase 60),
    y re-codificándola de forma segura en un buffer limpio.

    :param file_or_bytes: Objeto UploadedFile, ContentFile o bytes de la imagen.
    :param filename: Nombre sugerido para el archivo resultante.
    :param output_format: Formato deseado ('JPEG', 'PNG', 'WEBP').
    :param strip_exif: Si es True, no se preserva ningún metadato.
    :param quality: Calidad de compresión para formatos JPEG o WebP (1-100).
    :param max_dimensions: Tupla opcional (max_w, max_h) para aplicar redimensionamiento/downscale.
    :return: ContentFile sanitizado listo para asignar a un ImageField o FileField.
    """
    orig_name = filename or getattr(file_or_bytes, 'name', 'image.jpg') or 'image.jpg'
    base_name, ext = os.path.splitext(orig_name)
    ext_lower = ext.lower() if ext else '.jpg'

    if ext_lower not in ALLOWED_IMAGE_EXTENSIONS:
        ext_lower = '.jpg'

    if isinstance(file_or_bytes, (bytes, bytearray)):
        file_or_bytes = io.BytesIO(file_or_bytes)

    if hasattr(file_or_bytes, 'seek'):
        file_or_bytes.seek(0)

    try:
        img = Image.open(file_or_bytes)
        img.load()

        # Redimensionamiento inteligente conservando aspect ratio (Fase 60)
        if max_dimensions and (img.width > max_dimensions[0] or img.height > max_dimensions[1]):
            img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)

        # Eliminación exhaustiva de metadatos del diccionario info
        if strip_exif:
            for meta_key in ('exif', 'icc_profile', 'photoshop', 'xmp', 'comment', 'parameters', 'Software'):
                img.info.pop(meta_key, None)

        if output_format:
            fmt = output_format.upper()
        elif ext_lower in ('.jpg', '.jpeg'):
            fmt = 'JPEG'
        elif ext_lower == '.png':
            fmt = 'PNG'
        elif ext_lower == '.webp':
            fmt = 'WEBP'
        else:
            fmt = img.format or 'JPEG'

        if fmt.upper() not in ALLOWED_IMAGE_FORMATS:
            fmt = 'JPEG'
            ext_lower = '.jpg'

        if fmt.upper() == 'JPEG':
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

        output_buffer = io.BytesIO()
        save_kwargs = {'format': fmt}

        if fmt.upper() in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True
        elif fmt.upper() == 'PNG':
            save_kwargs['optimize'] = True

        img.save(output_buffer, **save_kwargs)
        sanitized_bytes = output_buffer.getvalue()

        clean_name = f"{base_name}{ext_lower}"
        return ContentFile(sanitized_bytes, name=clean_name)

    except Exception as exc:
        logger.error(f"Fallo al sanitizar imagen {orig_name}: {exc}")
        raise ValidationError(f"No se pudo sanitizar el archivo de imagen: {exc}") from exc
    finally:
        if hasattr(file_or_bytes, 'seek'):
            try:
                file_or_bytes.seek(0)
            except Exception:
                pass


@deconstructible
class BaseImageValidator:
    """Clase base serializable por las migraciones de Django para validación de ImageField."""

    def __init__(
        self,
        max_size_bytes: int,
        min_dims: Tuple[int, int] = MIN_IMAGE_DIMENSIONS,
        max_dims: Tuple[int, int] = MAX_IMAGE_DIMENSIONS,
        allowed_formats: Tuple[str, ...] = ALLOWED_IMAGE_FORMATS,
        allowed_extensions: Tuple[str, ...] = ALLOWED_IMAGE_EXTENSIONS,
    ):
        self.max_size_bytes = max_size_bytes
        self.min_dims = min_dims
        self.max_dims = max_dims
        self.allowed_formats = allowed_formats
        self.allowed_extensions = allowed_extensions

    def __call__(self, value):
        validate_image_file(
            file_obj=value,
            max_size_bytes=self.max_size_bytes,
            min_dims=self.min_dims,
            max_dims=self.max_dims,
            allowed_formats=self.allowed_formats,
            allowed_extensions=self.allowed_extensions,
        )

    def __eq__(self, other):
        return (
            isinstance(other, BaseImageValidator)
            and self.max_size_bytes == other.max_size_bytes
            and self.min_dims == other.min_dims
            and self.max_dims == other.max_dims
            and self.allowed_formats == other.allowed_formats
            and self.allowed_extensions == other.allowed_extensions
        )


@deconstructible
class AvatarImageValidator(BaseImageValidator):
    """Validador para fotos de perfil de usuario (Avatar <= 5MB)."""

    def __init__(self):
        super().__init__(max_size_bytes=MAX_AVATAR_SIZE_BYTES)


@deconstructible
class AuthorPhotoImageValidator(BaseImageValidator):
    """Validador para fotografías de autores (Foto <= 5MB)."""

    def __init__(self):
        super().__init__(max_size_bytes=MAX_AUTHOR_PHOTO_SIZE_BYTES)


@deconstructible
class CoverImageValidator(BaseImageValidator):
    """Validador para portadas de libros (Portada <= 10MB)."""

    def __init__(self):
        super().__init__(max_size_bytes=MAX_COVER_SIZE_BYTES)


@deconstructible
class ChatImageValidator(BaseImageValidator):
    """Validador para imágenes adjuntas en mensajes de chat (Chat <= 10MB)."""

    def __init__(self):
        super().__init__(max_size_bytes=MAX_CHAT_IMAGE_SIZE_BYTES)


# Instancias singleton utilizables directamente en los campos de modelos de Django
validate_avatar_image = AvatarImageValidator()
validate_author_photo = AuthorPhotoImageValidator()
validate_cover_image = CoverImageValidator()
validate_chat_image = ChatImageValidator()
