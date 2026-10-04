# Plan de Implementación — RoadmapV3: Sprint 6 (Preproducción, Smoke Tests y Ready for Production)

**Fecha:** 4 de octubre de 2026  
**Rama de trabajo:** `develop`  
**Estado:** Propuesto para revisión y aprobación  
**Prioridad:** P3 / Cierre Final (Preproducción, Smoke Tests E2E y Criterios de Aceptación)

---

## 1. Contexto y Objetivos

El **Sprint 6 de RoadmapV3** culmina el ciclo de desarrollo hacia la versión de producción estable de **MyBookConnect / My Book Social**, cubriendo las Secciones:
- **20 (CI/CD y Deploy Checks)**: `check --deploy`, validación de migraciones sin cambios pendientes, build Docker.
- **21 (Documentación Operativa)**: Actualización de guías y manuales de operaciones.
- **22 (Monitorización y Sondas)**: Verificación de sondas `/health/live` y `/health/ready`.
- **26 (Legal y Privacidad)**: Verificación de políticas RGPD, eliminación de cuenta y exportación.
- **27 (Smoke Tests de Producción)**: Flujo de extremo a extremo (Registro, Catálogo unificado, Reseñas, Social, Autores, FAQs).
- **28 (Soft Launch)** y **31 (Criterios de Ready for Production)**: Certificación de todas las áreas (Seguridad, Datos, Autores, Calidad, Operaciones, UX).

### Objetivos Principales:
1. **Comprobaciones del Sistema Django para Producción (`check --deploy`)**:
   - Ejecutar `python manage.py check --deploy` y auditar que las variables de seguridad (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`) estén correctamente gobernadas.
   - Ejecutar `python manage.py makemigrations --check` para certificar que el esquema está 100% sincronizado.
2. **Ensayo Certificado de Backup y Restore**:
   - Ejecutar el script `scripts/backup/test_restore_cycle.sh` dentro del entorno Docker para validar la recuperación ante desastres sin intervención manual.
3. **Suite Completa de Smoke Tests de Preproducción (`test_sprint6_preproduction_readiness.py`)**:
   - Flujo E2E de usuario: registro -> verificación -> login -> gestión de biblioteca (`UserBook`).
   - Flujo de catálogo y unificación: búsqueda global por ISBN principal y secundario -> reseñas con sanitización anti-XSS.
   - Flujo social: seguimiento de lectores y emisión de eventos en feed.
   - Flujo de autor verificado: solicitud `AuthorClaim` -> aprobación administrativa -> insignia y panel oficial.
   - Flujo de soporte: FAQs públicas categorizadas.
   - Sondas de disponibilidad: `/health/live/` (200 OK) y `/health/ready/` (200 OK con DB/Redis sanos).
4. **Verificación Integral Frontend**:
   - Confirmar `npm run typecheck` (código 0).
   - Confirmar `npm run test` (100% pasando en Vitest).
   - Confirmar `npm run build` sin errores.
5. **Cierre Documental y Entrega**:
   - Actualizar [RoadmapV3.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV3.md) (marcar todas las tareas de Sprint 6 y Criterios 31).
   - Actualizar [memory.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/memory.md) con el balance final.
   - Actualizar [CHANGELOG.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/CHANGELOG.md).
   - Commit semántico y push a `origin/develop`.

---

## 2. Plan de Acción Detallado

### Paso 1: Django Deploy Checks y Validación de Migraciones
- Ejecutar `docker compose exec -T backend python manage.py check` y `makemigrations --check`.
- Ejecutar `docker compose exec -T backend python manage.py check --deploy` con settings de producción para confirmar ausencia de fallos críticos.

### Paso 2: Validación de Backup / Restore en Contenedor
- Ejecutar `docker compose exec -T backend bash scripts/backup/test_restore_cycle.sh` y certificar creación/destrucción correcta de la base de datos efímera.

### Paso 3: Suite Backend Sprint 6 (`test_sprint6_preproduction_readiness.py`)
- Crear `backend/tests/test_sprint6_preproduction_readiness.py` con pruebas que cubran los requisitos de la Sección 27 del Roadmap:
  - `test_e2e_user_journey_auth_and_profile`
  - `test_e2e_catalog_search_and_deduplication`
  - `test_e2e_author_claim_to_verification_flow`
  - `test_e2e_social_interactions_and_feed`
  - `test_e2e_faqs_and_support_flow`
  - `test_production_health_and_readiness_probes`

### Paso 4: Ejecución Secuencial de la Suite Completa de Regresión
- Ejecutar la suite completa secuencial de Sprints 1 a 6 (`test_sprint1_security.py` ... `test_sprint6_preproduction_readiness.py`).

### Paso 5: Calidad Frontend y Build
- Ejecutar `npm run typecheck` en `frontend/`.
- Ejecutar `npm run test` (Vitest).
- Ejecutar `npm run build`.

### Paso 6: Actualización Documental y Commit Semántico
- Actualizar `RoadmapV3.md`, `memory.md`, `CHANGELOG.md`.
- `git add .`, commit semántico y `git push origin develop`.
