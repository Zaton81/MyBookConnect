#!/usr/bin/env bash
# ==============================================================================
# Script de Restauración de PostgreSQL con Verificación Criptográfica
# MyBookConnect - Fase 66
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <ruta_al_archivo_backup.sql.gz> [--no-verify]"
  exit 1
fi

BACKUP_FILE="$1"
VERIFY="${2:-}"
DB_NAME="${POSTGRES_DB:-mybookconnect}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "ERROR: El archivo de backup no existe: ${BACKUP_FILE}" >&2
  exit 1
fi

MANIFEST_FILE="${BACKUP_FILE}.manifest.json"

# Verificación de integridad SHA-256
if [ "${VERIFY}" != "--no-verify" ] && [ -f "${MANIFEST_FILE}" ]; then
  echo "Verificando firma criptográfica SHA-256..."
  CURRENT_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
  EXPECTED_HASH=$(grep -o '"sha256": *"[^"]*"' "${MANIFEST_FILE}" | cut -d'"' -f4)
  if [ "${CURRENT_HASH}" != "${EXPECTED_HASH}" ]; then
    echo "¡ERROR CRÍTICO! Discrepancia en el hash SHA-256." >&2
    echo "  Actual:    ${CURRENT_HASH}" >&2
    echo "  Esperado:  ${EXPECTED_HASH}" >&2
    echo "El archivo puede estar dañado o haber sido manipulado. Restauración abortada." >&2
    exit 1
  fi
  echo "Firma SHA-256 válida (${CURRENT_HASH})."
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Restaurando base de datos ${DB_NAME} desde ${BACKUP_FILE}..."

if command -v psql >/dev/null 2>&1; then
  gzip -dc "${BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --single-transaction
elif docker compose version >/dev/null 2>&1; then
  gzip -dc "${BACKUP_FILE}" | docker compose exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" --single-transaction
else
  echo "ERROR: psql no disponible localmente ni vía Docker Compose." >&2
  exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ¡Restauración completada exitosamente!"
