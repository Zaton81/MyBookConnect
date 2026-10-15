"""
Módulo de almacenamiento (Storage) con soporte de deduplicación criptográfica.

Proporciona implementaciones para:
1. `DeduplicatedFileSystemStorage`: Para desarrollo local y entornos sin bucket de objetos.
2. `DeduplicatedS3Storage`: Para AWS S3, Cloudflare R2 y MinIO en entornos cloud y producción.

Ambos backends implementan almacenamiento direccionable por contenido (CAS):
Si un archivo con la misma ruta/hash ya existe, reutilizan el recurso existente en O(1),
impidiendo la creación de archivos redundantes y sufijos de colisión aleatorios (_XYZ123).
"""

import logging

from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)


class DeduplicatedFileSystemStorage(FileSystemStorage):
    """
    Storage de disco local con deduplicación criptográfica.
    Si el archivo destino ya existe en el sistema de archivos, reutiliza la ruta existente.
    """

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            return name
        return super().get_available_name(name, max_length=max_length)

    def _save(self, name, content):
        if self.exists(name):
            logger.debug(f"[Deduplication Storage] Archivo existente detectado: {name}. Reutilizando sin reescribir.")
            return name
        return super()._save(name, content)


try:
    from storages.backends.s3boto3 import S3Boto3Storage

    class DeduplicatedS3Storage(S3Boto3Storage):
        """
        Storage compatible con AWS S3 / Cloudflare R2 con deduplicación criptográfica.
        Si la clave ya existe en el bucket de destino, evita transferencias de red superfluas.
        """

        def get_available_name(self, name, max_length=None):
            if self.exists(name):
                return name
            return super().get_available_name(name, max_length=max_length)

        def _save(self, name, content):
            if self.exists(name):
                logger.debug(f"[Deduplication S3] Objeto existente en bucket: {name}. Reutilizando sin reescribir.")
                return name
            return super()._save(name, content)

except ImportError:
    class DeduplicatedS3Storage:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "django-storages[s3] y boto3 son requeridos para usar DeduplicatedS3Storage. "
                "Instálelos mediante 'pip install django-storages[s3] boto3'."
            )
