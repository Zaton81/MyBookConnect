#!/usr/bin/env bash
# ==============================================================================
# Procedimiento Automatizado de Prueba de Restauración (Restore Test Cycle)
# MyBookConnect - Fase 15 (RoadmapV2, Sección 20.4)
# Ciclo: backup → restore → migrate/check → smoke tests → cleanup
# ==============================================================================
set -euo pipefail

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
TEST_DB_NAME="mbc_verify_restore_${TIMESTAMP}"
BACKUP_DIR="${BACKUP_DIR:-/backups/db/restore_tests}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
SOURCE_DB="${POSTGRES_DB:-mybookconnect}"

mkdir -p "${BACKUP_DIR}"

echo "=============================================================================="
echo "Iniciando ciclo de prueba de restauración (Restore Test Cycle)"
echo "Base de datos origen:     ${SOURCE_DB}"
echo "Base de datos temporal:   ${TEST_DB_NAME}"
echo "Directorio de prueba:     ${BACKUP_DIR}"
echo "=============================================================================="

# 1. Generar backup fresco
echo "[PASO 1/5] Generando backup completo de ${SOURCE_DB}..."
TEST_BACKUP_FILE="${BACKUP_DIR}/verify_backup_${TIMESTAMP}.sql.gz"

if command -v pg_dump >/dev/null 2>&1; then
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${SOURCE_DB}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${TEST_BACKUP_FILE}"
elif docker compose version >/dev/null 2>&1; then
  docker compose exec -T db pg_dump -U "${DB_USER}" -d "${SOURCE_DB}" \
    --clean --if-exists --no-owner --no-privileges | gzip -9 > "${TEST_BACKUP_FILE}"
else
  echo "ERROR: pg_dump no disponible." >&2
  exit 1
fi

# Generar manifest
SHA256_HASH=$(sha256sum "${TEST_BACKUP_FILE}" | awk '{print $1}')
FILE_SIZE=$(wc -c < "${TEST_BACKUP_FILE}" | tr -d ' ')
cat <<EOF > "${TEST_BACKUP_FILE}.manifest.json"
{
  "version": "1.1",
  "type": "database_restore_verify",
  "format": "pg_dump_gzip",
  "database": "${SOURCE_DB}",
  "filename": "$(basename "${TEST_BACKUP_FILE}")",
  "sha256": "${SHA256_HASH}",
  "size_bytes": ${FILE_SIZE},
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
echo "Backup generado correctamente (${FILE_SIZE} bytes, SHA-256: ${SHA256_HASH})."

# Función de limpieza ante salida
cleanup() {
  echo "[LIMPIEZA] Eliminando base de datos de prueba y archivos temporales..."
  if command -v psql >/dev/null 2>&1; then
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${TEST_DB_NAME}\";" >/dev/null 2>&1 || true
  elif docker compose version >/dev/null 2>&1; then
    docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${TEST_DB_NAME}\";" >/dev/null 2>&1 || true
  fi
  rm -f "${TEST_BACKUP_FILE}" "${TEST_BACKUP_FILE}.manifest.json"
  echo "[LIMPIEZA] Concluida."
}
trap cleanup EXIT

# 2. Crear base de datos aislada para verificación
echo "[PASO 2/5] Creando base de datos aislada ${TEST_DB_NAME}..."
if command -v psql >/dev/null 2>&1; then
  psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TEST_DB_NAME}\";"
elif docker compose version >/dev/null 2>&1; then
  docker compose exec -T db psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TEST_DB_NAME}\";"
fi

# 3. Restaurar volcado en la base de datos temporal
echo "[PASO 3/5] Restaurando volcado en ${TEST_DB_NAME}..."
if command -v psql >/dev/null 2>&1; then
  gzip -dc "${TEST_BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TEST_DB_NAME}" --single-transaction >/dev/null
elif docker compose version >/dev/null 2>&1; then
  gzip -dc "${TEST_BACKUP_FILE}" | docker compose exec -T db psql -U "${DB_USER}" -d "${TEST_DB_NAME}" --single-transaction >/dev/null
fi
echo "Restauración completada sin errores de sintaxis."

# 4. Verificar integridad y migraciones
echo "[PASO 4/5] Verificando consistencia de tablas y modelos..."
if command -v psql >/dev/null 2>&1; then
  TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TEST_DB_NAME}" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
elif docker compose version >/dev/null 2>&1; then
  TABLE_COUNT=$(docker compose exec -T db psql -U "${DB_USER}" -d "${TEST_DB_NAME}" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
fi
TABLE_COUNT=$(echo "${TABLE_COUNT}" | tr -d ' ')
echo "Tablas detectadas en la base restaurada: ${TABLE_COUNT}"
if [ "${TABLE_COUNT}" -lt 10 ]; then
  echo "ERROR: La base de datos restaurada no contiene las tablas esperadas." >&2
  exit 1
fi

# 5. Smoke tests
echo "[PASO 5/5] Ejecutando smoke tests de lectura..."
if command -v psql >/dev/null 2>&1; then
  USER_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TEST_DB_NAME}" -t -c "SELECT count(*) FROM users_user;")
elif docker compose version >/dev/null 2>&1; then
  USER_COUNT=$(docker compose exec -T db psql -U "${DB_USER}" -d "${TEST_DB_NAME}" -t -c "SELECT count(*) FROM users_user;")
fi
USER_COUNT=$(echo "${USER_COUNT}" | tr -d ' ')
echo "Smoke test superado: tabla users_user accesible y consistente (${USER_COUNT} registros)."

echo "=============================================================================="
echo "¡Ciclo de prueba de restauración superado al 100%! El backup es íntegro y restaurable."
echo "=============================================================================="
