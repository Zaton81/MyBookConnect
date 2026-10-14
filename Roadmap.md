# MyBookConnect — Roadmap de Producción y Evolución

> **Versión del documento:** 2.0  
> **Fecha:** 10 de octubre de 2026  
> **Estado del producto:** `1.0.0` (General Availability)  
> **Rama de trabajo:** `develop`  
> **Objetivo del documento:** Definir el plan completo, priorizado y ejecutable para (1) corregir fallos y riesgos residuales críticos, (2) endurecer la plataforma para producción pública real y (3) evolucionar el producto de forma sostenible.

---

## Principios rectores

1. **Seguridad e integridad primero.** Ninguna feature nueva tiene prioridad sobre vulnerabilidades o inconsistencias de dominio.
2. **Cero regresiones.** Toda fase debe dejar la suite de tests (backend + frontend) al 100 % y las migraciones en estado limpio.
3. **Operabilidad.** Todo cambio debe ser reversible, observable y documentado (ADRs + `memory.md` + runbooks).
4. **IA opcional.** Las capacidades de inteligencia artificial nunca deben bloquear el flujo principal de lectura, social o biblioteca.
5. **Privacidad por diseño.** Cumplimiento RGPD (Arts. 17 y 20) y minimización de datos son invariantes.
6. **Trabajo exclusivo en `develop`.** Tras cada fase: commit semántico + push a `develop`. Nunca push directo a `main`.
7. **Plan antes de código.** Antes de implementar una fase se redacta y aprueba `implementation_plan.md`.

---

## Estado actual del producto (baseline)

| Área | Estado | Notas |
|------|--------|-------|
| Backend | Django 5.2 LTS + DRF + Channels + Celery | Stack estable |
| Frontend | React 18 + TypeScript strict + Vite + Tailwind | Typecheck y build de producción OK |
| Base de datos | PostgreSQL 16 + pgvector | Extensión activa |
| Caché / tiempo real | Redis 7 (cache + Channels + broker) | Persistencia AOF |
| Infraestructura | Docker multi-stage, Nginx reverse proxy, redes aisladas | Usuario no-root |
| Seguridad | JWT, throttling, moderación, AuditLog, CSP/HSTS | Residual: token en localStorage |
| Dominio | Biblioteca, reseñas, social, chat, listas, autores verificados, newsletters, IA, analytics, beta | Funcionalmente rico |
| Tests | > 100 archivos de fase + suites de sprint | Cobertura alta, e2e y carga pendientes de refuerzo |
| Versión | `1.0.0` (GA) | Release Candidate y staging validados |

---

## Mapa de prioridades

| Prioridad | Significado | Criterio de inclusión |
|-----------|-------------|-----------------------|
| 🔴 **P0** | Bloquea producción pública segura | Vulnerabilidad, pérdida de datos, fallo de autenticación o integridad |
| 🟠 **P1** | Necesario para primera versión pública robusta | Experiencia core, operación, observabilidad |
| 🟡 **P2** | Mejora importante post-lanzamiento | Diferenciación, rendimiento, UX avanzada |
| 🟢 **P3** | Evolución a medio plazo | Features de crecimiento |
| 🔮 **FUTURO** | Visión a largo plazo | No planificado para los próximos 6 meses |

---

# BLOQUE A — Estabilización crítica (P0)

> Objetivo: eliminar riesgos que impiden confiar en un entorno de producción pública real.

## Fase A1 — Congelación y baseline de seguridad
**Duración estimada:** 1-2 días  
**Prioridad:** 🔴 P0

- [x] Crear tag `v1.0.0-pre-hardening` y branch de protección.
- [x] Backup completo de PostgreSQL (cifrado AES-256) + volumen `media/`.
- [x] Verificar `makemigrations --check` (0 pendientes).
- [x] Ejecutar suite completa de tests de fase y de sprint (100 %).
- [x] Auditoría exhaustiva de marcadores de conflicto residuales (`<<<<<<<`, `=======`, `>>>>>>>`).
- [x] Eliminación definitiva de código muerto (`backend/app/`, `backend/config/` u otros esqueletos FastAPI).
- [x] Rotación de secrets de desarrollo y documentación de política de secrets (nunca en git).
- [x] Actualizar `memory.md` con el estado de baseline.

