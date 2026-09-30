import csv
import json
import secrets
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from beta.models import BetaInvitation


class Command(BaseCommand):
    help = "Genera un lote de invitaciones seguras para una cohorte específica de la beta cerrada."

    def add_arguments(self, parser):
        parser.add_argument(
            '--cohort',
            type=str,
            default='ALFA',
            help='Nombre o identificador de la cohorte (ej. ALFA, BETA1). Máx 12 caracteres.',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Número de códigos de invitación a generar en este lote (default: 20).',
        )
        parser.add_argument(
            '--max-uses',
            type=int,
            default=1,
            help='Número máximo de veces que cada código puede ser canjeado (default: 1).',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Días de validez antes de la fecha de expiración (default: 30).',
        )
        parser.add_argument(
            '--invited-email',
            type=str,
            default='',
            help='Correo electrónico asignado (opcional, aplicable si count=1).',
        )
        parser.add_argument(
            '--export-json',
            type=str,
            default='',
            help='Ruta de archivo para exportar los códigos generados en formato JSON.',
        )
        parser.add_argument(
            '--export-csv',
            type=str,
            default='',
            help='Ruta de archivo para exportar los códigos generados en formato CSV.',
        )

    def handle(self, *args, **options):
        cohort = options['cohort'].strip().upper()[:12]
        count = options['count']
        max_uses = options['max_uses']
        days = options['days']
        invited_email = options['invited_email'].strip()
        export_json_path = options['export_json']
        export_csv_path = options['export_csv']

        if count <= 0:
            raise CommandError("El parámetro --count debe ser mayor que cero.")

        if max_uses <= 0:
            raise CommandError("El parámetro --max-uses debe ser mayor que cero.")

        if days <= 0:
            raise CommandError("El parámetro --days debe ser mayor que cero.")

        expires_at = timezone.now() + timedelta(days=days)
        generated_invitations = []
        created_objects = []

        self.stdout.write(
            self.style.NOTICE(f"Generando lote de {count} invitaciones para cohorte '{cohort}' (expira en {days} días)...")
        )

        for _ in range(count):
            # Garantizar unicidad y longitud <= 32 caracteres
            while True:
                # cohort (máx 12) + '-' (1) + hex (12) = máx 25 caracteres <= 32
                token = secrets.token_hex(6).upper()
                code = f"{cohort}-{token}"
                if not BetaInvitation.objects.filter(code=code).exists() and not any(inv['code'] == code for inv in generated_invitations):
                    break

            inv_obj = BetaInvitation(
                code=code,
                invited_email=invited_email if count == 1 else '',
                max_uses=max_uses,
                uses_count=0,
                is_active=True,
                expires_at=expires_at,
            )
            created_objects.append(inv_obj)
            generated_invitations.append({
                'code': code,
                'cohort': cohort,
                'max_uses': max_uses,
                'expires_at': expires_at.isoformat(),
                'invited_email': inv_obj.invited_email,
            })

        # Persistir en base de datos en bloque
        BetaInvitation.objects.bulk_create(created_objects)

        self.stdout.write(
            self.style.SUCCESS(f"✔ Se han creado con éxito {len(created_objects)} invitaciones para la cohorte '{cohort}'.")
        )

        # Exportación opcional a JSON
        if export_json_path:
            p = Path(export_json_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(generated_invitations, indent=2), encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f"  -> Exportado JSON en: {export_json_path}"))

        # Exportación opcional a CSV
        if export_csv_path:
            p = Path(export_csv_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['code', 'cohort', 'max_uses', 'expires_at', 'invited_email'])
                writer.writeheader()
                writer.writerows(generated_invitations)
            self.stdout.write(self.style.SUCCESS(f"  -> Exportado CSV en: {export_csv_path}"))

        return json.dumps(generated_invitations)
