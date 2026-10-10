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
- [ ] Migrar tokens de acceso/refresh desde `localStorage` (Zustand persist) a cookies `HttpOnly` + `Secure` + `SameSite=Strict` (o patrón híbrido con double-submit).
- [ ] Eliminar cualquier `console.log` o log que contenga tokens.
- [ ] Implementar rotación de refresh token + blacklist (Redis o modelo `OutstandingToken`).
- [ ] Configurar tiempos de vida cortos para access token y razonables para refresh.
- [ ] Actualizar cliente frontend (`client.ts` / interceptores) y store de autenticación.
- [ ] Tests de seguridad: robo de cookie, XSS simulado, rotación y logout.

### WebSockets
- [ ] Eliminar completamente autenticación por query string (`?token=`).
- [ ] Autenticación exclusiva mediante cookie HttpOnly o ticket de corta duración emitido por endpoint autenticado.
- [ ] Rate limiting / backpressure por conexión y por usuario.
- [ ] Tamaño máximo de mensaje y rechazo de acciones desconocidas.
- [ ] Manejo robusto de desconexiones y reconexión.
- [ ] Tests de abuso, usuarios bloqueados y payloads malformados.

### Cookies y headers
- [ ] Confirmar `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS, CSP, COOP.
- [ ] Revisar CORS y CSRF en el contexto de cookies cross-origin si aplica.

**Criterio de salida:** Suite de autenticación y WebSocket abuse al 100 %. Ningún token en localStorage ni en logs.

---

## Fase A3 — Integridad de dominio y permisos
**Duración estimada:** 3-4 días  
**Prioridad:** 🔴 P0

- [ ] Re-auditoría de `UniqueConstraint` en `Review` (user + book) y `UserBook`.
- [ ] Verificar que no existen signals destructivas o bucles de sincronización rating/notas.
- [ ] Cálculo eficiente y cacheado de `average_rating` (evitar `book.save()` completo en cada review).
- [ ] Validación estricta de media (MIME real, tamaño máximo, prevención de SSRF en enrichment de portadas).
- [ ] Throttling agresivo en endpoints costosos (import, enrichment, claim de autor, reportes).
- [ ] Revisión de permisos: `IsOwnerOrReadOnly`, roles editor/moderador, IDOR en perfiles, listas y mensajes.
- [ ] Política de bloqueo social: respuesta 404 (no filtrar existencia) confirmada y testeada.
- [ ] Soft-delete correcto en reseñas, comentarios y publicaciones de autor.

**Criterio de salida:** Tests de integridad + seguridad (IDOR, permisos, injection) al 100 %.

---

## Fase A4 — Health, readiness y superficie de ataque
**Duración estimada:** 1-2 días  
**Prioridad:** 🔴 P0

- [ ] `/health/live` y `/health/ready` no filtran información interna; códigos 200/503 correctos.
- [ ] Endpoints de métricas y observabilidad restringidos a personal autorizado.
- [ ] Eliminación o protección de cualquier endpoint de depuración residual.
- [ ] Revisión de OpenAPI / schema público (no exponer información sensible).
- [ ] Checklist OWASP Top 10 aplicado y documentado.

**Criterio de salida:** Smoke de seguridad + healthchecks validados en staging.

---

# BLOQUE B — Infraestructura y operación de producción (P0 → P1)

## Fase B1 — Docker y orquestación de producción
**Duración estimada:** 3-4 días  
**Prioridad:** 🔴 P0 / 🟠 P1

- [ ] Validación end-to-end de `docker-compose.prod.yml`:
  - Nginx como único punto de entrada (80/443).
  - Backend, Celery, PostgreSQL y Redis sin puertos públicos.
  - Redes `frontend_net` y `backend_net` (internal).
  - Usuario no-root en todos los contenedores de aplicación.
  - Healthchecks, `stop_signal` y `stop_grace_period`.
  - Límites de CPU y memoria.
- [ ] Secrets management (Docker secrets o solución equivalente; nunca `.env` en claro en prod).
- [ ] Configuración de SSL/TLS (certificados, renovación automática).
- [ ] Upstream balanceado y `limit_req_zone` en Nginx.
- [ ] Scripts de preflight y smoke de producción.

**Criterio de salida:** Entorno de staging idéntico a producción levantado y validado.

---

## Fase B2 — Backups, restore y disaster recovery
**Duración estimada:** 2-3 días  
**Prioridad:** 🔴 P0

- [ ] Backup automático diario de PostgreSQL (cifrado) + retención configurable.
- [ ] Backup de volumen `media/` y de configuración crítica.
- [ ] Procedimiento de restore documentado y **probado** en entorno limpio.
- [ ] Definición de RPO / RTO y monitorización de fallos de backup.
- [ ] Script de verificación de integridad post-restore (usuarios, libros, reseñas, mensajes).

**Criterio de salida:** Restore completo ejecutado con éxito al menos una vez en staging.

---

## Fase B3 — Observabilidad y alertas
**Duración estimada:** 2-3 días  
**Prioridad:** 🟠 P1

- [ ] Logs JSON estructurados sin secretos ni PII.
- [ ] Métricas de sistema (CPU, memoria, Redis, colas Celery, latencia p95/p99).
- [ ] Métricas de producto (signups, retención D1/D7/D30, embudo, errores 5xx).
- [ ] Alertas mínimas accionables (disco, memoria Redis, cola saturada, tasa de error).
- [ ] Integración con herramienta de error tracking (Sentry o equivalente).
- [ ] Runbooks de incidentes comunes.

**Criterio de salida:** Dashboard operativo + al menos 5 alertas configuradas y probadas.

---

## Fase B4 — Escalabilidad básica
**Duración estimada:** 3-5 días  
**Prioridad:** 🟠 P1

- [ ] Colas Celery separadas (`default`, `books`, `ai`, `recommendations`, `emails`) ya existentes → validar bajo carga.
- [ ] Primary/Replica router de PostgreSQL (si aplica) y configuración de réplicas de lectura.
- [ ] Upstream Nginx con varios workers Daphne.
- [ ] Estrategia de caché L2 (Redis) y invalidación en cascada revisada.
- [ ] Script de carga concurrente y definición de SLAs (p95/p99).
- [ ] Documentación de scaling horizontal de workers y de frontend.

**Criterio de salida:** Informe de carga con SLAs cumplidos en staging.

---

# BLOQUE C — Calidad y deuda técnica (P1)

## Fase C1 — Suite de tests y calidad de código
**Duración estimada:** 5-7 días  
**Prioridad:** 🟠 P1

- [ ] Tests de carga (Locust/k6) sobre listados, feed, búsqueda y chat.
- [ ] Tests e2e críticos (Playwright o Cypress): registro/login → biblioteca → reseña → chat → perfil.
- [ ] Cobertura de backend y frontend por encima de umbral definido (documentar).
- [ ] Erradicación de N+1 residuales (especialmente autores, feed y muro).
- [ ] Paginación global y filtros consistentes en todos los listados.
- [ ] Linting estricto: Ruff + mypy (backend), ESLint + TypeScript strict (frontend).
- [ ] CI/CD: pipelines modulares verdes (`ci-backend`, `ci-frontend`, `ci-docker`, `security`).
- [ ] Actualización y merge de Dependabot PRs pendientes.

**Criterio de salida:** CI 100 % verde + informe de cobertura + informe de performance.

---

## Fase C2 — Documentación y gobernanza
**Duración estimada:** 2-3 días  
**Prioridad:** 🟠 P1

- [ ] Actualización de ADRs existentes y creación de los pendientes.
- [ ] Runbooks de operación (restore, rotación de secrets, scaling, incidentes).
- [ ] Guía de contribución y de onboarding de agentes/desarrolladores.
- [ ] Sincronización de `memory.md`, `CHANGELOG.md` y este `Roadmap.md`.
- [ ] Versionado SemVer estricto y política de release.

**Criterio de salida:** Documentación operativa completa y accesible en `docs/`.

---

# BLOQUE D — Endurecimiento de producto core (P1)

> Solo se ejecuta tras completar los Bloques A–C.

## Fase D1 — Perfil de lector y privacidad
**Duración estimada:** 3-4 días  
**Prioridad:** 🟠 P1

- [ ] Perfil público/privado/amigos completamente funcional y consistente.
- [ ] Estadísticas de lectura, libros leídos/leyendo/pendientes, reseñas y actividad.
- [ ] Avatar, biografía, ubicación y fecha de nacimiento con control de privacidad.
- [ ] Exportación RGPD (Art. 20) y eliminación/anonimización (Art. 17) ya existentes → re-validación.
- [ ] Tests de visibilidad y bloqueos.

---

## Fase D2 — Autores y catálogo
**Duración estimada:** 4-5 días  
**Prioridad:** 🟠 P1

- [ ] Relación Book ↔ Author multi-rol (autor, coautor, traductor, ilustrador, narrador…).
- [ ] Sistema de aliases y normalización de nombres para evitar duplicados.
- [ ] Reclamo y verificación de autor (flujo ya existente) → endurecimiento de moderación.
- [ ] Deduplicación final de catálogo (ISBN + título normalizado + autor).
- [ ] Publicaciones de autor, newsletters y monetización básica (si aplica) con moderación.

---

## Fase D3 — Reseñas, social y feed
**Duración estimada:** 4-5 días  
**Prioridad:** 🟠 P1

- [ ] Una reseña activa por usuario/libro + soft-delete limpio.
- [ ] Likes únicos y agregaciones de rating eficientes.
- [ ] Feed social optimizado (exclusión de bloqueados/silenciados, paginación, caché).
- [ ] Notificaciones fiables (in-app + preferencias de email/push).
- [ ] Moderación de contenido (reportes, cola admin, AuditLog) re-validada.

---

## Fase D4 — Búsqueda, descubrimiento y recomendaciones
**Duración estimada:** 4-6 días  
**Prioridad:** 🟠 P1 / 🟡 P2

- [ ] Búsqueda híbrida (trigramas + embeddings) estable y rápida.
- [ ] Descubrimiento facetado y tendencias públicas.
- [ ] Motor de recomendaciones: diversidad, penalización de ya vistos, afinidad temporal y cold-start.
- [ ] Transparencia ética de la IA (explicabilidad mínima).

---

# BLOQUE E — Pre-producción y lanzamiento público (P1)

## Fase E1 — Staging y smoke tests
**Duración estimada:** 3-4 días  
**Prioridad:** 🟠 P1

- [ ] Entorno de staging idéntico a producción.
- [ ] Suite de smoke automatizada (API + frontend + WebSocket + backup).
- [ ] Checklist de seguridad pre-despliegue.
- [ ] Prueba de restore completa.
- [ ] Validación de feature flags de registro público / invitación.

---

## Fase E2 — Soft launch y monitorización
**Duración estimada:** 1 semana  
**Prioridad:** 🟠 P1

- [ ] Apertura controlada (cohorte o registro público con feature flag).
- [ ] Monitorización 24/7 de errores, latencia y métricas de negocio.
- [ ] Canal de feedback (BetaFeedback / SupportTicket) activo.
- [ ] Plan de rollback documentado y ensayado.
- [ ] Comunicación de incidentes preparada.

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
