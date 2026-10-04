# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning 2.0.0](https://semver.org/lang/es/).

## [Unreleased]

### Added / Legal & Privacy (RoadmapV3 - Sección 26: Legal y Privacidad, RGPD, Portabilidad y Eliminación)
- **Gestión de Documentos Normativos y Corpus Legal**:
  - Modelo `LegalDocument` gestionando documentos clave del servicio: Términos de uso (`terms`), Política de privacidad (`privacy`), Política de cookies (`cookies`), Aviso legal (`legal_notice`), Política de contenidos (`content_policy`), Política de cancelación (`deletion_policy`) y Canal de contacto (`contact`).
  - Endpoints públicos versionados en `/api/v1/books/legal/` y `/api/v1/books/legal/<slug>/`.
  - Edición administrativa autorizada en `/api/v1/admin/legal/<slug>/` con incremento automático de versión y fecha de actualización.
- **Portabilidad de Datos RGPD (`GET /api/v1/users/account/export/`)**:
  - Endpoint seguro de descarga estructurada de datos personales en formato JSON estándar.
  - Exportación consolidada de perfil, estanterías y progreso de lectura, reseñas, comentarios, listas de lectura y red social (seguidores/seguidos).
- **Derecho al Olvido y Eliminación de Cuenta (`POST /api/v1/users/account/delete/`)**:
  - Eliminación segura con re-autenticación obligatoria mediante contraseña actual para mitigar secuestro de sesión.
  - Anonimización de identificadores y revocación inmediata de credenciales activas.
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint8_legal_and_privacy.py` (4 pruebas al 100%).
  - Regresión secuencial completa de backend superada (59 pruebas pasando de Sprints 1 a 8).
  - Frontend verificado: TypeScript estricto con 0 errores, 42 tests en Vitest pasando al 100% y build de producción Vite exitoso.

### Added / Administration & Moderation (RoadmapV3 - Secciones 24 y 25: Administración, Moderación y Reportes Universales)
- **Sistema Universal de Reportes y Moderación**:
  - Ampliado `ReportCreateSerializer` y `ALLOWED_TARGET_MODELS` para admitir reportes sobre `Book`, `Author` y `UserPost` (publicaciones en muro), además de usuarios, reseñas, comentarios, mensajes y listas.
  - Vistas previas enriquecidas en la cola de moderación (`ReportListSerializer.get_target_preview`) con datos contextuales específicos (título/ISBN/autor para libros, biografía/verificación para autores, snippets para publicaciones).
  - Bloqueo riguroso de auto-denuncias y de denuncias duplicadas pendientes en todos los tipos de contenido.
  - Acciones disciplinarias completas (`HIDE_CONTENT`, `RESTORE_CONTENT`, `BAN_USER`, `MUTE_USER_24H/7D`, `DISMISS`) registradas en la auditoría con manejo seguro de transacciones.
- **Endpoints Administrativos de Catálogo y Usuarios**:
  - `POST /api/v1/admin/books/merge/`: Fusión atómica de libros duplicados (`merge_books`), consolidando múltiples ISBNs en `additional_isbns`, reasignando estanterías (`UserBook`), reseñas y listas de lectura sin pérdida de datos.
  - `POST /api/v1/admin/authors/merge/`: Fusión atómica de autores homónimos, unificando aliases, transfiriendo obras literarias y preservando verificaciones y reclamaciones oficiales.
  - `GET /api/v1/admin/users/<pk>/activity/`: Auditoría de actividad cronológica de usuarios investigados (`Activity`, `UserPost` y `Review`).
  - `GET /api/v1/admin/users/<pk>/reports/`: Consulta unificada de denuncias emitidas y recibidas por un usuario.
- **Frontend Admin Dashboard (`AdminDashboard.tsx`)**:
  - Filtros y badges para denuncias de libros, autores, publicaciones y listas.
  - Renderizado contextual de previews para cada tipo de contenido en la tabla de denuncias.
- **Pruebas y Verificación**:
  - Creada suite `backend/tests/test_sprint7_admin_and_moderation.py` (5 pruebas pasando al 100%).
  - Suite de regresión secuencial de Sprints 1 a 7 ejecutada con éxito (55 pruebas pasando al 100%).
  - Tipado de TypeScript estricto validado con 0 errores (`tsc --noEmit`), 42 pruebas de Vitest superadas y build de producción Vite exitoso.

### Added / Preproduction (RoadmapV3 - Sprint 6: Preproducción, Deploy Checks, Smoke Tests E2E y Ready for Production)
- **Verificación y Sanitización de Despliegue en Django**:
  - `python manage.py check`: 0 issues de integridad de modelos o dependencias.
  - `python manage.py makemigrations --check`: Garantía de sincronización absoluta entre modelos y esquemas de base de datos sin migraciones pendientes.
  - `python manage.py check --deploy`: Configuración verificada con HSTS, secure cookies, SSL redirects y security headers sin advertencias críticas de producción.
- **Suite de Smoke Tests E2E (`test_sprint6_preproduction_readiness.py`)**:
  - `test_e2e_user_journey_auth_and_session`: Registro con contraseñas seguras, autenticación JWT, obtención de access/refresh tokens y logout con revocación a lista negra.
  - `test_e2e_catalog_search_and_reading_flow`: Búsqueda de obras unificadas físico/digital, detalle de libro, adición a estantería de lectura, registro de avance y reseña protegida contra XSS.
  - `test_e2e_social_interaction_and_feed`: Seguimientos mutuos entre lectores comunitarios y consulta de feed de actividad enriquecido.
  - `test_e2e_author_claim_to_verification_flow`: Solicitud formal de reclamación de perfil de autor (`AuthorClaim`), moderación y resolución administrativa, activación de insignia de verificación y asignación de permisos de autor.
  - `test_e2e_faqs_and_support_flow`: Centro de ayuda con FAQs públicas categorizadas, ordenadas y filtrables.
  - `test_production_health_and_readiness_probes`: Probes de observabilidad de liveness y readiness sanitizados sin fugas de secretos en producción.
- **Regresión y Calidad Completa**:
  - 50 pruebas backend en Pytest cubriendo de forma secuencial Sprints 1 al 6 con 100% de éxito.
  - Frontend validado con TypeScript estricto (`tsc --noEmit`, 0 errores), 42 pruebas en Vitest pasando al 100% y bundle de producción Vite compilado limpiamente.
  - Actualizados `RoadmapV3.md` y `memory.md` reflejando el cumplimiento total de los criterios de Ready for Production.

### Added / Quality & Performance (RoadmapV3 - Sprint 5: Calidad, Rendimiento, Accesibilidad WCAG y Testing)
- **Erradicación de Consultas N+1 en Búsqueda Global y Catálogo**:
  - `GlobalSearchView` (`books/search_views.py`) optimizado para precomputar en una única consulta batch las distribuciones de calificación (`rating_distribution`) y conteos de reseñas (`reviews_count`), asignándolas a `_precomputed_rating_distribution` y `annotated_reviews_count` de cada libro.
  - Soporte en `BookSerializer` para reutilizar propiedades precomputadas, evitando 2 consultas SQL adicionales por cada libro devuelto.
  - Inclusión de `.select_related('claimed_by')` y `.prefetch_related('books', 'all_books')` en consultas de autores, fijando el coste en un número constante de queries (≤ 3) independientemente del volumen de datos.
- **Accesibilidad Web WCAG 2.1 AA en Frontend**:
  - `SearchPage` y `FaqsPage` provistas de roles semánticos WAI-ARIA (`role="search"`, `role="tablist"`, `role="tab"`, `aria-selected`, `aria-expanded`, `aria-controls`, `aria-label`).
  - Navegación completa por teclado con anillos de enfoque `focus-visible:ring-2 focus-visible:ring-teal-500` de alto contraste en formularios, botones y acordeones.
- **Limpieza Estricta de TypeScript (`tsc --noEmit`)**:
  - Subsanados todos los avisos de `noUnusedLocals` en componentes clave de frontend (`AdminAuthorClaimsTab.tsx`, `Author.tsx`, `SearchPage.tsx`, `FaqsPage.tsx`), logrando salida con código 0 limpio sin dependencias superfluas.
- **Suites de Pruebas Unitarias e Integración**:
  - **Frontend (Vitest)**: Nuevos tests unitarios y de interacción en `SearchPage.test.tsx` (5 pruebas) y `FaqsPage.test.tsx` (6 pruebas), elevando la suite a 13 archivos y 42 tests pasando al 100%.
  - **Backend (Pytest)**: Creada suite `test_sprint5_quality_and_performance.py` (5 pruebas) evaluando erradicación de N+1 con `django_assert_max_num_queries`, defensas XSS contra inyecciones maliciosas (`sanitize_plain_text`, `sanitize_html`), y ordenamiento/filtros del endpoint de FAQs.
  - Validación completa secuencial de la suite de regresión de Sprints 1 a 5 (44 tests superados sin bloqueos de base de datos).

### Added / Catalog (RoadmapV3 - Sprint 4: Catálogo, Unificación de Ediciones P1 y Búsqueda Global)
- **Unificación Canónica de Obras y Ediciones Literarias**:
  - Incorporada normalización fonética y ortográfica de títulos (`normalize_title`) tolerante a mayúsculas, signos de puntuación, dobles espacios y caracteres diacríticos.
  - Añadido campo `additional_isbns = models.JSONField(default=list)` en `Book` para almacenar y relacionar múltiples ISBNs (ediciones físicas, digitales Kindle/ePub, bolsillo, audiolibros) bajo una única ficha maestra.
  - Métodos `Book.add_isbn(new_isbn)`, `Book.get_all_isbns()` y `Book.find_by_isbn(query)` para resolver y buscar libros por cualquier edición de manera transparente.
  - Blindaje en `BookSerializer.create`, `import_service.py` y `csv_import_service.py` para unificar automáticamente cualquier libro entrante cuyo autor y título coincidan, impidiendo la fragmentación de reseñas y estanterías.
- **Servicio y Herramienta de Fusión Atómica de Duplicados**:
  - Implementado `deduplication_service.py` con `find_duplicate_books()`, `merge_books()` y `deduplicate_all_books()`.
  - Reubicación transaccional y atómica de dependencias foráneas (`UserBook` preservando estados más avanzados y mejores notas, `Review`, `ReadingListItem`, `UserPost`, `Activity`, portadas y categorías).
  - Comando Django `python manage.py deduplicate_catalog [--dry-run]` ejecutado con éxito en base de datos real (21 obras maestras consolidadas, 25 duplicados redundantes eliminados, 0 duplicados restantes).
- **Búsqueda Global Unificada (`/api/v1/search/`)**:
  - Endpoint `GlobalSearchView` en backend que devuelve en una sola consulta categorizada libros (con ISBNs unificados), autores (con estadísticas editoriales y verificación) y lectores comunitarios (respetando privacidad RGPD y bloqueos mutuos).
  - Nueva página en frontend `/search` (`SearchPage.tsx`) con buscador reactivo, pestañas interactivas ("Todo", "Libros", "Autores", "Lectores"), badges de ediciones unificadas y diseño premium.
  - Enlaces integrados en `Header.tsx` y `PublicHeader.tsx`.
- **Suite de Pruebas**:
  - Añadida suite `backend/tests/test_sprint4_catalog_deduplication.py` con 9 pruebas de integración y API cubriendo normalización, unificación por serializer, fusiones atómicas y endpoint global.

### Added / Infrastructure (RoadmapV3 - Sprint 2: Infraestructura y Backups P0)
- **Hardening del Reverse Proxy Nginx**:
  - `upstream django_cluster` balanceado con `keepalive 32`.
  - Mapeo estándar de WebSocket headers (`map $http_upgrade $connection_upgrade`).
  - Rate limiting defensivo a nivel de proxy (`limit_req_zone` de 30r/s para `/api/` y 5r/s para `/api/v1/auth/`).
  - Bloqueo explícito y proxy pass para Django Admin (`location /admin/` y `/panel-control-mbc/`) impidiendo que la SPA intercepte peticiones de administración.
  - Cabeceras de seguridad reforzadas (`Cross-Origin-Opener-Policy: same-origin`, CSP, HSTS, X-Frame-Options).
- **Persistencia y Resiliencia en Redis 7**:
  - Configurado Redis 7 con persistencia AOF (`appendonly yes`), volumen persistente `redis_data` / `redis_prod_data`, límite de memoria fijado a 256 MB y política de desalojo `allkeys-lru`.
- **Orquestación Docker Segura**:
  - Cuotas de CPU y memoria (`deploy.resources.limits`) aplicadas a todos los servicios en `docker-compose.prod.yml`.
  - Aislamiento de redes internas (`backend_net` con `internal: true`) evitando exposición innecesaria de puertos de PostgreSQL y Redis al host en entornos de producción.
- **Estrategia y Verificación Automatizada de Backups (PostgreSQL 16)**:
  - Scripts en `scripts/backup/` (`backup_db.sh`, `restore_db.sh`, `backup_media.sh`, `restore_media.sh`, `test_restore_cycle.sh`) adaptados con rutas relativas robustas y soporte para ejecución no-interactiva (`PGPASSWORD`).
  - Solucionada incompatibilidad de `pg_dump` con PostgreSQL 16 filtrando la directiva `SET transaction_timeout = 0;` en modo transaccional (`--single-transaction`).
  - Ciclo completo de restauración y verificación validado al 100% (65 tablas creadas, smoke test de 23 usuarios y limpieza automática exitosa).
- **Suite de Pruebas**:
  - Añadida suite `backend/tests/test_sprint2_infrastructure.py` con 6 pruebas verificando sondas de salud, versión, Redis caché, integridad de esquema en PostgreSQL 16 y consistencia de scripts de backup.

### Added (RoadmapV3 - Sprint 3: Autores P1 & Sistema de FAQs)
- **Subsistema de Autores de Primer Nivel**:
  - Ampliación del modelo `Author` con campos enriquecidos: `nationality`, `birth_date`, `death_date`, `website`, `twitter`, `instagram`, `wikipedia_url`, `canonical_name`, `aliases`, `external_ids`, `is_verified` y `claimed_by`.
  - Serializador `AuthorSerializer` con estadísticas editoriales calculadas en tiempo real (`published_books_count`, `average_rating`, `total_reviews_count`, `total_readers_count`, `is_claimed`, `can_claim`).
  - Modelo `AuthorClaim` con control de ciclo de vida (`pending`, `approved`, `rejected`, `cancelled`) y unicidad para evitar reclamaciones duplicadas concurrentes por autor.
  - Endpoints para solicitud de autoría `POST /api/v1/books/authors/<pk>/claim/` y consulta de estado `GET /api/v1/books/authors/<pk>/claim-status/`.
  - Endpoint de moderación `POST /api/v1/admin/author-claims/<id>/resolve/` con verificación de autor, asignación a cuenta de usuario y emisión de notificaciones en plataforma.
  - Vista pública del autor en frontend enriquecida con insignia de "Oficial Verificado", métricas de impacto editorial, enlaces oficiales y modal para reclamación de perfil.
  - Pestaña de administración de solicitudes de autor en el frontend (`AdminAuthorClaimsTab`).
- **Sistema Integral de Preguntas Frecuentes (FAQs)**:
  - Modelo `FAQ` en backend con campos (`question`, `answer`, `category`, `order`, `is_published`).
  - Endpoints públicos `GET /api/v1/faqs/` con filtrado por categoría y orden.
  - Endpoints administrativos CRUD `GET, POST, PUT, DELETE /api/v1/admin/faqs/` protegidos para staff/moderación.
  - Página pública de FAQs `/faqs` con formato acordeón interactivo (despliegue de respuestas al pinchar), buscador reactivo y selector temático por píldoras.
  - Pestaña administrativa de FAQs en `AdminDashboard` (`AdminFaqsTab`) para crear, editar, reordenar y publicar preguntas y respuestas.
  - Enlaces integrados en Header y Footer.
- **Suite de Pruebas**:
  - Añadida suite `backend/tests/test_sprint3_authors_and_faqs.py` con 9 pruebas de integración cubriendo estadísticas de autor, reclamaciones, duplicados, aprobación y ciclo CRUD de FAQs.

### Added / Security (RoadmapV3 - Sprint 1: Seguridad e Integridad P0)
- **Blindaje del Sistema de Notificaciones**:
  - Eliminado el método `POST` de `/api/v1/users/notifications/` (ahora estrictamente solo lectura `GET` con `ListAPIView`), previniendo creación de notificaciones no autorizadas e IDOR.
  - Añadido endpoint de detalle seguro `GET /api/v1/users/notifications/<id>/` con validación estricta de receptor (`recipient=request.user`), previniendo IDOR.
- **Robustez y Resiliencia en WebSockets (`ChatConsumer`)**:
  - Captura y manejo estructurado de `json.JSONDecodeError` respondiendo con evento `malformed_json` sin interrumpir la conexión.
  - Límite máximo de mensaje de 64 KB (`payload_too_large`) para prevenir ataques de denegación de servicio por memoria.
  - Validación de acciones permitidas y descarte controlado con evento `unknown_action`.
  - Rate limiting local de 10 mensajes por segundo (`rate_limited`) para evitar saturación de la conexión.
- **Sondas de Salud Desacopladas y Sanitizadas**:
  - Sanitizado `ReadinessCheckView` (`/health/ready/`) para devolver `unhealthy` sin filtrar detalles internos o credenciales de excepciones de base de datos o caché.
- **Infraestructura de Desarrollo**:
  - Sincronizado `docker-compose.yml` para utilizar `pgvector/pgvector:pg16`, homogeneizando la versión con producción.
- **Suite de Pruebas**:
  - Añadida suite exhaustiva `backend/tests/test_sprint1_security.py` con 15 pruebas cubriendo notificaciones, observabilidad, WebSockets y sondas de salud.

### Planned
- Notificaciones push mediante Web Push API.
- Internacionalización ampliada (soporte multi-idioma i18n).

---

## [1.0.0] - 2026-10-01

### Added
- **Cierre de Beta y Lanzamiento General (GA) (Fase 38)**:
  - Corte formal de versión definitiva SemVer 2.0.0 `1.0.0` unificada en backend (`version.py`, `pyproject.toml`) y frontend (`package.json`).
  - Sonda de versión `/api/v1/version/` reportando versión estable `1.0.0` sin etiquetas prerelease.
  - Auditoría final de seguridad, integridad y verificación de todas las directivas de Definition of Done (DoD 5/5).
  - Guía integral de despliegue a producción y disponibilidad general (`docs/deployment/general_availability_release_guide.md`).
- **Apertura de Beta Pública y Campaña de Adopción (Fase 37)**:
  - Feature flags dinámicas de registro (`PUBLIC_REGISTRATION_ENABLED` y `REQUIRE_BETA_INVITATION`) en `settings.py` y `UserCreateSerializer`.
  - Endpoint público de verificación de estado de registro (`GET /api/v1/beta/registration-status/`).
  - Sistema de referidos virales entre lectores (`ReferralService`) con endpoints `/api/v1/beta/referrals/my-code/` y `/api/v1/beta/referrals/stats/`.
  - Consolidación del cálculo de retención de cohortes D1 / D7 / D30 en el panel de telemetría (`BetaMetricsService.get_cohort_summary_metrics`).
  - Suite de pruebas de integración completa (`test_phase37_public_beta_and_retention.py`).
  - Guía de operaciones y adopción de beta pública (`docs/deployment/public_beta_and_adoption_guide.md`).
- **Apertura de Cohorte Beta Cerrada y Monitorización (Fase 36)**:
  - Comando CLI `generate_beta_cohort` para emisión masiva de invitaciones por lotes con prefijo de cohorte, expiración y exportación opcional JSON/CSV.
  - Servicio de métricas `BetaMetricsService` y endpoint administrativo `/api/v1/beta/admin/metrics/` con cálculo de tasa de activación, distribución de feedback y tickets de soporte.
  - Servicio de triaje y alertas inmediatas `BetaAlertsService` con hooks en feedback (`BUG`) y soporte urgente (`CRITICAL`/`HIGH`) en `/api/v1/beta/admin/alerts/`.
  - Guía operativa de gestión y monitorización de la beta cerrada (`docs/deployment/closed_beta_operations_guide.md`).
- **Despliegue y Validación en Staging (Beta Cerrada) (Fase 35)**:
  - Script de smoke testing automatizado de staging (`scripts/staging/smoke_test_staging.py` y `.sh`) validando sondas de liveness, readiness, versión, catálogo y códigos de invitación beta.
  - Script de auditoría pre-despliegue de staging (`scripts/staging/preflight_staging.sh`) con validación de PostgreSQL, Redis, migraciones y Django deploy checks.
  - Suite de pruebas de integración de ciclo de vida beta (`test_phase35_staging_validation.py`) para validación de invitaciones (`BetaInvitation`), feedback in-app (`BetaFeedback`) y soporte (`SupportTicket`).
  - Guía operativa de despliegue en staging (`docs/deployment/staging_deployment_guide.md`).
- **Consolidación y Release Candidate 1 (Fase 34)**:
  - Sincronización formal de versión SemVer 2.0.0 `1.0.0-rc1` en backend y frontend.
  - Suite de validación de Release Candidate (`test_phase34_release_candidate.py`).
  - Verificación automatizada de DoD y script de preflight.
  - Guía completa de congelación de código (*code freeze*) y despliegue de RC1 (`docs/deployment/release_candidate_guide.md`).
- **Calidad Avanzada y Prevención de N+1 (Fase 33)**:
  - Validación formal de contratos OpenAPI 3.0 con `drf-spectacular` frente a modelos y respuestas reales.
  - Flujo de integración continuo de extremo a extremo (E2E User Journey de 7 pasos).
  - Guardrails de seguridad contra IDOR, inyecciones de script/XSS y revocación de tokens JWT en blacklist.
  - Erradicación de consultas N+1 con complejidad estrictamente $O(1)$ en muro social, listado de reseñas y feed mediante optimización de prefetch cache y ciclo de vida de petición.
  - Script reproducible de prueba de carga concurrente y SLAs (`scripts/load_testing/load_test_benchmark.py`).
- **Soporte Multi-autor, Muro Social y Reseñas en Perfil (Fase 32)**:
  - Compatibilidad completa de múltiples autores por libro (`Book.authors` ManyToMany) manteniendo retrocompatibilidad transparente con `Book.author`.
  - Pestaña de reseñas en el perfil de usuario con endpoints `/api/v1/reviews/?user=<id>` y `/api/v1/users/<id>/reviews/`.
  - Muro interactivo de publicaciones (`UserPost`), comentarios sanitizados (`UserPostComment`), likes (`UserPostLike`) y actividad social `POST_CREATED` en el feed.
  - Ponderación de afinidad multi-autor en el motor híbrido de recomendaciones.
- **Monetización Ética y Plataforma de Autores (Fase 31)**:
  - Tag de afiliación de Amazon configurable (`AMAZON_AFFILIATE_TAG` con fallback `mybooksocial-21`).
  - Enlaces multiformato transparentes (papel, Kindle ebook, Audible audiolibro) con aviso legal obligatorio y endpoint dedicado `/api/v1/books/<id>/affiliate-links/`.
  - Plataforma de Autores: modelo `AuthorProfile`, comunicados oficiales (`AuthorAnnouncement`), solicitud de reclamo (`/claim/`) y panel de control (`/dashboard/`).
  - Modelo base de suscripciones (`UserSubscription`) y neutralidad algorítmica garantizada en recomendaciones.


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
