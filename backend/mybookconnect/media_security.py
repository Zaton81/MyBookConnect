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

import hashlib
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

# Tipos MIME permitidos (incluyendo variantes históricas de navegadores)
ALLOWED_MIME_TYPES: Tuple[str, ...] = (
    'image/jpeg',
    'image/pjpeg',
    'image/png',
    'image/x-png',
    'image/webp',
)

# Mapeo MIME a Formato Pillow
MIME_TO_FORMAT_MAP = {
    'image/jpeg': 'JPEG',
    'image/pjpeg': 'JPEG',
    'image/png': 'PNG',
    'image/x-png': 'PNG',
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
        # Si el cliente envía application/octet-stream genérico, no rechazar de inmediato:
        # la comprobación obligatoria de firmas binarias (magic bytes) y Pillow subsiguiente
        # determinará con certeza matemática si el payload es una imagen válida.
        if declared_mime not in ALLOWED_MIME_TYPES and declared_mime != 'application/octet-stream':
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
        if declared_mime and declared_mime in MIME_TO_FORMAT_MAP:
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
    output_format: str | None = 'WEBP',
    strip_exif: bool = True,
    quality: int = 82,
    max_dimensions: Tuple[int, int] | None = None,
) -> ContentFile:
    """
    Sanitiza una imagen abriéndola en Pillow, eliminando metadatos EXIF/IPTC/XMP/comentarios,
    redimensionando según max_dimensions preservando el aspect ratio (Fase 60), y re-codificándola
    de forma segura por defecto en formato WebP optimizado con hash SHA-256.

    :param file_or_bytes: Objeto UploadedFile, ContentFile o bytes de la imagen.
    :param filename: Nombre sugerido para el archivo resultante.
    :param output_format: Formato deseado ('WEBP', 'JPEG', 'PNG'). Por defecto: 'WEBP'.
    :param strip_exif: Si es True, no se preserva ningún metadato.
    :param quality: Calidad de compresión para WebP o JPEG (1-100). Por defecto: 82.
    :param max_dimensions: Tupla opcional (max_w, max_h) para aplicar redimensionamiento/downscale.
    :return: ContentFile sanitizado con atributo `.content_hash` y nombre `{hash}.webp`.
    """
    orig_name = filename or getattr(file_or_bytes, 'name', 'image.webp') or 'image.webp'

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

        fmt = (output_format or 'WEBP').upper()
        if fmt not in ALLOWED_IMAGE_FORMATS:
            fmt = 'WEBP'

        if fmt == 'WEBP':
            target_ext = '.webp'
            if img.mode in ('CMYK', 'YCbCr'):
                img = img.convert('RGB')
            elif img.mode == 'P':
                img = img.convert('RGBA') if 'transparency' in img.info else img.convert('RGB')
        elif fmt == 'JPEG':
            target_ext = '.jpg'
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
        elif fmt == 'PNG':
            target_ext = '.png'
            if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                img = img.convert('RGBA')
        else:
            fmt = 'WEBP'
            target_ext = '.webp'

        output_buffer = io.BytesIO()
        save_kwargs = {'format': fmt}

        if fmt in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True
            if fmt == 'WEBP':
                save_kwargs['method'] = 4
        elif fmt == 'PNG':
            save_kwargs['optimize'] = True

        img.save(output_buffer, **save_kwargs)
        sanitized_bytes = output_buffer.getvalue()

        # Cálculo de hash criptográfico SHA-256 para nombramiento determinista
        content_hash = hashlib.sha256(sanitized_bytes).hexdigest()
        clean_name = f"{content_hash}{target_ext}"

        result_file = ContentFile(sanitized_bytes, name=clean_name)
        result_file.content_hash = content_hash
        return result_file

    except Exception as exc:
        logger.error(f"Fallo al sanitizar imagen {orig_name}: {exc}")
        raise ValidationError(f"No se pudo sanitizar el archivo de imagen: {exc}") from exc
    finally:
        if hasattr(file_or_bytes, 'seek'):
            try:
                file_or_bytes.seek(0)
            except Exception:
                pass


