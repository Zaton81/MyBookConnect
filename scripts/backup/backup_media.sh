#!/usr/bin/env bash
# ==============================================================================
# Script de Backup de Archivos Multimedia (Media)
# MyBookConnect - Fase 15 (Backups y Disaster Recovery)
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${MEDIA_BACKUP_DIR:-./backups/media}"
MEDIA_DIR="${MEDIA_ROOT:-./backend/media}"
RETENTION_DAYS="${MEDIA_BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-${BACKUP_PASSPHRASE:-}}"

mkdir -p "${BACKUP_DIR}"

if [ ! -d "${MEDIA_DIR}" ]; then
  mkdir -p "${MEDIA_DIR}"
fi

RAW_BACKUP_FILE="${BACKUP_DIR}/media_backup_${TIMESTAMP}.tar.gz"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Iniciando empaquetado de media desde ${MEDIA_DIR}..."

# 1. Empaquetar y comprimir directorio de medios
tar -czf "${RAW_BACKUP_FILE}" -C "${MEDIA_DIR}" .

FINAL_BACKUP_FILE="${RAW_BACKUP_FILE}"
IS_ENCRYPTED=false
CIPHER_ALGO="none"

# 2. Cifrado simétrico AES-256 si se configuró clave
if [ -n "${ENCRYPTION_KEY}" ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Cifrando archivo de medios con AES-256-CBC..."
  ENC_BACKUP_FILE="${RAW_BACKUP_FILE}.enc"
  openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
    -in "${RAW_BACKUP_FILE}" -out "${ENC_BACKUP_FILE}"
  rm -f "${RAW_BACKUP_FILE}"
  FINAL_BACKUP_FILE="${ENC_BACKUP_FILE}"
  IS_ENCRYPTED=true
  CIPHER_ALGO="aes-256-cbc"
fi

# 3. Calcular hash SHA-256 y tamaño
SHA256_HASH=$(sha256sum "${FINAL_BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${FINAL_BACKUP_FILE}" | tr -d ' ')
MANIFEST_FILE="${FINAL_BACKUP_FILE}.manifest.json"

# 4. Generar manifest JSON
cat <<EOF > "${MANIFEST_FILE}"
{
  "version": "1.1",
  "type": "media",
  "filename": "$(basename "${FINAL_BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "encrypted": ${IS_ENCRYPTED},
  "cipher": "${CIPHER_ALGO}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "retention_days": ${RETENTION_DAYS}
}
EOF

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de media completado:"
echo "  - Archivo: ${FINAL_BACKUP_FILE}"
echo "  - SHA-256: ${SHA256_HASH}"
echo "  - Cifrado: ${IS_ENCRYPTED}"

# 5. Sincronización opcional con S3 / MinIO
S3_BUCKET="${BACKUP_S3_BUCKET:-${AWS_STORAGE_BUCKET_NAME:-}}"
if [ -n "${S3_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Sincronizando backup de media con s3://${S3_BUCKET}/backups/media/..."
  aws s3 cp "${FINAL_BACKUP_FILE}" "s3://${S3_BUCKET}/backups/media/"
  aws s3 cp "${MANIFEST_FILE}" "s3://${S3_BUCKET}/backups/media/"
fi

# 6. Aplicar política de retención
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Purgando copias de media con más de ${RETENTION_DAYS} días..."
find "${BACKUP_DIR}" -type f \( -name "media_backup_*.tar.gz" -o -name "media_backup_*.tar.gz.enc" \) -mtime +"${RETENTION_DAYS}" -print -delete || true
find "${BACKUP_DIR}" -type f -name "media_backup_*.manifest.json" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de media finalizado."
