#!/usr/bin/env bash
# ==============================================================================
# verify_dod.sh - Verificador Automatizado de la Definition of Done (DoD)
# ==============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}     MyBookConnect - Definition of Done (DoD) Verifier${NC}"
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

# 1. DoD Criterio 2: Comprobación de Migraciones (sin migraciones pendientes)
echo -e "\n${BLUE}--- [Criterio 2] Modelos y Migraciones Limpias ---${NC}"
if docker compose exec -T backend python manage.py makemigrations --check --dry-run > /dev/null 2>&1; then
    check_pass "No hay modelos con migraciones pendientes de generar"
else
    check_fail "Existen cambios en modelos sin migración asociada (ejecutar makemigrations)"
fi

# 2. DoD Criterio 11: Validación del Esquema OpenAPI
echo -e "\n${BLUE}--- [Criterio 11] Validación de Esquema OpenAPI / Swagger ---${NC}"
if docker compose exec -T backend python manage.py spectacular --validate > /dev/null 2>&1; then
    check_pass "Esquema OpenAPI validado sin errores de especificación"
else
    check_fail "El esquema OpenAPI presenta errores de especificación"
fi

# 3. DoD Criterio 12: Linter de Backend (ruff)
echo -e "\n${BLUE}--- [Criterio 12] Linter y Calidad Backend (ruff) ---${NC}"
if docker compose exec -T backend ruff check > /dev/null 2>&1; then
    check_pass "Linters de Python limpios (ruff check)"
else
    check_fail "Errores de formato o linter detectados en backend"
fi

# 4. DoD Criterio 7 y 12: Tipado Estricto Frontend (tsc --noEmit)
echo -e "\n${BLUE}--- [Criterios 7 y 12] Tipado Estricto Frontend (TypeScript) ---${NC}"
if (cd "${ROOT_DIR}" && npm --prefix frontend run typecheck > /dev/null 2>&1); then
    check_pass "TypeScript sin errores de tipos (tsc --noEmit)"
else
    check_fail "Errores de tipado detectados en frontend"
fi

# 5. Coherencia de Versiones y Release
echo -e "\n${BLUE}--- [Criterio 10] Versiones y CHANGELOG (SemVer 2.0.0) ---${NC}"
if bash "${SCRIPT_DIR}/verify_release.sh" > /dev/null 2>&1; then
    check_pass "Versiones sincronizadas y documentadas en CHANGELOG.md"
else
    check_fail "Desincronización de versión detectada"
fi

# Resumen Final
echo -e "\n${BLUE}======================================================${NC}"
if [[ ${FAILED_CHECKS} -eq 0 ]]; then
    echo -e "${GREEN}✔ DoD Verificada con éxito: Todas las comprobaciones automáticas superadas (${PASSED_CHECKS}/${TOTAL_CHECKS}).${NC}"
    echo -e "La rama cumple los criterios automáticos para abrir Pull Request."
    exit 0
else
    echo -e "${RED}✖ DoD incompleta: ${FAILED_CHECKS} comprobación(es) fallida(s).${NC}"
    echo -e "Consulta 'docs/development/definition_of_done.md' para resolver los requisitos pendientes."
    exit 1
fi
