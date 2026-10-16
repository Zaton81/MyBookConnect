import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from books.services.backup_service import DatabaseBackupService


class Command(BaseCommand):
    help = "Restaura la base de datos a partir de un archivo de backup verificando previamente su integridad SHA-256."

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            type=str,
            help="Ruta al archivo de backup a restaurar (.sql.gz o .json.gz).",
        )
        parser.add_argument(
            "--no-verify",
            action="store_true",
            help="Omite la verificación de integridad criptográfica SHA-256 (no recomendado).",
        )

    def handle(self, *args, **options):
        backup_file = Path(options["backup_file"])
        verify_checksum = not options.get("no_verify", False)

        if not backup_file.exists():
            raise CommandError(f"El archivo especificado no existe: {backup_file}")

        self.stdout.write(self.style.WARNING(f"Iniciando restauración de base de datos desde {backup_file}..."))
        try:
            result = DatabaseBackupService.restore_database(
                backup_file=backup_file,
                verify_checksum=verify_checksum,
            )
            self.stdout.write(self.style.SUCCESS(f"¡Restauración de base de datos completada!\n{json.dumps(result, indent=2)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al restaurar la base de datos: {e}"))
            raise e
