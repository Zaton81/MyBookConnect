#!/usr/bin/env bash
# ==============================================================================
# MyBookConnect - Pre-flight Check de Staging (Beta Cerrada)
# Fase 35 - Despliegue y Validación en Staging
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Detectar comando docker (en Windows Git Bash se requiere docker.exe)
if command -v docker.exe >/dev/null 2>&1; then
    DOCKER_CMD="docker.exe"
else
    DOCKER_CMD="docker"
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}     MyBookConnect — Auditoría Pre-Despliegue de Staging        ${NC}"
echo -e "${BLUE}=================================================================${NC}"

FAILURES=0

check_pass() {
    echo -e " [${GREEN}OK${NC}] $1"
}

check_fail() {
    echo -e " [${RED}FAIL${NC}] $1"
    FAILURES=$((FAILURES + 1))
}

check_warn() {
    echo -e " [${YELLOW}WARN${NC}] $1"
}

# 1. Chequeo de Base de Datos y Modelos
echo -e "\n${BLUE}--- 1. Base de Datos y Migraciones ---${NC}"
if ${DOCKER_CMD} compose exec -T backend python manage.py check --database default > /dev/null 2>&1; then
    check_pass "Conectividad con PostgreSQL (default)"
else
    check_fail "Error conectando con PostgreSQL"
fi

if ${DOCKER_CMD} compose exec -T backend python manage.py makemigrations --check --dry-run > /dev/null 2>&1; then
    check_pass "Modelos sincronizados, cero migraciones pendientes"
else
    check_fail "Existen cambios en modelos sin migración generada"
fi

# 2. Servicios de Caché y Redis
echo -e "\n${BLUE}--- 2. Servicios de Caché (Redis) ---${NC}"
if ${DOCKER_CMD} compose exec -T backend python manage.py shell -c 'from django.core.cache import cache; cache.set("staging_ping", 1, 5); assert cache.get("staging_ping") == 1' > /dev/null 2>&1; then
    check_pass "Conexión y lectura/escritura en Redis"
else
    check_fail "Fallo al comunicar con Redis caché"
fi

# 3. Auditoría de Seguridad Django Deploy
echo -e "\n${BLUE}--- 3. Auditoría Django Deploy ---${NC}"
if ${DOCKER_CMD} compose exec -T backend python manage.py check > /dev/null 2>&1; then
    check_pass "Chequeo del sistema Django sin errores críticos"
else
    check_fail "Chequeo del sistema Django reportó errores"
fi

# 4. Coherencia de Versiones y Release
echo -e "\n${BLUE}--- 4. Coherencia de Versiones SemVer 2.0.0 ---${NC}"
if bash "${ROOT_DIR}/scripts/verify_release.sh" > /dev/null 2>&1; then
    check_pass "Versión sincronizada en backend, frontend y CHANGELOG"
else
    check_fail "Desincronización de versión detectada"
fi

# 5. Ejecución del Smoke Test Sintético
echo -e "\n${BLUE}--- 5. Smoke Testing Sintético ---${NC}"
HOST_TARGET="${1:-http://localhost:8000}"
if python "${SCRIPT_DIR}/smoke_test_staging.py" --host "${HOST_TARGET}" > /dev/null 2>&1 || python3 "${SCRIPT_DIR}/smoke_test_staging.py" --host "${HOST_TARGET}" > /dev/null 2>&1; then
    check_pass "Smoke test completado exitosamente contra ${HOST_TARGET}"
else
    check_fail "Smoke test falló contra ${HOST_TARGET}"
fi

echo -e "\n${BLUE}=================================================================${NC}"
if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}✔ Auditoría Pre-Despliegue de Staging superada con éxito.${NC}"
    echo -e "El entorno de staging cumple con los criterios de la Fase 35."
    exit 0
else
    echo -e "${RED}✖ Auditoría incompleta con ${FAILURES} fallo(s).${NC}"
    exit 1
fi
