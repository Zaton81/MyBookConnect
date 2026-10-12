#!/usr/bin/env bash
# ==============================================================================
# Script de Backup de Configuración Crítica y Plantillas de Producción
# MyBookConnect - Fase B2 (Backups, Restore y Disaster Recovery)
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${CONFIG_BACKUP_DIR:-./backups/config}"
RETENTION_DAYS="${CONFIG_BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-${BACKUP_PASSPHRASE:-}}"

mkdir -p "${BACKUP_DIR}"

RAW_BACKUP_FILE="${BACKUP_DIR}/config_backup_${TIMESTAMP}.tar.gz"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Iniciando backup de configuración crítica..."

# Directorio temporal de staging para recopilar archivos clave de configuración
STAGING_DIR=$(mktemp -d)
trap 'rm -rf "${STAGING_DIR}"' EXIT

mkdir -p "${STAGING_DIR}/compose"
mkdir -p "${STAGING_DIR}/nginx"
mkdir -p "${STAGING_DIR}/env_templates"
mkdir -p "${STAGING_DIR}/scripts"

# Copiar archivos clave si existen
[ -f "docker-compose.prod.yml" ] && cp "docker-compose.prod.yml" "${STAGING_DIR}/compose/"
[ -f "docker-compose.yml" ] && cp "docker-compose.yml" "${STAGING_DIR}/compose/"
[ -f "frontend/nginx.conf" ] && cp "frontend/nginx.conf" "${STAGING_DIR}/nginx/"
[ -f "frontend/nginx.ssl.conf.template" ] && cp "frontend/nginx.ssl.conf.template" "${STAGING_DIR}/nginx/"
[ -f ".env.production.example" ] && cp ".env.production.example" "${STAGING_DIR}/env_templates/"
[ -f ".env.example" ] && cp ".env.example" "${STAGING_DIR}/env_templates/"

# Copiar scripts operativos de preflight y verificación
[ -d "scripts/production" ] && cp -r "scripts/production" "${STAGING_DIR}/scripts/"
[ -d "scripts/backup" ] && cp -r "scripts/backup" "${STAGING_DIR}/scripts/"

# Empaquetar y comprimir
tar -czf "${RAW_BACKUP_FILE}" -C "${STAGING_DIR}" .

FINAL_BACKUP_FILE="${RAW_BACKUP_FILE}"
IS_ENCRYPTED=false
CIPHER_ALGO="none"

# Cifrado simétrico AES-256 si se configuró clave
if [ -n "${ENCRYPTION_KEY}" ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Cifrando archivo de configuración con AES-256-CBC..."
  ENC_BACKUP_FILE="${RAW_BACKUP_FILE}.enc"
  openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
    -in "${RAW_BACKUP_FILE}" -out "${ENC_BACKUP_FILE}"
  rm -f "${RAW_BACKUP_FILE}"
  FINAL_BACKUP_FILE="${ENC_BACKUP_FILE}"
  IS_ENCRYPTED=true
  CIPHER_ALGO="aes-256-cbc"
fi

# Calcular firma SHA-256 y tamaño
SHA256_HASH=$(sha256sum "${FINAL_BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${FINAL_BACKUP_FILE}" | tr -d ' ')
MANIFEST_FILE="${FINAL_BACKUP_FILE}.manifest.json"

cat <<EOF > "${MANIFEST_FILE}"
{
  "version": "1.0",
  "type": "config",
  "filename": "$(basename "${FINAL_BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "encrypted": ${IS_ENCRYPTED},
  "cipher": "${CIPHER_ALGO}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "retention_days": ${RETENTION_DAYS}
}
EOF

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de configuración completado:"
echo "  - Archivo: ${FINAL_BACKUP_FILE}"
echo "  - SHA-256: ${SHA256_HASH}"
echo "  - Tamaño:  ${FILE_SIZE} bytes"
echo "  - Cifrado: ${IS_ENCRYPTED}"

# Sincronización opcional S3
S3_BUCKET="${BACKUP_S3_BUCKET:-${AWS_STORAGE_BUCKET_NAME:-}}"
if [ -n "${S3_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Sincronizando con s3://${S3_BUCKET}/backups/config/..."
  aws s3 cp "${FINAL_BACKUP_FILE}" "s3://${S3_BUCKET}/backups/config/"
  aws s3 cp "${MANIFEST_FILE}" "s3://${S3_BUCKET}/backups/config/"
fi

# Retención
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Aplicando política de retención (${RETENTION_DAYS} días)..."
find "${BACKUP_DIR}" -type f \( -name "config_backup_*.tar.gz" -o -name "config_backup_*.tar.gz.enc" \) -mtime +"${RETENTION_DAYS}" -print -delete || true
find "${BACKUP_DIR}" -type f -name "config_backup_*.manifest.json" -mtime +"${RETENTION_DAYS}" -print -delete || true

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup de configuración finalizado."
