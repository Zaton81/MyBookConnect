#!/usr/bin/env bash
# ==============================================================================
# Script de Restauración de PostgreSQL con Verificación Criptográfica y Descifrado
# MyBookConnect - Fase 15 (Backups y Disaster Recovery)
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <ruta_al_archivo_backup> [--no-verify] [--key <encryption_key>]"
  echo "Ejemplo: $0 /backups/db/db_backup_mybookconnect_20260927.sql.gz.enc"
  exit 1
fi

BACKUP_FILE="$1"
VERIFY=true
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-${BACKUP_PASSPHRASE:-}}"
DB_NAME="${POSTGRES_DB:-mybookconnect}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

shift
while [ $# -gt 0 ]; do
  case "$1" in
    --no-verify)
      VERIFY=false
      shift
      ;;
    --key)
      ENCRYPTION_KEY="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "ERROR: El archivo de backup no existe: ${BACKUP_FILE}" >&2
  exit 1
fi

MANIFEST_FILE="${BACKUP_FILE}.manifest.json"

# 1. Verificación estricta de integridad SHA-256 contra manifest
if [ "${VERIFY}" = true ] && [ -f "${MANIFEST_FILE}" ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Verificando firma criptográfica SHA-256..."
  CURRENT_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
  EXPECTED_HASH=$(grep -o '"sha256": *"[^"]*"' "${MANIFEST_FILE}" | cut -d'"' -f4)
  if [ "${CURRENT_HASH}" != "${EXPECTED_HASH}" ]; then
    echo "¡ERROR CRÍTICO! Discrepancia en el hash SHA-256." >&2
    echo "  Actual:    ${CURRENT_HASH}" >&2
    echo "  Esperado:  ${EXPECTED_HASH}" >&2
    echo "El archivo puede estar corrupto o haber sido manipulado. Restauración abortada." >&2
    exit 1
  fi
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Firma SHA-256 verificada con éxito: (${CURRENT_HASH})."
fi

TEMP_RESTORE_FILE=""
CLEANUP_TEMP=false

# 2. Descifrado si el archivo tiene extensión .enc o el manifest indica cifrado
if [[ "${BACKUP_FILE}" == *.enc ]]; then
  if [ -z "${ENCRYPTION_KEY}" ]; then
    echo "ERROR: El backup está cifrado con AES-256 pero no se proporcionó BACKUP_ENCRYPTION_KEY ni flag --key." >&2
    exit 1
  fi
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Descifrando volcado AES-256..."
  TEMP_RESTORE_FILE=$(mktemp --suffix=.sql.gz)
  CLEANUP_TEMP=true
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
    -in "${BACKUP_FILE}" -out "${TEMP_RESTORE_FILE}"
  SOURCE_FILE="${TEMP_RESTORE_FILE}"
else
  SOURCE_FILE="${BACKUP_FILE}"
fi

trap 'if [ "${CLEANUP_TEMP}" = true ] && [ -f "${TEMP_RESTORE_FILE}" ]; then rm -f "${TEMP_RESTORE_FILE}"; fi' EXIT

# 3. Restauración en PostgreSQL
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Restaurando base de datos ${DB_NAME} desde ${BACKUP_FILE}..."

if command -v psql >/dev/null 2>&1; then
  gzip -dc "${SOURCE_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --single-transaction
elif docker compose version >/dev/null 2>&1; then
  gzip -dc "${SOURCE_FILE}" | docker compose exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" --single-transaction
else
  echo "ERROR: psql no disponible localmente ni vía Docker Compose." >&2
  exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ¡Restauración completada exitosamente!"
