# Guía de Release Candidate (RC1) — MyBookConnect

## 1. Introducción y Propósito

El presente documento establece el procedimiento estándar de operaciones (SOP) para el despliegue, verificación y auditoría de la versión **1.0.0-rc1** (Release Candidate 1) de la plataforma **MyBookConnect**.

Un Release Candidate representa un hito de congelación de código (*Code Freeze*) donde la funcionalidad prevista para la versión `1.0.0` está completa y validada, enfocándose exclusivamente en la estabilidad, rendimiento y preparación para el despliegue en producción.

---

## 2. Checklist de Congelación de Código (Code Freeze)

Antes de iniciar el despliegue del Release Candidate, se debe comprobar el cumplimiento de los siguientes requisitos:

- [x] **SemVer 2.0.0 unificado:** `1.0.0-rc1` configurado en `backend/mybookconnect/version.py`, `backend/pyproject.toml`, `frontend/package.json` y `CHANGELOG.md`.
- [x] **Migraciones sincronizadas:** No existen migraciones pendientes (`python manage.py makemigrations --check --dry-run`).
- [x] **Esquema OpenAPI validado:** Sin errores de serialización (`python manage.py spectacular --validate`).
- [x] **Sondas de salud:** Endpoints `/health/live`, `/health/ready` y `/api/v1/health/` operativos.
- [x] **Definición de Hecho (DoD):** Script de auditoría `scripts/verify_dod.sh` completado satisfactoriamente.
- [x] **Script de Release:** Script de verificación de release `scripts/verify_release.sh` ejecutado con éxito.

---

## 3. Etiquetado Git del Release Candidate

Para congelar y marcar formalmente la versión en el repositorio de control de versiones:

```bash
# 1. Asegurar sincronización en la rama develop
git checkout develop
git pull origin develop

# 2. Crear etiqueta anotada y firmada/verificada
git tag -a v1.0.0-rc1 -m "release: MyBookConnect Release Candidate 1 (v1.0.0-rc1)"

# 3. Publicar la etiqueta en el repositorio remoto
git push origin v1.0.0-rc1
```

---

## 4. Despliegue en Entorno Staging / Pre-producción

El despliegue del RC1 se ejecuta mediante Docker Compose empleando las configuraciones de producción:

### 4.1 Preparación del Entorno

1. Copiar y verificar las variables de entorno de producción:
   ```bash
   cp .env.production.example .env.production
   # Editar .env.production con credenciales seguras y rotadas para staging
   ```

2. Validar que las variables críticas se encuentren definidas:
   - `SECRET_KEY` (clave criptográfica de al menos 50 caracteres)
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
   - `REDIS_URL`
   - `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS`
   - `SECURE_SSL_REDIRECT=True`
   - `SESSION_COOKIE_SECURE=True`
   - `CSRF_COOKIE_SECURE=True`

### 4.2 Construcción y Arranque de Contenedores

```bash
# Construir imágenes de staging/producción
docker compose -f docker-compose.prod.yml build --no-cache

# Levantar servicios en segundo plano
docker compose -f docker-compose.prod.yml up -d
```

### 4.3 Ejecución de Migraciones y Recolección de Estáticos

```bash
# Aplicar migraciones pendientes
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --noinput

# Recolectar archivos estáticos
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

---

## 5. Protocolo de Smoke Testing Automatizado

Una vez levantados los servicios, ejecutar las siguientes validaciones de disponibilidad:

### 5.1 Sonda de Liveness
```bash
curl -f -s http://localhost:8000/health/live | jq .
# Esperado: {"status": "healthy", "process": "alive", "version": "1.0.0-rc1"}
```

### 5.2 Sonda de Readiness
```bash
curl -f -s http://localhost:8000/health/ready | jq .
# Esperado: {"status": "ready", "services": {"database": "ready", "cache": "ready"}}
```

### 5.3 Endpoint Informativo de Versión
```bash
curl -f -s http://localhost:8000/api/v1/version/ | jq .
# Esperado: {"version": "1.0.0-rc1", "major": 1, "minor": 0, "patch": 0, "prerelease": "rc1", ...}
```

---

## 6. Procedimiento de Rollback

En caso de detectarse anomalías críticas no toleradas durante la fase de validación del RC1:

1. **Detener el tráfico entrante:**
   Desviar temporalmente el proxy inverso (Nginx / Cloudflare) a la página de mantenimiento.

2. **Revertir contenedores a la versión anterior:**
   ```bash
   docker compose -f docker-compose.prod.yml down
   # Desplegar la imagen etiquetada previa o volver a la rama estable
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Reversión de migraciones (si aplica):**
   Si la versión contenía migraciones incompatibles, aplicar el rollback específico:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py migrate <app_name> <migration_number_anterior>
   ```

4. **Restauración desde copia de seguridad (Disaster Recovery):**
   En caso de corrupción de datos, consultar `docs/deployment/disaster_recovery.md` para el procedimiento de restauración de PostgreSQL y Redis desde backups RPO < 1h.

---

## 7. Criterios de Promoción a 1.0.0 Final (GA)

Para que el Release Candidate `1.0.0-rc1` sea promovido a General Availability (`1.0.0`):
1. Cero defectos de severidad Bloqueante o Crítica reportados en staging tras 48 horas.
2. Todas las suites de pruebas unitarias, de integración y end-to-end con 100% de éxito.
3. Validación de rendimiento y tiempos de respuesta P95 < 200ms en endpoints clave.