**Criterio de salida:** Repo limpio, tests verdes, backup restaurable en entorno limpio.

---

## Fase A2 — Autenticación y sesión segura
**Duración estimada:** 3-4 días  
**Prioridad:** 🔴 P0

### JWT y almacenamiento de tokens
- [x] Migrar tokens de acceso/refresh desde `localStorage` (Zustand persist) a cookies `HttpOnly` + `Secure` + `SameSite=Lax/Strict` (con soporte transparente en `client.ts` y backend).
- [x] Eliminar cualquier `console.log` o log que contenga tokens.
- [x] Implementar rotación de refresh token + blacklist (`OutstandingToken` y `BlacklistedToken` de SimpleJWT).
- [x] Configurar tiempos de vida cortos para access token (15 min) y razonables para refresh (7 días).
- [x] Actualizar cliente frontend (`client.ts` / interceptores) y store de autenticación (`useAuthStore` con `partialize`).
- [x] Tests de seguridad: robo de cookie, XSS simulado, rotación y logout al 100%.

### WebSockets
- [x] Eliminar completamente autenticación por query string (`?token=`) y bloquear intentos inseguros en middleware.
- [x] Autenticación exclusiva mediante cookie HttpOnly o ticket de corta duración emitido por endpoint autenticado (`/api/v1/auth/ws-ticket/`).
- [x] Rate limiting / backpressure por conexión y por usuario.
- [x] Tamaño máximo de mensaje y rechazo de acciones desconocidas.
- [x] Manejo robusto de desconexiones y reconexión.
- [x] Tests de abuso, usuarios bloqueados y payloads malformados.