def sanitize_and_prepare_image(
    file_or_bytes,
    preset: Tuple[int, int] | None = None,
    filename: str | None = None,
    output_format: str = 'WEBP',
    quality: int = 82,
) -> ContentFile:
    """Helper unificado para sanitizar, redimensionar según preset y codificar en WebP optimizado."""
    return sanitize_image(
        file_or_bytes,
        filename=filename,
        output_format=output_format,
        quality=quality,
        max_dimensions=preset,
    )


@deconstructible
class UploadToHashedPath:
    """
    Callable serializable para ImageField/FileField `upload_to`.
    Calcula el hash SHA-256 del contenido binario para ubicar el archivo en una estructura
    jerárquica con sharding de dos niveles:
        {subfolder}/{hash[:2]}/{hash}.webp

    Beneficios arquitectónicos:
    - Previene saturación del sistema de archivos al no acumular miles de ficheros en un solo directorio.
    - Facilita indexación y caching O(1) en Cloudflare R2 / AWS S3.
    - Garantiza unicidad e inmutabilidad criptográfica, permitiendo deduplicación total.
    """

    def __init__(self, subfolder: str):
        self.subfolder = subfolder.strip('/')

    def __call__(self, instance, filename: str) -> str:
        clean_base, ext = os.path.splitext(os.path.basename(filename))
        clean_ext = ext.lower() if ext.lower() in ('.webp', '.jpg', '.jpeg', '.png') else '.webp'

        computed_hash = None

        # 1. Comprobar si el archivo adjunto al modelo tiene hash o bytes legibles
        for attr_name in ('cover', 'photo', 'avatar', 'image', 'file', 'cover_image', 'logo'):
            field_file = getattr(instance, attr_name, None)
            if field_file:
                # Comprobar atributo .content_hash adjuntado por sanitize_image
                if hasattr(field_file, 'content_hash') and field_file.content_hash:
                    computed_hash = field_file.content_hash
                    break
                # Comprobar inner file si está abierto
                inner_file = getattr(field_file, 'file', None)
                if inner_file and hasattr(inner_file, 'content_hash') and inner_file.content_hash:
                    computed_hash = inner_file.content_hash
                    break
                if inner_file and hasattr(inner_file, 'read'):
                    try:
                        pos = inner_file.tell() if hasattr(inner_file, 'tell') else 0
                        if hasattr(inner_file, 'seek'):
                            inner_file.seek(0)
                        hasher = hashlib.sha256()
                        while chunk := inner_file.read(65536):
                            hasher.update(chunk)
                        if hasattr(inner_file, 'seek'):
                            inner_file.seek(pos)
                        computed_hash = hasher.hexdigest()
                        break
                    except Exception:
                        pass

        # 2. Si el propio filename recibido ya es un hash hexadecimal SHA-256 (64 caracteres)
        if not computed_hash:
            if len(clean_base) == 64 and all(c in '0123456789abcdefABCDEF' for c in clean_base):
                computed_hash = clean_base.lower()

        # 3. Fallback determinista
        if not computed_hash:
            computed_hash = hashlib.sha256(f"{filename}-{getattr(instance, 'pk', '')}".encode('utf-8')).hexdigest()

        return f"{self.subfolder}/{computed_hash[:2]}/{computed_hash}{clean_ext}"

    def __eq__(self, other):
        return isinstance(other, UploadToHashedPath) and self.subfolder == other.subfolder


# Instancias singleton reutilizables para modelos
upload_to_covers = UploadToHashedPath('covers')
upload_to_author_photos = UploadToHashedPath('author_photos')
upload_to_avatars = UploadToHashedPath('avatars')
upload_to_chat_images = UploadToHashedPath('chat_images')
upload_to_reviews = UploadToHashedPath('reviews')


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
