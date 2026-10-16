import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from books.services.backup_service import MediaBackupService


class Command(BaseCommand):
    help = "Restaura archivos multimedia a partir de un tarball .tar.gz verificando integridad archivo por archivo."

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            type=str,
            help="Ruta al archivo tar.gz de backup de media.",
        )
        parser.add_argument(
            "--target-dir",
            type=str,
            default=None,
            help="Directorio destino para extraer los archivos (por defecto: MEDIA_ROOT).",
        )
        parser.add_argument(
            "--no-verify",
            action="store_true",
            help="Omite la verificación criptográfica SHA-256.",
        )

    def handle(self, *args, **options):
        backup_file = Path(options["backup_file"])
        target_dir = Path(options["target_dir"]) if options["target_dir"] else None
        verify_checksum = not options.get("no_verify", False)

        if not backup_file.exists():
            raise CommandError(f"El archivo especificado no existe: {backup_file}")

        self.stdout.write(self.style.WARNING(f"Iniciando restauración de archivos multimedia desde {backup_file}..."))
        try:
            result = MediaBackupService.restore_media(
                backup_file=backup_file,
                target_dir=target_dir,
                verify_checksum=verify_checksum,
            )
            self.stdout.write(self.style.SUCCESS(f"¡Restauración de media completada exitosamente!\n{json.dumps(result, indent=2)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al restaurar media: {e}"))
            raise e
