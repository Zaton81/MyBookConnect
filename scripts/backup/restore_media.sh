#!/usr/bin/env bash
# ==============================================================================
# Script de Restauración de Archivos Multimedia (Media)
# MyBookConnect - Fase 15 (Backups y Disaster Recovery)
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <ruta_al_archivo_media_backup> [--target-dir <directorio>] [--no-verify] [--key <encryption_key>]"
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DIR="${MEDIA_ROOT:-/app/media}"
VERIFY=true
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-${BACKUP_PASSPHRASE:-}}"

shift
while [ $# -gt 0 ]; do
  case "$1" in
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
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
  echo "ERROR: Archivo de backup no existe: ${BACKUP_FILE}" >&2
  exit 1
fi

MANIFEST_FILE="${BACKUP_FILE}.manifest.json"

# 1. Verificación de integridad SHA-256
if [ "${VERIFY}" = true ] && [ -f "${MANIFEST_FILE}" ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Verificando firma criptográfica SHA-256 del tarball..."
  CURRENT_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
  EXPECTED_HASH=$(grep -o '"sha256": *"[^"]*"' "${MANIFEST_FILE}" | cut -d'"' -f4)
  if [ "${CURRENT_HASH}" != "${EXPECTED_HASH}" ]; then
    echo "¡ERROR CRÍTICO! Hash SHA-256 no coincide con el manifest." >&2
    echo "  Actual:   ${CURRENT_HASH}" >&2
    echo "  Esperado: ${EXPECTED_HASH}" >&2
    exit 1
  fi
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Firma SHA-256 válida."
fi

TEMP_RESTORE_FILE=""
CLEANUP_TEMP=false

# 2. Descifrado si procede
if [[ "${BACKUP_FILE}" == *.enc ]]; then
  if [ -z "${ENCRYPTION_KEY}" ]; then
    echo "ERROR: El archivo de media está cifrado pero no se proporcionó clave." >&2
    exit 1
  fi
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Descifrando tarball de medios con AES-256..."
  TEMP_RESTORE_FILE=$(mktemp --suffix=.tar.gz)
  CLEANUP_TEMP=true
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
    -in "${BACKUP_FILE}" -out "${TEMP_RESTORE_FILE}"
  SOURCE_FILE="${TEMP_RESTORE_FILE}"
else
  SOURCE_FILE="${BACKUP_FILE}"
fi

trap 'if [ "${CLEANUP_TEMP}" = true ] && [ -f "${TEMP_RESTORE_FILE}" ]; then rm -f "${TEMP_RESTORE_FILE}"; fi' EXIT

mkdir -p "${TARGET_DIR}"

# 3. Extracción
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Extrayendo archivos multimedia en ${TARGET_DIR}..."
tar -xzf "${SOURCE_FILE}" -C "${TARGET_DIR}"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ¡Restauración de media completada exitosamente!"
