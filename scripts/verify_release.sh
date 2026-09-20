#!/usr/bin/env bash
# ==============================================================================
# verify_release.sh - Validador de coherencia de versión y release para MyBookConnect
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Verificando coherencia de Release para MyBookConnect ==="

# 1. Extraer versión de backend/mybookconnect/version.py
VERSION_PY="${ROOT_DIR}/backend/mybookconnect/version.py"
if [[ ! -f "${VERSION_PY}" ]]; then
    echo "ERROR: No se encontró ${VERSION_PY}"
    exit 1
fi
BACKEND_VER=$(grep -E "^VERSION\s*=" "${VERSION_PY}" | sed -E 's/.*VERSION\s*=\s*\(([0-9]+),\s*([0-9]+),\s*([0-9]+)\).*/\1.\2.\3/')
echo "-> Versión en backend/mybookconnect/version.py: ${BACKEND_VER}"

# 2. Extraer versión de backend/pyproject.toml
PYPROJECT_TOML="${ROOT_DIR}/backend/pyproject.toml"
if [[ ! -f "${PYPROJECT_TOML}" ]]; then
    echo "ERROR: No se encontró ${PYPROJECT_TOML}"
    exit 1
fi
PYPROJECT_VER=$(grep -E '^version\s*=' "${PYPROJECT_TOML}" | sed -E 's/.*version\s*=\s*"([^"]+)".*/\1/')
echo "-> Versión en backend/pyproject.toml: ${PYPROJECT_VER}"

if [[ "${BACKEND_VER}" != "${PYPROJECT_VER}" ]]; then
    echo "ERROR: Desincronización detectada entre version.py (${BACKEND_VER}) y pyproject.toml (${PYPROJECT_VER})"
    exit 1
fi

# 3. Extraer versión de frontend/package.json
PACKAGE_JSON="${ROOT_DIR}/frontend/package.json"
if [[ ! -f "${PACKAGE_JSON}" ]]; then
    echo "ERROR: No se encontró ${PACKAGE_JSON}"
    exit 1
fi
FRONTEND_VER=$(grep -E '"version":' "${PACKAGE_JSON}" | head -n 1 | sed -E 's/.*"version":\s*"([^"]+)".*/\1/')
echo "-> Versión en frontend/package.json: ${FRONTEND_VER}"

if [[ "${BACKEND_VER}" != "${FRONTEND_VER}" ]]; then
    echo "ERROR: Desincronización detectada entre backend (${BACKEND_VER}) y frontend/package.json (${FRONTEND_VER})"
    exit 1
fi

# 4. Verificar entrada en CHANGELOG.md
CHANGELOG_MD="${ROOT_DIR}/CHANGELOG.md"
if [[ ! -f "${CHANGELOG_MD}" ]]; then
    echo "ERROR: No se encontró ${CHANGELOG_MD}"
    exit 1
fi

if ! grep -q -E "^##\s*\[${BACKEND_VER}\]" "${CHANGELOG_MD}"; then
    echo "ERROR: No se encontró la sección de release [${BACKEND_VER}] en ${CHANGELOG_MD}"
    exit 1
fi
echo "-> Entrada en CHANGELOG.md: [${BACKEND_VER}] verificada correctamente."

echo "=========================================================="
echo "✔ Release v${BACKEND_VER} verificado con éxito. Todo en orden."
echo "=========================================================="
exit 0
