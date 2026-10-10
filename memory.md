# Memoria del Proyecto y Contexto Operativo — MyBookConnect

Este documento contiene el **contexto arquitectónico continuo**, el **historial de decisiones técnicas**, las **restricciones obligatorias** y las **trampas resueltas (*gotchas*)** del proyecto **MyBookConnect**.

Cualquier agente de IA o desarrollador que se incorpore a la base de código **DEBE leer y respetar este documento** antes de realizar cambios.

---

## 1. Reglas de Oro del Proyecto (Invariantes Obligatorias — Roadmap.md)

1. **Seguridad e integridad primero:** Ninguna feature nueva tiene prioridad sobre vulnerabilidades, autenticación o inconsistencias de dominio.
2. **Cero regresiones:** Toda fase debe dejar la suite de tests (backend + frontend de Vitest) al 100% y cero migraciones pendientes.
3. **Operabilidad y Reversibilidad:** Todo cambio debe ser reversible, observable y documentado (ADRs + `memory.md` + `Roadmap.md`).
4. **IA opcional:** Las capacidades de IA nunca deben bloquear el flujo principal de lectura, social o biblioteca.
5. **Privacidad por diseño:** Cumplimiento estricto RGPD (Arts. 17 y 20) y minimización de datos son invariantes.
6. **Trabajo exclusivo en `develop`:** Tras cada fase: commit semántico + push a `develop`. Nunca push directo a `main`.
7. **Plan antes de código:** Antes de implementar una fase se redacta y somete a aprobación `implementation_plan.md`.
8. **Seguridad de Base de Datos de Pruebas:** **PROHIBIDO ejecutar comandos concurrentes/paralelos de `pytest`**. La base de datos de test PostgreSQL (`test_booksocial`) entra en bloqueo transaccional (`OperationalError: database is being accessed by other users`) si se ejecutan múltiples instancias a la vez.

---

## 2. Pila Tecnológica y Arquitectura

- **Backend:** Python 3.12, Django 5.2, Django REST Framework, Django Channels (Daphne ASGI), Celery.
- **Bases de Datos y Caché:** PostgreSQL 16 con extensión `pgvector`, Redis 7 Alpine (caché L2, rate limiting, broker de Celery y layer de Channels).
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, Zustand (gestión de estado de autenticación y UI), React Query (@tanstack/react-query).
- **Contenedores y Producción:** Docker Compose, Nginx 1.27-alpine como API Gateway / Reverse Proxy, multi-stage Dockerfiles, redes aisladas (`frontend_net` y `backend_net internal: true`).

---

## 3. Estado de Ejecución de Fases y Funcionalidades (Consolidado)

| Fase | Título | Estado | Hito Clave / Entregable |
| :--- | :--- | :--- | :--- |
| **01** | Integridad del Dominio | COMPLETADA | Constraints en modelos, slugging, normalización ISBN y soft-deletes. |
| **02** | Privacidad Social y Bloqueos | COMPLETADA | Políticas de visibilidad de perfiles, bloqueos bidireccionales (retorno 404/403). |
| **03** | Auth y Seguridad de Sesiones | COMPLETADA | JWT con rotación, blacklist, control de sesiones concurrentes y confirmación de email. |
| **04** | Mensajería Realtime | COMPLETADA | WebSockets seguros con Daphne, Channels y Redis channel layer. |
| **05** | IA y Seguridad | COMPLETADA | Multi-proveedor (OpenAI, OpenRouter, Ollama), guardrails contra prompt injection y sanitización. |
| **06** | Búsqueda y Ranking | COMPLETADA | Búsqueda híbrida unificada: trigram (`pg_trgm`), vector embeddings y metadatos. |
| **07** | Recomendaciones | COMPLETADA | Motor v3 ponderado con embeddings semánticos, similitud coseno y feedback loop. |
| **08** | Estrategia de Caché | COMPLETADA | Invalidación en cascada, `safe_cache_get/set` con fallback graceful ante fallos de Redis. |
| **09** | Rendimiento y Presupuestos | COMPLETADA | Erradicación de N+1, índices compuestos (`Book`, `Review`, `UserBook`) y SLAs p95/p99. |
| **10** | Calidad de Frontend | COMPLETADA | ESLint, Prettier, TypeScript strict, Vitest, auto scroll-to-top en navegación. |
| **11** | Backend Testing Suite | COMPLETADA | Tests Unit, Integration, API, Security (IDOR, auth 401, injection) y Regression. |
| **12** | CI/CD Pipelines | COMPLETADA | GitHub Actions modulares (`ci-backend`, `ci-frontend`, `ci-docker`, `security`, `dependabot`). |
| **13** | Docker y Producción | COMPLETADA | Nginx reverse proxy, aislamiento de redes, sondas `/health/live` y `/health/ready`, graceful shutdown. |
| **14** | Observabilidad | COMPLETADA | Logs JSON estructurados sin secretos, métricas de backend, KPIs de producto y sistema de alertas. |
| **15** | Backups y Disaster Recovery | COMPLETADA | Frecuencia de backups PostgreSQL/Media, retención, cifrado AES-256, restore test y RPO/RTO. |
| **16** | Moderación y Seguridad Social | COMPLETADA | Reportes (user, review, comment, message, list), cola admin, acciones con AuditLog, 5 throttles resilientes, política de contenido. |
| **17** | Cuenta y Privacidad del Usuario | COMPLETADA | Cambio de email/password seguro, eliminación RGPD Art. 17 con anonimización atómica, exportación JSON RGPD Art. 20, tabs en UI y AuditLog. |
| **18** | Legal y Privacidad para Beta | COMPLETADA | 7 documentos normativos sembrados, API pública list/detail, IA sin entrenamiento, privacy-first, páginas frontend y footer. |
| **19** | Producto: Onboarding | COMPLETADA | Experiencia de bienvenida no obstructiva, géneros favoritos (`favorite_categories`), cold start boost en recomendaciones, modal de 3 pasos e importador. |
| **20** | Descubrimiento de Libros | COMPLETADA | Exploración facetada independiente de IA (`/api/v1/books/discover/`), tendencias públicas, Landing visual y modales emergentes de autenticación (`AuthModal`). |
| **21** | Listas Sociales | COMPLETADA | Listas públicas/privadas/seguidores, clonación atómica (`clone`), comentarios (`ReadingListComment`), apertura `views_count`, compartición y métricas. |
| **22** | Feed Social y Actividad | COMPLETADA | 9 eventos de lectura/reacciones/listas, ocultamiento (`HiddenActivity`), exclusión de silenciados/bloqueados y filtros temáticos. |
| **23** | Notificaciones | COMPLETADA | Eventos (follow, follow_accepted, likes, comentarios, respuestas, listas, mensajes, recomendaciones), `NotificationPreference` (in-app, email, push), `NotificationService` y centro UI. |
| **24** | **IA de producto** | COMPLETADA | Asistente literario interactivo, explicación profunda de obras, comparativas temáticas, unificación 1-5 estrellas y transparencia ética obligatoria. |
| **25** | **Embeddings y pgvector** | COMPLETADA | Canalización completa: normalización formal, hash SHA256, Celery embedding jobs, aislamiento de modelos y observabilidad. |
| **26** | **Analytics de producto** | COMPLETADA | 13 eventos canónicos, métricas de embudo/funnel, disociación RGPD (SET_NULL, hash IP SHA-256) y telemetría asíncrona. |
| **27** | **Beta cerrada y despliegue** | COMPLETADA | Sistema de invitaciones (`BetaInvitation`), feedback in-app (`BetaFeedback` con 7 categorías), modal accesible y checklist de 17 puntos. |
| **28** | **Beta abierta** | COMPLETADA | Métricas de retención D1/D7/D30, tickets de soporte (`SupportTicket`), control de tasa de error y costes conocidos. |
| **29** | **Preparación de producción** | COMPLETADA | Endurecimiento de seguridad (`SECURE_PROXY_SSL_HEADER`, cookies, CSP, HSTS), plantilla de producción `.env.production.example`, script preflight y guía integral `docs/deployment/production_readiness_guide.md`. |
| **30** | **Escalabilidad** | COMPLETADA | Escalabilidad en 4 etapas: enrutamiento de 5 colas Celery (`default`, `books`, `ai`, `recommendations`, `emails`), tareas asíncronas de email, `PrimaryReplicaRouter` para PostgreSQL, upstream `django_cluster` en Nginx y guía técnica `scalability_and_performance_tuning.md`. |
| **31** | **Monetización y Plataforma de Autores** | COMPLETADA | Tag de afiliación de Amazon configurable (`mybooksocial-21`), enlaces multiformato (papel, ebook, audiolibro) con disclosure legal transparente, plataforma de autores (`AuthorProfile`, `AuthorAnnouncement`, `/claim/`, `/dashboard/`), modelo base de suscripciones (`UserSubscription`) y neutralidad algorítmica garantizada. |
| **32** | **Multi-autor, Muro Social y Recomendaciones** | COMPLETADA | Soporte de múltiples autores por libro (`Book.authors`), visualización integral de reseñas en el perfil de usuario, muro interactivo (`UserPost`, likes, comentarios, feed `POST_CREATED`) y ponderación de afinidad multi-autor en el motor híbrido. |
| **33** | **Calidad avanzada** | COMPLETADA | Contratos OpenAPI 3.0 validados con `drf-spectacular`, flujo de integración E2E completo (registro a feed), suite de seguridad IDOR/XSS/JWT, erradicación de consultas N+1 con complejidad $O(1)$ en muro, reseñas y feed, y script de carga concurrente y SLAs (`load_test_benchmark.py`). |
| **34** | **Consolidación y Release Candidate (RC1)** | COMPLETADA | Versionado formal SemVer 2.0.0 (`1.0.0-rc1`) sincronizado en backend, frontend, CHANGELOG y scripts de release, suite de pruebas de release candidate (`test_phase34_release_candidate.py`, 6 tests pasando), sondas de salud `/health/live` y `/health/ready` operativas, 0 migraciones pendientes, OpenAPI 3.0 validado, y guía técnica `docs/deployment/release_candidate_guide.md`. |
| **35** | **Despliegue y Validación en Staging (Beta Cerrada)** | COMPLETADA | Scripts automatizados de smoke testing (`scripts/staging/smoke_test_staging.py` y `.sh`) y auditoría pre-despliegue (`preflight_staging.sh`), suite de pruebas de integración de ciclo de vida beta (`test_phase35_staging_validation.py`, 5 tests pasando), y guía operativa `docs/deployment/staging_deployment_guide.md`. |
| **36** | **Apertura de Cohorte Beta Cerrada y Monitorización** | COMPLETADA | Comando CLI de generación de cohortes (`generate_beta_cohort`), servicio y endpoint de telemetría de evaluadores (`BetaMetricsService` en `/api/v1/beta/admin/metrics/`), servicio de alertas inmediatas de incidencias (`BetaAlertsService` en `/api/v1/beta/admin/alerts/`), suite de pruebas de cohorte (`test_phase36_beta_cohort.py`, 5 tests pasando) y guía de operaciones `docs/deployment/closed_beta_operations_guide.md`. |
| **37** | **Apertura de Beta Pública y Campaña de Adopción** | COMPLETADA | Feature flags de registro (`PUBLIC_REGISTRATION_ENABLED`, `REQUIRE_BETA_INVITATION`), endpoint público de estado (`GET /api/v1/beta/registration-status/`), sistema viral de referidos entre lectores (`ReferralService`, `/my-code/`, `/stats/`), panel de retención de cohortes D1/D7/D30 en telemetría (`BetaMetricsService`), suite exhaustiva (`test_phase37_public_beta_and_retention.py`, 13 tests pasando) y guía operativa `docs/deployment/public_beta_and_adoption_guide.md`. |
| **38** | **Cierre de Beta, Auditoría Final y Release 1.0.0 General (GA)** | COMPLETADA | Versión oficial definitiva SemVer 2.0.0 `1.0.0` unificada en backend (`version.py`, `pyproject.toml`) y frontend (`package.json`), endpoint `/api/v1/version/`, suite de producción (`test_phase38_general_availability.py`, 8 tests pasando), 5/5 comprobaciones DoD superadas y guía de despliegue a producción `docs/deployment/general_availability_release_guide.md`. |

---

## 3.1. Estado de Ejecución de RoadmapV3 (Producción y Lanzamiento Estable)

| Sprint | Título | Estado | Hito Clave / Entregable |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | **Seguridad e Integridad (P0)** | COMPLETADA | Eliminado `POST` en `/api/v1/users/notifications/` (solo lectura `GET`), protección IDOR en `/notifications/<id>/`, blindaje de `ChatConsumer` (captura `JSONDecodeError`, límite 64 KB, descarte de acciones desconocidas y rate limiting de 10 msg/s), sanitización de trazas en `/health/ready`, y unificación de PostgreSQL 16 `pgvector` en `docker-compose.yml`. Suite de 15 tests pasando (`test_sprint1_security.py`). |
| **Sprint 2** | **Infraestructura (P0)** | COMPLETADA | Endurecimiento Nginx reverse proxy (upstream balanceado, `limit_req_zone` 30r/s y 5r/s auth, proxy `/admin/` y `/panel-control-mbc/`, headers COOP/CSP/HSTS), Redis 7 con persistencia AOF (`appendonly yes`, `maxmemory 256mb`, `allkeys-lru`), orquestación Docker Compose y Prod con límites CPU/memoria y redes aisladas, scripts de backup/restore PostgreSQL 16 y ciclo completo de restauración verificado al 100% (65 tablas, smoke test con 23 usuarios). Suite de 6 tests pasando (`test_sprint2_infrastructure.py`). |
| **Sprint 3** | **Autores (P1) & FAQs** | COMPLETADA | Modelo de autor enriquecido (`nationality`, `birth_date`, `death_date`, `website`, `wikipedia_url`, `is_verified`, `claimed_by`), estadísticas en tiempo real, modelo `AuthorClaim` con unicidad y ciclo de vida, endpoints de solicitud y resolución administrativa con notificación. Subsistema integral de FAQs (modelo `FAQ`, endpoints público y admin, acordeón reactivo interactivo en `/faqs`, gestión administrativa en `AdminFaqsTab`). Suite de 9 tests pasando (`test_sprint3_authors_and_faqs.py`). |
| **Sprint 4** | **Catálogo y UX (P1)** | COMPLETADA | Unificación canónica de libros por autor y título normalizado (`normalize_title`), soporte de múltiples ISBNs físicos y digitales con `Book.additional_isbns`, búsqueda unificada por cualquier edición con `Book.find_by_isbn`, servicio de deduplicación y fusión atómica `merge_books` con migración de UserBook, Review y Listas, comando CLI `deduplicate_catalog` (21 obras y 25 duplicados consolidados en DB con 0 duplicados restantes), endpoint global `/api/v1/search/` (libros, autores, lectores con privacidad) y página responsive en frontend `/search` con tabs y badge de ediciones. Suite de 9 tests pasando (`test_sprint4_catalog_deduplication.py`). |
| **Sprint 5** | **Calidad (P2)** | PENDIENTE | Tests exhaustivos, performance, accesibilidad WCAG y CI/CD. |
| **Sprint 6** | **Preproducción y Lanzamiento** | PENDIENTE | Deploy staging, smoke tests de producción y soft launch. |

---

## 4. Trampas Conocidas y Lecciones Aprendidas (Gotchas)

### 4.1. Token de Autenticación en Frontend
- **Problema histórico:** Varios componentes de gamificación buscaban el token con `localStorage.getItem('access_token')`, devolviendo `null` porque Zustand almacena el estado bajo la clave `auth-storage`.
- **Solución Canónica:** Importar siempre el hook central:
  ```typescript
  import { useAuthStore } from '@/store/auth';
  const token = useAuthStore((state) => state.token);
  ```

### 4.2. Bloqueos Sociales y Visibilidad de Perfil
- Cuando el usuario Alice bloquea a Bob (o existe bloqueo mutuo), la política estricta de seguridad ([backend/users/views.py](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/users/views.py)) devuelve **`404 NOT FOUND`** ("Usuario no encontrado") para no filtrar la existencia de la cuenta al acosador/bloqueado. En pruebas de acceso, esperar `status.HTTP_404_NOT_FOUND` o `status.HTTP_403_FORBIDDEN`.

### 4.3. Importación CSV de Goodreads
- El servicio [CSVImportService](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/books/services/csv_import_service.py) devuelve un payload estructurado compatible tanto con `preview_items` como con `raw_items_payload`.
- El componente `ImportBooksModal.tsx` tolera ambas claves:
  ```typescript
  const items = previewData?.raw_items_payload || previewData?.preview_items || [];
  ```

### 4.4. Aislamiento de Embeddings en Entorno de Pruebas
- Si se ejecutan pruebas de búsqueda que usan `mode='hybrid'`, asegurarse de mockear `OllamaProvider.get_embedding` y `get_embedding_for_text`:
  ```python
  with patch('ai.clients.ollama_client.OllamaProvider.get_embedding', return_value=None), \
       patch('ai.embeddings.get_embedding_for_text', return_value=None):
      # Petición de búsqueda sin demoras de red contra Ollama inexistente en tests
  ```

### 4.5. `Book.get_author_names()` y Prefetch Cache en Relaciones ManyToMany
- **Problema:** En Django ORM, llamar a `self.authors.values_list('name', flat=True)` ignora el cache de `prefetch_related` y lanza una consulta `SELECT` directa a PostgreSQL por cada entidad renderizada, provocando N+1 en listados masivos.
- **Solución Canónica:** Inspeccionar `_prefetched_objects_cache` e iterar sobre `.all()` en memoria si ya fue prefetcheado:
  ```python
  if hasattr(self, '_prefetched_objects_cache') and 'authors' in self._prefetched_objects_cache:
      names = [a.name for a in self.authors.all()]
  else:
      names = list(self.authors.values_list('name', flat=True))
  ```

### 4.6. Caching en Ciclo de Vida del Request para Serializers Anidados
- **Problema:** Al renderizar listados que anidan entidades complejas (ej. `ReviewSerializer` serializando `BookSerializer` con `get_rating_distribution` y `get_reviews_count`), se disparaban consultas repetidas para el mismo libro.
- **Solución Canónica:** Cachear el cálculo en el objeto `request` (`request._rating_dist_{obj.id}`) y reutilizarlo durante la serialización del payload actual.

### 4.7. Throttling de Autenticación en Pruebas
- **Problema:** Ejecutar repetidamente `POST /api/v1/auth/token/` en los métodos de `setup` de suites con múltiples tests activa el `LoginRateThrottle` (retornando `429 Too Many Requests`).
- **Solución Canónica:** Usar `RefreshToken.for_user(user)` directamente en los setups de tests que requieran tokens sin pretender probar la vista de login.

### 4.3. Importación CSV de Goodreads
- El servicio [CSVImportService](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/books/services/csv_import_service.py) devuelve un payload estructurado compatible tanto con `preview_items` como con `raw_items_payload`.
- El componente `ImportBooksModal.tsx` tolera ambas claves:
  ```typescript
  const items = previewData?.raw_items_payload || previewData?.preview_items || [];
  ```

### 4.4. Aislamiento de Embeddings en Entorno de Pruebas
- Si se ejecutan pruebas de búsqueda que usan `mode='hybrid'`, asegurarse de mockear `OllamaProvider.get_embedding` y `get_embedding_for_text`:
  ```python
  with patch('ai.clients.ollama_client.OllamaProvider.get_embedding', return_value=None), \
       patch('ai.embeddings.get_embedding_for_text', return_value=None):
      # Petición de búsqueda sin demoras de red contra Ollama inexistente en tests
  ```

### 4.5. Sondas de Salud Desacopladas
- `/health/live`: Sonda de Liveness para orquestadores. **Nunca debe conectar a la base de datos ni a Redis**; comprueba solo el proceso Django/Daphne.
- `/health/ready`: Sonda de Readiness. Comprueba conectividad con PostgreSQL y Redis, retornando `503` ante cualquier fallo.

### 4.6. Moderación y Prevención de Abuso (Fase 16)
- **Throttles Resilientes:** Los limitadores de abuso social (`reports`, `follows`, `comments`, `likes`, `messages`) heredan de `ResilientUserRateThrottle`. Si Redis sufre un microcorte, no bloquean al usuario legítimo con error 500, sino que degradan limpiamente.
- **Normalización de Estados:** `ReportStatus.normalize(val)` traduce automáticamente entre la nomenclatura de roadmap (`open`, `investigating`, `resolved`, `dismissed`) y los choices de BD (`OPEN`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`).
### 4.7. Onboarding y Arranque en Frío (Cold Start) de Recomendaciones (Fase 19)
- **Cold Start:** Un lector recién registrado no tiene lecturas en `UserBook`. El servicio `recommendation_service._calculate_user_affinity` incluye directamente las categorías de `user.favorite_categories` con peso 1.0, permitiendo sugerencias inmediatas y relevantes en el paso final del onboarding.
- **Flujo No Obstructivo:** Bajo ninguna circunstancia se debe forzar una pantalla modal bloqueante sin opción de salida. El endpoint `POST /api/v1/users/onboarding/skip/` y el botón "Explorar directamente" permiten omitir el asistente instantáneamente fijando `onboarding_completed = True`.

### 4.8. Relación Inversa UserBook en Book y Descubrimiento (Fase 20)
- **Nombre de Relación Inversa:** El modelo `Book` se relaciona con `UserBook` a través de `related_name='user_entries'` (no `user_books`). Para realizar agregaciones por volumen de lectores, usar `annotate(readers_count=Count('user_entries'))`.
- **Tendencias Públicas:** `TrendingBooksView` debe mantener `permission_classes = (AllowAny,)` para nutrir tanto a la Landing Page pública como a lectores autenticados sin exigir tokens JWT.

### 4.9. Listas Sociales, Clonación y Métricas de Apertura (Fase 21)
- **Clonación Atómica (`clone`):** Duplica la lista asignándole como creador al usuario solicitante (`request.user`), preservando libros, orden y notas en una transacción atómica bajo visibilidad privada por defecto.
### 4.10. Feed Social, Ocultamiento y Moderación Personal (Fase 22)
- **Filtrado Multidimensional:** `FeedView.get_queryset()` integra `PrivacyService.filter_visible_activities(user, qs)` que aplica simultáneamente bloqueos bidireccionales (`blocked_users`, `blocked_by`), silenciados (`muted_users`) y restricciones de privacidad (`activity_privacy_level`).
- **Ocultamiento de Publicaciones (`HiddenActivity`):** Permite a cada lector descartar publicaciones individuales de su feed sin afectar al resto de usuarios, garantizando persistencia y reversibilidad (`/feed/<id>/hide/` y `/feed/<id>/unhide/`).

### 4.11. Sistema Centralizado de Notificaciones y Privacidad (Fase 23)
- **Despacho Exclusivo:** Toda emisión de alertas debe realizarse mediante `NotificationService.send_notification(...)`. Dicho servicio verifica la no auto-notificación (`actor != recipient`), bloqueos bidireccionales (`PrivacyService.are_mutually_blocked`), silencios activos y preferencias granulares de canal (`in_app` y `email`).
### 4.12. Unificación del Sistema de Calificaciones (Escala 1 a 5 Estrellas)
- **Alineación Total:** Tanto `UserBook.rating` (nota personal de lectura) como `Review.rating` (opinión pública) se rigen exclusivamente por el rango 1 a 5 estrellas (`validators=[MinValueValidator(1), MaxValueValidator(5)]`).
- **Normalización de Estrellas en UI:** El componente `StarRating.tsx` asume de forma canónica `maxRating = 5` y no debe dividir el valor por 2 si la escala es 5. Los selectores de `BookDetail.tsx`, `AddBook.tsx` y `Library.tsx` deben iterar siempre sobre `[5, 4, 3, 2, 1]` para evitar que notas sobre 10 distorsionen las estadísticas del usuario (`stats_service.py`).

### 4.13. Transparencia y Etiquetado Obligatorio de IA (Fase 24)
- **Principio de Confianza:** Cualquier endpoint que entregue análisis, resúmenes o comparativas literarias (`AIExplainBookView`, `AICompareBooksView`, `AIBookSummaryView`) debe devolver inmutablemente `is_ai_generated: True`, `badge: "✨ Generado por IA"` y un disclaimer orientativo/divulgativo visible en la interfaz para el lector.

### 4.14. Aislamiento y Versionado de Embeddings (Fase 25)
- **Incompatibilidad de Modelos:** El servicio `search_books_by_embedding` filtra obligatoriamente por `embedding_model` y dimensionalidad (`dimension == len(query_vector)`). Queda terminantemente prohibido calcular similitudes coseno entre vectores generados por modelos incompatibles (ej. nomic-embed-text vs text-embedding-3-small).
### 4.15. Telemetría de Producto y Privacidad RGPD (Fase 26)
- **Desvinculación Obligatoria (RGPD Art. 17):** `ProductAnalyticsEvent.user` utiliza `on_delete=models.SET_NULL`. Al anonimizar o eliminar la cuenta de un usuario, sus eventos de telemetría histórica persisten con `user_id=null`, asegurando que las métricas agregadas del embudo de conversión sigan siendo coherentes sin retener ningún dato personal identificable.
- **Anonimización Criptográfica de IPs:** Toda dirección IP recolectada se procesa y trunca mediante SHA-256 (`hash_ip_address`) a 16 caracteres hexadecimales antes de guardarse, prohibiendo el almacenamiento de direcciones IP en texto plano.
- **Metadatos Sin PII:** El payload JSON de `metadata` debe contener exclusivamente identificadores relacionales técnicos (`book_id`, `category`, `source`), estando terminantemente prohibido incluir emails o nombres.

### 4.16. Circuito de Feedback de Beta e Invitaciones (Fase 27)
- **Vinculación Desacoplada de Feedback:** `BetaFeedback.user` vincula opcionalmente al usuario mediante `on_delete=models.SET_NULL`. Si el usuario elimina su cuenta, el feedback técnico persiste para el equipo de desarrollo sin retener datos personales.
- **Categorías Canónicas Inmutables:** Las 7 categorías de feedback se rigen estrictamente por el roadmap: `bug`, `confusing_ux`, `missing_feature`, `performance`, `privacy_concern`, `recommendation_quality`, `general_feedback`.
- **Agotamiento Atómico de Invitaciones:** El método `BetaInvitation.use()` verifica vigencia temporal (`expires_at`), estado activo e incrementa `uses_count`, desactivando la invitación automáticamente si `uses_count >= max_uses`.

### 4.17. Retención de Cohortes y Sistema de Soporte (Fase 28)
- **Cálculo de Retención D1/D7/D30:** `AnalyticsService.get_retention_metrics` utiliza ventanas de tiempo relativas al timestamp del evento `signup` (`D1: 1 a 2 días`, `D7: 6 a 8 días`, `D30: 27 a 33 días`), evaluando actividad subsiguiente excluida la propia creación de cuenta para evitar falsos positivos de retención.
- **Soporte Desacoplado y RGPD:** `SupportTicket.user` utiliza `on_delete=models.SET_NULL`. Al anonimizar o eliminar la cuenta, las respuestas administrativas y el historial técnico persisten para resolución operativa sin conservar datos personales.

### 4.18. Terminación SSL en Reverse Proxy y Hardening (Fase 29)
- **`SECURE_PROXY_SSL_HEADER`:** Con Nginx realizando la terminación SSL y reenviando las peticiones a Daphne por HTTP (puerto 8000), Django requiere `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` y que Nginx envíe `proxy_set_header X-Forwarded-Proto $scheme;`. Sin esto, `request.is_secure()` retorna `False`, provocando bucles de redirección 301 infinitos con `SECURE_SSL_REDIRECT = True` o problemas de rechazo de cookies seguras.
- **Manejo de `DisallowedHost`:** Django captura `DisallowedHost` internamente en la capa de middleware/handlers retornando un `HttpResponseBadRequest` (HTTP 400). En pruebas automáticas con `APIClient` o `Client`, se debe asertar `response.status_code == 400` o verificar `request.get_host()` usando `RequestFactory` si se evalúa la excepción directa.
- **Cabeceras HSTS y CSP en Nginx:** La directiva `Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;` y `Content-Security-Policy` protegen a los clientes de ataques Man-in-the-Middle y XSS permitiendo de forma explícita proveedores confiables de autenticación (Google OAuth) y fuentes tipográficas.

### 4.19. Enrutamiento de Colas Celery y Enrutador de Bases de Datos (Fase 30)
- **Aislamiento de Colas:** Al separar en 5 colas especializadas (`default`, `books`, `ai`, `recommendations`, `emails`), el worker polivalente de desarrollo/etapa 1 debe escuchar con `-Q default,books,ai,recommendations,emails`. En escalado de producción (Etapa 3), se despliegan workers independientes dedicados por cola, evitando que la inferencia de IA o la latencia SMTP bloqueen el enriquecimiento de libros.
- **`PrimaryReplicaRouter`:** Cuando `DATABASES` no incluye `replica` (entorno local o etapa 1), `db_for_read` devuelve elegantemente `default` sin generar errores de conexión. Las migraciones siempre se ejecutan en `default`.

### 4.20. Afiliación Transparente y Plataforma de Autores (Fase 31)
- **Tag de Afiliado Configurable:** El tag oficial de Amazon está establecido en `mybooksocial-21` mediante la variable de entorno `AMAZON_AFFILIATE_TAG` (backend) y `VITE_AMAZON_AFFILIATE_TAG` (frontend), permitiendo su modificación sin desplegar nuevo código.
- **Transparencia y Disclosure Obligatorio:** Todos los enlaces comerciales a libros físicos, ebooks (Kindle) y audiolibros (Audible) incluyen el disclosure legal explícito ("Enlace de afiliado: MyBookConnect puede recibir una pequeña comisión sin coste adicional para ti").
- **Neutralidad Algorítmica Inviolable:** Queda estrictamente prohibido que las compras, clics o enlaces de afiliación alteren el ranking o cálculo de afinidad de `recommendation_service.py`. Las recomendaciones son 100% orgánicas y guiadas por los gustos y lecturas de la comunidad.
- **Plataforma de Autores Desacoplada:** El modelo `AuthorProfile` vincula cuentas de usuario (`User`) con fichas del catálogo (`Author`). Los autores verificados disponen de panel de analítica agregada (`/dashboard/`) y publicación de comunicados oficiales (`AuthorAnnouncement`), accesibles en `/api/v1/authors/...`.

---

### 4.21. Soporte Multi-autor, Reseñas en Perfil y Muro Social (Fase 32)
- **Coexistencia Many-to-Many y ForeignKey en `Book`:** `Book.authors` (relación `all_books`) coexiste con `Book.author` (autor principal) para mantener compatibilidad total hacia atrás. En el `save()`, el autor principal se añade siempre a `authors`.
- **Filtro de Reseñas por Usuario:** Tanto `/api/v1/reviews/?user=<id>` como `/api/v1/users/<id>/reviews/` permiten consultar las opiniones del lector, aplicando filtros de privacidad y bloqueos mutuos mediante `filter_visible_reviews`.
- **Muro Social y Feed (`ActivityType.POST_CREATED`):** Las publicaciones en el muro (`UserPost`) se propagan al feed de actividades (`Activity`) de los seguidores para máxima interacción social comunitaria.

---

### 4.22. Compatibilidad de Backups y Restore en PostgreSQL 16 (Sprint 2 - RoadmapV3)
- **`SET transaction_timeout = 0;` en `pg_dump` moderno:** Nuevas versiones de utilitarios cliente de PostgreSQL generan volcados SQL con `SET transaction_timeout = 0;`. Al restaurar en PostgreSQL 16 bajo modo transaccional estricto (`--single-transaction`), el motor aborta la transacción entera porque `transaction_timeout` se introdujo en PostgreSQL 17.
- **Solución Canónica:** En los scripts `restore_db.sh` y `test_restore_cycle.sh`, se filtra el comando incompatibe antes de ejecutar la restauración:
  ```bash
  gunzip -c "$BACKUP_FILE" | sed '/transaction_timeout/d' | psql ... --single-transaction
  ```
- **Conexión Administrativa a la BD Fuente:** Al crear o destruir bases de datos temporales para pruebas de restauración, conectarse mediante `-d "${SOURCE_DB}"` o la base de datos de mantenimiento configurada en vez de asumir `-d postgres`, respetando el usuario no-root `booksocial`.

### 4.23. Unificación Canónica de Ediciones y Múltiples ISBNs (Sprint 4 - RoadmapV3)
- **El Problema del Libro Múltiple (Físico vs Digital):** Obras literarias idénticas ("Dune", "La catedral del mar") poseen distintos ISBNs según el formato (tapa dura, rústica, ebook Kindle, audiolibro). Si el sistema crea un `Book` por cada ISBN, se fragmentan las valoraciones, reseñas y estanterías de los lectores.
- **Solución Canónica:**
  - El modelo `Book` almacena su ISBN principal en `isbn` y acumula todas las ediciones adicionales normalizadas en `additional_isbns = models.JSONField(default=list)`.
  - `Book.find_by_isbn(query)` busca simultáneamente en ambos campos.
  - Al crear o importar libros, `normalize_title` y la comparación contra el autor unifican automáticamente la obra en vez de duplicarla.
  - El comando `python manage.py deduplicate_catalog` reubica de forma transaccional `UserBook`, `Review`, `ReadingListItem`, `UserPost` y `Activity` sin violaciones de unicidad, borrando los duplicados redundantes.

---

### 4.24. Erradicación de N+1 Queries, Accesibilidad WCAG y Calidad (Sprint 5 - RoadmapV3)
- **Erradicación de N+1 en Búsqueda Global y Catálogo:**
  - Al serializar listas de libros (`BookSerializer`), acceder a `rating_distribution` y `reviews_count` generaba 2 consultas SQL adicionales por cada libro (`2*N` queries).
  - **Solución Canónica:** `GlobalSearchView` precomputa en una única consulta batch (`Review.objects.filter(book_id__in=b_ids).values('book_id', 'rating').annotate(count=Count('id'))`) las distribuciones y conteos, asignándolos a `b._precomputed_rating_distribution` y `b.annotated_reviews_count`. El serializer comprueba estas propiedades precomputadas y evita consultas secundarias.
  - Para autores, se incluyó `.select_related('claimed_by')` y `.prefetch_related('books', 'all_books')`, reduciendo las consultas a un total constante (3 consultas) independientemente del volumen de resultados.
- **Accesibilidad WCAG 2.1 AA:**
  - `SearchPage` y `FaqsPage` implementan atributos semánticos `role="search"`, `role="tablist"`, `role="tab"`, `aria-selected`, `aria-expanded`, `aria-controls`, `aria-label`, y bordes `focus-visible` de alto contraste en Tailwind.
  - La suite de frontend en Vitest verifica rigurosamente las propiedades ARIA y la interacción con teclado.
- **Cero Errores TypeScript (`tsc --noEmit`):**
  - Con `noUnusedLocals: true`, cualquier importación residual en componentes de React rompe la compilación; se garantiza 0 errores estrictos en frontend.

### 4.25. Preproducción, Deploy Checks y Smoke Testing E2E (Sprint 6 - RoadmapV3)
- **Django Deploy Checks Sanitizados:**
  - `python manage.py check`: 0 issues de configuración o referencias en modelos.
  - `python manage.py makemigrations --check`: Garantiza que todos los modelos están al 100% migrados y no existen desviaciones en schemas.
  - `python manage.py check --deploy`: Valida HSTS, secure cookies, SSL redirects y security headers sin errores bloqueantes.
- **Smoke Tests E2E de Preproducción (`tests/test_sprint6_preproduction_readiness.py`):**
  - Flujo 1: Registro de usuario (`password` y `password2`), login JWT, obtención de access/refresh tokens y logout con blacklisting de tokens.
  - Flujo 2: Búsqueda unificada y deduplicada físico/digital, detalle canónico de libro, adición a biblioteca personal, avance de lectura y reseña con sanitización anti-XSS (`bleach`).
  - Flujo 3: Interacción social, seguimientos mutuos y consulta de feed de actividades.
  - Flujo 4: Reclamación de autor (`POST /api/v1/books/authors/<id>/claim/` con `proof_description`, `contact_email`, `supporting_link`), moderación/resolución por administrador (`action: approve`, `moderation_notes`), verificación oficial (`is_verified=True`) y asignación de autor reclamado.
  - Flujo 5: Centro de ayuda y soporte (FAQs públicas categorizadas y ordenadas).
  - Flujo 6: Probes de salud y producción (`/api/v1/health/` liveness, `/api/v1/health/ready/` readiness sin fuga de credenciales).
- **Regresión Integral 100%:**
  - 50 tests pasando de forma secuencial en pytest cubriendo los Sprints 1 a 6.
  - 42 tests en Vitest pasando al 100% en el frontend con build de producción Vite exitoso.

### 4.26. Administración, Moderación y Sistema Universal de Reportes (RoadmapV3 - Secciones 24 y 25)
- **Sistema Universal de Reportes (`users.Report`):**
  - Admite denuncias formales sobre `User`, `Review`, `ReviewComment`, `Message`, `ReadingList`, `Book`, `Author` y `UserPost`.
  - Mapeo canónico `ALLOWED_TARGET_MODELS` y vistas previas enriquecidas en `ReportListSerializer.get_target_preview`.
  - Prevención estricta de auto-denuncias (un usuario no puede reportar sus propios posts o perfiles reclamados) y prevención de reportes duplicados pendientes.
  - Medidas disciplinarias auditadas: `HIDE_CONTENT`, `RESTORE_CONTENT`, `BAN_USER`, `MUTE_USER_24H`, `MUTE_USER_7D` y `DISMISS`. En `HIDE_CONTENT` sobre `UserPost`, el borrado se efectúa tras asegurar la persistencia del expediente para evitar inconsistencias de GenericForeignKey.
- **Endpoints Administrativos de Catálogo y Usuarios:**
  - `POST /api/v1/admin/books/merge/`: Fusión atómica de libros duplicados (`merge_books`), unificando ISBNs en `additional_isbns`, reasignando estanterías `UserBook`, reseñas y listas sin pérdida de datos.
  - `POST /api/v1/admin/authors/merge/`: Fusión atómica de autores homónimos, unificando aliases, reasignando obras literarias y preservando estados de verificación oficial.
  - `GET /api/v1/admin/users/<pk>/activity/`: Auditoría cronológica de actividades (`Activity`), publicaciones en muro (`UserPost`) y reseñas.
  - `GET /api/v1/admin/users/<pk>/reports/`: Consulta unificada de denuncias emitidas y denuncias recibidas por un usuario.
### 4.27. Legalidad, RGPD, Portabilidad de Datos y Derecho al Olvido (Sprint 8 - RoadmapV3 Sección 26)
- **Documentos Normativos y Legal API:**
  - Modelo `LegalDocument` gestionado con slug canónico (`terms`, `privacy`, `cookies`, `legal_notice`, `content_policy`, `deletion_policy`, `contact`).
  - Endpoints públicos versionados: `GET /api/v1/books/legal/` (listado) y `GET /api/v1/books/legal/<slug>/` (detalle normativo renderizable).
  - Endpoint administrativo seguro: `PATCH/PUT /api/v1/admin/legal/<slug>/` para actualización del corpus legal con incremento automático de versión y fecha de actualización.
- **Portabilidad de Datos RGPD (`GET /api/v1/users/account/export/`):**
  - Exportación integral de datos del usuario autenticado en formato JSON normalizado.
  - Secciones incluidas: `_metadata` (timestamps, id, legal notice), `profile` (username, email, biografía, avatar, fecha de alta), `library` (estanterías, libros, rating personal, fechas de lectura, notas), `reviews` (reseñas y ratings publicados), `comments` (comentarios en reseñas), `reading_lists` (listas de lectura creadas y libros asociados) y `social` (seguidores y seguidos).
- **Derecho al Olvido / Cancelación de Cuenta (`POST /api/v1/users/account/delete/`):**
  - Requiere re-autenticación obligatoria con contraseña actual para mitigar secuestro de sesión.
  - Proceso de anonimización y cascade seguro: revocación de tokens JWT activos, eliminación/anonimización de datos de perfil, desvinculación de identificadores personales en logs y auditoría, respetando la consistencia referencial en reseñas comunitarias y registros contables/legales.
### 4.28. Clubs de Lectura, Membresías y Debates por Capítulos (Sprint 9 - RoadmapV3 Sección 30.1)
- **Modelos de Dominio (`books.club_models`):**
  - `ReadingClub`: Gestión de comunidades literarias públicas y privadas con slug autogenerado, reglas de convivencia, creador y libro actual en curso (`current_book`).
  - `ReadingClubMember`: Membresías con control de roles (`ADMIN`, `MODERATOR`, `MEMBER`) y estados (`ACTIVE`, `PENDING`, `BANNED`), con unión directa en clubs públicos y flujo de solicitud/aprobación en privados.
  - `ReadingClubBook`: Plan de lecturas conjuntas con estados (`CURRENT`, `UPCOMING`, `FINISHED`), fechas límite e hitos por capítulos/páginas.
  - `ReadingClubDiscussion` & `ReadingClubDiscussionComment`: Hilos de debate estructurados por libro o tema general, soporte de avisos de spoilers (`has_spoilers` con blur/revelación bajo demanda), hilos fijados (`is_pinned`) y comentarios anidados con conteo optimizado (`_annotated_comments_count`).
- **Endpoints API REST (`/api/v1/clubs/`):**
  - Listado con filtros de búsqueda y pertenencia (`?my_clubs=true`, `?q=...`), creación con auto-asignación de administrador, unión (`/join/`), salida (`/leave/` con bloqueo si es el único administrador), gestión de miembros y aprobación (`/members/<id>/`), plan de lecturas (`/books/`) y debates/comentarios (`/discussions/`, `/discussions/<id>/comments/`).
  - Sanitización anti-XSS mediante `mybookconnect.html_sanitizer` (`sanitize_plain_text`, `sanitize_html`).
- **Frontend y UX (`frontend/src/features/clubs/`):**
  - `ClubsPage.tsx`: Vista general de exploración, pestañas accesibles WAI-ARIA, buscador dinámico y modal interactivo para creación de clubs.
  - `ClubDetailPage.tsx`: Panel completo del club con lectura actual, hitos, foros con advertencias de spoiler, comentarios y lista de miembros.
  - Navegación integrada en `AppRouter`, `Header.tsx` y `PublicHeader.tsx`.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint9_reading_clubs.py`: 6 tests pasando al 100%.
  - Regresión secuencial backend: 65 tests pasando al 100% de forma consecutiva (Sprints 1 al 9 con 0 fallos).
  - Frontend: `tsc --noEmit` con 0 errores, 46 tests en Vitest pasando al 100% en 14 suites, y build de producción Vite generado limpiamente.

### 4.30. Sprint 10 — Listas Colaborativas y Atribución de Autoría
- **Modelos de Dominio y Base de Datos:**
  - `ReadingList.is_collaborative`: Flag booleano indexado que habilita listas compartidas.
  - `ReadingListItem.added_by`: Clave foránea nullable a `User` para registrar quién aportó cada libro a la lista.
  - `ReadingListCollaborator`: Modelo relacional con `reading_list`, `user`, `role` (`EDITOR`, `VIEWER`), `status` (`PENDING`, `ACCEPTED`, `REJECTED`), `can_add_books`, `can_remove_books` e `invited_by`.
  - Migración aplicada en PostgreSQL: `0034_readinglistcollaborator_readinglist_is_collaborative_and_more.py`.
- **API REST y Permisos:**
  - Modificación de `ReadingListViewSet`:
    - Filtrado `?collaborative=true` para devolver listas colaborativas propias o donde el usuario colabora (estado `ACCEPTED` o `PENDING`).
    - Actualización de `PrivacyService.filter_visible_reading_lists` para permitir acceso de lectura a colaboradores aceptados en listas privadas.
    - Endpoints `@action` en `collaborators` (`GET`, `POST`) y `collaborators/(?P<user_id>\d+)` (`PATCH`, `DELETE`).
    - Lógica de permisos en `add_book` y `remove_book`: colaboradores con `can_add_books=True` pueden añadir libros (registrando `added_by`); pueden eliminar sus propios libros aportados o cualquier libro si poseen `can_remove_books=True`.
- **Frontend React y Experiencia de Usuario:**
  - Nueva pestaña "🤝 Colaborativas" en la navegación de `ReadingLists.tsx`.
  - Badges informativos de lista colaborativa en las tarjetas del grid y en la cabecera del detalle.
  - Panel interactivo de colaboradores en la vista de detalle con avatares, roles y estados.
  - Banner interactivo para aceptar o rechazar invitaciones pendientes de colaboración.
  - Modal para invitar nuevos colaboradores por nombre de usuario con asignación granular de permisos.
  - Atribución de autoría ("Aportado por @username") en cada tarjeta de libro dentro de la lista.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint10_collaborative_lists.py`: 7/7 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 10): 72/72 tests pasando al 100%.
  - Frontend: `npm run typecheck` limpio (0 errores), 14 suites / 46 tests Vitest pasando, y `npm run build` generado sin incidencias.

### 4.31. Eventos y Encuentros Literarios de Autores (Sprint 11 — Futuro)
- **Modelos de Dominio:**
  - `AuthorEvent`: representa presentaciones (`BOOK_LAUNCH`), firmas de libros (`SIGNING`), coloquios (`QA_SESSION`), lecturas públicas (`READING`), talleres (`WORKSHOP`) y otros eventos literarios. Soporta formatos `ONLINE`, `IN_PERSON` y `HYBRID`, libro presentado opcional, ubicación o URL de streaming, zona horaria explícita (`event_timezone`) y aforo máximo (`max_attendees`).
  - `AuthorEventAttendee`: gestiona las inscripciones con estados `REGISTERED`, `WAITLIST` (lista de espera cuando el aforo está completo) y `CANCELLED`. Permite adjuntar preguntas o notas para el autor (`notes`).
- **Lógica de Negocio y Endpoints REST:**
  - `AuthorEventViewSet` en `/api/v1/books/author-events/`:
    - Filtrado flexible por `author`, `book`, `event_type`, `format`, `upcoming=true` o `past=true`, y búsqueda textual (`search`).
    - Acción `@action register`: inscribe al usuario en el evento; si el aforo está completo, asigna automáticamente estado `WAITLIST`.
    - Acción `@action cancel_registration`: cancela la inscripción y, si la plaza liberada estaba confirmada (`REGISTERED`), promociona de forma automática y secuencial al primer asistente de la lista de espera (`WAITLIST`).
    - Acción `@action attendees`: permite a los autores y administradores consultar la lista completa de asistentes con sus preguntas o dedicatorias solicitadas.
- **Frontend React y Experiencia de Usuario:**
  - Componente accesible `AuthorEventsSection.tsx` integrado en la página pública del autor (`Author.tsx`).
  - Filtros entre "Próximos eventos" y "Histórico de eventos".
  - Visualización enriquecida con badges de formato, fecha formateada en locale español, indicador de capacidad y aforo restante.
  - Modales accesibles para reservar plaza con envío de preguntas al autor, modal para crear eventos y modal para gestionar inscripciones.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint11_author_events.py`: 7/7 tests pasando al 100%.
  - Suite `frontend/src/features/books/__tests__/AuthorEventsSection.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 11): 79/79 tests pasando al 100%.
  - Frontend: `npm run typecheck` limpio (0 errores), 15 suites / 50 tests Vitest pasando al 100%, y `npm run build` generado sin incidencias.

### 4.32. Publicaciones Avanzadas de Autores y Adelantos Literarios (Sprint 12 — Futuro)
- **Modelos de Dominio y Base de Datos:**
  - `AuthorAnnouncement`: enriquecido con tipos literarios (`publication_type`: `ANNOUNCEMENT`, `CHAPTER_PREVIEW`, `AUTHOR_DIARY`, `DELETED_SCENE`, `Q_AND_A`), relación opcional directa a `Author` (`catalog_author`), extracto automático (`excerpt`), cálculo automático de tiempo de lectura (`estimated_reading_time` basado en 200 ppm), advertencias y flags de spoiler (`has_spoilers`, `spoiler_warning`) y soporte para borradores (`is_draft`).
  - Migración aplicada en PostgreSQL: `0036_alter_authorannouncement_options_and_more.py`.
- **API REST y Lógica de Negocio:**
  - ViewSet unificado `AuthorPublicationViewSet` en `/api/v1/books/author-publications/` con soporte para filtrado por autor, catálogo, tipo de publicación, libro asociado y parámetros para ver borradores (`include_drafts`).
  - Acción `@action toggle_pin` para fijar o desfijar comunicados en el perfil de autor.
  - Mantenimiento y compatibilidad retroactiva total de `AuthorAnnouncementListView` y `AuthorAnnouncementCreateView` en `/api/v1/books/authors/<author_id>/announcements/`.
- **Frontend React y Experiencia de Usuario:**
  - Componente modular `AuthorPublicationsSection.tsx` integrado en `Author.tsx`.
  - Filtros interactivos por tipo de publicación (Todos, Comunicados, Adelantos, Diarios, Escenas eliminadas, Preguntas y respuestas).
  - Lector interactivo de publicaciones con extracto inicial, botón "Leer más / Colapsar", advertencia visual y botón de revelación/ocultación de spoilers.
  - Soporte de borradores con toggle para autores propietarios ("Ver borradores") e insignias de borrador y fijado.
  - Modales accesibles para crear y editar publicaciones con control granular de tipo, libro relacionado, spoiler warning y borrador.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint12_author_publications.py`: 7/7 tests pasando al 100%.
  - Suite `frontend/src/features/books/__tests__/AuthorPublicationsSection.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 12): 86/86 tests pasando al 100% consecutivamente en 79s.
  - Frontend: `npm run typecheck` limpio (0 errores), 16 suites / 54 tests Vitest pasando al 100%, y `npm run build` generado sin incidencias en 11s.

### 4.33. Newsletters y Boletines de Autores (Sprint 13 — Futuro)
- **Modelos de Dominio y Base de Datos:**
  - `AuthorNewsletter`: configuración de boletín por autor (`author`, `author_profile`, `title`, `description`, `frequency` [`WEEKLY`, `BIWEEKLY`, `MONTHLY`, `OCCASIONAL`], `is_active`). Propiedades calculadas: `active_subscribers_count` y `sent_issues_count`.
  - `AuthorNewsletterSubscriber`: suscripción del lector con token seguro para baja instantánea (`unsubscribe_token` UUID), estado activo indexado y fechas `subscribed_at` / `unsubscribed_at`. Restricción única `(newsletter, user)`.
  - `AuthorNewsletterIssue`: números del boletín con títulos, asunto, contenido, estados `DRAFT`, `SCHEDULED`, `SENT`, fechas de programación y envío, recuento de destinatarios (`recipients_count`) y lecturas (`views_count`).
  - Migración aplicada en PostgreSQL: `0037_authornewsletter_authornewsletterissue_and_more.py`.
- **API REST y Lógica de Negocio:**
  - `AuthorNewsletterViewSet` en `/api/v1/books/author-newsletters/`:
    - Filtrado por `author` o `author_id`.
    - Acción `@action subscribe`: suscripción inmediata o reactivación sin duplicados con retorno de contador dinámico.
    - Acción `@action unsubscribe`: baja instantánea con actualización de timestamp.
    - Acción `@action my_subscriptions`: listado de boletines a los que está suscrito el usuario.
    - Acción `@action subscribers`: consulta paginada de suscriptores restringida al autor propietario y administradores.
  - `AuthorNewsletterIssueViewSet` en `/api/v1/books/author-newsletter-issues/`:
    - Filtrado por `newsletter` y visibilidad restringida (lectores generales solo ven entregas con estado `SENT`).
    - Acción `@action send_issue`: cálculo de destinatarios, marcado a `SENT`, timestamp de envío y guardado atómico.
- **Frontend React y Experiencia de Usuario:**
  - Componente accesible `AuthorNewsletterSection.tsx` integrado en `Author.tsx`.
  - Tarjeta de suscripción editorial con frecuencia, contador dinámico de lectores y botón interactivo 1-clic con feedback visual.
  - Histórico de entregas con visor expandible de contenido ("Leer entrega" / "Ocultar") y métricas de lectores.
  - Panel para el autor verificado con modales para configurar la newsletter y redactar/enviar nuevas entregas con opción de borrador o publicación inmediata.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint13_author_newsletters.py`: 7/7 tests pasando al 100%.
  - Suite `frontend/src/features/books/__tests__/AuthorNewsletterSection.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 13): 88/88 tests pasando consecutivamente al 100% en 98s.
  - Frontend: `npm run typecheck` limpio (0 errores), 17 suites / 58 tests Vitest pasando al 100%, y build de producción Vite generado limpiamente en 12s.

### 4.34. Gamificación Avanzada y Retos de Lectura (Sprint 14 — Futuro)
- **Modelos de Dominio y Sincronización Automática:**
  - `ReadingChallenge`: retos comunitarios y anuales por libros (`books_count`), páginas (`pages_count`), reseñas (`reviews_count`) o género (`genre_books`).
  - `UserChallenge`: participación del lector, progreso actualizado en vivo (`current_count`), estado `is_completed` y fecha de finalización.
  - `ReadingStreak`: registro de racha actual, racha récord más larga, días congelados y registro de sesiones de lectura (`log_reading_session`).
  - `GamificationService`:
    - `sync_user_challenge_progress()`: motor reactivo de sincronización que calcula el progreso exacto según los `UserBook` completados en el rango del reto, finaliza el reto automáticamente si se alcanza la meta y concede la insignia asociada.
    - `ensure_default_challenges()`: siembra automática e idempotente de retos comunitarios clave (Reto Anual 2026, Sprint de Novela, Maratón de Páginas, Clásicos Inolvidables).
    - `leave_challenge()`: lógica transaccional para abandonar un reto y decrementar participantes.
- **API REST y Endpoints:**
  - `ReadingChallengeListView` en `/api/v1/gamification/challenges/`: sincroniza el progreso del usuario autenticado en caliente y devuelve catálogo de retos con flags `has_joined`, `is_completed` y progreso porcentual.
  - `LeaveChallengeView` en `POST /api/v1/gamification/challenges/<slug>/leave/`: endpoint para abandonar retos con actualización inmediata.
  - `ReadingGoalViewSet` en `/api/v1/gamification/goal/`: cálculo de ritmo anual (`books_per_month_required`, `status` [ahead, on_track, behind]).
  - `GamificationOverviewView` en `/api/v1/gamification/overview/`: vista unificada de nivel, puntos, racha, insignias y retos activos.
- **Frontend React y Experiencia de Usuario:**
  - Página dedicada `ChallengesPage.tsx` (`/challenges`) accesible en la barra de navegación superior (`Header.tsx`) y registrada en `router.tsx`.
  - 4 Pestañas WAI-ARIA completas:
    - 🏆 **Retos Comunitarios**: catálogo de retos, tarjetas con barras de progreso, métricas de participantes y botones dinámicos para Unirse / Abandonar reto.
    - 🎯 **Mi Meta Anual**: tarjeta de meta del año actual con progreso de libros leídos, proyección de ritmo (adelantado/a tiempo) y modal para configurar libros y páginas objetivo.
    - 🔥 **Racha & Registro**: visualización de racha actual en días, racha histórica récord, congeladores disponibles y modal para registrar lecturas diarias con páginas y minutos leídos.
    - 🎖️ **Medallero**: catálogo completo de insignias con filtros por categoría (Todas, Lectura, Racha, Retos, Social), estado de desbloqueo y fecha de obtención.
- **Calidad y Regresión Total:**
  - Suite `backend/tests/test_sprint14_gamification_challenges.py`: 7/7 tests pasando al 100%.
  - Suite `frontend/src/features/books/__tests__/ChallengesPage.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 14): 95/95 tests pasando consecutivamente al 100% en 85s.
  - Frontend: `npm run typecheck` estricto con 0 errores, suite completa Vitest (18 suites / 62 tests pasando al 100%) y build de producción Vite generado limpiamente en 29s.

### 4.35. Estadísticas Avanzadas de Lectura, Ritmo y Memoria Anual (Sprint 15 — Futuro)
- **Motor de Dominio y Estadísticas Granulares (`stats_service.py`):**
  - Parámetro de filtrado temporal `year` (`?year=YYYY` o `?year=all`) y descubrimiento automático de `available_years`.
  - Clave de caché Redis adaptada: `stats:user:<id>[:year:<year>]` con invalidación atómica multianual en `cache_utils.py`.
  - Métricas de Ritmo y Velocidad (`reading_pace`): días promedio por libro (`avg_days_per_book`), libro más veloz (`fastest_book`), libro más pausado (`slowest_book`), páginas al día y al mes, y mes pico de lectura (`highest_reading_month`).
  - Distribución por Longitud (`length_distribution`): clasificación en Cortos (<200p), Medios (200-399p), Largos (400-599p) y Épicos (600+p) junto a los extremos leídos (`longest_book` y `shortest_book`).
  - Distribución por Formato y Posesión (`format_distribution`): proporción física vs digital/ebook y en propiedad vs prestado.
  - Memoria Anual / "Year in Review" (`year_in_review`): retrospectiva anual con libro mejor calificado, género y autor predilectos, y comparativa interanual frente al año previo (+libros y +páginas).
- **API REST y Vistas:**
  - `ReadingStatsView` en `/api/v1/books/statistics/`: acepta parámetro `year`, delega en `services.get_user_reading_stats(target_user_id, year=year)` y respeta estrictamente los niveles de privacidad del perfil.
- **Frontend React y Experiencia de Usuario (`ReadingStats.tsx`):**
  - Selector dinámico de año en la cabecera (píldoras interactivas con `Histórico`, `2026`, `2025`, etc.).
  - 4 Pestañas WAI-ARIA completas:
    - 📊 **Resumen General**: KPIs principales, gráfico de barras mensual con alternancia entre métrica de **Libros** y **Páginas**, distribución de estrellas (1..5), preferencias literarias y autores predilectos.
    - ⚡ **Ritmo & Velocidad**: tarjetas de duración media por libro, páginas diarias/mensuales, mes récord y tarjetas destacadas de lectura más veloz y más pausada.
    - 📐 **Longitud & Formatos**: barras visuales de tramos de páginas, libros extremos completados y comparativas de formato (papel vs digital) y posesión.
    - 🏆 **Memoria Anual**: tarjeta editorial retrospectiva del año con destacados, libro cumbre mejor valorado y comparativa de crecimiento frente al año previo (+/- libros y páginas).
- **Calidad y Regresión Total:**
  - Suite backend `backend/tests/test_sprint15_advanced_reading_stats.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/books/__tests__/ReadingStats.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 15): 107/107 tests pasando consecutivamente al 100% en 126s.
  - Frontend: `npm run typecheck` estricto 0 errores, Vitest completo (19 suites / 66 tests pasando al 100%) y build de producción Vite limpio generado en 13.88s.

### 4.36. Sprint 16 — Integración con Redes Sociales y Compartición Gráfica

- **Servicio y Motor de Compartición Backend (`social_share_service.py`):**
  - Implementación de `generate_social_share_card(share_type, object_id, user, year)`:
    - 📖 **Libros (`book`)**: metadatos enriquecidos con título, autor, valoración media, hashtags específicos (`#<Titulo>`, `#LibrosRecomendados`) y URL canónica.
    - 📊 **Estadísticas / Memoria Anual (`reading_stats`)**: métricas agregadas anuales o históricas (libros leídos, páginas acumuladas, autor y género cumbre) y hashtags (`#MemoriaLectora`, `#ReadingGoals`).
    - 🏆 **Retos de Lectura (`challenge`)**: progreso actual, meta objetivo, porcentaje y llamada a la acción comunitaria.
    - 🎖️ **Insignias y Medallas (`badge`)**: categoría, nombre y nivel de maestría alcanzado.
    - 📋 **Listas de Lectura (`reading_list`)**: tipo de lista (personal o colaborativa), recuento de obras y descripción.
  - Generación automática de deep links directos de 1 clic para:
    - **X (Twitter)** (`https://twitter.com/intent/tweet?text=...&url=...`)
    - **WhatsApp** (`https://api.whatsapp.com/send?text=...`)
    - **Telegram** (`https://t.me/share/url?url=...&text=...`)
    - **LinkedIn** (`https://www.linkedin.com/sharing/share-offsite/?url=...`)
    - **Facebook** (`https://www.facebook.com/sharer/sharer.php?u=...`)
    - **Email** (`mailto:?subject=...&body=...`)
  - Tracking analítico de difusión (`track_social_share(share_type, object_id, platform, user)`) registrado con `AuditLog` o métricas de difusión.
- **Endpoints REST Registrados:**
  - `GET /api/v1/books/share/card/` (`SocialShareCardView`): consulta y generación en tiempo real de metadatos sociales estructurados y deep links.
  - `POST /api/v1/books/share/track/` (`SocialShareTrackView`): telemetría y registro de clics de compartición por plataforma social.
- **Frontend Interactivo y Accesible (`SocialShareModal.tsx`):**
  - Componente modal con previsualización en vivo de la tarjeta social gráfica ("Social Card Preview"): gradientes temáticos, portadas/emojis, badges destacados y formato estándar listo para difusión.
  - Botones directos para las 5 redes con apertura en nueva pestaña segura (`rel="noopener noreferrer"`).
  - Botón de copiado de URL y botón de copiado de texto formateado con emojis y hashtags, con feedback visual reactivo (`¡Enlace copiado!`, `¡Texto copiado!`).
  - Integración en `ReadingStats.tsx` (botón en cabecera y en tarjeta de Memoria Anual) y en `BookDetail.tsx` (botón "Compartir este libro").
- **Calidad y Regresión Total:**
  - Suite backend `backend/tests/test_sprint16_social_sharing.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/social/__tests__/SocialShareModal.test.tsx`: 4/4 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 16): 114/114 tests pasando consecutivamente al 100% en 101s.
  - Frontend: `npm run typecheck` estricto con 0 errores, Vitest completo (20 suites / 70 tests pasando al 100%) y build de producción Vite limpio generado en 16.05s.

### 4.37. Sprint 17: Recomendaciones Avanzadas y Lectores Afines

- **Motor Multimodal y Algoritmos Granulares (`recommendation_service.py`):**
  - Soporte de 7 estrategias de recomendación: `hybrid` (v3 fusionando señales semánticas, colaborativas y de temática), `collab` (v2 colaborativo), `semantic` (vectores de embedding y trama), `serendipity` (descubrimiento de joyas altamente valoradas de autores no leídos por el usuario), `rules`, `social` y `v1`.
  - Exposición de porcentaje de match transparente (`affinity_percentage`, escala calibrada 65% - 98%), vector de desglose de contribución (`breakdown`) y motivo contextual explicable (`reason`).
  - Estimación robusta de número de páginas en el catálogo mediante `user_entries__current_page` (`Max('user_entries__current_page')`).
  - Filtros granulares por género (`category_id`) y extensión de lectura (`length_tier`: `short` <200p, `medium` 200-399p, `long` 400-599p, `epic` 600+p).
  - Exclusión automática de obras descartadas por el usuario (`exclude_dismissed=true`).
- **Endpoint de Descarte Rápido y Caché Redis:**
  - `POST /api/v1/books/recommendations/dismiss/` con función de servicio `dismiss_recommendation` en `recommendation_feedback_service.py`. Registra la interacción `DISMISSED` en el modelo `RecommendationFeedback`.
  - Invalidación quirúrgica e instantánea de la caché Redis del usuario para todas las combinaciones y variantes de estrategias en `cache_utils.py`.
- **Red de Gemelos Lectores (`similar-readers`):**
  - Endpoint `GET /api/v1/books/recommendations/similar-readers/` operativo que compara vectores y valoraciones para encontrar usuarios con máxima afinidad de gustos literarios y libros compartidos.
- **Frontend Interactivo Dedicado (`RecommendationsPage.tsx`):**
  - Página completa en `/recommendations` integrada en `router.tsx` bajo `ProtectedLayout`, con enlace principal "Descubre" en `Header.tsx` y enlace rápido "Ver todas →" desde el muro principal `Home.tsx`.
  - Selector de 4 modos con estética premium: "Híbrido IA", "Gemelos Lectores", "Estilo y Temática", "Descubrimiento".
  - Barra de filtros combinados de género y extensión con contador reactivo de obras encontradas.
  - Tarjetas de libros con portadas adaptables, badges con degradados del `% Afinidad`, justificación explicable, botón de 1 clic a "Quiero leer" (con transición inmediata a "En tu biblioteca") y botón de descarte rápido (remoción fluida de la tarjeta).
  - Panel lateral de "Gemelos Lectores" con avatars, porcentaje de similitud y libros en común.
- **Calidad y Regresión Total:**
  - Suite backend `backend/tests/test_sprint17_advanced_recommendations.py`: 7/7 tests pasando al 100%.
  - Suite frontend `frontend/src/features/discovery/__tests__/RecommendationsPage.test.tsx`: 5/5 tests pasando al 100%.
  - Regresión secuencial completa backend (Sprints 1 al 17): **121/121 tests pasando consecutivamente al 100%** en 107.97s.
  - Frontend: `npm run typecheck` estricto con 0 errores, Vitest completo (**21 suites / 75 tests pasando al 100%**) y bundle de producción Vite generado limpiamente en 14.88s.

### 4.38. Sprint 18: Audiolibros y Text-to-Speech (TTS)

- **Modelado de Datos y Persistencia de Escucha (`audiobook_models.py`):**
  - Modelo `AudiobookTrack`: orden de pista (`track_number`), título (`title`), narrador (`narrator`), duración en segundos (`duration_seconds`), URL de audio (`audio_url`) y bandera de muestra gratuita (`is_sample`).
  - Modelo `UserAudiobookProgress`: seguimiento por usuario y libro, última pista escuchada (`last_track`), timestamp de reproducción en segundos (`current_seconds`), porcentaje completado (`completion_percentage`), timestamp de última escucha y bandera `is_completed`.
  - Migración `0038_audiobooktrack_useraudiobookprogress_and_more.py` aplicada limpiamente en PostgreSQL.
- **Capa de Servicios de Dominio (`audiobook_service.py`):**
  - `get_book_audiobook_details(book_id, user)`: cálculo de duración total, formateo HH:MM:SS, obtención de pistas ordenadas, progreso persistido y fallback inteligente a BookVoice TTS con sample sintético si no hay audio comercial grabado.
  - `save_audiobook_progress(book_id, user, track_id, current_seconds, is_completed)`: sincronización y actualización atómica del progreso con recálculo dinámico de porcentaje de compleción.
  - `get_audiobook_catalog(category_id, narrator, search)`: catálogo de obras con narración y metadatos de pistas.
  - `get_user_listening_shelf(user)`: estantería de escucha en curso del lector para acceso y reanudación inmediata.
- **Endpoints API REST (`/api/v1/books/`):**
  - `GET /api/v1/books/<id>/audiobook/`: detalles de audiolibro, pistas y progreso del usuario autenticado.
  - `POST /api/v1/books/<id>/audiobook/progress/`: guardado periódico de timestamp y pista escuchada.
  - `GET /api/v1/books/audiobooks/`: catálogo general de audiolibros.
  - `GET /api/v1/books/audiobooks/in-progress/`: audiolibros en progreso para la biblioteca del usuario.
- **Frontend y Reproductor Global Interactivo:**
  - Store Zustand `audioPlayer.ts`: estado reactivo de pista actual, reproducción, velocidad (0.75x a 2.0x), volumen, silenciamiento, modo TTS y cola de pistas.
  - `AudioPlayerBar.tsx`: barra de reproducción flotante global integrada en `ProtectedLayout.tsx` y `PublicLayout.tsx`. Dispone de botones ±15 segundos, barra de scrubber interactiva, selector de velocidad, indicador visual de narrador sintético y sincronización automática de progreso con el backend.
  - `BookAudiobookSection.tsx`: sección en la ficha de libro (`BookDetail.tsx`) con listado de pistas, duración total, botón de reproducción de muestra y fallback 1-clic a narrador BookVoice TTS.
  - Sección "🎧 Audiolibros en curso" en `Library.tsx` con barras de progreso y enlace para continuar la escucha.
- **Calidad y Regresión Total:**
  - Suite backend `backend/tests/test_sprint18_audiobooks_tts.py`: **7/7 tests pasando al 100%**.
  - Suite frontend `frontend/src/features/books/__tests__/AudiobookPlayer.test.tsx`: **5/5 tests pasando al 100%**.
  - Regresión secuencial completa backend (Sprints 1 al 18): **128/128 tests pasando consecutivamente al 100%** en 133.23s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (**22 suites / 80 tests pasando al 100%**) y build de producción Vite generado limpiamente en 33.17s.

### 4.39. Sprint 19: Marketplace y Enlaces Editoriales

- **Modelado de Datos y Entidad Editorial (`marketplace_models.py`):**
  - Modelo `Publisher`: entidad editorial con nombre, slug canónico, descripción, web oficial, logotipo, país de origen, acreditación verificada (`is_verified`) y usuario representante oficial (`claimed_by`).
  - Campo `publisher` en `Book`: relación directa de clave foránea a la editorial catalogada.
  - Modelo `BookBuyLink`: oferta comercial para la obra con denominación de comercio, tipo (`indie_network`, `online_retailer`, `publisher_direct`, `ebook_store`, `audio_store`), formato (`paperback`, `hardcover`, `ebook`, `audiobook`), enlace directo, precio estimado opcional, moneda, acreditación oficial del autor y flag de afiliación.
  - Modelo `MarketplaceClick`: registro anónimo de clics hacia tiendas y opciones de compra para telemetría y conversión sin registrar datos personales ni IP (RGPD compliant).
  - Migración `0039_bookbuylink_marketplaceclick_publisher_and_more.py` aplicada limpiamente en PostgreSQL.
- **Capa de Servicios de Dominio (`marketplace_service.py`):**
  - `get_book_marketplace_offers(book, user)`: agregador multitienda con prioridad a librerías de proximidad (**TodosTusLibros**), grandes superficies (**Casa del Libro**, **Fnac**), tiendas digitales (**Amazon**, **Kindle**, **Audible**, **Google Play Books**) y enlaces directos de autor/editorial.
  - `record_marketplace_click(book_id, merchant_name, format_type, buy_link_id)`: telemetría anónima sin PII y compatibilidad con `AffiliateClick` para Amazon.
  - `create_or_update_buy_link(book_id, user, data)`: gestión con control de acceso estricto (autor verificado o admin).
  - `delete_buy_link(buy_link_id, user)`: eliminación segura de enlace comercial.
  - `get_publishers_catalog(search, country)` y `get_publisher_detail(identifier)`: catálogo público de editoriales.
- **Endpoints API REST (`/api/v1/books/`):**
  - `GET /api/v1/books/<id>/marketplace/`: opciones agregadas multitienda y desglose por formato.
  - `POST /api/v1/books/<id>/marketplace/click/`: registro de intención de compra anónimo.
  - `POST /api/v1/books/<id>/marketplace/links/`: creación/edición de enlaces oficiales para autores propietarios.
  - `DELETE /api/v1/books/marketplace/links/<id>/`: borrado de enlaces comerciales oficiales.
  - `GET /api/v1/books/publishers/` y `GET /api/v1/books/publishers/<slug>/`: catálogo y ficha de editoriales.
- **Frontend y Experiencia de Usuario (`BookMarketplaceModal.tsx`):**
  - Modal accesible WAI-ARIA con pestañas de filtrado (Todas, Librerías de Barrio, Papel, Ebook, Audiolibro).
  - Tarjetas de tiendas con badges informativos, precio estimado y enlaces seguros `rel="noopener noreferrer sponsored"`.
  - Botón directo "🛍️ Dónde comprar / Librerías" integrado en `BookDetail.tsx`.
  - Mención de la editorial asociada a la obra en los metadatos de cabecera.
  - Formulario integrado para que autores verificados puedan añadir sus enlaces de venta directa.
- **Calidad y Regresión Total:**
  - Suite backend `backend/tests/test_sprint19_marketplace_editoriales.py`: **7/7 tests pasando al 100%**.
  - Suite frontend `frontend/src/features/books/__tests__/BookMarketplace.test.tsx`: **5/5 tests pasando al 100%**.
  - Regresión secuencial completa backend (Sprints 1 al 19): **135/135 tests pasando consecutivamente al 100%** en 134.34s.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), Vitest completo (**23 suites / 85 tests pasando al 100%**) y build de producción Vite generado limpiamente en 13.01s.

### 4.40. Sprint 20: IA Multimodal y Asistente Literario Ampliado
- **Motor de Visión Computacional Literaria (`backend/ai/multimodal_service.py`):**
  - Análisis cromático avanzado: extracción de paleta de colores dominantes con código hexadecimal, nombres humanos evocadores y contrastes, respaldado por validación de imágenes con Pillow/PIL y fallback determinista.
  - Clasificación estética y tonal: categorización de estilos artísticos (Realismo Mágico, Ilustración Fantástica, Fotografía Editorial, Minimalista, etc.) y atmósferas sensoriales (nostálgica, épica, misteriosa, etc.).
  - Accesibilidad Universal: generación de texto alternativo descriptivo enriquecido (`accessible_alt_text`) para personas con discapacidad visual según estándares WCAG 2.1 AA.
  - Búsqueda visual inversa: coincidencia visual y semántica con obras del catálogo existente (`analyze_cover_image`) calculando el porcentaje de certidumbre (`match_confidence`).
- **Endpoints API REST (`backend/books/ai_views.py`):**
  - `POST /api/v1/books/ai/multimodal/analyze-cover/`: análisis visual completo y búsqueda por portada (acepta JSON base64 o multipart/form-data).
  - `POST /api/v1/books/ai/multimodal/assistant/`: interacción conversacional con IA con soporte de adjuntos de imagen para resolver dudas sobre ediciones, estilos y portadas.
  - `GET /api/v1/books/<id>/ai/visual-insights/`: análisis cromático y artístico específico de la cubierta de una obra existente.
- **Frontend y Experiencia de Usuario:**
  - `VisualBookSearchModal.tsx`: modal interactivo de búsqueda visual con drag & drop de imágenes, vista previa, análisis visual con IA, visualización de paleta cromática con copia de códigos HEX al portapapeles y enlace directo a la ficha del libro detectado.
  - `AIAssistantModal.tsx`: ampliación con botón de cámara 📷 para adjuntar imágenes, miniaturas en las burbujas de chat y diálogo multimodal.
  - `BookDetail.tsx`: pestaña interactiva "🎨 Arte & Portada" en la tarjeta BookAI con swatches de color, estilos, atmósferas y descripción accesible.
- **Calidad y Verificación Integral:**
  - Suite backend `backend/tests/test_sprint20_multimodal_ai.py`: **7/7 tests pasando al 100%**.
  - Regresión secuencial completa backend (Sprints 1 al 20): **142/142 tests pasando al 100% de forma consecutiva** (126.59s).
  - Suite frontend `frontend/src/features/ai/__tests__/MultimodalAI.test.tsx`: **6/6 tests pasando al 100%**.
  - Frontend verificado: TypeScript estricto con 0 errores (`tsc --noEmit`), suite completa de Vitest (**24 suites / 91 tests pasando al 100%**) y build de producción Vite limpio en 13.06s.

### Integración de Búsqueda Externa: Amazon PA-API v5 y Soporte de `page_count` (Libros)
- **Proveedor Amazon PA-API v5 (`backend/books/services/providers/amazon.py`):**
  - Configurado como la **1ª opción en la cadena de búsqueda e importación de libros** (`import_service.py`), con fallback transparente a Google Books, Wikipedia y OpenLibrary cuando `is_configured()` es `False` o ante fallos externos.
  - Firma canónica AWS SigV4 (`AWS4-HMAC-SHA256`) nativa con `hashlib` y `hmac`.
  - Settings configurados: `AMAZON_PAAPI_ACCESS_KEY`, `AMAZON_PAAPI_SECRET_KEY`, `AMAZON_PAAPI_TAG`, `AMAZON_PAAPI_REGION`, `AMAZON_PAAPI_HOST`.
  - Extracción y persistencia de `page_count` (`TechnicalInfo.NumberOfPages`) y generación automática de `BookBuyLink` de afiliado.
- **Soporte de Páginas (`page_count`):**
  - Modelo `Book`: campo `page_count = models.PositiveIntegerField(null=True, blank=True)`. Migración `0040_book_page_count.py` aplicada en PostgreSQL.
  - Proveedores adaptados: `GoogleBooksProvider` (`volumeInfo.pageCount`) y `OpenLibraryProvider` (`number_of_pages` / `number_of_pages_median`).
  - Serializer `BookSerializer` exponiendo `page_count`.
  - Frontend `BookDetail.tsx` renderizando el número de páginas (`📖 {book.page_count} páginas`).
- **Pruebas y Verificación:**
  - Suite backend `backend/tests/test_amazon_books_provider.py`: **12/12 tests pasando al 100%**.
  - Regresión combinada de importación y catálogo: **17/17 tests pasando al 100%**.
  - Frontend verificado: `npm run typecheck` (0 errores), Vitest (**24 suites / 91 tests pasando al 100%**) y build de producción Vite limpio.

### Publicaciones de Autores Verificados, Monetización y Moderación/Censura de Administración (RoadmapV3)
- **Autorización Estricta de Creación y Edición de Publicaciones:**
  - Solo el **autor verificado titular** (`(author.claimed_by == user and author.is_verified) or (profile.author == author and profile.is_verified)`) tiene permisos para crear publicaciones en su perfil (`AuthorPublicationViewSet.perform_create` y `AuthorAnnouncementCreateView`). Usuarios comunes o solicitudes no aprobadas reciben `403 Forbidden`.
  - La modificación y eliminación (`perform_update`, `perform_destroy`) quedan restringidas exclusivamente al autor verificado titular o a usuarios con rol `ADMIN` / `MODERATOR`. Terceros reciben `403 Forbidden`.
- **Evolución del Modelo `AuthorAnnouncement` y Migración:**
  - Campos incorporados: `is_paid` (boolean), `price` (decimal positivo), `is_moderated` (boolean), `moderation_reason` (text), `moderated_by` (FK User), `moderated_at` (DateTimeField).
  - Migración aplicada en PostgreSQL: `books/migrations/0041_authorannouncement_moderation_and_paid.py`.
- **Consola y Flujo de Moderación/Censura:**
  - Endpoint `@action(detail=True, methods=['post'])` en `AuthorPublicationViewSet` (`/api/v1/books/author-publications/<id>/censor/`) para alternar censura o fijar `is_moderated`, motivo y autoría con registro de `AuditLog`.
  - Consola universal de moderación administrativa (`AdminContentHideView` y `AdminContentRestoreView` en `/api/v1/admin/moderation/hide/` y `/restore/`) adaptada para `author_publication` y `announcement`.
  - Filtrado de lectura: publicaciones censuradas (`is_moderated=True`) son excluidas del queryset para lectores anónimos y comunes, permaneciendo visibles para el autor original (con aviso de moderación) y administradores.
- **Frontend y Controles de Interfaz (`Author.tsx`, `AuthorPublicationsSection.tsx`):**
  - Distinción rigurosa en `Author.tsx`: `isVerifiedAuthorOwner` (`author.claimed_by === user.id && author.is_verified`) y `isAdminOrModerator`.
  - Botón "Nueva Publicación" visible exclusivamente para el autor verificado titular.
  - Formulario modal enriquecido con opciones de monetización (checkbox `🔒 Contenido exclusivo de pago` y campo `precio €`).
  - Controles de moderación para administradores: botones de edición/eliminación administrativa, botón "Censurar" / "Restaurar" y modal con motivo de censura.
  - Badges visuales: `🔒 De pago (X.XX €)`, `🚫 Censurada` y cartel de advertencia con motivo de moderación.
- **Calidad y Verificación Integral:**
  - Suite backend dedicada `backend/tests/test_author_verified_publications.py`: **9/9 tests pasando al 100%**.
  - Regresión backend `backend/tests/test_sprint12_author_publications.py`: **7/7 tests pasando al 100%**.
  - Frontend verificado: `npm run typecheck` limpio (0 errores) y build de producción Vite generado exitosamente.

---

## 5. Hoja de Ruta Activa: Roadmap de Producción y Evolución (Roadmap.md)

| Bloque | Objetivo Principal | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **BLOQUE A** | **Estabilización crítica (P0)**: baseline, JWT/cookies HttpOnly, WebSockets seguros, integridad y superficie de ataque | 🔴 P0 | **EN CURSO (Iniciando Fase A1)** |
| **BLOQUE B** | **Infraestructura y operación (P0/P1)**: Docker prod, backups/restore, observabilidad, escalabilidad | 🔴/🟠 | Pendiente |
| **BLOQUE C** | **Calidad y deuda técnica (P1)**: tests e2e/carga, linting estricto, CI/CD, gobernanza | 🟠 P1 | Pendiente |
| **BLOQUE D** | **Endurecimiento de producto core (P1)**: perfil lector, multi-rol autores/catálogo, reseñas/social, búsqueda híbrida | 🟠 P1 | Pendiente |
| **BLOQUE E** | **Pre-producción y lanzamiento público (P1)**: staging, soft launch, GA endurecida | 🟠 P1 | Pendiente |
| **BLOQUE F** | **Evolución post-lanzamiento (P2/P3)**: Core Web Vitals, producto avanzado, escala multi-región | 🟡/🟢 | Posterior |

### Desglose de Fases Inmediatas (Bloque A — P0):
- **Fase A1 — Congelación y baseline de seguridad (P0):** Tag `v1.0.0-pre-hardening`, branch de protección, backup cifrado PostgreSQL + media, verificación de 0 migraciones pendientes, ejecución de suite 100% verde, auditoría de marcadores de conflicto residuales y limpieza de código muerto.
- **Fase A2 — Autenticación y sesión segura (P0):** Migración de JWT de `localStorage` a cookies `HttpOnly` + `Secure` + `SameSite=Strict`, eliminación de tokens en query strings de WebSockets, tickets efímeros y tests de robo/XSS.
- **Fase A3 — Integridad de dominio y permisos (P0):** `UniqueConstraint` en `Review`/`UserBook`, cálculo optimizado de rating sin `save()` completo, validación MIME real en subidas y throttling de endpoints sensibles.
- **Fase A4 — Health, readiness y superficie de ataque (P0):** Sondas seguras sin fuga de datos, OpenAPI protegido y checklist OWASP Top 10.

---

## 6. Ubicación de Documentación Relevante

- **Arquitectura y Rendimiento:** [docs/architecture/database_performance.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/architecture/database_performance.md)
- **Estrategia de Escalabilidad y Performance Tuning:** [docs/architecture/scalability_and_performance_tuning.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/architecture/scalability_and_performance_tuning.md)
- **Estrategia de Pruebas Backend:** [docs/backend/testing_strategy.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/backend/testing_strategy.md)
- **Calidad de Frontend:** [docs/frontend/quality_and_testing.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/frontend/quality_and_testing.md)
- **CI/CD Pipeline:** [docs/devops/ci_cd_pipeline.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/ci_cd_pipeline.md)
- **Despliegue y Docker en Producción:** [docs/devops/production_docker.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/production_docker.md)
- **Scripts de Copias de Seguridad:** `scripts/backup/backup_db.sh` y `scripts/backup/restore_db.sh`
- **Política de Moderación de Contenido:** [docs/security/content_moderation_policy.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/security/content_moderation_policy.md)
- **Experiencia de Onboarding y Activación:** [docs/product/onboarding_experience.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/onboarding_experience.md)
- **Descubrimiento y Landing Pública:** [docs/product/book_discovery_and_public_experience.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/book_discovery_and_public_experience.md)
- **Listas Sociales y Colecciones:** [docs/product/social_reading_lists.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/social_reading_lists.md)
- **Feed Social y Actividad:** [docs/product/social_feed.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/social_feed.md)
- **Sistema de Notificaciones:** [docs/product/notifications_system.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/notifications_system.md)
- **IA de Producto y Asistente Literario:** [docs/product/ai_product_assistant.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/ai_product_assistant.md)
- **Embeddings y Búsqueda Vectorial:** [docs/ai/embeddings_and_vector_search.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/ai/embeddings_and_vector_search.md)
- **Analytics de Producto y Telemetría:** [docs/product/product_analytics.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/product_analytics.md)
- **Checklist de Beta Cerrada y Despliegue:** [docs/deployment/closed_beta_checklist.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/deployment/closed_beta_checklist.md)
- **Preparación para Beta Abierta:** [docs/deployment/open_beta_readiness.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/deployment/open_beta_readiness.md)
- **Guía de Preparación de Producción y Hardening:** [docs/deployment/production_readiness_guide.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/deployment/production_readiness_guide.md)
- **Monetización y Plataforma de Autores:** [docs/business/monetization_and_author_platform.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/business/monetization_and_author_platform.md)
- **Multi-autor, Reseñas en Perfil y Muro Social:** [docs/product/wall_posts_and_multiauthor_platform.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/product/wall_posts_and_multiauthor_platform.md)



