#!/usr/bin/env bash
# ==============================================================================
# doctor.sh - Diagnóstico de Salud y Entorno de Desarrollo para MyBookConnect
# ==============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}        MyBookConnect - System Health Doctor          ${NC}"
echo -e "${BLUE}======================================================${NC}"

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

check_pass() {
    echo -e " [${GREEN}OK${NC}] $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

check_fail() {
    echo -e " [${RED}FAIL${NC}] $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

check_warn() {
    echo -e " [${YELLOW}WARN${NC}] $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

# 1. Verificación de Git
echo -e "\n${BLUE}--- 1. Git & Version Control ---${NC}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "${CURRENT_BRANCH}" != "unknown" ]]; then
    check_pass "Rama actual de Git: ${CURRENT_BRANCH}"
else
    check_fail "No es un repositorio Git válido"
fi

DIRTY_FILES=$(git status --porcelain 2>/dev/null | wc -l || echo 0)
if [[ "${DIRTY_FILES}" -eq 0 ]]; then
    check_pass "Árbol de trabajo limpio (sin cambios pendientes)"
else
    check_warn "Existen archivos modificados o sin rastrear (${DIRTY_FILES} elementos)"
fi

# 2. Verificación de Coherencia de Versiones SemVer
echo -e "\n${BLUE}--- 2. Versiones y Release ---${NC}"
if bash "${SCRIPT_DIR}/verify_release.sh" > /dev/null 2>&1; then
    check_pass "Sincronización de versiones SemVer (backend, frontend, CHANGELOG)"
else
    check_fail "Desincronización de versiones detectada (ejecutar verify_release.sh)"
fi

# 3. Verificación de Docker y Contenedores
echo -e "\n${BLUE}--- 3. Contenedores Docker ---${NC}"
if docker compose ps > /dev/null 2>&1; then
    check_pass "Docker Compose CLI operativo"
    
    # Comprobar contenedor backend
    if docker compose ps --status running | grep -q "backend"; then
        check_pass "Contenedor Backend en ejecución"
    else
        check_fail "Contenedor Backend no está corriendo"
    fi

    # Comprobar contenedor db
    if docker compose ps --status running | grep -q "db"; then
        check_pass "Contenedor PostgreSQL (db) en ejecución"
    else
        check_fail "Contenedor PostgreSQL no está corriendo"
    fi

    # Comprobar contenedor redis
    if docker compose ps --status running | grep -q "redis"; then
        check_pass "Contenedor Redis en ejecución"
    else
        check_fail "Contenedor Redis no está corriendo"
    fi
else
    check_fail "Docker daemon o Docker Compose no responde"
fi

# 4. Verificación de Base de Datos y Django
echo -e "\n${BLUE}--- 4. Conectividad y Migraciones ---${NC}"
if docker compose exec -T backend python manage.py check --database default > /dev/null 2>&1; then
    check_pass "Conexión a base de datos PostgreSQL exitosa"
else
    check_fail "Fallo de conexión a la base de datos PostgreSQL"
fi

# Comprobar migraciones no aplicadas
PENDING_MIGRATIONS=$(docker compose exec -T backend python manage.py showmigrations --plan 2>/dev/null | grep -E '^\[ \]' | wc -l || echo 0)
if [[ "${PENDING_MIGRATIONS}" -eq 0 ]]; then
    check_pass "Todas las migraciones de Django están aplicadas"
else
    check_warn "Existen ${PENDING_MIGRATIONS} migraciones pendientes de aplicar"
fi

# 5. Verificación de Redis Cache
echo -e "\n${BLUE}--- 5. Caché Redis ---${NC}"
if docker compose exec -T backend python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings'); django.setup(); from django.core.cache import cache; cache.set('doctor_ping', 'ok', 5); assert cache.get('doctor_ping') == 'ok';" > /dev/null 2>&1; then
    check_pass "Caché Redis operativa y respondiendo lectura/escritura"
else
    check_fail "Fallo al comunicar con la caché Redis"
fi

# Resumen Final
echo -e "\n${BLUE}======================================================${NC}"
if [[ ${FAILED_CHECKS} -eq 0 ]]; then
    echo -e "${GREEN}✔ Diagnóstico completado: Sistema saludable (${PASSED_CHECKS}/${TOTAL_CHECKS} verificaciones superadas).${NC}"
    exit 0
else
    echo -e "${RED}✖ Diagnóstico completado con fallos: ${FAILED_CHECKS} error(es) detectado(s).${NC}"
    echo -e "Consulta 'docs/development/troubleshooting_and_runbooks.md' para resolverlos."
    exit 1
fi
