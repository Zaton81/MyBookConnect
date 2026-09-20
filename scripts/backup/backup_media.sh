#!/usr/bin/env bash
# ==============================================================================
# Script de Backup de Archivos Multimedia (Media)
# MyBookConnect - Fase 66
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${MEDIA_BACKUP_DIR:-/backups/media}"
MEDIA_DIR="${MEDIA_ROOT:-/app/media}"
RETENTION_DAYS="${MEDIA_BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/media_backup_${TIMESTAMP}.tar.gz"
MANIFEST_FILE="${BACKUP_FILE}.manifest.json"

mkdir -p "${BACKUP_DIR}"

if [ ! -d "${MEDIA_DIR}" ]; then
  mkdir -p "${MEDIA_DIR}"
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Iniciando empaquetado de media desde ${MEDIA_DIR}..."

# Empaquetar directorio de medios
tar -czf "${BACKUP_FILE}" -C "${MEDIA_DIR}" .

SHA256_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${BACKUP_FILE}" | tr -d ' ')

# Generar manifest
cat <<EOF > "${MANIFEST_FILE}"
{
  "version": "1.0",
  "type": "media",
  "filename": "$(basename "${BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "retention_days": ${RETENTION_DAYS}
}
EOF

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de media completado:"
echo "  - Archivo: ${BACKUP_FILE}"
echo "  - SHA-256: ${SHA256_HASH}"

# Sincronización opcional con S3 / MinIO
if [ -n "${AWS_STORAGE_BUCKET_NAME:-}" ] && command -v aws >/dev/null 2>&1; then
  echo "Sincronizando backup con bucket S3: s3://${AWS_STORAGE_BUCKET_NAME}/backups/media/..."
  aws s3 cp "${BACKUP_FILE}" "s3://${AWS_STORAGE_BUCKET_NAME}/backups/media/"
  aws s3 cp "${MANIFEST_FILE}" "s3://${AWS_STORAGE_BUCKET_NAME}/backups/media/"
fi

# Aplicar política de retención
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Purgando copias de media con más de ${RETENTION_DAYS} días..."
find "${BACKUP_DIR}" -type f -name "media_backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -print -delete || true
find "${BACKUP_DIR}" -type f -name "media_backup_*.manifest.json" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de media finalizado."
