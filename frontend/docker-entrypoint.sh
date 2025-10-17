#!/bin/sh
set -e

# Configurar store local y asegurar instalación
pnpm config set store-dir /app/.pnpm-store --global 1>/dev/null

echo "[entrypoint] Instalando dependencias (pnpm install)..."
pnpm install --no-frozen-lockfile

echo "[entrypoint] Iniciando Vite dev server..."
exec pnpm dev
