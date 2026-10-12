#!/usr/bin/env bash
# Wrapper canónico para el chequeo pre-vuelo de producción
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/preflight_check.sh" "$@"
