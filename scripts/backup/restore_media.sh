#!/usr/bin/env bash
# ==============================================================================
# Script de Restauración de Archivos Multimedia (Media)
# MyBookConnect - Fase 66
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <ruta_al_archivo_media_backup.tar.gz> [--target-dir <directorio>] [--no-verify]"
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DIR="${MEDIA_ROOT:-/app/media}"
VERIFY=true

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

# Verificación de integridad SHA-256
if [ "${VERIFY}" = true ] && [ -f "${MANIFEST_FILE}" ]; then
  echo "Verificando firma criptográfica SHA-256 del tarball..."
  CURRENT_HASH=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
  EXPECTED_HASH=$(grep -o '"sha256": *"[^"]*"' "${MANIFEST_FILE}" | cut -d'"' -f4)
  if [ "${CURRENT_HASH}" != "${EXPECTED_HASH}" ]; then
    echo "¡ERROR CRÍTICO! Hash SHA-256 no coincide con el manifest." >&2
    echo "  Actual:   ${CURRENT_HASH}" >&2
    echo "  Esperado: ${EXPECTED_HASH}" >&2
    exit 1
  fi
  echo "Firma SHA-256 válida."
fi

mkdir -p "${TARGET_DIR}"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Extrayendo archivos multimedia en ${TARGET_DIR}..."
tar -xzf "${BACKUP_FILE}" -C "${TARGET_DIR}"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ¡Restauración de media completada exitosamente!"
