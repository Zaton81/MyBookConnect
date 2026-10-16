import json
from pathlib import Path

from django.core.management.base import BaseCommand

from books.services.backup_service import DatabaseBackupService


class Command(BaseCommand):
    help = "Genera un backup completo de la base de datos PostgreSQL con firma SHA-256 y retención."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Directorio de destino para guardar el backup (por defecto: backups/db/).",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=None,
            help="Días de retención para purgar backups antiguos (por defecto: 7 o BACKUP_RETENTION_DAYS).",
        )
        parser.add_argument(
            "--force-django-dump",
            action="store_true",
            help="Fuerza el uso de dumpdata en lugar del binario pg_dump.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]) if options["output_dir"] else None
        retention_days = options.get("retention_days")
        force_django = options.get("force_django_dump", False)

        self.stdout.write(self.style.NOTICE("Iniciando proceso de backup de base de datos..."))
        try:
            result = DatabaseBackupService.backup_database(
                output_dir=output_dir,
                retention_days=retention_days,
                force_django_dump=force_django,
            )
            self.stdout.write(self.style.SUCCESS(f"¡Backup generado exitosamente!\n{json.dumps(result, indent=2)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al generar el backup de base de datos: {e}"))
            raise e
