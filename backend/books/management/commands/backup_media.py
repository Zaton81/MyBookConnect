import json
from pathlib import Path

from django.core.management.base import BaseCommand

from books.services.backup_service import MediaBackupService


class Command(BaseCommand):
    help = "Empaqueta y respalda el directorio de medios (Media) con hashes individuales y retención."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Directorio de destino para el tarball de media (por defecto: backups/media/).",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=None,
            help="Días de retención para purgar copias de media antiguas.",
        )
        parser.add_argument(
            "--media-root",
            type=str,
            default=None,
            help="Directorio origen de archivos de media a respaldar (por defecto: settings.MEDIA_ROOT).",
        )
        parser.add_argument(
            "--s3-sync",
            action="store_true",
            help="Habilita la sincronización del tarball hacia almacenamiento de objetos S3/R2/MinIO.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]) if options["output_dir"] else None
        media_root = Path(options["media_root"]) if options.get("media_root") else None
        retention_days = options.get("retention_days")
        s3_sync = options.get("s3_sync", False)

        self.stdout.write(self.style.NOTICE("Iniciando proceso de backup de media..."))
        try:
            result = MediaBackupService.backup_media(
                output_dir=output_dir,
                retention_days=retention_days,
                media_root=media_root,
                s3_sync=s3_sync,
            )
            self.stdout.write(self.style.SUCCESS(f"¡Backup de media generado exitosamente!\n{json.dumps(result, indent=2)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al generar backup de media: {e}"))
            raise e
