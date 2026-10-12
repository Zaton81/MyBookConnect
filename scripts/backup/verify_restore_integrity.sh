#!/usr/bin/env bash
# ==============================================================================
# Script de Verificación de Integridad Post-Restore
# MyBookConnect - Fase B2 (Backups, Restore y Disaster Recovery)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CHECK_MEDIA="${CHECK_MEDIA:-false}"
MIN_USERS="${MIN_USERS:-1}"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Ejecutando verificación de integridad post-restore..."

CMD_ARGS="--min-users ${MIN_USERS}"
if [ "${CHECK_MEDIA}" = "true" ]; then
  CMD_ARGS="${CMD_ARGS} --check-media"
fi

if docker compose version >/dev/null 2>&1 && docker compose ps backend | grep -q "Up"; then
  docker compose exec -T backend python manage.py verify_restore_integrity ${CMD_ARGS}
elif command -v python >/dev/null 2>&1 && [ -f "${ROOT_DIR}/backend/manage.py" ]; then
  python "${ROOT_DIR}/backend/manage.py" verify_restore_integrity ${CMD_ARGS}
else
  echo "ERROR: No se encontró entorno de ejecución (Docker Compose o Python local)." >&2
  exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Verificación de integridad completada con éxito."