### Cookies y headers
- [x] Confirmar `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS, CSP, COOP.
- [x] Revisar CORS y CSRF en el contexto de cookies cross-origin (`CORS_ALLOW_CREDENTIALS = True`, `AUTH_COOKIE_SAMESITE = 'Lax'`).

**Criterio de salida:** Suite de autenticación y WebSocket abuse al 100 %. Ningún token en localStorage ni en logs. [COMPLETADO - 2026-10-11]

---

## Fase A3 — Integridad de dominio y permisos
**Duración estimada:** 3-4 días  
**Prioridad:** 🔴 P0

- [x] Re-auditoría de `UniqueConstraint` en `Review` (user + book) y `UserBook`.
- [x] Verificar que no existen signals destructivas o bucles de sincronización rating/notas.
- [x] Cálculo eficiente y cacheado de `average_rating` (evitar `book.save()` completo en cada review con `Book.objects.filter().update()`).
- [x] Validación estricta de media (MIME real, tamaño máximo, prevención de SSRF en enrichment de portadas con `validate_safe_external_url`).
- [x] Throttling agresivo en endpoints costosos (`book_import: 10/hour`, `enrichment: 20/hour`, `author_claims: 5/hour`).
- [x] Revisión de permisos: `IsOwnerOrReadOnly`, roles editor/moderador, IDOR en perfiles, listas y mensajes.
- [x] Política de bloqueo social: respuesta 404 (no filtrar existencia) confirmada y testeada.
- [x] Soft-delete correcto en reseñas, comentarios y publicaciones de autor.

**Criterio de salida:** Tests de integridad + seguridad (IDOR, permisos, injection) al 100 %. [COMPLETADO - 2026-10-11]

---

## Fase A4 — Health, readiness y superficie de ataque
**Duración estimada:** 1-2 días  
**Prioridad:** 🔴 P0

- [x] `/health/live` y `/health/ready` no filtran información interna; códigos 200/503 correctos.
- [x] Endpoints de métricas y observabilidad restringidos a personal autorizado.
- [x] Eliminación o protección de cualquier endpoint de depuración residual.
- [x] Revisión de OpenAPI / schema público (no exponer información sensible).
- [x] Checklist OWASP Top 10 aplicado y documentado.

**Criterio de salida:** Smoke de seguridad + healthchecks validados en staging. [COMPLETADO - 2026-10-11]

---

# BLOQUE B — Infraestructura y operación de producción (P0 → P1)

## Fase B1 — Docker y orquestación de producción
**Duración estimada:** 3-4 días  
**Prioridad:** 🔴 P0 / 🟠 P1

- [x] Validación end-to-end de `docker-compose.prod.yml`:
  - Nginx como único punto de entrada (80/443).
  - Backend, Celery, PostgreSQL y Redis sin puertos públicos.
  - Redes `frontend_net` y `backend_net` (internal).
  - Usuario no-root en todos los contenedores de aplicación.
  - Healthchecks, `stop_signal` y `stop_grace_period`.
  - Límites de CPU y memoria.
- [x] Secrets management (Docker secrets o solución equivalente; nunca `.env` en claro en prod).
- [x] Configuración de SSL/TLS (certificados, renovación automática).
- [x] Upstream balanceado y `limit_req_zone` en Nginx.
- [x] Scripts de preflight y smoke de producción.

**Criterio de salida:** Entorno de staging idéntico a producción levantado y validado. [COMPLETADO - 2026-10-12]

---

## Fase B2 — Backups, restore y disaster recovery
**Duración estimada:** 2-3 días  
**Prioridad:** 🔴 P0

- [x] Backup automático diario de PostgreSQL (cifrado) + retención configurable.
- [x] Backup de volumen `media/` y de configuración crítica.
- [x] Procedimiento de restore documentado y **probado** en entorno limpio.
- [x] Definición de RPO / RTO y monitorización de fallos de backup.
- [x] Script de verificación de integridad post-restore (usuarios, libros, reseñas, mensajes).

**Criterio de salida:** Restore completo ejecutado con éxito al menos una vez en staging. [COMPLETADO - 2026-10-12]

---

## Fase B3 — Observabilidad y alertas
**Duración estimada:** 2-3 días  
**Prioridad:** 🟠 P1

- [x] Logs JSON estructurados sin secretos ni PII.
- [x] Métricas de sistema (CPU, memoria, Redis, colas Celery, latencia p95/p99).
- [x] Métricas de producto (signups, retención D1/D7/D30, embudo, errores 5xx).
- [x] Alertas mínimas accionables (disco, memoria Redis, cola saturada, tasa de error).
- [x] Integración con herramienta de error tracking (Sentry o equivalente).
- [x] Runbooks de incidentes comunes.

**Criterio de salida:** Dashboard operativo + al menos 5 alertas configuradas y probadas. [COMPLETADO - 2026-10-12]

---

## Fase B4 — Escalabilidad básica
**Duración estimada:** 3-5 días  
**Prioridad:** 🟠 P1

- [x] Colas Celery separadas (`default`, `books`, `ai`, `recommendations`, `emails`) ya existentes → validar bajo carga.
- [x] Primary/Replica router de PostgreSQL (si aplica) y configuración de réplicas de lectura.
- [x] Upstream Nginx con varios workers Daphne.
- [x] Estrategia de caché L2 (Redis) y invalidación en cascada revisada.
- [x] Script de carga concurrente y definición de SLAs (p95/p99).
- [x] Documentación de scaling horizontal de workers y de frontend.

**Criterio de salida:** Informe de carga con SLAs cumplidos en staging. [COMPLETADO - 2026-10-12]

---

# BLOQUE C — Calidad y deuda técnica (P1)

## Fase C1 — Suite de tests y calidad de código
**Duración estimada:** 5-7 días  
**Prioridad:** 🟠 P1

- [x] Tests de carga (Locust/k6) sobre listados, feed, búsqueda y chat (`scripts/load_testing/locustfile.py`, `run_locust_headless.py`, `load_test_benchmark.py`).
- [x] Tests e2e críticos: registro/login → biblioteca → reseña → post/chat ws-ticket → feed → perfil (`test_phase_c1_e2e_critical_flow.py`).
- [x] Cobertura de backend (126 tests pytest 100% verde) y frontend (24 archivos vitest, 93 tests 100% verde) documentada (`docs/testing/test_coverage_and_quality_report.md`).
- [x] Erradicación de N+1 residuales con complejidad constante $O(1)$ en `BookSerializer` validada con `CaptureQueriesContext` (`test_phase_c1_query_optimization.py`).
- [x] Paginación global y filtros consistentes en todos los listados.
- [x] Linting estricto: Ruff (Backend 0 errors, All checks passed!) y ESLint (Frontend 0 errors).
- [x] CI/CD: pipelines modulares y validación local de integración continua.
- [x] Rebranding y unificación de marca/variables: migración exhaustiva a My Book Social (`mybooksocial.com`) en todo el código base y variables de entorno.

**Criterio de salida:** CI 100 % verde + informe de cobertura + informe de performance. [COMPLETADO - 2026-10-12]

---

## Fase C2 — Documentación y gobernanza
**Duración estimada:** 2-3 días  
**Prioridad:** 🟠 P1

- [x] Actualización de ADRs existentes y creación de los pendientes (ADRs 009 a 013 e índice en `docs/decisions/`).
- [x] Runbooks de operación (restore, rotación de secrets, scaling, incidentes) en `docs/devops/operations_runbook.md`.
- [x] Guía de contribución y de onboarding de agentes/desarrolladores en `CONTRIBUTING.md`.
- [x] Sincronización de `memory.md`, `CHANGELOG.md` y este `Roadmap.md`.
- [x] Versionado SemVer estricto y política de release en `docs/development/versioning_and_release_policy.md`.

**Criterio de salida:** Documentación operativa completa y accesible en `docs/`. [COMPLETADO - 2026-10-12]

---

# BLOQUE D — Endurecimiento de producto core (P1)

> Solo se ejecuta tras completar los Bloques A–C.

## Fase D1 — Perfil de lector y privacidad
**Duración estimada:** 3-4 días  
**Prioridad:** 🟠 P1

- [x] Perfil público/privado/amigos completamente funcional y consistente (`users/privacy_service.py`, `Profile.tsx`).
- [x] Estadísticas de lectura, libros leídos/leyendo/pendientes, reseñas y actividad con protección `reading_privacy_level` (ocultas para terceros si es privado).
- [x] Avatar, biografía, ubicación y fecha de nacimiento con control granular de privacidad y ofuscación de PII (`apply_profile_field_visibility`).
- [x] Exportación RGPD (Art. 20 con filename `mybooksocial_data_export_{username}.json` y metadatos `My Book Social`) y eliminación/anonimización (Art. 17).
- [x] Tests de visibilidad, aislamiento y bloqueos (`backend/tests/test_phase_d1_reader_profile_and_privacy.py`).

**Criterio de salida:** Suite de visibilidad y RGPD 100% verde + cero fugas de datos privados. [COMPLETADO - 2026-10-12]

---

## Fase D2 — Autores y catálogo
**Duración estimada:** 4-5 días  
**Prioridad:** 🟠 P1

- [x] Relación Book ↔ Author multi-rol (autor, coautor, traductor, ilustrador, narrador…) con modelo `BookContribution` y sincronización automática.
- [x] Sistema de normalización y equivalencia matemática determinista ISBN-10 / ISBN-13 (`isbn10_to_isbn13`, `isbn13_to_isbn10`) y búsqueda cruzada en catálogo (`Book.find_by_isbn`).
- [x] Deduplicación atómica de catálogo (`merge_books`) preservando ISBNs absorbidos, reseñas, estanterías y datos de usuarios sin colisiones.
- [x] Resolución de conteo de páginas (`page_count`): persistencia en enriquecimiento (Google Books / OpenLibrary), auto-detección de metadatos faltantes en `BookDetailView` y renderizado en UI de perfil de libro (`📄 {page_count} páginas` y tracking de lectura).
- [x] Suite de pruebas exhaustiva (`backend/tests/test_phase_d2_authors_and_catalog.py`) 100% verde (6/6 passed).

**Criterio de salida:** Suite de autores, catálogo y conteo de páginas 100% verde + interoperabilidad multi-rol y equivalencia ISBN. [COMPLETADO - 2026-10-12]

---

## Fase D3 — Reseñas, social y feed
**Duración estimada:** 4-5 días  
**Prioridad:** 🟠 P1

- [x] Una reseña activa por usuario/libro (`unique_active_review_user_book`) + reactivación limpia tras soft-delete reutilizando entidad previa sin duplicados.
- [x] Likes únicos e idempotentes (`ReviewLike`) con protección ante bloqueos y agregación atómica de ratings (`update_book_rating`, `recalculate_book_rating_task`).
- [x] Feed social optimizado y blindado (exclusión bidireccional de bloqueados, silenciados, actividades de reseñas borradas/moderadas y privacidad `activity_privacy_level: private`).
- [x] Notificaciones fiables y respetuosas de privacidad (supresión de notificaciones entre usuarios bloqueados y observancia de canales `NotificationPreference`).
- [x] Moderación de contenido re-validada con filtrado automático en feeds públicos y detalle para no-admins.
- [x] Suite de pruebas exhaustiva (`backend/tests/test_phase_d3_reviews_social_feed.py`) 100% verde (7/7 passed).

**Criterio de salida:** Suite de interacción social, reseñas y feed 100% verde + cero filtraciones entre usuarios bloqueados. [COMPLETADO - 2026-10-14]

---

## Fase D4 — Búsqueda, descubrimiento y recomendaciones
**Duración estimada:** 4-6 días  
**Prioridad:** 🟠 P1 / 🟡 P2

- [x] Búsqueda híbrida (`UnifiedSearchEngine`) multicanal (léxica, difusa por trigramas y semántica) estable y resiliente con fallback sin dependencias duras externas.
- [x] Descubrimiento facetado y tendencias públicas (`BookDiscoveryView` en `/api/v1/books/discover/`) con filtrado por género y caché normalizada sin caracteres especiales.
- [x] Motor de recomendaciones con diversidad, exclusión estricta de obras en biblioteca (`UserBook`) y soporte de arranque en frío (*cold-start*) basado en preferencias de onboarding (`favorite_categories`).
- [x] Transparencia ética y explicabilidad algorítmica obligatoria (`reason` en cada ítem y endpoint estructurado `/explain/`).
- [x] Suite de pruebas exhaustiva (`backend/tests/test_phase_d4_search_discovery_recommendations.py`) 100% verde (7/7 passed).

**Criterio de salida de Bloque D:** Catálogo, autores, privacidad, feed, descubrimiento y recomendaciones 100% endurecidos, operables y auditados. [COMPLETADO - 2026-10-12]

---

# BLOQUE E — Pre-producción y lanzamiento público (P1)

## Fase E1 — Staging y smoke tests
**Duración estimada:** 3-4 días  
**Prioridad:** 🟠 P1

- [x] Entorno de staging idéntico a producción y scripts de auditoría preflight (`preflight_staging.sh`, `smoke_test_staging.py`).
- [x] Suite de smoke automatizada (`backend/tests/test_phase_e1_staging_smoke.py`, 8/8 passed) cubriendo liveness, readiness sanitizado, autenticación con cookies HttpOnly seguras y ticket efímero de WebSocket de un solo uso.
- [x] Checklist de seguridad pre-despliegue exhaustivo y firmado (`docs/deployment/pre_deployment_security_checklist.md`).
- [x] Prueba de restore completa auditada con éxito mediante comando `verify_restore_integrity` sobre usuarios, catálogo e interacciones.
- [x] Validación de feature flags de registro público e invitaciones (`PUBLIC_REGISTRATION_ENABLED` y `REQUIRE_BETA_INVITATION`).

**Criterio de salida:** Suite de smoke testing y checklist de pre-despliegue 100% aprobados en staging. [COMPLETADO - 2026-10-13]

---

## Fase E2 — Soft launch y monitorización
**Duración estimada:** 1 semana  
**Prioridad:** 🟠 P1

- [x] Apertura controlada (cohorte o registro público con feature flags `PUBLIC_REGISTRATION_ENABLED` y `REQUIRE_BETA_INVITATION`).
- [x] Monitorización 24/7 de errores, latencia y métricas de negocio mediante `BetaMetricsService` y `BetaAlertsService`.
- [x] Canales de feedback (`BetaFeedback`) y soporte técnico formal (`SupportTicket`) con seguimiento de estado y triaje admin.
- [x] Plan formal de rollback documentado y ensayado (`docs/devops/rollback_and_incident_communication_guide.md`).
- [x] Protocolo y plantillas de comunicación de incidentes (SEV-1/SEV-2, mitigación, resolución y post-mortem).
- [x] Suite de pruebas automatizadas exhaustiva (`backend/tests/test_phase_e2_soft_launch_monitoring.py`) 100% verde (5/5 passed).

**Criterio de salida:** Soft launch operable con observabilidad, canales de soporte/feedback activos y protocolo de rollback ensayado. [COMPLETADO - 2026-10-14]

---

## Fase E3 — General Availability (GA) endurecida
**Duración estimada:** 2-3 días  
**Prioridad:** 🟠 P1

- [ ] Deploy a producción (blue/green o canary si es posible).
- [ ] Verificación post-deploy (smoke + health + métricas).
- [ ] Anuncio de versión y CHANGELOG público.
- [ ] On-call mínimo definido.
- [ ] Cierre formal de la fase de beta.

**Criterio de salida de Bloque E:** Plataforma en producción pública con monitorización activa y capacidad de rollback.

---

# BLOQUE F — Evolución post-lanzamiento (P2 / P3)

## Fase F1 — Rendimiento y experiencia (P2)
- Optimización de Core Web Vitals y Lighthouse.
- Accesibilidad WCAG 2.1 AA.
- Mejoras de UX en onboarding, biblioteca y descubrimiento.
- Caché avanzada y CDN para assets estáticos y media.

## Fase F2 — Producto avanzado (P2 / P3)
- Recomendaciones personalizadas de mayor calidad.
- Clubs de lectura y discusiones estructuradas.
- Marketplace de libros (si se decide monetizar).
- App móvil (PWA o nativa).
- Integraciones adicionales (Goodreads sync bidireccional, librerías, etc.).

## Fase F3 — Escala y organización (P3)
- Multi-región / multi-AZ.
- Separación total de Redis (cache vs Channels vs Celery).
- Observabilidad avanzada (tracing distribuido).
- Equipo de moderación y soporte escalado.
- Modelo de negocio y métricas de unit economics.

---

# Resumen ejecutivo de ejecución

| Bloque | Objetivo principal | Prioridad | Orden |
|--------|--------------------|-----------|-------|
| **A** | Corregir fallos críticos de seguridad e integridad | 🔴 P0 | 1º |
| **B** | Infraestructura, backups y operación | 🔴/🟠 | 2º |
| **C** | Calidad, tests y deuda técnica | 🟠 P1 | 3º |
| **D** | Endurecimiento de producto core | 🟠 P1 | 4º |
| **E** | Staging → Soft launch → GA endurecida | 🟠 P1 | 5º |
| **F** | Evolución post-lanzamiento | 🟡/🟢 | Posterior |

---

## Flujo de trabajo obligatorio por fase

1. Leer `memory.md` e `instruccionesAgente.md`.
2. Redactar y someter a aprobación `implementation_plan.md` de la fase.
3. Implementar en `develop`.
4. Ejecutar tests + linters + typecheck + build.
5. Actualizar `memory.md`, `CHANGELOG.md` y este `Roadmap.md`.
6. Commit semántico + `git push origin develop`.
7. Solo tras validación: merge a `main` y tag de versión si corresponde.

---

## Objetivo final

> **MyBookConnect debe ser una red social literaria sólida, segura, rápida y mantenible**, donde los lectores gestionen su biblioteca, descubran libros y autores, compartan opiniones y se conecten, y donde los autores dispongan de una presencia verificable y herramientas propias.

La prioridad no es acumular funcionalidades.  
La prioridad es que **todo lo que existe funcione correctamente, sea seguro, observable y operable en producción**.

---

*Documento vivo. Debe actualizarse al cierre de cada fase.*
