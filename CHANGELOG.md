# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning 2.0.0](https://semver.org/lang/es/).

## [Unreleased]

### Planned
- Notificaciones push mediante Web Push API.
- Internacionalización ampliada (soporte multi-idioma i18n).

---

## [1.0.0-rc1] - 2026-09-30

### Added
- **Monetización Ética y Plataforma de Autores (Fase 31)**:
  - Tag de afiliación de Amazon configurable (`AMAZON_AFFILIATE_TAG` con fallback `mybooksocial-21`).
  - Enlaces multiformato transparentes (papel, Kindle ebook, Audible audiolibro) con aviso legal obligatorio y endpoint dedicado `/api/v1/books/<id>/affiliate-links/`.
  - Plataforma de Autores: modelo `AuthorProfile`, comunicados oficiales (`AuthorAnnouncement`), solicitud de reclamo (`/claim/`) y panel de control (`/dashboard/`).
  - Modelo base de suscripciones (`UserSubscription`) y neutralidad algorítmica garantizada en recomendaciones.
- **Soporte Multi-autor, Muro Social y Reseñas en Perfil (Fase 32)**:
  - Compatibilidad completa de múltiples autores por libro (`Book.authors` ManyToMany) manteniendo retrocompatibilidad transparente con `Book.author`.
  - Pestaña de reseñas en el perfil de usuario con endpoints `/api/v1/reviews/?user=<id>` y `/api/v1/users/<id>/reviews/`.
  - Muro interactivo de publicaciones (`UserPost`), comentarios sanitizados (`UserPostComment`), likes (`UserPostLike`) y actividad social `POST_CREATED` en el feed.
  - Ponderación de afinidad multi-autor en el motor híbrido de recomendaciones.
- **Calidad Avanzada y Prevención de N+1 (Fase 33)**:
  - Validación formal de contratos OpenAPI 3.0 con `drf-spectacular` frente a modelos y respuestas reales.
  - Flujo de integración continuo de extremo a extremo (E2E User Journey de 7 pasos).
  - Guardrails de seguridad contra IDOR, inyecciones de script/XSS y revocación de tokens JWT en blacklist.
  - Erradicación de consultas N+1 con complejidad estrictamente $O(1)$ en muro social, listado de reseñas y feed mediante optimización de prefetch cache y ciclo de vida de petición.
  - Script reproducible de prueba de carga concurrente y SLAs (`scripts/load_testing/load_test_benchmark.py`).
- **Consolidación y Release Candidate 1 (Fase 34)**:
  - Sincronización formal de versión SemVer 2.0.0 `1.0.0-rc1` en backend y frontend.
  - Suite de validación de Release Candidate (`test_phase34_release_candidate.py`).
  - Verificación automatizada de DoD y script de preflight.
  - Guía completa de congelación de código (*code freeze*) y despliegue de RC1 (`docs/deployment/release_candidate_guide.md`).
- **Despliegue y Validación en Staging (Beta Cerrada) (Fase 35)**:
  - Script de smoke testing automatizado de staging (`scripts/staging/smoke_test_staging.py` y `.sh`) validando sondas de liveness, readiness, versión, catálogo y códigos de invitación beta.
  - Script de auditoría pre-despliegue de staging (`scripts/staging/preflight_staging.sh`) con validación de PostgreSQL, Redis, migraciones y Django deploy checks.
  - Suite de pruebas de integración de ciclo de vida beta (`test_phase35_staging_validation.py`) para validación de invitaciones (`BetaInvitation`), feedback in-app (`BetaFeedback`) y soporte (`SupportTicket`).
  - Guía operativa de despliegue en staging (`docs/deployment/staging_deployment_guide.md`).
- **Apertura de Cohorte Beta Cerrada y Monitorización (Fase 36)**:
  - Comando CLI `generate_beta_cohort` para emisión masiva de invitaciones por lotes con prefijo de cohorte, expiración y exportación opcional JSON/CSV.
  - Servicio de métricas `BetaMetricsService` y endpoint administrativo `/api/v1/beta/admin/metrics/` con cálculo de tasa de activación, distribución de feedback y tickets de soporte.
  - Servicio de triaje y alertas inmediatas `BetaAlertsService` con hooks en feedback (`BUG`) y soporte urgente (`CRITICAL`/`HIGH`) en `/api/v1/beta/admin/alerts/`.
  - Guía operativa de gestión y monitorización de la beta cerrada (`docs/deployment/closed_beta_operations_guide.md`).

---

## [1.0.0] - 2026-09-20

### Added
- **Catálogo de Libros y Autores**: Búsqueda difusa (TrigramSimilarity), filtros por género/categoría, paginación con cursor y offset, y sincronización asíncrona mediante Celery.
- **Reseñas y Calificaciones**: CRUD de reseñas, cálculo atómico de promedios de calificación, likes en reseñas y prevención de votos duplicados.
- **Sistema Social y Comunidad**:
  - Seguimiento entre usuarios (Followers/Following) con recuentos cacheados e invalidación atómica.
  - Muro de actividad / feed de lectura personalizado.
  - Clubes de lectura con foros de discusión y gestión de miembros.
  - Mensajería directa en tiempo real con WebSockets (Django Channels) y persistencia en base de datos.
- **Gamificación y Metas**:
  - Desafíos anuales de lectura y seguimiento de progreso de lectura.
  - Sistema de insignias (badges) y puntos por actividad lectora.
- **Seguridad y Moderación**:
  - Autenticación JWT con refresh tokens en rotación y blacklist.
  - Rate limiting adaptativo por endpoint y protección CSRF/CORS estricta.
  - Sistema de reportes de usuarios y moderación de contenido con soft-delete.
  - Política de cookies con consentimiento granular y banner legal (RGPD/LSSI-CE).
- **Rendimiento, Caché y Concurrencia**:
  - Estrategia de caché Redis multi-capa con invalidación granular orientada a eventos.
  - Bloqueo optimista y transacciones atómicas (`select_for_update`) contra condiciones de carrera.
  - Paginación optimizada para colecciones masivas.
- **Alta Disponibilidad y Operaciones**:
  - Endpoints de salud: liveness (`/api/v1/health/`), readiness (`/api/v1/ready/`) y versión (`/api/v1/version/`).
  - Servicios y comandos de backup automatizado para PostgreSQL y medios (`backup_db`, `backup_media`).
  - Plan de Recuperación ante Desastres (DRP) documentado con 5 runbooks y comando de reconstrucción de caché (`rebuild_cache`).
  - Métricas de observabilidad en tiempo real (`/api/v1/observability/metrics/`).
- **Frontend SPA React**:
  - Arquitectura moderna con React 18, Vite, TypeScript, TailwindCSS y Zustand.
  - TanStack Query con revalidación optimista y caché sincronizada.
  - Diseño responsivo, tema dark/light, microinteracciones y accesibilidad WCAG 2.1 AA.

### Changed
- Estandarización de versionado bajo Semantic Versioning 2.0.0 unificado en backend (`pyproject.toml`, `mybookconnect.version`) y frontend (`package.json`).
- Centralización de variables de entorno y endurecimiento de configuraciones de despliegue en Docker Compose para producción.

---

[Unreleased]: https://github.com/Zaton81/MyBookConnect/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Zaton81/MyBookConnect/releases/tag/v1.0.0
