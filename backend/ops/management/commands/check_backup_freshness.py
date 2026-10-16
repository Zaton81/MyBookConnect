import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class Command(BaseCommand):
    help = "Verifica la frescura e integridad criptográfica del último backup para garantizar el cumplimiento del RPO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-age-hours",
            type=int,
            default=24,
            help="Edad máxima permitida en horas para el último backup válido (por defecto 24 horas, correspondiente al RPO).",
        )
        parser.add_argument(
            "--subsystems",
            type=str,
            default="db,media,config",
            help="Subsistemas a verificar separados por coma (db, media, config).",
        )
        parser.add_argument(
            "--backup-root",
            type=str,
            default=None,
            help="Ruta raíz personalizada para los directorios de backup (por defecto: BASE_DIR/backups).",
        )
        parser.add_argument(
            "--skip-checksum",
            action="store_true",
            help="Omite el cálculo del checksum SHA-256 (solo valida presencia y fecha).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Genera salida estructurada en formato JSON.",
        )

    def handle(self, *args, **options):
        max_age_hours = options.get("max_age_hours", 24)
        subsystems_to_check = [s.strip().lower() for s in options.get("subsystems", "db").split(",") if s.strip()]
        skip_checksum = options.get("skip_checksum", False)
        is_json = options.get("json", False)

        backup_root = Path(options["backup_root"]) if options["backup_root"] else settings.BASE_DIR / "backups"
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        subsystem_dirs = {
            "db": (backup_root / "db", ["db_backup_*.sql.gz*", "db_backup_*.json.gz*"]),
            "media": (backup_root / "media", ["media_backup_*.tar.gz*"]),
            "config": (backup_root / "config", ["config_backup_*.tar.gz*"]),
        }

        report = {
            "status": "PASS",
            "rpo_max_age_hours": max_age_hours,
            "cutoff_timestamp": cutoff_time.isoformat(),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "subsystems": {},
            "errors": [],
        }

        for sub in subsystems_to_check:
            if sub not in subsystem_dirs:
                continue

            target_dir, patterns = subsystem_dirs[sub]
            sub_report = {
                "directory": str(target_dir),
                "latest_file": None,
                "latest_mtime": None,
                "age_hours": None,
                "fresh": False,
                "checksum_verified": None,
                "status": "MISSING",
            }

            if not target_dir.exists():
                report["errors"].append(f"El directorio de backups del subsistema '{sub}' no existe: {target_dir}")
                report["subsystems"][sub] = sub_report
                continue

            # Encontrar candidatos excluyendo manifiestos
            candidate_files = []
            for pat in patterns:
                candidate_files.extend([
                    f for f in target_dir.glob(pat)
                    if f.is_file() and not f.name.endswith(".manifest.json")
                ])

            if not candidate_files:
                report["errors"].append(f"No se encontraron archivos de backup para el subsistema '{sub}'.")
                report["subsystems"][sub] = sub_report
                continue

            # Ordenar por fecha de modificación descendente
            candidate_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest = candidate_files[0]
            mtime = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc)
            age = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600.0

            sub_report["latest_file"] = latest.name
            sub_report["latest_mtime"] = mtime.isoformat()
            sub_report["age_hours"] = round(age, 2)

            # Comprobar frescura respecto a RPO
            if age > max_age_hours:
                sub_report["fresh"] = False
                sub_report["status"] = "STALE"
                report["errors"].append(
                    f"Backup de '{sub}' ({latest.name}) es obsoleto: tiene {round(age, 1)}h (máximo permitido: {max_age_hours}h)."
                )
            else:
                sub_report["fresh"] = True
                sub_report["status"] = "OK"

            # Comprobar integridad con manifest si existe y no se omitió
            if not skip_checksum:
                manifest_file = latest.with_name(f"{latest.name}.manifest.json")
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as mf:
                            meta = json.load(mf)
                        expected_hash = meta.get("sha256")
                        actual_hash = compute_file_sha256(latest)
                        if expected_hash == actual_hash:
                            sub_report["checksum_verified"] = True
                        else:
                            sub_report["checksum_verified"] = False
                            sub_report["status"] = "CORRUPTED"
                            report["errors"].append(
                                f"Discrepancia en checksum SHA-256 de '{sub}' ({latest.name}). Esperado: {expected_hash}, Actual: {actual_hash}."
                            )
                    except Exception as err:
                        sub_report["checksum_verified"] = False
                        report["errors"].append(f"Fallo al leer o validar manifest de '{sub}': {err}")
                else:
                    sub_report["checksum_verified"] = None  # Sin manifest disponible

            report["subsystems"][sub] = sub_report

        if report["errors"]:
            report["status"] = "FAIL"

        if is_json:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self.stdout.write("==============================================================================")
            self.stdout.write("AUDITORÍA DE FRESCURA E INTEGRIDAD DE BACKUPS (RPO MONITOR)")
            self.stdout.write("==============================================================================")
            self.stdout.write(f"Estado global: {'CORRECTO' if report['status'] == 'PASS' else 'ALERTA RPO / CORRUPCIÓN'}")
            self.stdout.write(f"RPO objetivo: <= {max_age_hours} horas")
            for sub, meta in report["subsystems"].items():
                self.stdout.write(
                    f"  [{sub.upper()}] Archivo: {meta.get('latest_file') or 'N/A'} | "
                    f"Edad: {meta.get('age_hours')}h | Estado: {meta.get('status')}"
                )

            if report["errors"]:
                self.stdout.write("\nERRORES / VIOLACIONES DE RPO:")
                for err in report["errors"]:
                    self.stdout.write(self.style.ERROR(f"  [X] {err}"))
            self.stdout.write("==============================================================================")

        if report["status"] == "FAIL":
            raise SystemExit(1)
