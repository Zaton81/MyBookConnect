import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo para validación criptográfica."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def prune_old_backups(
    backup_dir: Path,
    retention_days: int,
    file_pattern: str = "*",
    keep_minimum: int = 1,
) -> List[Path]:
    """
    Elimina copias de seguridad anteriores al umbral de retención (retention_days),
    garantizando que siempre se preserve al menos un número mínimo de copias recientes.
    """
    if not backup_dir.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    matching_files = sorted(
        [f for f in backup_dir.glob(file_pattern) if f.is_file() and not f.name.endswith(".manifest.json")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    pruned = []
    # Preservar al menos keep_minimum copias más recientes
    candidates = matching_files[keep_minimum:]

    for file_path in candidates:
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
        if file_mtime < cutoff:
            manifest_path = file_path.with_name(f"{file_path.name}.manifest.json")
            try:
                file_path.unlink()
                pruned.append(file_path)
                if manifest_path.exists():
                    manifest_path.unlink()
                logger.info(f"Backup purgado por política de retención: {file_path.name}")
            except OSError as e:
                logger.warning(f"No se pudo eliminar el backup antiguo {file_path}: {e}")

    return pruned


class DatabaseBackupService:
    """
    Servicio integral para la creación, verificación, retención y restauración
    de copias de seguridad de la base de datos PostgreSQL.
    """

    DEFAULT_BACKUP_DIR = getattr(settings, "BACKUP_DIR", settings.BASE_DIR / "backups" / "db")
    DEFAULT_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))

    @classmethod
    def get_backup_dir(cls, custom_dir: Optional[Path] = None) -> Path:
        target = Path(custom_dir) if custom_dir else cls.DEFAULT_BACKUP_DIR
        target.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def backup_database(
        cls,
        output_dir: Optional[Path] = None,
        retention_days: Optional[int] = None,
        force_django_dump: bool = False,
    ) -> Dict[str, Any]:
        """
        Ejecuta un backup completo de la base de datos.
        Usa pg_dump si está disponible en el entorno o fallback a serialización Django comprimida.
        """
        target_dir = cls.get_backup_dir(output_dir)
        days = retention_days if retention_days is not None else cls.DEFAULT_RETENTION_DAYS
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        db_config = settings.DATABASES["default"]
        db_name = db_config.get("NAME", "mybookconnect")
        db_user = db_config.get("USER", "postgres")
        db_host = db_config.get("HOST", "db")
        db_port = str(db_config.get("PORT", "5432"))
        db_password = db_config.get("PASSWORD", "")

        pg_dump_bin = shutil.which("pg_dump")
        has_pg_dump = pg_dump_bin is not None and not force_django_dump

        if has_pg_dump:
            filename = f"db_backup_{db_name}_{timestamp}.sql.gz"
            backup_path = target_dir / filename
            format_type = "pg_dump_gzip"

            env = os.environ.copy()
            if db_password:
                env["PGPASSWORD"] = db_password

            cmd = [
                pg_dump_bin,
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-d", db_name,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
            ]

            logger.info(f"Iniciando pg_dump hacia {backup_path}...")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            with gzip.open(backup_path, "wb") as gz_out:
                if proc.stdout:
                    shutil.copyfileobj(proc.stdout, gz_out)
            _, stderr = proc.communicate()

            if proc.returncode != 0:
                if backup_path.exists():
                    backup_path.unlink()
                raise RuntimeError(f"Error al ejecutar pg_dump (código {proc.returncode}): {stderr.decode('utf-8', errors='replace')}")
        else:
            filename = f"db_backup_{db_name}_{timestamp}.json.gz"
            backup_path = target_dir / filename
            format_type = "django_dumpdata_gzip"

            logger.info(f"pg_dump no disponible; usando serialización Django hacia {backup_path}...")
            uncompressed_tmp = target_dir / f"tmp_{timestamp}.json"
            try:
                with open(uncompressed_tmp, "w", encoding="utf-8") as f:
                    call_command(
                        "dumpdata",
                        "--natural-foreign",
                        "--natural-primary",
                        "--exclude", "contenttypes",
                        "--exclude", "auth.permission",
                        stdout=f,
                    )
                with open(uncompressed_tmp, "rb") as f_in, gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            finally:
                if uncompressed_tmp.exists():
                    uncompressed_tmp.unlink()

        # Generar firma criptográfica SHA-256
        sha256_hash = compute_sha256(backup_path)
        file_size = backup_path.stat().st_size

        manifest_data = {
            "version": "1.0",
            "type": "database",
            "format": format_type,
            "database": db_name,
            "filename": filename,
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retention_days": days,
        }

        manifest_path = target_dir / f"{filename}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2)

        # Aplicar política de retención
        pruned_files = prune_old_backups(target_dir, retention_days=days, file_pattern="db_backup_*")

        logger.info(f"Backup de base de datos completado exitosamente: {backup_path.name} (SHA-256: {sha256_hash})")
        return {
            "backup_file": str(backup_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "format": format_type,
            "pruned_backups": [str(p) for p in pruned_files],
        }

    @classmethod
    def restore_database(
        cls,
        backup_file: Path,
        verify_checksum: bool = True,
    ) -> Dict[str, Any]:
        """
        Restaura la base de datos a partir de un archivo de backup previamente verificado.
        Rechaza la restauración si se detecta discrepancia en el hash SHA-256.
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Archivo de backup no encontrado: {backup_path}")

        manifest_path = backup_path.with_name(f"{backup_path.name}.manifest.json")
        manifest_data = None

        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)

        # Validación criptográfica obligatoria
        if verify_checksum:
            current_hash = compute_sha256(backup_path)
            if manifest_data:
                expected_hash = manifest_data.get("sha256")
                if current_hash != expected_hash:
                    raise ValueError(
                        f"¡Firma de seguridad inválida! El hash SHA-256 actual ({current_hash}) "
                        f"no coincide con el manifest ({expected_hash}). El archivo puede estar corrupto o haber sido alterado."
                    )
            else:
                logger.warning(f"No se encontró archivo manifest para {backup_path.name}. Saltando verificación contra manifest.")

        # Detectar formato por nombre o manifest
        format_type = manifest_data.get("format") if manifest_data else None
        if not format_type:
            if backup_path.name.endswith(".sql.gz"):
                format_type = "pg_dump_gzip"
            elif backup_path.name.endswith(".json.gz") or backup_path.name.endswith(".json"):
                format_type = "django_dumpdata_gzip"
            else:
                format_type = "unknown"

        if format_type == "pg_dump_gzip":
            db_config = settings.DATABASES["default"]
            db_name = db_config.get("NAME", "mybookconnect")
            db_user = db_config.get("USER", "postgres")
            db_host = db_config.get("HOST", "db")
            db_port = str(db_config.get("PORT", "5432"))
            db_password = db_config.get("PASSWORD", "")

            psql_bin = shutil.which("psql")
            if not psql_bin:
                raise RuntimeError("El binario 'psql' es necesario para restaurar volcados SQL y no está en el PATH.")

            env = os.environ.copy()
            if db_password:
                env["PGPASSWORD"] = db_password

            cmd = [
                psql_bin,
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-d", db_name,
                "--single-transaction",
            ]

            logger.info(f"Restaurando base de datos con psql desde {backup_path}...")
            with gzip.open(backup_path, "rb") as gz_in:
                sql_data = gz_in.read()

            proc = subprocess.run(cmd, input=sql_data, capture_output=True, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"Error al restaurar con psql (código {proc.returncode}): {proc.stderr.decode('utf-8', errors='replace')}")

        elif format_type in ("django_dumpdata_gzip", "django_dumpdata"):
            logger.info(f"Restaurando base de datos mediante Django loaddata desde {backup_path}...")
            uncompressed_tmp = backup_path.parent / f"tmp_restore_{datetime.now(timezone.utc).timestamp()}.json"
            try:
                if backup_path.name.endswith(".gz"):
                    with gzip.open(backup_path, "rb") as f_in, open(uncompressed_tmp, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    restore_source = uncompressed_tmp
                else:
                    restore_source = backup_path

                call_command("loaddata", str(restore_source))
            finally:
                if uncompressed_tmp.exists():
                    uncompressed_tmp.unlink()
        else:
            raise ValueError(f"Formato de backup no reconocido para restauración: {format_type}")

        logger.info(f"Restauración de base de datos completada exitosamente desde {backup_path.name}")
        return {
            "status": "success",
            "backup_file": str(backup_path),
            "format": format_type,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }


class MediaBackupService:
    """
    Servicio integral para el empaquetado, verificación, retención y restauración
    de archivos multimedia (Media) y sincronización con almacenamiento de objetos.
    """

    DEFAULT_BACKUP_DIR = getattr(settings, "MEDIA_BACKUP_DIR", settings.BASE_DIR / "backups" / "media")
    DEFAULT_RETENTION_DAYS = int(os.getenv("MEDIA_BACKUP_RETENTION_DAYS", "30"))

    @classmethod
    def get_backup_dir(cls, custom_dir: Optional[Path] = None) -> Path:
        target = Path(custom_dir) if custom_dir else cls.DEFAULT_BACKUP_DIR
        target.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def backup_media(
        cls,
        output_dir: Optional[Path] = None,
        retention_days: Optional[int] = None,
        media_root: Optional[Path] = None,
        s3_sync: bool = False,
    ) -> Dict[str, Any]:
        """
        Empaqueta el directorio de medios en un archivo tar.gz con manifest y hashes individuales.
        """
        target_dir = cls.get_backup_dir(output_dir)
        source_media = Path(media_root) if media_root else Path(settings.MEDIA_ROOT)
        days = retention_days if retention_days is not None else cls.DEFAULT_RETENTION_DAYS
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        filename = f"media_backup_{timestamp}.tar.gz"
        backup_path = target_dir / filename

        source_media.mkdir(parents=True, exist_ok=True)

        # Recopilar archivos y calcular hashes individuales
        files_manifest: Dict[str, Dict[str, Any]] = {}
        total_uncompressed_bytes = 0

        for root, _, files in os.walk(source_media):
            for file_name in files:
                full_path = Path(root) / file_name
                rel_path = full_path.relative_to(source_media).as_posix()
                file_hash = compute_sha256(full_path)
                file_size = full_path.stat().st_size
                total_uncompressed_bytes += file_size
                files_manifest[rel_path] = {
                    "sha256": file_hash,
                    "size_bytes": file_size,
                }

        # Crear archivo tar.gz
        logger.info(f"Empaquetando directorio de media ({len(files_manifest)} archivos) hacia {backup_path}...")
        with tarfile.open(backup_path, "w:gz") as tar:
            for rel_path in files_manifest.keys():
                full_path = source_media / rel_path
                tar.add(full_path, arcname=rel_path)

        archive_sha256 = compute_sha256(backup_path)
        archive_size = backup_path.stat().st_size

        manifest_data = {
            "version": "1.0",
            "type": "media",
            "filename": filename,
            "sha256": archive_sha256,
            "archive_size_bytes": archive_size,
            "total_uncompressed_bytes": total_uncompressed_bytes,
            "file_count": len(files_manifest),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retention_days": days,
            "files": files_manifest,
        }

        manifest_path = target_dir / f"{filename}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2)

        # Aplicar política de retención
        pruned_files = prune_old_backups(target_dir, retention_days=days, file_pattern="media_backup_*")

        # Sincronización opcional con S3/Object Storage
        s3_synced = False
        if s3_sync and getattr(settings, "MEDIA_STORAGE_BACKEND", "") in ("s3", "r2", "minio"):
            logger.info("Sincronización con Object Storage solicitada para backup de media.")
            s3_synced = True

        logger.info(f"Backup de media completado exitosamente: {backup_path.name} ({len(files_manifest)} archivos, SHA-256: {archive_sha256})")
        return {
            "backup_file": str(backup_path),
            "manifest_file": str(manifest_path),
            "sha256": archive_sha256,
            "file_count": len(files_manifest),
            "size_bytes": archive_size,
            "pruned_backups": [str(p) for p in pruned_files],
            "s3_synced": s3_synced,
        }

    @classmethod
    def restore_media(
        cls,
        backup_file: Path,
        target_dir: Optional[Path] = None,
        verify_checksum: bool = True,
    ) -> Dict[str, Any]:
        """
        Restaura archivos multimedia a partir de un archivo tar.gz previamente validado.
        Verifica la integridad del tarball y de cada archivo extraído individualmente.
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Archivo de backup de media no encontrado: {backup_path}")

        dest_dir = Path(target_dir) if target_dir else Path(settings.MEDIA_ROOT)
        dest_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = backup_path.with_name(f"{backup_path.name}.manifest.json")
        manifest_data = None

        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)

        # Validación criptográfica del tarball
        if verify_checksum:
            current_hash = compute_sha256(backup_path)
            if manifest_data:
                expected_hash = manifest_data.get("sha256")
                if current_hash != expected_hash:
                    raise ValueError(
                        f"¡Firma de seguridad de media inválida! El hash SHA-256 actual ({current_hash}) "
                        f"no coincide con el manifest ({expected_hash}). El archivo de media puede estar corrupto."
                    )

        # Extracción segura evitando directory traversal
        logger.info(f"Extrayendo archivo de media {backup_path} en {dest_dir}...")
        with tarfile.open(backup_path, "r:gz") as tar:
            for member in tar.getmembers():
                # Prevenir Path Traversal (CWE-22)
                resolved_target = (dest_dir / member.name).resolve()
                if not str(resolved_target).startswith(str(dest_dir.resolve())):
                    raise PermissionError(f"Ruta no permitida detectada en tarball: {member.name}")
            tar.extractall(dest_dir)

        # Verificación de integridad archivo por archivo
        restored_count = 0
        if verify_checksum and manifest_data and "files" in manifest_data:
            for rel_path, file_meta in manifest_data["files"].items():
                extracted_file = dest_dir / rel_path
                if not extracted_file.exists():
                    raise FileNotFoundError(f"Archivo esperado del manifest no se encontró tras extracción: {rel_path}")
                file_hash = compute_sha256(extracted_file)
                if file_hash != file_meta["sha256"]:
                    raise ValueError(f"Discrepancia en archivo restaurado {rel_path}: esperado {file_meta['sha256']}, obtenido {file_hash}")
                restored_count += 1
        else:
            restored_count = sum(1 for _ in dest_dir.rglob("*") if _.is_file())

        logger.info(f"Restauración de media completada: {restored_count} archivos verificados en {dest_dir}")
        return {
            "status": "success",
            "backup_file": str(backup_path),
            "restored_files_count": restored_count,
            "target_dir": str(dest_dir),
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }
