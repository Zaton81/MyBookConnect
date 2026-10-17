# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning 2.0.0](https://semver.org/lang/es/).

## [Unreleased]

### Added & Changed / Post-GA Fase 5: Reestructuración y Optimización de la Suite de Testing y QA
- **Saneamiento y Eliminación de Archivos Vacíos de Django**:
  - Eliminados los archivos residuales vacíos `backend/users/tests.py` y `backend/messages_app/tests.py`.
- **Taxonomía Semántica por Dominios en `backend/tests/`**:
  - Reorganizados los 140 archivos de prueba en 9 subdirectorios por dominio de negocio:
    - `catalog/`: libros, modelos de datos, ingesta CSV, proveedores externos (Amazon, Google Books, OpenLibrary) y búsqueda trigram/Postgres.
    - `recommendations_and_ai/`: embeddings vectoriales (`pgvector`), pipeline de 4 etapas, BookAI Assistant, multimodal y seguridad de IA.
    - `social_and_community/`: reseñas públicas, muros sociales, smart feed, listas de lectura, clubes y notificaciones.
    - `creators_and_commerce/`: portal de autor verificado, eventos, newsletters, audiolibros TTS, marketplace y monetización.
    - `reader_experience/`: gamificación, retos, insignias, estadísticas de lectura y onboarding.
    - `messaging/`: chat en tiempo real y WebSockets.
    - `security_and_privacy/`: auth JWT, cookies HttpOnly, permisos, visibilidad, moderación de contenido y GDPR.
    - `platform_and_infra/`: caché L1/L2, transacciones, query budgets, observabilidad/health checks y backups/DR.
    - `governance/`: branching, commit linting, definition of done y comprobaciones de infraestructura.
- **Fixtures Compartidas y Factories**:
  - Enriquecido `backend/tests/conftest.py` con fixtures estándar DRF (`api_client`, `auth_client`, `test_user`, `admin_user`, `author_user`, `author_client`).
  - Creado módulo `backend/tests/factories/` para instanciación estandarizada de modelos (`UserFactory`, `AuthorFactory`, `BookFactory`, `ReviewFactory`).
- **Aceleración de Ejecución de Pruebas y CI**:
  - Incorporado `pytest-xdist>=3.5.0` en `backend/requirements.txt` y habilitado `-n auto --dist loadscope` en `.github/workflows/ci-backend.yml`.
- **Modularización de la Suite E2E de Playwright (`frontend/e2e/`)**:
  - Desacoplado `critical-flows.spec.ts` en 4 suites modulares:
    - `e2e/auth-and-onboarding.spec.ts`
    - `e2e/library-and-import.spec.ts`
    - `e2e/clubs-and-social.spec.ts`
    - `e2e/author-portal.spec.ts`


### Added & Changed / Post-GA Fase 4: Refactorización y Limpieza Arquitectónica del Frontend (`frontend/src/`)
- **Eliminación Integral de Archivos Puente (*Re-export Shims*)**:
  - Eliminado por completo el directorio legado `frontend/src/pages/` (14 archivos raíz y 7 en `pages/legal/`), redirigiendo todas las importaciones directamente a `@/features/<feature>/pages/*`.
  - Eliminados los 16 archivos puente huérfanos de la raíz de `frontend/src/components/`, dejando la carpeta organizada exclusivamente en sus subdirectorios funcionales: `audio/`, `layout/` y `ui/`.
- **Unificación de la Capa de Red y Estado de Autenticación**:
  - Fusionado `src/services/api.ts` dentro de `src/api/client.ts` centralizando `authApi` (`login`, `register`, `loginWithGoogle`, `getProfile`, `updateProfile`).
  - Trasladado `src/services/erratas.ts` hacia `src/features/books/services/errataService.ts` y eliminada la carpeta obsoleta `src/services/`.
  - Unificados `src/lib/auth.ts` y `src/lib/useAuth.ts` en el hook canónico reactivo `useAuth` (`src/features/auth/hooks/useAuth.ts`), respaldado por el store persistido Zustand `useAuthStore` (`src/store/auth.ts`), eliminando la carpeta `src/lib/`.
- **Estandarización de TanStack React Query**:
  - Ampliadas y tipadas las claves de invalidación en `src/api/queryKeys.ts` para los dominios `clubs`, `discovery`, `library`, `profile` y `admin`.
  - Creados hooks tipados con TanStack Query:
    - `useClubsQuery.ts`: `useClubs`, `useClubDetail`, `useClubMembers`, `useClubDiscussions`, mutaciones de suscripción y creación.
    - `useDiscoveryQuery.ts`: `useDiscoveryTrending`, `useDiscoverySearch`, `useDiscoveryRecommendations`, `useContextualRecommendations`, `useRecommendationFeedbackMutation`.
    - `useLibraryQuery.ts`: `useUserBooks`, mutaciones de actualización y eliminación.
    - `useProfileQuery.ts`: `useUserProfile`, `useUserWall`, mutaciones de seguimiento y edición.
    - `useAdminQuery.ts`: `useAdminStats`, `useAdminAuditLogs`, `useAdminReports`, `useAdminSystemHealth`, mutación para resolución de reportes.
- **Descomposición Modular de Componentes Monolíticos**:
  - `features/social/pages/Home.tsx`: Extraídos `FeedActivityCard.tsx`, `FeedFilterTabs.tsx` y `TrendingSidebar.tsx`.
  - `features/books/pages/BookDetail.tsx`: Extraído `SimilarBooksCarousel.tsx`.
- **Sincronización Automática OpenAPI y Build de Producción**:
  - Añadido comando `"generate:types": "openapi-typescript ../backend/schema.yaml -o src/types/openapi.d.ts"` a `package.json` y verificación en `.github/workflows/ci-frontend.yml`.
  - Ajustado `pool: 'forks'` en `vite.config.js` para asegurar ejecución robusta de la suite de pruebas.
  - Verificado 100% de éxito en Vitest (24/24 suites, 93/93 tests) y `npm run build` en 18s.

### Added & Changed / Post-GA Fase 3: Consolidación de IA, Embeddings (`pgvector`) y Motor de Recomendaciones
- **Eliminación de Duplicidades y Modularización de Vistas de IA**:
  - Eliminado el proxy obsoleto `backend/mybookconnect/ai_service.py` (`git rm`).
  - Trasladadas todas las vistas de IA (13 clases: `AIStatusView`, `AIAssistantView`, `SemanticSearchView`, `BookComparisonView`, `EmbeddingsStatsView`, `AIToolsCatalogView`, `MultimodalBookCoverAnalysisView`, `BookSummaryView`, `BookKeyThemesView`, `BookSentimentAnalysisView`, `BookQuotesView`, `BookCharactersView`, `BookReadingGuideView`) a la app canónica `backend/ai/views.py`.
  - Creado `backend/ai/urls.py` y montado en `/api/v1/ai/` en `mybookconnect/urls.py`.
  - Mantenida compatibilidad retrospectiva completa conservando `/api/v1/books/ai/` y re-exportando las vistas en `backend/books/ai_views.py`.
- **Unificación del Sistema de Embeddings Vectoriales (`pgvector`)**:
  - Implementada función matemática de utilidad `weighted_average_embeddings` con normalización L2 opcional en `backend/ai/embeddings.py`.
  - Confirmada `BookEmbedding` y `backend/books/services/embedding_service.py` como única fuente canónica para indexación y búsqueda semántica con `pgvector`.
- **Refactorización del Motor de Recomendaciones en Pipeline de 4 Etapas**:
  - Creado submódulo modular `backend/books/services/recommendations/`:
    - `CandidateGenerator` (`candidates.py`): Generación multi-fuente ($K=200$) combinando semántica vectorial v3, filtrado colaborativo v2, heurísticas v1 y fallback cold-start.
    - `RecommendationFilter` (`filtering.py`): Exclusión de leídos, en lectura, abandonados (`ReadingStatus.ABANDONED`) y libros descartados (`RecommendationFeedbackAction.DISMISSED`), con filtros por categorías y longitud.
    - `MMRReranker` (`reranking.py`): Reordenación con Maximal Marginal Relevance y balance de diversidad por autor y categoría.
    - `BatchExplanationEngine` (`explanations.py`): Enriquecimiento en bloque de explicaciones comprensibles sin consultas $N+1$.
    - `RecommendationPipeline` (`pipeline.py`): Orquestador desacoplado con caché y métricas de ejecución.
  - Integrado `strategy='pipeline'` en `get_user_recommendations` en `backend/books/services/recommendation_service.py` y re-exportado en `backend/books/services/__init__.py`.
- **Suite de Pruebas y Validación**:
  - Creado `backend/tests/test_phase_postga_fase3_ai_and_recommendations.py` con 9 pruebas exhaustivas (100% aprobadas).
  - Verificada la suite completa de IA y recomendaciones (91/91 pruebas pasadas) y frontend Vitest (93/93 pruebas pasadas).
  - Ruff linting verificado con 0 errores y 0 advertencias.

### Added & Changed / Post-GA Fase 2: Deconstrucción del Monolito `backend/books/` (Modularización sin Downtime)
- **Modularización Arquitectónica sin Downtime ni Pérdida de Datos**:
  - Desacoplados 5 dominios de negocio y operaciones transversales fuera del monolito `backend/books/` en aplicaciones Django independientes registradas en `INSTALLED_APPS`: `clubs`, `gamification`, `audiobooks`, `marketplace`, `authors_portal` y `ops`.
  - Preservación estricta de tablas relacionales en PostgreSQL mediante `Meta.db_table = 'books_<modelo>'` y migraciones con el patrón `SeparateDatabaseAndState` (`database_operations=[]`, `state_operations=[migrations.CreateModel(...)]`), garantizando cero alteraciones de DDL y cero tiempo de inactividad.
- **Extracción de Clubes de Lectura (`backend/clubs/`)**:
  - Modelos `ReadingClub`, `ReadingClubMembership`, `ReadingClubBook`, `ReadingClubDiscussion`, `ReadingClubComment` trasladados con serializadores, vistas, URLs y servicios dedicados.
  - Migraciones `clubs.0001_initial` y `books.0044_transfer_clubs_models_to_clubs_app`.
- **Extracción de Gamificación (`backend/gamification/`)**:
  - Modelos `Badge`, `UserBadge`, `ReadingChallenge`, `UserChallenge`, `ReadingGoal`, `ReadingStreak`, `DailyReadingLog` trasladados con sus servicios (`GamificationService`, insignias y retos predeterminados), serializadores, vistas y URLs.
  - Migraciones `gamification.0001_initial` y `books.0045_transfer_gamification_models_to_gamification_app`.
- **Extracción de Audiolibros y TTS (`backend/audiobooks/`)**:
  - Modelos `AudiobookTrack` y `UserAudiobookProgress` trasladados con servicios (`AudiobookService`), reproductor, progreso de escucha, estantería y catálogo público.
  - Migraciones `audiobooks.0001_initial` y `books.0046_transfer_audiobook_models_to_audiobooks_app`.
- **Extracción de Marketplace y Editoriales (`backend/marketplace/`)**:
  - Modelos `Publisher`, `BookBuyLink` y `MarketplaceClick` trasladados con `MarketplaceService` y `AffiliateService` (manteniendo `Book.publisher` relacionado con `'marketplace.Publisher'`).
  - Migraciones `marketplace.0001_initial` y `books.0047_transfer_marketplace_models_to_marketplace_app`.
- **Extracción del Portal de Autores (`backend/authors_portal/`)**:
  - Modelos de gestión y comunidad para autores: `AuthorProfile`, `AuthorAnnouncement`, `AuthorEvent`, `AuthorEventAttendee`, `AuthorNewsletter`, `AuthorNewsletterIssue`, `AuthorNewsletterSubscriber`, `AuthorClaim` y `AuthorClaimStatus`.
  - Invariante arquitectónico protegido: La entidad bibliográfica `Author` permanece en `backend/books/` como catálogo canónico universal.
  - Migraciones `authors_portal.0001_initial` y `books.0048_transfer_author_portal_models_to_authors_portal_app`.
- **Extracción de Comandos Operativos y Recuperación ante Desastres (`backend/ops/`)**:
  - Comandos de gestión desacoplados a `ops/management/commands/`: `backup_db`, `backup_media`, `restore_db`, `restore_media`, `check_backup_freshness`, `verify_restore_integrity`, `evaluate_system_alerts`, `benchmark_queries` y `rebuild_cache`.
  - Servicio transversal `DatabaseBackupService` y `MediaBackupService` trasladados a `backend/ops/services/backup_service.py`.
- **Compatibilidad Retrospectiva Total (Re-exports)**:
  - Preservados *shims* de compatibilidad retrospectiva con `# noqa: E402, F401` en `books/models.py`, `books/serializers.py`, `books/views.py`, `books/services/` y módulos de URLs para no romper importaciones existentes ni tareas de Celery.
- **Suite de Pruebas de Arquitectura y Modularización**:
  - Creado `backend/tests/test_phase_postga_fase2_modularization.py` con 5 pruebas exhaustivas verificando el registro en `INSTALLED_APPS`, identidad de nombres de tablas de base de datos, resolución de vistas y presencia canónica de `Author` en `books`.
  - Suite de pruebas de backend (pytest) y frontend (vitest) verificada al 100%.

### Added & Changed / Post-GA Fase 1: Higiene de Git, Activos Estáticos y Almacenamiento Multimedia
- **Higiene de Repositorio Git y Purga de Binarios**:
  - Desindexados 78 archivos multimedia del control de versiones Git mediante `git rm -r --cached backend/media/` preservando los archivos locales.
  - Creado `backend/media/.gitkeep` y actualizados `.gitignore` y exclusiones para respaldos (`*.zip`, `*.tar.gz`).
  - Creado comando de gestión `seed_dev_catalog` (`python manage.py seed_dev_catalog`) para generar catálogos de prueba deterministas con portadas sintéticas WebP en memoria.
- **Deduplicación Criptográfica y WebP Universal**:
  - Implementado callable serializable `UploadToHashedPath` (`backend/mybookconnect/media_security.py` y `backend/books/media_utils.py`) con sharding jerárquico `{subfolder}/{hash[:2]}/{hash}.webp`.
  - Re-codificación sistemática de imágenes a formato WebP optimizado (calidad 82, eliminación exhaustiva de EXIF y reducción de ~40-60% de peso).
  - Vinculados `upload_to_covers`, `upload_to_author_photos`, `upload_to_avatars`, `upload_to_chat_images` y `upload_to_reviews` a los campos ImageField de los modelos con migraciones aplicadas.
- **Optimización de Activos Estáticos del Frontend**:
  - Reducción masiva de peso en logotipos: `logo-horizontal.png` (24 KB, -95.3%), `logo-principal.png` (21 KB, -95.6%), `logo-libro.png` (20 KB, -98.2%).
  - Reemplazado `favicon.ico` sobredimensionado (1.13 MB) por un icono multi-resolución estándar (16/32/48 px, 3.8 KB, -99.66%) y generado `apple-touch-icon.png` (180x180 px, 12 KB).
  - Carga de activos estáticos del frontend reducida en más de un 97.5% (de 3.28 MB a ~80 KB en total).
- **Abstracción de Almacenamiento Compatible S3 / Cloudflare R2**:
  - Incorporadas librerías `django-storages[s3]` y `boto3` en `backend/requirements.txt`.
  - Creado `backend/mybookconnect/storage.py` con `DeduplicatedFileSystemStorage` y `DeduplicatedS3Storage` para deduplicación transparente en $O(1)$.
  - Configurado diccionario `STORAGES` en `backend/mybookconnect/settings.py` soportando conmutación dinámica con `STORAGE_BACKEND=local|s3`.
- **Consolidación de Scripts Operativos**:
  - Eliminado `scripts/locustfile.py` duplicado de la raíz en favor de `scripts/load_testing/locustfile.py`.
  - Fusionado el chequeo de producción en un único `scripts/production/preflight_prod.sh` y eliminado el wrapper obsoleto `preflight_check.sh`.
- **Suite de Pruebas de Calidad**:
  - Creado `backend/tests/test_phase_postga_fase1_hygiene_and_storage.py` con 100% de éxito.

## [1.0.0] - 2026-10-14 — General Availability (GA)

### Added & Changed / General Availability (GA) Hardening & Public Launch (Roadmap Bloque E - Fase E3)
- **Informe de Cierre Formal de Fase Beta (`docs/deployment/beta_closure_report.md`)**:
  - Auditoría formal de fin de fase beta, certificación de calidad con cero vulnerabilidades críticas abiertas, 100% pruebas aprobadas, cero migraciones pendientes y formalización del paso a modo GA público.
- **Comunicado Oficial de Lanzamiento Global (`docs/deployment/ga_release_announcement.md`)**:
  - Declaración pública de General Availability (GA v1.0.0) detallando las funcionalidades para lectores, panel de autores, recomendaciones éticas, observabilidad y cumplimiento estricto del RGPD.
- **Manual de Guardia y Respuesta a Incidentes (`docs/devops/on_call_runbook.md`)**:
  - Protocolo operativo 24/7 con matriz de severidad (SEV-1/SEV-2/SEV-3), SLAs de respuesta (<15 min para SEV-1, <30 min para SEV-2), roles de guardia (Primary, Secondary, Incident Commander, Communications Lead), canales de alerta (Sentry, sondas HTTP, Celery) y directrices para post-mortem sin culpa en menos de 48h.
- **Suite Integral de Pruebas de General Availability (`backend/tests/test_phase_e3_general_availability.py`)**:
  - Cobertura completa de verificación de versión oficial SemVer 1.0.0 limpia, registro público por defecto (`mode='public'`), sondas de salud y métricas restringidas, viaje e2e del lector y preservación de artefactos de gobernanza y operaciones.

### Added & Changed / Soft Launch, Monitoring & Rollback Protocols (Roadmap Bloque E - Fase E2)
- **Guía Operativa de Rollback y Comunicación de Incidentes (`docs/devops/rollback_and_incident_communication_guide.md`)**:
  - Procedimiento paso a paso para la contención y reversión de despliegues ante degradaciones de SLA (5xx > 1.0%, latencia p95 > 2000ms, caídas de base de datos o fallos de migración).
  - Protocolos de rollback para código, contenedores Docker, migraciones reversibles y restauración de snapshots con `restore_db.sh` y verificación con `verify_restore_integrity`.
  - 4 plantillas estandarizadas de comunicación pública y para autores: notificación inicial de incidencia (SEV-1/SEV-2), actualización de mitigación, anuncio de servicio restablecido y estructura de post-mortem técnico.
- **Canales de Feedback y Soporte Técnico Formal (`backend/beta/views.py`)**:
  - Operatividad auditada de `/api/v1/beta/feedback/` con captura de contexto de dispositivo/página y triaje administrativo.
  - Circuito de tickets `/api/v1/beta/support/` y `/api/v1/beta/support/my/` con seguimiento de estado (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`), prioridades y resolución documentada por administradores.
- **Telemetría de Cohorte y Detección de Alertas Críticas (`backend/beta/metrics_service.py`, `backend/beta/alerts_service.py`)**:
  - Agregación en tiempo real de tasas de activación de invitaciones, distribución de incidencias y tickets de soporte.
  - Triaje y alerta automática en logs estructurados ante bugs y tickets de severidad alta o crítica.
- **Suite Integral de Pruebas de Soft Launch y Monitorización (`backend/tests/test_phase_e2_soft_launch_monitoring.py`)**:
  - 5 pruebas unitarias y de integración pasando al 100% que validan el registro controlado por feature flags, ciclo de feedback, soporte técnico, telemetría operativa y la integridad del manual de rollback.

### Added & Changed / Staging Parity, Smoke Testing & Pre-Deployment Hardening (Roadmap Bloque E - Fase E1)
- **Checklist de Seguridad Pre-Despliegue (`docs/deployment/pre_deployment_security_checklist.md`)**:
  - Matriz integral de seguridad auditando directivas Django (`DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, cookies HttpOnly/Secure/SameSite=Lax, HSTS estricto de 1 año), aislamiento estricto de redes Docker (`backend_net internal: true`, puertos de base de datos y Redis cerrados al exterior), backup cifrado con DRP y feature flags de control de apertura.
- **Auditoría Preflight y Smoke Testing de Staging (`scripts/staging/`)**:
  - Sincronizado `preflight_staging.sh` con el dominio canónico `mybooksocial.com`.
  - Herramienta sintética `smoke_test_staging.py` validando sondas `/health/live` y `/health/ready`, versiones SemVer 2.0.0 y contratos de catálogo.
- **Suite Integral de Pruebas Automáticas de Staging (`backend/tests/test_phase_e1_staging_smoke.py`)**:
  - 8 pruebas pasando al 100% que validan contratos de sondas de salud sin fugas de secretos, login seguro con emisión de cookies HttpOnly, emisión y consumo de un solo uso de tickets efímeros WebSocket, control de feature flags de registro público e invitaciones, ejecución exitosa del comando de integridad post-restauración `verify_restore_integrity` y presencia física de artefactos de auditoría.

### Added & Changed / Search, Discovery & Recommendations Hardening (Roadmap Bloque D - Fase D4)
- **Búsqueda Híbrida Resiliente (`backend/books/services/unified_search_service.py`)**:
  - `UnifiedSearchEngine` consolidado combinando FTS (`SearchVector`/`SearchRank`), búsqueda difusa por trigramas (`TrigramSimilarity`/`TrigramWordSimilarity`) y embeddings semánticos con fallback automático tolerante a fallos sin dependencias duras externas.
- **Descubrimiento Facetado y Tendencias Públicas (`backend/books/discovery_views.py`)**:
  - `BookDiscoveryView`: soporte para filtrado por slug o nombre de género (`Q(categories__slug__iexact=...) | Q(categories__name__iexact=...)`), con normalización de claves de caché para evitar caracteres especiales en Redis y Memcached.
- **Motor de Recomendaciones con Transparencia Ética y Cold-Start (`backend/books/services/recommendation_service.py`)**:
  - Exclusión estricta de obras en biblioteca (`UserBook`) y obras descartadas (`RecommendationFeedbackAction.DISMISSED`).
  - Algoritmo de arranque en frío (*cold-start*) aprovechando las categorías favoritas de onboarding (`user.favorite_categories`).
  - Explicabilidad algorítmica obligatoria (`reason`) en cada ítem y endpoint `/api/v1/books/recommendations/<id>/explain/` detallando motivos de sugerencia.
- **Suite Integral de Pruebas de Búsqueda, Descubrimiento y Recomendaciones (`backend/tests/test_phase_d4_search_discovery_recommendations.py`)**:
  - 7 pruebas unitarias y de integración pasando al 100% que validan búsqueda híbrida, endpoint global, descubrimiento no autenticado, faceteado por género, exclusión de leídos, cold-start y transparencia ética de la IA.

### Added & Changed / Reviews, Social Interactions, Feed & Notifications Hardening (Roadmap Bloque D - Fase D3)
- **Ciclo de Vida de Reseñas y Reactivación Limpia tras Soft-Delete (`backend/books/views.py`)**:
  - Garantizada la unicidad de reseña activa por usuario y libro (`unique_active_review_user_book`). Si un usuario publica nuevamente para un libro cuya reseña previa fue eliminada con soft-delete, el sistema restaura la entidad existente (`deleted_at = None`), actualiza su puntuación y contenido, y recalcula de forma atómica el promedio del libro sin generar filas huérfanas duplicadas.
  - Erradicada la degradación N+1 en listados de libros precargando `contributions__author` en `BookListCreateView` y `BookDetailView`.
- **Aislamiento Social, Exclusión de Moderados y Blindaje del Feed (`backend/users/privacy_service.py`)**:
  - `PrivacyService.filter_visible_activities`: Exclusión rigurosa de actividades ligadas a reseñas con soft-delete (`review__deleted_at__isnull=False`) o moderadas (`review__is_moderated=True`) para usuarios sin permisos de staff.
  - Filtro estricto de bloqueos bidireccionales (`blocked_users`, `blocked_by`) y usuarios silenciados (`muted_users`) en el feed social cronológico e inteligente.
  - Respeto del nivel privado de actividad (`activity_privacy_level: private`).
- **Fiabilidad en Notificaciones y Protección ante Bloqueos (`backend/users/notification_service.py`)**:
  - Supresión garantizada de cualquier notificación si existe bloqueo activo entre los usuarios, e integridad en el cumplimiento de canales según preferencias `NotificationPreference` (In-App y Email).
- **Suite Integral de Pruebas de Reseñas, Social y Feed (`backend/tests/test_phase_d3_reviews_social_feed.py`)**:
  - 7 pruebas unitarias y de integración pasando al 100% que validan el ciclo de vida de reseñas, soft-delete y reactivación limpia, validación temprana de duplicados, likes y concurrencia, exclusión de moderados/silenciados en el feed y fiabilidad de notificaciones.

### Added & Changed / Authors, Multi-Role Contributions, ISBN-10/13 & Page Count (Roadmap Bloque D - Fase D2)
- **Modelo de Contribuciones Multi-Rol (`backend/books/models.py`, `backend/books/serializers.py`)**:
  - Incorporado modelo `BookContribution` con roles definidos (`AUTHOR`, `COAUTHOR`, `TRANSLATOR`, `ILLUSTRATOR`, `NARRATOR`, `EDITOR`) y sincronización automática bidireccional con campos históricos `book.author` y `book.authors`.
  - Serializador `BookContributionSerializer` expuesto dentro de `BookSerializer.contributions` para visualización granular en cliente.
- **Normalización y Búsqueda Cruzada de ISBN-10 y ISBN-13 (`backend/books/models.py`)**:
  - Implementadas funciones deterministas `isbn10_to_isbn13`, `isbn13_to_isbn10` y `get_equivalent_isbns`.
  - `Book.find_by_isbn` ampliado para buscar por equivalencias cruzadas en ediciones físicas y digitales.
- **Resolución y Visualización de Páginas de Libro (`page_count`)**:
  - `backend/books/services/enrichment_service.py`: Persistencia garantizada de `page_count` recuperado desde Google Books (`volumeInfo.pageCount`) y OpenLibrary (`ol_data.page_count`).
  - `backend/books/views.py`: `BookDetailView` evalúa la ausencia de `page_count` para desencadenar el enriquecimiento asíncrono preventivo en segundo plano.
  - `frontend/src/features/books/pages/BookDetail.tsx`: Renderizado visible del badge `📄 {page_count} páginas` en cabecera del libro, desglose de contribuciones multi-rol (traductor, ilustrador, narrador, etc.) y seguimiento de lectura reactivo `Pág. {currentPage} de {book.page_count}`.
- **Suite Integral de Pruebas de Autores y Catálogo (`backend/tests/test_phase_d2_authors_and_catalog.py`)**:
  - 6 pruebas unitarias y de integración pasando al 100% que validan contribuciones multi-rol, persistencia de `page_count`, endpoint de detalle, conversión matemática ISBN-10/13, búsqueda cruzada y fusión atómica deduplicada.

### Added & Changed / Reader Profile, Field Masking & GDPR Hardening (Roadmap Bloque D - Fase D1)
- **Consistencia y Blindaje de Privacidad de Perfil (`backend/users/privacy_service.py`)**:
  - Control de visibilidad estricto para perfiles `public`, `friends` y `private`, con ofuscación granular de PII (`email`, `birth_date`, `location`, `bio`) para terceros cuando las banderas de visibilidad están desactivadas.
  - Protección de biblioteca y métricas de lectura (`books_read_count`, `reviews_count`) bajo `reading_privacy_level` (ocultas para terceros en modo `private`).
  - Aislamiento bidireccional en bloqueos: auto-unfollow, denegación de acceso a perfil, prohibición de mensajes directos e interacciones sociales.
- **Re-validación RGPD bajo My Book Social (`backend/users/account_views.py`)**:
  - Actualizado el endpoint de portabilidad (`/api/v1/users/account/export/`) para generar archivos descargables con nombre canónico `mybooksocial_data_export_{username}.json` y metadatos con `platform: "My Book Social"`.
  - Re-validación del circuito de supresión y anonimización de cuenta (Art. 17) con registro de auditoría en `AuditLog`.
- **Suite Integral de Pruebas de Perfil y Privacidad (`backend/tests/test_phase_d1_reader_profile_and_privacy.py`)**:
  - 8 pruebas unitarias y de integración pasando al 100% que validan el enmascaramiento de datos personales, acceso a perfiles de amigos y privados, bloqueos mutuos, privacidad de lecturas y exportación/eliminación RGPD.

### Added / Documentation, ADRs & Governance Hardening (Roadmap Bloque C - Fase C2)
- **Nuevos Registros de Decisión Arquitectónica (`docs/decisions/`)**:
  - Incorporados ADR-009 (Mitigación de XSS mediante Cookies HttpOnly y Handshake WebSocket por Tickets Efímeros), ADR-010 (Topología Docker Aislada con Nginx como Punto Único de Entrada), ADR-011 (Copias de Seguridad Cifradas AES-256, DRP y Verificación de Integridad), ADR-012 (Enrutamiento Celery Multi-Cola y Read-Replicas) y ADR-013 (Batching Anti-N+1 en ListSerializer).
  - Creado índice maestro en `docs/decisions/README.md` catalogando los 13 ADRs del sistema.
- **Manual de Operaciones y Runbooks de Producción (`docs/devops/operations_runbook.md`)**:
  - Manual unificado con instrucciones ejecutables paso a paso para restauración ante desastres (DRP), rotación segura de secretos críticos (`SECRET_KEY`, PostgreSQL, AWS S3/PA-API), escalado horizontal de Celery/Daphne y protocolo de triaje y respuesta rápida a incidentes P0.
- **Guía de Contribución y Onboarding (`CONTRIBUTING.md`)**:
  - Guía centralizada en la raíz del repositorio con estándares de código (Ruff, ESLint), flujos de ramas (`develop`/`main`), convenciones de commits semánticos, checklist Definition of Done y protocolo obligatorio para agentes autónomos de IA.
- **Política de Versionado SemVer y Ciclo de Release (`docs/development/versioning_and_release_policy.md`)**:
  - Formalización del esquema SemVer 2.0.0, etapas de feature freeze, preparación de release, etiquetado de tags Git y gestión ágil de hotfixes de seguridad.

### Added & Changed / Test Hardening, Anti-N+1, E2E & Rebranding (Roadmap Bloque C - Fase C1)
- **Unificación de Marca y Dominio a My Book Social (`mybooksocial.com`)**:
  - Reemplazo exhaustivo de todas las referencias al antiguo dominio y nombre en `.env.production.example`, `frontend/nginx.ssl.conf.template`, `backend/users/notification_service.py`, `backend/users/tasks.py`, `backend/books/services/base.py`, páginas legales, componentes UI (`SocialShareModal`, `AccountPrivacySection`, `PublicLandingPage`, etc.) y suites de pruebas (0 incidencias residuales de `mybookconnect.com`).
- **Optimización Anti-N+1 con Complejidad Invariante $O(1)$ (`backend/books/serializers.py`)**:
  - Implementado agrupamiento por lotes (batching) en `BookSerializer.get_rating_distribution` y `get_reviews_count` cuando opera dentro de un `ListSerializer`. Reducción de $2N + 1$ consultas SQL a una única consulta agregada en BD con memoización en request actual.
  - Verificada la complejidad $O(1)$ constante mediante `backend/tests/test_phase_c1_query_optimization.py` utilizando `CaptureQueriesContext`.
- **Suite de Integración E2E de Ciclo Crítico (`backend/tests/test_phase_c1_e2e_critical_flow.py`)**:
  - Flujo completo de ciclo de vida en una prueba continua: Registro $\to$ Biblioteca (ReadingStatus) $\to$ Reseña (5★) $\to$ Amistad / Muro social $\to$ Ticket WebSocket efímero $\to$ Feed de actividad $\to$ Perfil del usuario.
- **Herramientas de Estrés y Pruebas de Carga Concurrentes (`scripts/load_testing/`)**:
  - Creado `locustfile.py` con perfil `MyBookSocialUser` para simular tráfico masivo sobre catálogo, búsqueda, feed social y handshake de WebSockets.
  - Creado ejecutor desatendido multiplataforma `run_locust_headless.py`.
  - Actualizado `load_test_benchmark.py` con métricas p50/p95/p99 y cabeceras de `MyBookSocial`.
- **Informe Técnico de Calidad y Cobertura (`docs/testing/test_coverage_and_quality_report.md`)**:
  - Documentación integral del estado de las suites (126 pruebas backend en pytest pasando al 100%, 24 suites de frontend con 93 pruebas en vitest pasando al 100%, y linters Ruff y ESLint limpios).

### Added / Basic Scalability & Performance SLAs (Roadmap Bloque B - Fase B4)
- **Router Primario / Réplica de Base de Datos (`backend/mybookconnect/db_routers.py`, `backend/mybookconnect/settings.py`)**:
  - Implementado `PrimaryReplicaRouter` que enruta lecturas hacia la base de datos `replica` si está configurada, manteniendo todas las escrituras en `default` (primario), con fallback transparente a `default` si no existe réplica, y bloqueo de migraciones en réplicas de sólo lectura.
- **Topología de 5 Colas Dedicadas en Celery (`backend/mybookconnect/settings.py`, `docker-compose.prod.yml`)**:
  - Configurado enrutamiento explícito `CELERY_TASK_ROUTES` con 5 colas independientes: `default`, `books`, `ai`, `recommendations` y `emails`. Worker de Celery orquestado para consumir de todas las colas concurrentemente (`-Q default,books,ai,recommendations,emails`).
- **Balanceo de Carga Nginx con Least Connections (`frontend/nginx.conf`, `frontend/nginx.ssl.conf.template`)**:
  - Definida la directiva `upstream django_cluster` con algoritmo de distribución `least_conn` tanto en desarrollo local como en la plantilla de producción SSL/TLS.
- **Invalidación Reactiva de Caché en Cascada para Reseñas (`backend/books/cache_utils.py`)**:
  - Implementada `cascade_review_invalidation(book_id)` que invalida atómicamente la caché del detalle del libro, desglose de calificaciones, recomendaciones asociadas y rankings de tendencias ante cualquier mutación de reseña.
- **Herramienta de Pruebas de Carga y Exportación JSON (`scripts/load_testing/load_test_benchmark.py`)**:
  - Incorporado parámetro `--output-json` para exportar métricas estandarizadas a CI/CD y automatizaciones, midiendo endpoints críticos de salud (`/health/live`, `/health/ready`), catálogo y búsqueda.
- **Informe Técnico de SLAs de Carga y Capacidad (`docs/deployment/load_test_sla_report.md`)**:
  - Documento formal con arquitectura de escalabilidad, objetivos de nivel de servicio (SLAs p95 < 250ms, p99 < 500ms, tasa de error 0.00%) y procedimientos de ejecución y auditoría de carga.
- **Suite de Pruebas de Escalabilidad Básica (`backend/tests/test_phase_b4_basic_scalability.py`)**:
  - 12 pruebas unitarias y de arquitectura pasando al 100% que validan el router primario/réplica, las 5 colas de Celery, upstream `least_conn` de Nginx, cascada de invalidación de caché, exportación JSON del benchmark y el informe de SLAs.

### Added / Observability, Telemetry & Alerts Hardening (Roadmap Bloque B - Fase B3)
- **Configuración Formal de Logs Estructurados (`backend/mybookconnect/settings.py`)**:
  - `LOGGING` configurado con `StructuredJsonFormatter` para emitir registros en JSON estructurado de una línea sin contraseñas, tokens JWT, headers de autenticación ni API keys (`sanitize_sensitive_data`). Flag `STRUCTURED_LOGS` para forzar logging estructurado en cualquier entorno.
- **Integración y Enmascaramiento Preventivo con Sentry (`backend/mybookconnect/settings.py`)**:
  - Soporte configurable mediante `SENTRY_DSN` con importación resiliente. Hook `sentry_before_send` que garantiza que ningún secreto, token o dato identificable personal (PII) se envíe a plataformas externas.
- **Comando de Evaluación y Notificación de Alertas del Sistema (`backend/books/management/commands/evaluate_system_alerts.py`)**:
  - Comando Django que evalúa en tiempo real los 7 umbrales de salud operativa (`high_5xx_rate`, `db_unavailable`, `redis_unavailable`, `celery_backlog`, `disk_usage_high`, `memory_usage_high`, `high_error_rate`), con soporte para salida JSON y notificaciones webhook (Slack/Discord/Alertmanager).
- **Manual Operativo de Incidentes de Producción (`docs/devops/incident_runbooks.md`)**:
  - Runbooks paso a paso para el diagnóstico rápido, mitigación inmediata y resolución definitiva de los 5 incidentes más críticos en producción.
- **Suite de Pruebas de Observabilidad y Alertas (`backend/tests/test_phase_b3_observability_and_alerts.py`)**:
  - 14 pruebas unitarias e integración que validan el formateador JSON, enmascaramiento de credenciales, métricas operativas y percentiles, métricas de producto, evaluador de alertas, comando CLI y hook `before_send` de Sentry.

### Added / Backup, Restore & Disaster Recovery Hardening (Roadmap Bloque B - Fase B2)
- **Backup de Configuración Crítica (`scripts/backup/backup_config.sh`)**:
  - Empaquetado y cifrado simétrico AES-256-CBC de plantillas compose, configuraciones y templates Nginx, variables de entorno sanadas y scripts operativos, con generación de manifiesto SHA-256 y retención configurable.
- **Orquestador Maestro Diario (`scripts/backup/backup_all.sh`)**:
  - Script unificado que ejecuta secuencialmente el backup de PostgreSQL, Media y Configuración, generando reporte JSON consolidado `daily_backup_summary_<timestamp>.json` con métricas de duración, estado por subsistema y código de salida determinista para alertas de cron/monitoreo.
- **Auditoría e Integridad Post-Restore (`backend/books/management/commands/verify_restore_integrity.py`, `scripts/backup/verify_restore_integrity.sh`)**:
  - Comando Django y script para validar la integridad referencial y de dominio tras una restauración: coherencia de usuarios, catálogo, integridad de ratings atómicos [0.0, 5.0], reseñas [1, 5], mensajería y consistencia física de archivos en `MEDIA_ROOT`.
- **Monitorización de Frescura de Backups y Cumplimiento RPO (`backend/books/management/commands/check_backup_freshness.py`)**:
  - Comando Django para auditoría de frescura que valida que el último backup tenga una antigüedad inferior al RPO ($\le 24$ horas) y que su firma SHA-256 coincida con el manifest, retornando código de fallo ante backups obsoletos (`STALE`), manipulados (`CORRUPTED`) o ausentes (`MISSING`).
- **Runbooks de DRP y Suite de Pruebas Automatizadas (`docs/deployment/disaster_recovery.md`, `backend/tests/test_phase_b2_backup_and_disaster_recovery.py`)**:
  - Actualización exhaustiva del manual de Disaster Recovery con procedimientos paso a paso y suite de 9 tests unitarios y de arquitectura pasando al 100%.

### Added / Docker & Production Orchestration Hardening (Roadmap Bloque B - Fase B1)
- **Orquestación de Producción y Topología Segura (`docker-compose.prod.yml`)**:
  - Nginx configurado como único punto de entrada expuesto a la red pública (`80:80`, `443:443`).
  - Servicios internos (`backend`, `celery_worker`, `db`, `cache`) aislados sin puertos mapeados al host.
  - Red `backend_net` blindada con directiva `internal: true` impidiendo acceso de red externo directo.
  - Cuotas de CPU y límites de memoria explícitos en todos los contenedores para mitigación de ataques de denegación de servicio (DoS).
  - Ciclo de vida y parada ordenada configurada con señales y periodos de gracia dedicados (`stop_signal: SIGQUIT` en frontend, `SIGTERM` con 30s en backend y 60s en Celery).
  - Integrado contenedor auxiliar `certbot` y volúmenes `certbot_www` y `certbot_certs` para emisión y renovación automática de certificados Let's Encrypt.
- **Plantilla de Configuración Nginx SSL/TLS (`frontend/nginx.ssl.conf.template`)**:
  - Soporte HTTPS nativo con protocolos TLS 1.2 y TLS 1.3, ACME challenge para Let's Encrypt, compresión gzip, rate limiting (`limit_req_zone`) y soporte para WebSockets (`/ws/`).
- **Scripts de Auditoría y Verificación de Producción (`scripts/production/preflight_prod.sh`, `scripts/production/smoke_test_prod.py`)**:
  - `preflight_prod.sh`: Auditoría pre-vuelo que evalúa la configuración compose, variables de entorno seguras (`DEBUG=0`), migraciones de base de datos y sondas de salud.
  - `smoke_test_prod.py`: Batería automatizada de smoke testing para verificar disponibilidad de frontend SPA, endpoints de salud, versionado y perímetro de seguridad (401 en accesos no autorizados).
- **Suite de Pruebas de Orquestación Docker (`backend/tests/test_phase_b1_docker_orchestration.py`)**:
  - 12 pruebas de arquitectura y configuración que auditan topología, cuotas, puertos, usuario no-root, variables de entorno y existencia/ejecución de scripts.

### Added / Health, Readiness & Attack Surface Hardening (Roadmap Bloque A - Fase A4)
- **Desacoplamiento y Sanitización de Sondas de Salud (`backend/mybookconnect/health.py`)**:
  - Sonda `/health/live` desacoplada de dependencias externas para evitar reinicios en cascada por latencia de red.
  - Sonda `/health/ready` con verificación estricta de PostgreSQL y Redis; ante caídas devuelve `503 Service Unavailable` sanitizado sin filtrar trazas de excepción, IPs de base de datos ni cadenas de conexión.
- **Restricción Estricta de Métricas y Observabilidad (`backend/mybookconnect/observability.py`, `backend/analytics/views.py`, `backend/beta/views.py`)**:
  - Endpoints de métricas de rendimiento, embudos y alertas operativas (`/api/v1/observability/metrics/`, `/api/v1/analytics/funnel/`, `/api/v1/analytics/summary/`, `/api/v1/analytics/retention/`, `/api/v1/beta/admin/metrics/`, `/api/v1/beta/admin/alerts/`) restringidos exclusivamente a personal con privilegios de administrador (`IsAdminUser`), retornando 401/403 a usuarios no autorizados.
- **Erradicación de Endpoints de Depuración y Protección Honeypot (`backend/mybookconnect/urls.py`)**:
  - Auditoría de rutas descartando endpoints residuales de depuración o testing en la superficie pública.
  - Protección honeypot contra escaneos predecibles (`admin_probe_trap_view` devolviendo 404 y registrando la anomalía).
- **Extensión OpenAPI y Auditoría de Seguridad de Contratos (`backend/users/authentication.py`, `docs/security/owasp_top_10_checklist.md`)**:
  - Registrada extensión `RevocationCheckingJWTAuthenticationScheme` para `drf-spectacular`, garantizando validación y documentación formal del esquema de autenticación Bearer JWT.
  - Generada matriz y checklist de auditoría OWASP Top 10 certificando el cumplimiento de las 10 categorías de seguridad en `docs/security/owasp_top_10_checklist.md`.
- **Suite de Pruebas de Superficie de Ataque (`backend/tests/test_phase_a4_health_and_attack_surface.py`)**:
  - 9 pruebas unitarias y de integración al 100% verificando sondas de salud (incluyendo fallback 503 sanitizado), control de acceso en métricas, bloqueo de rutas de depuración y esquema OpenAPI sin fugas de secretos.

### Added / Security & Domain Integrity Hardening (Roadmap Bloque A - Fase A3)
- **Prevención Anti-SSRF en Media y Enriquecimiento de Portadas (`backend/books/services/cover_service.py`)**:
  - Implementado validador `validate_safe_external_url` con verificación estricta de esquemas HTTP/HTTPS, resolución DNS y denegación de IPs privadas (RFC 1918), loopback, link-local / cloud metadata (`169.254.169.254`), multicast y direcciones reservadas.
  - La función `download_and_attach_image` valida de forma recurrente contra SSRF antes de realizar la descarga y en cada salto de redirección HTTP.
- **Cálculo Atómico de Rating sin Cascada de Signals (`backend/books/tasks.py`, `backend/books/models.py`)**:
  - `recalculate_book_rating_task` y `update_book_rating` ejecutan actualización atómica directa mediante `Book.objects.filter(id=...).update(average_rating=...)`, evitando disparar bucles recursivos de `post_save` en `Book` y refrescando deterministamente la caché (`invalidate_book_cache`).
- **Throttling Agresivo en Endpoints Costosos (`backend/books/throttling.py`, `backend/mybookconnect/settings.py`, `backend/books/views.py`, `backend/books/import_views.py`)**:
  - Nuevas clases `BookImportThrottle` (10/hora), `EnrichmentThrottle` (20/hora) y `AuthorClaimThrottle` (5/hora) aplicadas a importaciones CSV, sincronización externa bajo demanda y reclamos de autor.
- **Validación Temprana contra Reseñas Duplicadas (`backend/books/serializers.py`)**:
  - `ReviewSerializer.validate` comprueba proactivamente si el usuario autenticado ya posee una reseña activa no eliminada (`deleted_at__isnull=True`) para el libro, retornando `ValidationError` con código semántico `duplicate_review`.
- **Aislamiento Social y Anti-Enumeración (`backend/users/views.py`, `backend/users/privacy_service.py`)**:
  - Confirmado y blindado el retorno `404 Not Found` en `UserDetailView` para usuarios bloqueados, previniendo enumeración de cuentas.
- **Suite de Pruebas de Integridad de Dominio (`backend/tests/test_phase_a3_domain_integrity.py`)**:
  - 24 pruebas unitarias y de integración al 100% cubriendo protección SSRF, cálculo atómico, throttling agresivo, unicidad de reseñas y aislamiento social.

### Security / Authentication & Session Hardening (Roadmap Bloque A - Fase A2)
- **Cookies HttpOnly Seguras para JWT (`backend/users/auth_cookies.py`, `backend/mybookconnect/settings.py`)**:
  - Migración y emisión de `access_token` y `refresh_token` como cookies `HttpOnly`, `SameSite=Lax`, `Secure` en `CustomTokenObtainPairView`, `GoogleOAuthLoginView`, `PasswordChangeView` y `CustomTokenRefreshView`.
  - Soporte transparente para autenticación por cookie en `RevocationCheckingJWTAuthentication`, manteniendo compatibilidad con cabecera `Authorization: Bearer`.
- **Rotación Estricta de Refresh Tokens y Blacklist (`backend/users/auth_views.py`, `backend/users/views.py`)**:
  - `CustomTokenRefreshView` renueva el par de tokens extrayendo el refresh token de cookies seguras o cuerpo JSON, añadiendo el token previo a la blacklist (`BlacklistedToken`).
  - `LogoutView` revoca el refresh token y elimina las cookies HttpOnly de la respuesta (`delete_auth_cookies`).
- **WebSockets Seguros y Erradicación de Query String Auth (`backend/mybookconnect/middleware.py`)**:
  - Erradicación terminante del parámetro `?token=` en WebSockets (CWE-598 / OWASP). Todo intento es bloqueado y clasificado como `AnonymousUser`.
  - Autenticación segura mediante ticket efímero de un solo uso (`?ticket=`) generado vía `/api/v1/auth/ws-ticket/` (validez <60s) o cookies HttpOnly del handshake.
- **Frontend Hardening (`frontend/src/store/auth.ts`, `frontend/src/api/client.ts`, `frontend/src/hooks/useChatWebSocket.ts`)**:
  - Erradicación del almacenamiento de tokens JWT en `localStorage` mediante `partialize` en Zustand persist (únicamente se preserva el perfil y estado booleano de sesión).
  - Configuración global de `credentials: 'include'` en `apiClient` para transmisión automática de cookies de sesión.
  - Actualización de `useChatWebSocket` para conectar exclusivamente con ticket efímero o cookies, eliminando fugas de JWT en URLs.
- **Suite de Pruebas de Seguridad (`backend/tests/test_phase_a2_security_auth.py`)**:
  - Cobertura del 100% (7 pruebas unitarias e integración) validando cookies HttpOnly, rotación, blacklist, logout y rechazo de query strings inseguros en WebSockets.

### Changed / Baseline Freeze & Security Hardening Foundation (Roadmap Bloque A - Fase A1)
- **Tag y Punto de Congelación Git**:
  - Creado y publicado tag git `v1.0.0-pre-hardening` para garantizar reproducibilidad y punto de retorno limpio.
- **Copia de Seguridad y Recuperación Ante Desastres**:
  - Volcado de PostgreSQL cifrado mediante AES-256-CBC (`backups/db/db_backup_pre_hardening_20261010.sql.gz.enc`, SHA-256 `39e179...`) acompañado de su manifiesto criptográfico JSON v1.1.
  - Copia de seguridad comprimida del volumen `media/` (`backups/media/media_backup_pre_hardening_20261010.tar.gz`, 220MB).
  - Corrección de valores por defecto de usuario y base de datos (`booksocial`) en `scripts/backup/backup_db.sh` y `restore_db.sh`.
- **Integridad de Migraciones y Código**:
  - Comprobación de migraciones de base de datos (`makemigrations --check`): 0 discrepancias pendientes.
  - Auditoría de marcadores de conflicto (`<<<<<<<`): 0 conflictos residuales.
  - Confirmada la erradicación total de módulos y código muerto (`backend/app`, `backend/config`).
- **Política de Gestión y Rotación de Secrets**:
  - Creada política formal en `docs/security/secrets_management_policy.md` con pautas de rotación para `SECRET_KEY`, credenciales de base de datos, APIs de IA y afiliados.
  - Actualizada plantilla `.env.example` con variables de configuración de Amazon PA-API.
- **Validación de Pruebas**:
  - Suite de pruebas de baseline ejecutada al 100% (43 tests pasando sin fallos).
  - Verificación estricta de TypeScript (`npm run typecheck`) limpia con 0 errores.

### Added / Verified Author Exclusive Publications & Administration Moderation / Censorship (RoadmapV3)
- **Autorización Estricta de Publicaciones de Autor (`backend/books/views.py`, `backend/books/serializers.py`)**:
  - Restricción rigurosa en `AuthorPublicationViewSet.perform_create` y `AuthorAnnouncementCreateView`: únicamente los autores titulares con perfil verificado (`(author.claimed_by == user and author.is_verified) or (profile.author == author and profile.is_verified)`) pueden publicar en el perfil de autor (`403 Forbidden` para usuarios ordinarios, terceros o reclamaciones no verificadas).
  - Modificación y eliminación (`perform_update`, `perform_destroy`): restringido exclusivamente al autor verificado titular o administradores/moderadores (`403 Forbidden` para terceros).
- **Campos de Moderación y Monetización en `AuthorAnnouncement` (`backend/books/models.py`)**:
  - Añadidos `is_paid` (boolean), `price` (decimal positivo), `is_moderated` (boolean), `moderation_reason` (text), `moderated_by` (FK User), `moderated_at` (DateTimeField).
  - Migración de base de datos `books/migrations/0041_authorannouncement_moderation_and_paid.py` generada y aplicada en PostgreSQL.
- **Flujo de Censura y Moderación (`censor` endpoint & consola universal)**:
  - Acción `@action(detail=True, methods=['post'])` en `AuthorPublicationViewSet` (`/api/v1/books/author-publications/<id>/censor/`) que permite a administradores y moderadores alternar o fijar `is_moderated`, especificar `moderation_reason`, y registrar trazas en `AuditLog`.
  - Integración en la consola de moderación administrativa universal (`AdminContentHideView` y `AdminContentRestoreView` en `/api/v1/admin/moderation/hide/` y `/restore/`) para `target_type='author_publication'` y `'announcement'`.
  - Ocultación garantizada: los lectores anónimos u ordinarios nunca ven publicaciones con `is_moderated=True` (`get_queryset` y `get_announcements_for_author`), mientras que el autor original y los administradores pueden visualizarlas con advertencia de moderación.
- **Frontend y Controles de Interfaz (`Author.tsx`, `AuthorPublicationsSection.tsx`)**:
  - Validación en `Author.tsx` distinguiendo `isVerifiedAuthorOwner` (`author.claimed_by === user.id && author.is_verified`) de `isAdminOrModerator`.
  - Botón "Nueva Publicación" reservado exclusivamente para el autor verificado titular.
  - Opciones de monetización en formulario: checkbox para publicaciones de pago (`is_paid`) y campo de precio (€).
  - Controles de moderación para administradores: botón de edición/eliminación administrativa, botón y modal de censura (`Confirmar Censura` / `Restaurar y Publicar`).
  - Distintivos visuales: badge `🔒 De pago (X.XX €)`, badge `🚫 Censurada` y alerta de moderación con motivo.
- **Pruebas y Verificación**:
  - Suite de pruebas backend exhaustiva `backend/tests/test_author_verified_publications.py` (**9/9 tests PASSED**).
  - Regresión backend `backend/tests/test_sprint12_author_publications.py` (**7/7 tests PASSED**).
  - Verificación frontend: `npm run typecheck` limpio (0 errores) y build de producción Vite exitoso.

### Added / Amazon PA-API Affiliate Provider & Book Page Count Support
- **Proveedor Amazon Product Advertising API v5 (`backend/books/services/providers/amazon.py`)**:
  - Implementación de firma canónica AWS Signature Version 4 (`AWS4-HMAC-SHA256`) sin dependencias externas mediante `hashlib` y `hmac`.
  - Configuración preparada en Django settings (`AMAZON_PAAPI_ACCESS_KEY`, `AMAZON_PAAPI_SECRET_KEY`, `AMAZON_PAAPI_TAG`, `AMAZON_PAAPI_REGION`, `AMAZON_PAAPI_HOST`).
  - Detección reactiva mediante `is_configured()` con fallback transparente e inmediato a Google Books cuando no hay credenciales activas.
  - Métodos `search_by_title` y `get_by_isbn` extrayendo título, autor, portada en alta resolución, recuento de páginas (`TechnicalInfo.NumberOfPages`) y enlace de afiliado (`DetailPageURL`).
- **Soporte Global de Recuento de Páginas (`page_count`)**:
  - Campo `page_count = models.PositiveIntegerField(null=True, blank=True)` añadido a `Book` con migración `0040_book_page_count.py` aplicada en PostgreSQL.
  - Extracción de número de páginas en `GoogleBooksProvider` (`volumeInfo.pageCount`) y `OpenLibraryProvider` (`number_of_pages` / `number_of_pages_median`).
  - Exposición de `page_count` en `BookSerializer` y en la cabecera de la ficha del libro en frontend (`BookDetail.tsx` con icono `📖 {book.page_count} páginas`).
- **Cadena Jerárquica de Importación y Monetización (`import_service.py`)**:
  - Orden prioritario de búsqueda externa: 1º Amazon PA-API, 2º Google Books, 3º Wikipedia, 4º OpenLibrary.
  - Creación automática de oferta comercial `BookBuyLink` en el marketplace al importar libros desde Amazon.
  - Corrección de deduplicación de ISBN principal al actualizar obras existentes.
- **Verificación y Pruebas**:
  - Suite de pruebas backend `backend/tests/test_amazon_books_provider.py` (**12/12 tests pasando al 100%**).
  - Regresión combinada de importación y catálogo (**17/17 tests pasando al 100%**).
  - Verificación global frontend: `npm run typecheck` limpio (0 errores), Vitest (**24 suites / 91 tests pasando al 100%**) y build de producción Vite exitoso.

### Added / Multimodal AI & Enhanced Literary Assistant (RoadmapV3 - Sección 30: IA Multimodal - Sprint 20)
- **Motor de Visión Computacional Literaria (`backend/ai/multimodal_service.py`)**:
  - Análisis cromático avanzado: extracción de paleta de colores dominantes en formato hexadecimal y nombres descriptivos con fallback heurístico determinista y validación PIL.
  - Clasificación estética y tonal: categorización de estilos artísticos (Realismo Mágico, Ilustración Fantástica, Fotografía Editorial, Minimalista, etc.) y atmósferas sensoriales (nostálgica, épica, misteriosa, etc.).
  - Accesibilidad Universal: generación de texto alternativo descriptivo enriquecido (`accessible_alt_text`) para lectores con discapacidad visual conforme a estándares WCAG 2.1 AA.
  - Búsqueda visual inversa: coincidencia visual y semántica con obras del catálogo existente (`analyze_cover_image`) calculando el porcentaje de certidumbre (`match_confidence`).
- **Endpoints API REST (`/api/v1/books/ai/multimodal/`)**:
  - `POST /api/v1/books/ai/multimodal/analyze-cover/`: análisis visual completo y búsqueda por portada (acepta JSON base64 o multipart/form-data).
  - `POST /api/v1/books/ai/multimodal/assistant/`: interacción conversacional con IA con soporte de adjuntos de imagen para resolver dudas sobre ediciones, estilos y portadas.
  - `GET /api/v1/books/<id>/ai/visual-insights/`: análisis cromático y artístico específico de la cubierta de una obra existente.
- **Frontend y Experiencia de Usuario**:
  - `VisualBookSearchModal.tsx`: modal interactivo de búsqueda visual con drag & drop de imágenes, vista previa, análisis visual con IA, visualización de paleta cromática con copia de códigos HEX al portapapeles y enlace directo a la ficha del libro detectado.
  - `AIAssistantModal.tsx`: ampliación con botón de cámara 📷 para adjuntar imágenes, miniaturas en las burbujas de chat y diálogo multimodal.
  - `BookDetail.tsx`: pestaña interactiva "🎨 Arte & Portada" en la tarjeta BookAI con swatches de color, estilos, atmósferas y descripción accesible.
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint20_multimodal_ai.py`: **7/7 tests pasando al 100%**.
  - Regresión secuencial completa backend (Sprints 1 al 20): **142/142 tests pasando consecutivamente al 100%** (126.59s).
  - Suite frontend `frontend/src/features/ai/__tests__/MultimodalAI.test.tsx`: **6/6 tests pasando al 100%**.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), suite completa de Vitest (**24 suites / 91 tests pasando al 100%**) y build de producción limpio en Vite (13.06s).

### Added / Marketplace & Editorial Buy Links (RoadmapV3 - Sección 30: Marketplace / Editoriales)
- **Modelado de Datos y Entidad Editorial (`marketplace_models.py`)**:
  - Modelo `Publisher` con atributos de país, descripción, web oficial, logotipo y acreditación oficial verificada.
  - Atributo de relación `publisher` en el modelo principal `Book`.
  - Modelo `BookBuyLink` para opciones de compra con denominación de tienda, categorización de canal (`indie_network`, `online_retailer`, `publisher_direct`, etc.), formato de obra, precio estimado y badge de acreditación oficial.
  - Modelo `MarketplaceClick` para telemetría de conversión y seguimiento de intención de compra totalmente anonimizado (compatible con RGPD).
  - Migración `0039_bookbuylink_marketplaceclick_publisher_and_more.py` ejecutada en PostgreSQL.
- **Servicio de Dominio y Agregación Multitienda (`marketplace_service.py`)**:
  - Agregación ética de ofertas comerciales con soporte preferente para la red de librerías locales e independientes (**TodosTusLibros / CEGAL**), grandes librerías (**Casa del Libro**, **Fnac**), plataformas digitales (**Amazon**, **Kindle**, **Audible**, **Google Play Books**) y venta directa del autor o sello editorial.
  - Generación dinámica inteligente de enlaces canónicos a partir de ISBN y título/autor.
  - Registro de clics éticos sin almacenar PII y compatibilidad retroactiva con `AffiliateClick`.
  - Gestión y validación de permisos de autor verificado para agregar o revocar enlaces oficiales.
- **Endpoints API REST (`/api/v1/books/`)**:
  - `GET /api/v1/books/<id>/marketplace/`: opciones agregadas multitienda y agrupadas por formato.
  - `POST /api/v1/books/<id>/marketplace/click/`: telemetría anónima de clics de compra.
  - `POST /api/v1/books/<id>/marketplace/links/`: gestión de enlaces oficiales para autores propietarios.
  - `DELETE /api/v1/books/marketplace/links/<id>/`: eliminación de enlaces oficiales de compra.
  - `GET /api/v1/books/publishers/` y `GET /api/v1/books/publishers/<slug>/`: catálogo y ficha de editoriales.
- **Frontend y Experiencia de Usuario (`BookMarketplaceModal.tsx`)**:
  - Modal interactivo WAI-ARIA accesible con pestañas de filtrado (Todas, Librerías de Barrio, Papel, Ebook, Audiolibro).
  - Apertura segura con atributos `rel="noopener noreferrer sponsored"` y telemetría no intrusiva.
  - Botón "🛍️ Dónde comprar / Librerías" y mención de editorial en la ficha de libro (`BookDetail.tsx`).
  - Formulario integrado para que autores verificados publiquen sus enlaces de venta directa.
- **Pruebas y Verificación Integral**:
  - Suite backend `test_sprint19_marketplace_editoriales.py`: 7/7 tests pasando al 100%.
  - Suite frontend `BookMarketplace.test.tsx`: 5/5 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 19): 135/135 tests pasando consecutivamente al 100% en 134.34s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (23 suites / 85 tests pasando al 100%) y build de producción limpio generado en 13.01s.

### Added / Audiobooks & Text-to-Speech (TTS) (RoadmapV3 - Sección 30: Audiolibros y TTS)
- **Modelado de Datos y Persistencia de Escucha (`audiobook_models.py`)**:
  - Modelo `AudiobookTrack` para pistas narradas con metadatos de duración, orden secuencial, narrador y muestra previa (`is_sample`).
  - Modelo `UserAudiobookProgress` para el seguimiento del timestamp de escucha, porcentaje completado y finalización por usuario y libro.
  - Migración `0038_audiobooktrack_useraudiobookprogress_and_more.py` aplicada en base de datos PostgreSQL.
- **Servicio de Dominio y Lógica de Escucha (`audiobook_service.py`)**:
  - Formateo y cómputo de duración total de audiolibros con soporte para fragmentos de muestra.
  - Sincronización y actualización atómica del progreso de escucha del lector con recálculo dinámico de porcentaje completado.
  - Fallback automático e inteligente a Text-to-Speech ("BookVoice TTS") con síntesis por párrafos cuando el libro no cuenta con pistas comerciales grabadas.
  - Catálogo de audiolibros con filtros por género, narrador y búsqueda por título/autor.
  - Estantería de audiolibros en progreso para reanudación inmediata desde la biblioteca personal.
- **Endpoints API REST (`/api/v1/books/`)**:
  - `GET /api/v1/books/<id>/audiobook/`: detalle de pistas y progreso de escucha del usuario.
  - `POST /api/v1/books/<id>/audiobook/progress/`: guardado de posición y estado de escucha.
  - `GET /api/v1/books/audiobooks/`: catálogo general de audiolibros disponibles.
  - `GET /api/v1/books/audiobooks/in-progress/`: estantería de audiolibros en curso del usuario autenticado.
- **Frontend y Reproductor Global Interactivo**:
  - Store global Zustand `audioPlayer.ts` con control de audio nativo y motor Web Speech API (TTS).
  - Reproductor flotante persistente `AudioPlayerBar.tsx` integrado en layouts protegidos y públicos con controles de salto ±15s, slider de tiempo, selector de velocidad (0.75x a 2.0x) y guardado en backend.
  - Componente `BookAudiobookSection.tsx` integrado en `BookDetail.tsx` con listado de pistas y activación de modo narración.
  - Sección "🎧 Audiolibros en curso" en `Library.tsx` con barras de progreso y enlace para continuar la escucha.
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint18_audiobooks_tts.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/books/__tests__/AudiobookPlayer.test.tsx`: 5/5 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 18): 128/128 tests pasando consecutivamente al 100% en 133.23s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (22 suites / 80 tests pasando al 100%) y build de producción limpio generado en 33.17s.

### Added / Multimodal Recommendations & Similar Readers (RoadmapV3 - Sección 30: Recomendaciones Avanzadas y Lectores Afines)
- **Motor Multimodal y Algoritmos Granulares (`recommendation_service.py` & `cache_utils.py`)**:
  - Soporte completo de 7 estrategias de recomendación: `hybrid` (v3 multimodal tri-vectorial), `collab` (v2 colaborativo), `semantic` (vectores de embedding y trama), `serendipity` (joyas altamente valoradas de autores no leídos por el usuario), `rules`, `social` y `v1`.
  - Exposición de porcentaje de match transparente (`affinity_percentage`, escala calibrada 65% - 98%), vector de desglose de contribución (`breakdown`) y motivo contextual explicable (`reason`).
  - Estimación de número de páginas en el catálogo mediante `user_entries__current_page` (`Max('user_entries__current_page')`).
  - Filtros granulares por género (`category_id`) y extensión de lectura (`length_tier`: `short` <200p, `medium` 200-399p, `long` 400-599p, `epic` 600+p).
  - Exclusión automática de obras descartadas por el usuario (`exclude_dismissed=true`).
- **Endpoint de Descarte Rápido y Caché Redis (`/api/v1/books/recommendations/dismiss/`)**:
  - `POST /api/v1/books/recommendations/dismiss/` respaldado por `dismiss_recommendation` en `recommendation_feedback_service.py`. Registra la interacción `DISMISSED` en el modelo `RecommendationFeedback`.
  - Invalidación quirúrgica e instantánea de la caché Redis del usuario para todas las combinaciones y variantes de estrategias en `cache_utils.py`.
- **Red de Gemelos Lectores (`/api/v1/books/recommendations/similar-readers/`)**:
  - Endpoint `GET /api/v1/books/recommendations/similar-readers/` operativo que compara patrones de valoración y vectores de usuarios para encontrar lectores afines con libros compartidos.
- **Frontend Interactivo Dedicado (`RecommendationsPage.tsx` / `/recommendations`)**:
  - Nueva página `/recommendations` integrada en `router.tsx` bajo `ProtectedLayout`, con enlace principal "Descubre" en `Header.tsx` y enlace rápido "Ver todas →" desde el muro principal `Home.tsx`.
  - Selector de 4 modos: "Híbrido IA", "Gemelos Lectores", "Estilo y Temática", "Descubrimiento".
  - Barra de filtros combinados de género y extensión con contador reactivo de obras encontradas.
  - Tarjetas interactivas de libros con portadas adaptables, badges con degradados del `% Afinidad`, motivo explicable, botón de 1 clic a "Quiero leer" (con transición inmediata a "En tu biblioteca") y botón de descarte rápido (remoción fluida de la tarjeta).
  - Panel lateral de "Gemelos Lectores" con avatars, porcentaje de similitud y libros en común.
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint17_advanced_recommendations.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/discovery/__tests__/RecommendationsPage.test.tsx`: 5/5 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 17): 121/121 tests pasando consecutivamente al 100% en 107.97s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (21 suites / 75 tests pasando al 100%) y build de producción limpio generado en 14.88s.

### Added / Social Sharing & Graphic Cards Preview (RoadmapV3 - Sección 30: Integración con Redes Sociales y Compartición Gráfica)
- **Motor de Compartición Backend (`social_share_service.py`)**:
  - `generate_social_share_card(share_type, object_id, user, year)`: generación enriquecida de cargas útiles sociales para 5 entidades principales (`book`, `reading_stats`, `challenge`, `badge`, `reading_list`).
  - Deep links directos de 1 clic para X (Twitter), WhatsApp, Telegram, LinkedIn, Facebook y correo electrónico.
  - Generación de textos con emojis, hashtags contextuales y URL canónica.
  - `track_social_share(share_type, object_id, platform, user)`: registro de telemetría de difusión y auditoría de eventos de compartición.
- **Endpoints API REST (`/api/v1/books/share/`)**:
  - `GET /api/v1/books/share/card/` (`SocialShareCardView`): consulta y generación en tiempo real de metadatos sociales estructurados y deep links.
  - `POST /api/v1/books/share/track/` (`SocialShareTrackView`): telemetría y registro de clics de compartición por plataforma social.
- **Frontend y UX (`SocialShareModal.tsx`)**:
  - Modal accesible con previsualización en vivo de la tarjeta gráfica social ("Social Card Preview"): gradientes temáticos, portada o insignias métricas, formato editorial listo para compartir.
  - Botones directos con iconos oficiales para X (Twitter), WhatsApp, Telegram, LinkedIn y Facebook (`rel="noopener noreferrer"`).
  - Botón de copiado de URL y botón de copiado de texto enriquecido con emojis y hashtags con feedback háptico/visual (`¡Enlace copiado!`, `¡Texto copiado!`).
  - Integración en `ReadingStats.tsx` (en la cabecera y en la sección de Memoria Anual) y en `BookDetail.tsx` (botón "Compartir este libro").
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint16_social_sharing.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/social/__tests__/SocialShareModal.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 16): 114/114 tests pasando consecutivamente al 100% en 101s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (20 suites / 70 tests pasando al 100%) y build de producción limpio generado en 16.05s.

### Added / Advanced Reading Statistics & Year in Review (RoadmapV3 - Sección 30: Estadísticas Avanzadas de Lectura, Ritmo y Memoria Anual)
- **Motor de Dominio y Estadísticas Granulares (`stats_service.py` & `cache_utils.py`)**:
  - Soporte de filtrado por año (`?year=YYYY` o `?year=all`) con lista de años disponibles con actividad (`available_years`) y clave de caché Redis adaptada `stats:user:<id>[:year:<year>]` con invalidación atómica multianual.
  - Métricas de Ritmo y Velocidad (`reading_pace`): días promedio por libro (`avg_days_per_book`), libro más rápido (`fastest_book`), libro más pausado (`slowest_book`), promedio de páginas al día y al mes, y detección automática del mes cumbre de lectura (`highest_reading_month`).
  - Distribución por Longitud (`length_distribution`): clasificación de lecturas en Cortos (<200p), Medios (200-399p), Largos (400-599p) y Épicos (600+p) con libros extremos completados (`longest_book` y `shortest_book`).
  - Distribución por Formato y Posesión (`format_distribution`): físico vs digital/ebook y en propiedad vs prestado.
  - Memoria Anual / "Year in Review" (`year_in_review`): retrospectiva anual con libro mejor calificado, género y autor predilectos, y comparativa interanual frente al año previo (+libros y +páginas).
- **Endpoints API REST (`/api/v1/books/statistics/`)**:
  - `ReadingStatsView`: acepta parámetro `year`, delega en `services.get_user_reading_stats(target_user_id, year=year)` y valida estrictamente la privacidad del perfil (público, solo amigos o privado).
- **Frontend y UX (`ReadingStats.tsx` / `/statistics`)**:
  - Selector dinámico de año en la cabecera (píldoras interactivas con `Histórico`, `2026`, `2025`, etc.).
  - 4 Pestañas WAI-ARIA completas:
    - 📊 **Resumen General**: KPIs principales, gráfico de barras mensual con alternancia entre métrica de **Libros** y **Páginas**, distribución de estrellas (1..5), preferencias literarias y autores predilectos.
    - ⚡ **Ritmo & Velocidad**: tarjetas de duración media por libro, páginas diarias/mensuales, mes récord y tarjetas destacadas de lectura más veloz y más pausada.
    - 📐 **Longitud & Formatos**: barras visuales de tramos de páginas, libros extremos completados y comparativas de formato (papel vs digital) y posesión.
    - 🏆 **Memoria Anual**: tarjeta editorial retrospectiva del año con destacados, libro cumbre mejor valorado y comparativa de crecimiento frente al año previo (+/- libros y páginas).
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint15_advanced_reading_stats.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/books/__tests__/ReadingStats.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 15): 107/107 tests pasando consecutivamente al 100% en 126s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (19 suites / 66 tests pasando) y build de producción limpio generado en 13.88s.

### Added / Advanced Gamification & Reading Challenges (RoadmapV3 - Sección 30: Gamificación Avanzada y Retos de Lectura)
- **Motor de Sincronización Dinámica de Retos**:
  - `GamificationService.sync_user_challenge_progress()`: cálculo reactivo de progreso según libros leídos (`books_count`), páginas leídas (`pages_count`), reseñas (`reviews_count`) o género literario (`genre_books`), concediendo las insignias correspondientes y completando el reto automáticamente.
  - `GamificationService.ensure_default_challenges()`: siembra automática e idempotente de retos comunitarios ("Reto de Lectura Anual 2026", "Sprint de Novela Corta", "Maratón de Páginas 2026", "Clásicos Inolvidables").
  - `GamificationService.leave_challenge()`: lógica transaccional para abandonar un reto y decrementar el contador de participantes.
- **Endpoints API REST (`/api/v1/gamification/challenges/`)**:
  - `ReadingChallengeListView`: sincroniza en caliente el progreso del usuario autenticado y expone el listado completo de retos con progreso y estado de inscripción.
  - `LeaveChallengeView` en `POST /api/v1/gamification/challenges/<slug>/leave/`: permite al lector desapuntarse de un reto.
  - Integración en `ReadingGoalViewSet` y `GamificationOverviewView` para ritmo y proyección de lectura anual y estado de racha diaria.
- **Frontend y UX (`ChallengesPage.tsx` / `/challenges`)**:
  - Página dedicada `/challenges` accesible desde el `Header.tsx` con navegación WAI-ARIA en 4 pestañas interactivas.
  - Pestaña **🏆 Retos Comunitarios**: visualización de tarjetas de reto con porcentaje de avance, metas, participantes y botones dinámicos para Unirse / Abandonar.
  - Pestaña **🎯 Mi Meta Anual**: tarjeta de meta del año con libros leídos, ritmo proyectado (adelantado/a tiempo) y modal para configurar libros y páginas objetivo.
  - Pestaña **🔥 Racha & Registro**: contador de racha actual en días, racha histórica récord, días congelados y modal para registrar lecturas diarias con páginas y minutos.
  - Pestaña **🎖️ Medallero**: catálogo filtrable de medallas (Todas, Lectura, Racha, Retos, Social) con insignias desbloqueadas y pendientes.
- **Pruebas y Verificación Integral**:
  - Suite backend `backend/tests/test_sprint14_gamification_challenges.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/books/__tests__/ChallengesPage.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 14): 95/95 tests pasando consecutivamente al 100% en 85s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo con 62/62 tests pasando en 18 suites y build de producción limpio generado en 29s.

### Added / Author Newsletters & Broadcasts (RoadmapV3 - Sección 30: Newsletters y Boletines Literarios de Autores)
- **Modelos de Dominio y Base de Datos**:
  - `AuthorNewsletter`: Configuración del boletín oficial por autor literario (`title`, `description`, `frequency` [`WEEKLY`, `BIWEEKLY`, `MONTHLY`, `OCCASIONAL`], `is_active`) con recuento automático de suscriptores y boletines emitidos.
  - `AuthorNewsletterSubscriber`: Registro de suscripción con token seguro (`unsubscribe_token` UUID) para desuscripción en un clic sin requerir contraseñas, estado activo indexado y trazabilidad temporal.
  - `AuthorNewsletterIssue`: Entregas y números de la newsletter con estados `DRAFT`, `SCHEDULED`, `SENT`, soporte de programación futura, fecha de envío y métricas de alcance de lectores.
  - Migración aplicada en PostgreSQL: `0037_authornewsletter_authornewsletterissue_and_more.py`.
- **Endpoints API REST (`/api/v1/books/author-newsletters/` y `author-newsletter-issues/`)**:
  - ViewSet `AuthorNewsletterViewSet` con acciones `@action subscribe` (suscripción o reactivación en 1 clic), `@action unsubscribe` (cancelación inmediata), `@action my_subscriptions` (consulta de boletines suscritos por el lector) y `@action subscribers` (listado paginado exclusivo para el autor).
  - ViewSet `AuthorNewsletterIssueViewSet` con filtrado por newsletter, control estricto de visibilidad (solo entregas enviadas para público general) y acción `@action send_issue` para emisión inmediata a todos los suscriptores activos.
- **Frontend y UX (`Author.tsx` / `AuthorNewsletterSection.tsx`)**:
  - Componente accesible `AuthorNewsletterSection` con diseño editorial y paleta armónica integrado en la ficha del autor.
  - Tarjeta de suscripción destacada con selector dinámico de frecuencia, recuento en vivo de lectores suscritos y botón con retroalimentación instantánea ("Suscribirme con 1 clic" / "✓ Suscrito (Cancelar)").
  - Lector desplegable de entregas publicadas con formateo de fechas y métricas de audiencia.
  - Panel de autor verificado con modales interactivos para configurar la newsletter y redactar/enviar nuevas entregas con opción de borrador o publicación inmediata.
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint13_author_newsletters.py` (7/7 tests al 100%).
  - Creada suite `frontend/src/features/books/__tests__/AuthorNewsletterSection.test.tsx` (4/4 tests al 100%).
  - Regresión secuencial completa de backend superada (88/88 pruebas pasando al 100% de Sprints 1 al 13).
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), 58 tests en Vitest pasando al 100% en 17 suites y build de producción Vite exitoso.

### Added / Author Publications & Chapter Previews (RoadmapV3 - Sección 30: Publicaciones Avanzadas de Autores y Adelantos Literarios)
- **Modelos de Dominio y Base de Datos**:
  - `AuthorAnnouncement`: Enriquecido con clasificación tipológica (`publication_type`: `ANNOUNCEMENT`, `CHAPTER_PREVIEW`, `AUTHOR_DIARY`, `DELETED_SCENE`, `Q_AND_A`), vinculación opcional directa al catálogo de autores (`catalog_author`), generación automática de extractos (`excerpt`), cálculo dinámico de tiempo estimado de lectura (`estimated_reading_time`), aviso y delimitación de spoilers (`has_spoilers`, `spoiler_warning`) y soporte para borradores privados (`is_draft`).
  - Migración aplicada en PostgreSQL: `0036_alter_authorannouncement_options_and_more.py`.
- **Endpoints API REST (`/api/v1/books/author-publications/`)**:
  - ViewSet completo `AuthorPublicationViewSet` con filtrado por autor, catálogo, tipo de contenido, libro vinculado y soporte de visualización de borradores (`include_drafts`) para autores propietarios.
  - Acción `@action toggle_pin`: Permite anclar/desanclar publicaciones destacadas en la parte superior del perfil del autor.
  - Compatibilidad retroactiva garantizada para vistas existentes de comunicados (`AuthorAnnouncementListView` y `AuthorAnnouncementCreateView`).
- **Frontend y UX (`Author.tsx` / `AuthorPublicationsSection.tsx`)**:
  - Componente accesible `AuthorPublicationsSection` integrado en el perfil de autor.
  - Filtro por categorías literarias con botones de píldora interactivos.
  - Lector desplegable con truncado elegante de texto, advertencia explícita de spoilers con botón de revelación interactivo y etiquetas de tiempo de lectura.
  - Interruptor para visualizar borradores en tiempo real por parte del creador.
  - Modales accesibles para crear y editar publicaciones con control granular de tipo, libro relacionado, spoiler warning y borrador.
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint12_author_publications.py` (7/7 tests al 100%).
  - Creada suite `frontend/src/features/books/__tests__/AuthorPublicationsSection.test.tsx` (4/4 tests al 100%).
  - Regresión secuencial completa de backend superada (86/86 pruebas pasando al 100% de Sprints 1 al 12).
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), 54 tests en Vitest pasando al 100% en 16 suites y build de producción Vite exitoso.

### Added / Author Events & Encounters (RoadmapV3 - Sección 30: Eventos de Autores, Presentaciones y Reservas)
- **Modelos de Dominio y Base de Datos**:
  - `AuthorEvent`: Modelo para eventos literarios (presentaciones, firmas, Q&A, lecturas, talleres). Soporta formatos `ONLINE`, `IN_PERSON`, `HYBRID`, enlace a libro presentado, zona horaria y aforo máximo (`max_attendees`).
  - `AuthorEventAttendee`: Inscripciones de lectores con estados `REGISTERED`, `WAITLIST`, `CANCELLED` y preguntas opcionales para el autor.
  - Migración aplicada en PostgreSQL: `0035_authorevent_authoreventattendee.py`.
- **Endpoints API REST (`/api/v1/books/author-events/`)**:
  - ViewSet completo con filtrado avanzado por autor, libro, tipo, formato, próximos/pasados (`upcoming=true`) y búsqueda por texto.
  - Acción `@action register`: reserva de plazas con colocación automática en lista de espera al alcanzar aforo.
  - Acción `@action cancel_registration`: cancelación de plaza y autopromoción automática del primer usuario en lista de espera a confirmado.
  - Acción `@action attendees`: consulta de asistentes y preguntas registradas para autores y moderadores.
- **Frontend y UX (`Author.tsx` / `AuthorEventsSection.tsx`)**:
  - Componente accesible `AuthorEventsSection` integrado en la vista de autor.
  - Filtro interactivo de eventos próximos e históricos.
  - Tarjetas de eventos con badges de tipo, formato, indicador de plazas y fecha localizada en español.
  - Modal para inscribirse con formulario de preguntas para el coloquio o notas al autor.
  - Modal para programar nuevos eventos y modal para consultar lista de inscritos y preguntas formuladas.
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint11_author_events.py` (7/7 tests al 100%).
  - Creada suite `frontend/src/features/books/__tests__/AuthorEventsSection.test.tsx` (4/4 tests al 100%).
  - Regresión secuencial completa de backend superada (79/79 pruebas pasando al 100% de Sprints 1 al 11).
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), 50 tests en Vitest pasando al 100% en 15 suites y build de producción Vite exitoso.

### Added / Collaborative Lists (RoadmapV3 - Sección 30: Listas Colaborativas y Atribución de Autoría)
- **Modelos de Dominio y Base de Datos**:
  - `ReadingList.is_collaborative`: Flag booleano indexado para habilitar listas de lectura colaborativas entre usuarios.
  - `ReadingListItem.added_by`: Clave foránea a `User` para registrar y atribuir qué miembro aportó cada libro a la lista.
  - `ReadingListCollaborator`: Modelo relacional de invitaciones y colaboraciones (`role`, `status`, `can_add_books`, `can_remove_books`, `invited_by`).
  - Migración aplicada en PostgreSQL: `0034_readinglistcollaborator_readinglist_is_collaborative_and_more.py`.
- **Endpoints API REST (`/api/v1/books/reading-lists/`)**:
  - Soporte de filtro `?collaborative=true` para consultar listas colaborativas en las que el usuario participa o es propietario.
  - Adaptación de `PrivacyService.filter_visible_reading_lists` para visibilidad de listas privadas por colaboradores aceptados.
  - Endpoints `@action` en `collaborators/` (`GET`, `POST`) y `collaborators/<user_id>/` (`PATCH`, `DELETE`).
  - Permisos adaptados en `add-book` y `remove-book` con autoría `added_by` y control de borrado según permisos o aportación propia.
- **Frontend y UX (`ReadingLists.tsx`)**:
  - Pestaña "🤝 Colaborativas" en la barra de navegación de listas.
  - Badges de lista colaborativa en tarjetas de cuadrícula y vista de detalle.
  - Panel interactivo de colaboradores con avatares, roles y estados.
  - Banner para aceptar o rechazar invitaciones de colaboración pendientes.
  - Modal interactivo para invitar colaboradores por nombre de usuario con roles (`EDITOR`, `VIEWER`) y permisos granulares.
  - Atribución visual de autoría ("Añadido por @usuario") en cada libro de la lista.
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint10_collaborative_lists.py` (7/7 pruebas al 100%).
  - Regresión secuencial completa de backend superada (72/72 pruebas pasando al 100% de Sprints 1 al 10).
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), 46 tests en Vitest pasando al 100% en 14 suites y build de producción Vite exitoso.

### Added / Reading Clubs & Groups (RoadmapV3 - Sección 30.1: Clubs de Lectura, Grupos y Debates por Capítulos)
- **Modelos de Dominio de Clubs y Grupos Literarios**:
  - Modelos `ReadingClub`, `ReadingClubMember`, `ReadingClubBook`, `ReadingClubDiscussion` y `ReadingClubDiscussionComment`.
  - Soporte de clubs públicos y privados, roles jerárquicos (`ADMIN`, `MODERATOR`, `MEMBER`) y estados (`ACTIVE`, `PENDING`, `BANNED`).
  - Plan de lecturas conjuntas (`CURRENT`, `UPCOMING`, `FINISHED`) con hitos por capítulos y actualización automática del libro en curso del club.
  - Hilos de debate con avisos y ocultación de spoilers (`has_spoilers`), temas fijados (`is_pinned`) y comentarios anidados.
- **Endpoints API REST (`/api/v1/clubs/`)**:
  - Catálogo de clubs con filtros por pertenencia (`my_clubs=true`) y búsqueda por texto (`q`).
  - Creación con auto-asignación de administrador al creador, unión automática o por solicitud según privacidad, salida segura (impidiendo huérfanos de administrador único), gestión de roles y plan de lectura.
- **Frontend y UX (`frontend/src/features/clubs/`)**:
  - `ClubsPage.tsx`: Vista de catálogo y exploración con pestañas WAI-ARIA, modal interactivo de creación de club y tarjetas informativas.
  - `ClubDetailPage.tsx`: Panel completo con lectura activa, plan de lecturas, foros de debate con blur/reveal de spoilers, comentarios y listado de miembros.
  - Integración en navegación (`router.tsx`, `Header.tsx`, `PublicHeader.tsx`).
- **Pruebas y Verificación Integral**:
  - Creada suite `backend/tests/test_sprint9_reading_clubs.py` (6 pruebas al 100%).
  - Creada suite `frontend/src/features/clubs/__tests__/ClubsPage.test.tsx` (4 pruebas al 100%).
  - Regresión secuencial completa de backend superada (65 pruebas pasando al 100% de Sprints 1 al 9).
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), 46 tests en Vitest pasando al 100% en 14 suites y build de producción Vite exitoso.

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

[Unreleased]: https://github.com/Zaton81/MyBookSocial/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Zaton81/MyBookSocial/releases/tag/v1.0.0
