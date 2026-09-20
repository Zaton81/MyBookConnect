#!/usr/bin/env bash
# ==============================================================================
# Script de Backup Diario de PostgreSQL para Producción
# MyBookConnect - Fase 66
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/db}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-mybookconnect}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/db_backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
MANIFEST_FILE="${BACKUP_FILE}.manifest.json"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Iniciando backup de PostgreSQL: ${DB_NAME}..."

# Ejecutar pg_dump y comprimir con gzip
if command -v pg_dump >/dev/null 2>&1; then
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${BACKUP_FILE}"
elif docker compose version >/dev/null 2>&1; then
  docker compose exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${BACKUP_FILE}"
else
  echo "ERROR: pg_dump no disponible localmente ni vía Docker Compose." >&2
  exit 1
fi

# Calcular firma SHA-256
SHA256_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${BACKUP_FILE}" | tr -d ' ')

# Generar archivo manifest
cat <<EOF > "${MANIFEST_FILE}"
{
  "version": "1.0",
  "type": "database",
  "format": "pg_dump_gzip",
  "database": "${DB_NAME}",
  "filename": "$(basename "${BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "retention_days": ${RETENTION_DAYS}
}
EOF

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup completado exitosamente:"
echo "  - Archivo: ${BACKUP_FILE}"
echo "  - SHA-256: ${SHA256_HASH}"
echo "  - Tamaño:  ${FILE_SIZE} bytes"

# Política de retención: purgar copias que superen RETENTION_DAYS
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Aplicando política de retención (${RETENTION_DAYS} días)..."
find "${BACKUP_DIR}" -type f -name "db_backup_*.sql.gz" -mtime +"${RETENTION_DAYS}" -print -delete || true
find "${BACKUP_DIR}" -type f -name "db_backup_*.manifest.json" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Proceso finalizado."
