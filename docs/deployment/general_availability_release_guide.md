# Guía de Lanzamiento General (General Availability — GA v1.0.0) — MyBookConnect

## 1. Resumen Ejecutivo y Alcance

La **Fase 38** formaliza el hito cumbre del desarrollo de **MyBookConnect**, transitando desde el ciclo de *Release Candidate* (`1.0.0-rc1`) hacia la versión oficial de **Disponibilidad General (General Availability — GA `1.0.0`)**.

El sistema ha superado con éxito las 38 fases del [RoadmapV2.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV2.md), consolidando:
- **Plataforma Social y Catálogo:** Gestión de lecturas, biblioteca personal, múltiples autores por obra, reseñas públicas, muro interactivo, clubes de lectura y mensajería en tiempo real vía WebSockets.
- **Motor de Recomendaciones y Búsqueda Híbrida:** Recomendaciones ponderadas con afinidad multi-autor, búsqueda difusa (`pg_trgm`) y soporte de embeddings semánticos con `pgvector`.
- **Monetización Ética:** Enlaces de afiliación a Amazon multiformato con aviso legal transparente y neutralidad algorítmica estricta.
- **Plataforma de Autores:** Verificación y reclamo de perfil, comunicados y panel de autor.
- **Seguridad, RGPD y Calidad:** Autenticación JWT con rotación y blacklist, políticas de privacidad granulares, exportación y anonimización atómica de datos (RGPD Arts. 17 y 20), rate limiting adaptativo y validación continua de contratos OpenAPI 3.0.

---

## 2. Coherencia de Versión (SemVer 2.0.0)

La versión oficial de producción ha quedado sincronizada de forma determinista en todos los componentes:

| Componente | Archivo Fuente | Versión Reportada |
| :--- | :--- | :---: |
| **Backend Core** | `backend/mybookconnect/version.py` | `1.0.0` |
| **Backend Metadatos** | `backend/pyproject.toml` | `1.0.0` |
| **Frontend SPA** | `frontend/package.json` | `1.0.0` |
| **API Pública** | `GET /api/v1/version/` | `1.0.0` |
| **Historial de Cambios** | `CHANGELOG.md` | `[1.0.0] - 2026-10-01` |

Validador automático:
```bash
bash scripts/verify_release.sh
```

---

## 3. Checklist de Pre-Despliegue a Producción

Antes de ejecutar el despliegue en la infraestructura de producción, el equipo de ingeniería debe verificar los siguientes 8 puntos:

- [ ] **1. Definition of Done (DoD 5/5):** Ejecutar `bash scripts/verify_dod.sh` y certificar que linter, migraciones, OpenAPI, TypeScript y versiones están limpios.
- [ ] **2. Suite de Backend Completa:** Ejecutar `pytest` secuencialmente en el contenedor backend y confirmar 0 errores.
- [ ] **3. Suite de Frontend Completa:** Ejecutar `npm --prefix frontend test` y confirmar 31/31 pruebas pasando.
- [ ] **4. Build de Producción de Frontend:** Ejecutar `npm --prefix frontend run build` para generar los bundles minificados en `frontend/dist/`.
- [ ] **5. Variables de Entorno de Producción:** Verificar que `.env.production` cuente con:
  - `DEBUG=False`
  - `SECRET_KEY` de alta entropía (>50 caracteres aleatorios).
  - `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` restringidos a los dominios autorizados.
  - `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`.
  - `PUBLIC_REGISTRATION_ENABLED=True` y `REQUIRE_BETA_INVITATION=False`.
- [ ] **6. Estado de Base de Datos:** Validar que PostgreSQL y la extensión `pgvector` estén inicializados y con copias de seguridad previas generadas (`scripts/backup_database.sh`).
- [ ] **7. Topología de Workers Celery:** Verificar el levantamiento de las 5 colas especializadas (`default`, `books`, `ai`, `recommendations`, `emails`).
- [ ] **8. Sondas de Liveness y Readiness:** Confirmar respuesta 200 OK en `/health/live` y `/health/ready`.

---

## 4. Procedimiento de Despliegue Zero-Downtime

### Paso 1: Actualización de Repositorio y Corte de Release Tag
```bash
git checkout main
git merge develop --ff-only
git tag -a v1.0.0 -m "Release v1.0.0 - General Availability"
git push origin main --tags
```

### Paso 2: Despliegue de Contenedores y Migraciones
```bash
# Construir imágenes de producción
docker compose -f docker-compose.prod.yml build

# Aplicar migraciones pendientes
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput

# Recopilar estáticos
docker compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

# Reiniciar servicios con estrategia de recarga progresiva
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

### Paso 3: Smoke Test Inmediato
```bash
python scripts/staging/smoke_test_staging.py --base-url https://mybookconnect.com
```

---

## 5. Monitorización Operativa y SLAs de Producción

### 5.1 Endpoints de Telemetría y Salud
- **Sonda de Liveness:** `GET /health/live` (monitoreado cada 10s por el orquestador).
- **Sonda de Readiness:** `GET /health/ready` (valida conectividad activa a PostgreSQL y Redis).
- **Métricas Prometheus / Observabilidad:** `GET /api/v1/observability/metrics/`.
- **Panel Administrativo de Telemetría Beta/GA:** `GET /api/v1/beta/admin/metrics/`.

### 5.2 Objetivos de Nivel de Servicio (SLAs)
- **Disponibilidad Global:** $\ge 99.9\%$ mensual.
- **Latencia API (p95):** $\le 200$ ms en endpoints de lectura y catálogo.
- **Latencia Búsqueda Híbrida (p95):** $\le 350$ ms combinando trigramas y similitud coseno.
- **Tiempo de Respuesta a Incidentes Críticos (P0):** $\le 15$ minutos.

---

## 6. Procedimiento de Rollback de Emergencia

Si se detecta una degradación severa tras el despliegue:

```bash
# 1. Regresar al commit o tag previo estable
git checkout v1.0.0-rc1

# 2. Restaurar copia de seguridad de base de datos si hubo migraciones destructivas
bash scripts/restore_database.sh /app/backups/pre_v1.0.0_backup.sql.gz

# 3. Reiniciar contenedores en la versión anterior
docker compose -f docker-compose.prod.yml up -d --force-recreate
```
