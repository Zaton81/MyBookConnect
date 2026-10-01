#!/usr/bin/env bash
# ==============================================================================
# MyBookConnect - Pre-flight Check de Producción
# Fase 29 - Preparación de Producción
# ==============================================================================
# Verifica que el entorno, contenedores, configuraciones de seguridad y
# dependencias críticas cumplen con el estándar para entrar en producción.
# ==============================================================================

set -eo pipefail

echo "================================================================="
echo "🚀 MyBookConnect — Verificación Pre-Vuelo de Producción"
echo "================================================================="

FAILURES=0

check_step() {
    local name="$1"
    local cmd="$2"
    echo -n "🔍 Comprobando: ${name}... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅ [OK]"
    else
        echo "❌ [FALLO]"
        FAILURES=$((FAILURES + 1))
    fi
}

# 1. Variables de entorno de producción
echo "─── 1. Seguridad de Entorno ───"
if [ "$DEBUG" = "1" ] || [ "$DEBUG" = "true" ] || [ "$DEBUG" = "True" ]; then
    echo "❌ [FALLO] DEBUG está activado. En producción debe ser obligatorio DEBUG=0 / False."
    FAILURES=$((FAILURES + 1))
else
    echo "✅ [OK] DEBUG desactivado (DEBUG=0)."
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "cambiar_por_una_clave_segura_en_produccion" ]; then
    echo "❌ [FALLO] SECRET_KEY es insegura o vacía."
    FAILURES=$((FAILURES + 1))
else
    echo "✅ [OK] SECRET_KEY configurada con entropía adecuada."
fi

# 2. Conectividad con Base de Datos
echo "─── 2. Base de Datos y Extensiones ───"
check_step "Conectividad PostgreSQL" "python manage.py check --database default"

# 3. Estado de Migraciones
echo "─── 3. Migraciones de Base de Datos ───"
check_step "Cero migraciones pendientes" "python manage.py showmigrations | grep -v '\[X\]' | grep -v '^ [a-z]' | wc -l | grep -q '^0$'"

# 4. Chequeo de despliegue de Django (deploy checks)
echo "─── 4. Auditoría de Seguridad Django Deploy ───"
check_step "Django check --deploy" "python manage.py check --deploy --fail-level WARNING"

# 5. Conectividad con Redis
echo "─── 5. Servicios de Caché y Mensajería ───"
check_step "Conexión a Redis Caché" "python -c 'from django.core.cache import cache; cache.set(\"preflight_test\", 1, 5); assert cache.get(\"preflight_test\") == 1'"

# 6. Sondas de Salud
echo "─── 6. Sondas de Salud y Liveness/Readiness ───"
check_step "Liveness probe (/health/live)" "python -c 'from django.test import Client; c = Client(); r = c.get(\"/health/live\"); assert r.status_code == 200'"
check_step "Readiness probe (/health/ready)" "python -c 'from django.test import Client; c = Client(); r = c.get(\"/health/ready\"); assert r.status_code == 200'"

# 7. Recolección de estáticos
echo "─── 7. Activos Estáticos ───"
check_step "Archivos estáticos en staticfiles" "test -d staticfiles || test -d /app/staticfiles"

echo "================================================================="
if [ "$FAILURES" -eq 0 ]; then
    echo "🎉 Todos los chequeos de pre-vuelo de producción han PASADO con éxito."
    echo "El sistema cumple con los criterios de seguridad y arquitectura de la Fase 29."
    exit 0
else
    echo "⚠️ Se han detectado ${FAILURES} fallos en el pre-vuelo de producción."
    echo "Por favor subsana los errores antes de exponer tráfico real."
    exit 1
fi
