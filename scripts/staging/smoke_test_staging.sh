#!/usr/bin/env bash
# ==============================================================================
# MyBookConnect - Wrapper de Smoke Testing para Staging
# Fase 35 - Despliegue y Validación en Staging (Beta Cerrada)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HOST="${1:-http://localhost:8000}"

echo "Iniciando Smoke Test contra: ${HOST}"
python3 "${SCRIPT_DIR}/smoke_test_staging.py" --host "${HOST}" "$@" || python "${SCRIPT_DIR}/smoke_test_staging.py" --host "${HOST}" "$@"
