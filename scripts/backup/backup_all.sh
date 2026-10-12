#!/usr/bin/env bash
# ==============================================================================
# Script Maestro de Backup Diario Automatizado (DB + Media + Config)
# MyBookConnect - Fase B2 (Backups, Restore y Disaster Recovery)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BASE_BACKUP_DIR="${BASE_BACKUP_DIR:-${ROOT_DIR}/backups}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
START_TIME=$(date +%s)
SUMMARY_FILE="${BASE_BACKUP_DIR}/daily_backup_summary_${TIMESTAMP}.json"

mkdir -p "${BASE_BACKUP_DIR}"

echo "=============================================================================="
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] INICIANDO CICLO MAESTRO DE BACKUP DIARIO"
echo "Directorio base: ${BASE_BACKUP_DIR}"
echo "=============================================================================="

DB_STATUS="SUCCESS"
MEDIA_STATUS="SUCCESS"
CONFIG_STATUS="SUCCESS"
ERROR_MESSAGE=""

# 1. Backup de Base de Datos PostgreSQL
echo "--> Paso 1/3: Ejecutando backup de PostgreSQL..."
if bash "${SCRIPT_DIR}/backup_db.sh"; then
  echo "--> Paso 1/3 Completado: Base de datos respaldada con éxito."
else
  DB_STATUS="FAILED"
  ERROR_MESSAGE="Error durante el backup de PostgreSQL"
  echo "ERROR: Falló el backup de la base de datos." >&2
fi

# 2. Backup de Volumen Media
echo "--> Paso 2/3: Ejecutando backup de Media..."
if [ "${DB_STATUS}" = "SUCCESS" ]; then
  if bash "${SCRIPT_DIR}/backup_media.sh"; then
    echo "--> Paso 2/3 Completado: Archivos de media respaldados con éxito."
  else
    MEDIA_STATUS="FAILED"
    ERROR_MESSAGE="Error durante el backup de Media"
    echo "ERROR: Falló el backup de media." >&2
  fi
fi

# 3. Backup de Configuración Crítica
echo "--> Paso 3/3: Ejecutando backup de configuración crítica..."
if [ "${DB_STATUS}" = "SUCCESS" ] && [ "${MEDIA_STATUS}" = "SUCCESS" ]; then
  if bash "${SCRIPT_DIR}/backup_config.sh"; then
    echo "--> Paso 3/3 Completado: Configuración respaldada con éxito."
  else
    CONFIG_STATUS="FAILED"
    ERROR_MESSAGE="Error durante el backup de configuración"
    echo "ERROR: Falló el backup de configuración." >&2
  fi
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

OVERALL_STATUS="SUCCESS"
if [ "${DB_STATUS}" != "SUCCESS" ] || [ "${MEDIA_STATUS}" != "SUCCESS" ] || [ "${CONFIG_STATUS}" != "SUCCESS" ]; then
  OVERALL_STATUS="FAILED"
fi

# Generar resumen JSON
cat <<EOF > "${SUMMARY_FILE}"
{
  "version": "1.0",
  "type": "daily_backup_master",
  "timestamp": "${TIMESTAMP}",
  "status": "${OVERALL_STATUS}",
  "duration_seconds": ${DURATION},
  "subsystems": {
    "database": "${DB_STATUS}",
    "media": "${MEDIA_STATUS}",
    "configuration": "${CONFIG_STATUS}"
  },
  "error": "$([ -n "${ERROR_MESSAGE}" ] && echo "${ERROR_MESSAGE}" || echo "null")",
  "completed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo "=============================================================================="
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] RESUMEN DE EJECUCIÓN (${DURATION}s):"
echo "  - Estado Global:  ${OVERALL_STATUS}"
echo "  - Base de Datos:  ${DB_STATUS}"
echo "  - Media:          ${MEDIA_STATUS}"
echo "  - Configuración:  ${CONFIG_STATUS}"
echo "  - Resumen JSON:   ${SUMMARY_FILE}"
echo "=============================================================================="

if [ "${OVERALL_STATUS}" != "SUCCESS" ]; then
  echo "¡ALERTA RPO/DISASTER RECOVERY! El ciclo de backup falló: ${ERROR_MESSAGE}" >&2
  exit 1
fi

echo "Ciclo maestro de backup finalizado satisfactoriamente."
exit 0
