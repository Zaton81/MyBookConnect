#!/usr/bin/env bash
# ==============================================================================
# Script de Backup Diario de PostgreSQL para Producción
# MyBookConnect - Fase 15 (Backups y Disaster Recovery)
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/db}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-mybookconnect}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD:-}}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-${BACKUP_PASSPHRASE:-}}"

mkdir -p "${BACKUP_DIR}"

RAW_BACKUP_FILE="${BACKUP_DIR}/db_backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Iniciando backup de PostgreSQL: ${DB_NAME}..."

# 1. Ejecutar pg_dump y comprimir con gzip
if command -v pg_dump >/dev/null 2>&1; then
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${RAW_BACKUP_FILE}"
elif docker compose version >/dev/null 2>&1; then
  docker compose exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${RAW_BACKUP_FILE}"
else
  echo "ERROR: pg_dump no disponible localmente ni vía Docker Compose." >&2
  exit 1
fi

FINAL_BACKUP_FILE="${RAW_BACKUP_FILE}"
IS_ENCRYPTED=false
CIPHER_ALGO="none"

# 2. Cifrado simétrico AES-256-CBC en reposo si se especifica clave
if [ -n "${ENCRYPTION_KEY}" ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Aplicando cifrado AES-256-CBC al volcado..."
  ENC_BACKUP_FILE="${RAW_BACKUP_FILE}.enc"
  openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
    -in "${RAW_BACKUP_FILE}" -out "${ENC_BACKUP_FILE}"
  rm -f "${RAW_BACKUP_FILE}"
  FINAL_BACKUP_FILE="${ENC_BACKUP_FILE}"
  IS_ENCRYPTED=true
  CIPHER_ALGO="aes-256-cbc"
fi

# 3. Calcular firma criptográfica SHA-256 del archivo final
SHA256_HASH=$(sha256sum "${FINAL_BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${FINAL_BACKUP_FILE}" | tr -d ' ')
MANIFEST_FILE="${FINAL_BACKUP_FILE}.manifest.json"

# 4. Generar archivo manifest
cat <<EOF > "${MANIFEST_FILE}"
{
  "version": "1.1",
  "type": "database",
  "format": "$([ "${IS_ENCRYPTED}" = true ] && echo "pg_dump_gzip_aes256" || echo "pg_dump_gzip")",
  "database": "${DB_NAME}",
  "filename": "$(basename "${FINAL_BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "encrypted": ${IS_ENCRYPTED},
  "cipher": "${CIPHER_ALGO}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "retention_days": ${RETENTION_DAYS}
}
EOF

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de base de datos completado exitosamente:"
echo "  - Archivo:   ${FINAL_BACKUP_FILE}"
echo "  - SHA-256:   ${SHA256_HASH}"
echo "  - Tamaño:    ${FILE_SIZE} bytes"
echo "  - Cifrado:   ${IS_ENCRYPTED} (${CIPHER_ALGO})"

# 5. Sincronización opcional con almacenamiento en la nube (S3 / MinIO / GCS)
S3_BUCKET="${BACKUP_S3_BUCKET:-${AWS_STORAGE_BUCKET_NAME:-}}"
if [ -n "${S3_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Sincronizando con s3://${S3_BUCKET}/backups/db/..."
  aws s3 cp "${FINAL_BACKUP_FILE}" "s3://${S3_BUCKET}/backups/db/"
  aws s3 cp "${MANIFEST_FILE}" "s3://${S3_BUCKET}/backups/db/"
fi

# 6. Política de retención: purgar copias que superen RETENTION_DAYS
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Aplicando política de retención (${RETENTION_DAYS} días)..."
find "${BACKUP_DIR}" -type f \( -name "db_backup_*.sql.gz" -o -name "db_backup_*.sql.gz.enc" \) -mtime +"${RETENTION_DAYS}" -print -delete || true
find "${BACKUP_DIR}" -type f -name "db_backup_*.manifest.json" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Proceso finalizado."
