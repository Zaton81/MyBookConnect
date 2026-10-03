# Plan de Implementación — RoadmapV3: Sprint 2 (Infraestructura y Backups — P0)

**Fecha:** 3 de octubre de 2026  
**Rama de trabajo:** `develop`  
**Estado:** Propuesto para ejecución  
**Prioridad:** P0 (Crítico para producción y lanzamiento)

---

## 1. Contexto y Objetivos

El **Sprint 2 de RoadmapV3** (junto con la Sección 3 de Backups y Recuperación) establece la base operativa y de infraestructura necesaria para garantizar un despliegue seguro, resiliente y de alto rendimiento antes de salir a producción:

1. **Arquitectura Web y Reverse Proxy (Sección 2.1):**
   - Blindaje de Nginx como único punto de entrada (reverse proxy perimetral).
   - Aislamiento absoluto de Django/Daphne, PostgreSQL y Redis (sin puertos expuestos al host en producción).
   - Soporte para balanceo con upstream `django_cluster`.
   - Configuración limpia de `/api/`, `/admin/` (y slug administrativo custom), `/ws/` (con variables para WebSocket upgrade `Connection $connection_upgrade`), `/media/`, `/django_static/` y SPA frontend.
   - Rate limiting a nivel de Nginx (`limit_req_zone`) para mitigar abusos y ataques de denegación de servicio.
   - Cabeceras completas de seguridad HTTP (HSTS con preload, CSP estricto, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy).
   - Preparación para HTTPS / SSL y renovación Let's Encrypt.

2. **Base de Datos y Caché (Secciones 2.2 y 2.3):**
   - Consolidar PostgreSQL 16 con `pgvector` en todos los entornos, asegurando que las migraciones corran limpiamente.
   - Consolidar Redis 7 (`redis:7-alpine`) con persistencia AOF (`appendonly yes`), volumen persistente `redis_data`, límite de memoria prudente (`maxmemory 256mb`) y política de desalojo (`allkeys-lru`).

3. **Seguridad y Orquestación Docker (Sección 2.4):**
   - Asegurar que los contenedores corran como usuario no privilegiado (`appuser` en backend, configuración sin root en Nginx/frontend cuando proceda).
   - Fijar versiones deterministas en imágenes base (`python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`, `pgvector/pgvector:pg16`, `redis:7-alpine`).
   - Definir healthchecks estandarizados y cuotas de recursos CPU / memoria (`deploy.resources.limits`) en `docker-compose.prod.yml`.
   - Limpieza y verificación de redes internas segregadas (`frontend_net` pública, `backend_net` privada e interna).

4. **Estrategia y Verificación de Backups y Recuperación (Sección 3):**
   - Revisión y ajuste de los scripts de backup y restore en `scripts/backup/` (`backup_db.sh`, `restore_db.sh`, `test_restore_cycle.sh`).
   - Validación del procedimiento automatizado de restauración: creación de base de datos temporal, volcado, importación, verificación de tablas y smoke test de consistencia.

---

## 2. Modificaciones Técnicas Propuestas

### 2.1. Nginx Hardening (`frontend/nginx.conf`)
- Añadir el mapeo `map $http_upgrade $connection_upgrade` para gestionar upgrades de WebSocket de manera estándar.
- Unificar las directivas `proxy_pass` hacia `http://django_cluster` en lugar de `http://backend:8000` directo, facilitando escalado horizontal.
- Añadir `location /admin/` (y soporte para la variable `ADMIN_PATH`) para no atrapar el panel de Django en el `try_files` del frontend.
- Añadir directiva `limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;` y aplicarla en `/api/` con burst configurable.
- Añadir soporte para servidor HTTPS en puerto 443 con certificados SSL opcionales o montados, y redirección condicional en puerto 80.

### 2.2. Configuración de Redis y Persistencia
- En `docker-compose.yml` y `docker-compose.prod.yml`:
  - Configurar Redis 7 con parámetros explícitos: `command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --save 60 1`.
  - Añadir volumen `redis_data` para evitar pérdida de colas y estados de Celery/Channels ante reinicios.

### 2.3. Configuración de Producción (`docker-compose.prod.yml`)
- Añadir límites de CPU y memoria (`deploy.resources.limits: cpus: '...', memory: '...'`) en servicios críticos para evitar *OOM-killer* en el host.
- Asegurar que `backend`, `db` y `cache` no publiquen puertos hacia el host exterior (solo expuestos en redes internas).
- Validar permisos de `appuser` en volúmenes compartidos (`media`, `staticfiles`, `backups`).

### 2.4. Validación de Backups y Disaster Recovery
- Ajustar scripts en `scripts/backup/` para asegurar compatibilidad con la imagen `pgvector/pgvector:pg16` y comandos directos de docker compose.
- Ejecutar el script `test_restore_cycle.sh` o prueba equivalente para certificar la recuperabilidad de la base de datos sin errores ni pérdida de datos.

---

## 3. Plan de Pruebas y Validación

1. **Validación de Configuración Nginx:**
   - Comprobación sintáctica con `nginx -t` dentro del contenedor frontend.
   - Verificación de rutas proxy: `/api/v1/version/`, `/health/ready`, `/ws/` y `/admin/`.
2. **Prueba de Ciclo de Recuperación de PostgreSQL:**
   - Ejecutar `bash scripts/backup/test_restore_cycle.sh` o procedimiento automatizado.
   - Verificar integridad de tablas tras restore (incluyendo modelos de autores y FAQs creados en Sprint 3).
3. **Pruebas de Regresión Backend:**
   - Ejecutar la suite completa de tests de seguridad y sprints previos de forma estrictamente secuencial:
     `pytest tests/test_sprint1_security.py tests/test_sprint3_authors_and_faqs.py`
4. **Build de Frontend:**
   - Ejecutar `npm run build` en `frontend/` para garantizar que la compilación de producción sigue limpia (código 0).

---

## 4. Criterios de Aceptación (Definition of Done)

- [ ] Nginx configurado con upstream balanceado, límites de petición, cabeceras seguras y soporte WebSocket.
- [ ] No existen puertos internos de base de datos o backend expuestos al host en configuración de producción.
- [ ] Redis 7 configurado con persistencia AOF y política de desalojo LRU.
- [ ] Ciclo de backup y restauración de PostgreSQL 16 ejecutado y comprobado satisfactoriamente.
- [ ] 100% de tests pasando sin regresiones en backend y build exitoso en frontend.
- [ ] Documentación actualizada en `RoadmapV3.md`, `memory.md` y `CHANGELOG.md`.
- [ ] Commit semántico y push a la rama `develop`.
