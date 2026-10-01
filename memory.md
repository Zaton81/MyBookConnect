# Memoria del Proyecto y Contexto Operativo — MyBookConnect

Este documento contiene el **contexto arquitectónico continuo**, el **historial de decisiones técnicas**, las **restricciones obligatorias** y las **trampas resueltas (*gotchas*)** del proyecto **MyBookConnect**.

Cualquier agente de IA o desarrollador que se incorpore a la base de código **DEBE leer y respetar este documento** antes de realizar cambios.

---

## 1. Reglas de Oro del Proyecto (Invariantes Obligatorias)

1. **Rama de trabajo exclusiva:**
   - Todo el trabajo de desarrollo e integración se realiza **SIEMPRE en la rama `develop`**.
   - Nunca hacer push directo a `main`.
2. **Flujo de Fases y Commits:**
   - Seguir estrictamente el orden de fases definido en [RoadmapV2.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV2.md).
   - Redactar y someter a aprobación del usuario un plan detallado en `implementation_plan.md` antes de implementar una nueva fase.
   - Tras completar cada fase, verificar calidad (100% tests pasando, linters limpios, cero cambios de migración pendientes) y realizar inmediatamente un **commit semántico** y **`git push origin develop`**.
3. **Cero Regresiones:**
   - La suite completa de backend (114 tests del Roadmap, >680 tests totales) y frontend (27 tests de Vitest) debe pasar al 100%. Ningún commit debe romper funcionalidad previa.
4. **Seguridad de Base de Datos de Pruebas:**
   - **PROHIBIDO ejecutar comandos concurrentes/paralelos de `pytest`**. La base de datos de test PostgreSQL (`test_booksocial`) entra en bloqueo transaccional (`OperationalError: database is being accessed by other users`) si se ejecutan múltiples instancias a la vez.

---

## 2. Pila Tecnológica y Arquitectura

- **Backend:** Python 3.12, Django 5.2, Django REST Framework, Django Channels (Daphne ASGI), Celery.
- **Bases de Datos y Caché:** PostgreSQL 16 con extensión `pgvector`, Redis 7 Alpine (caché L2, rate limiting, broker de Celery y layer de Channels).
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, Zustand (gestión de estado de autenticación y UI), React Query (@tanstack/react-query).
- **Contenedores y Producción:** Docker Compose, Nginx 1.27-alpine como API Gateway / Reverse Proxy, multi-stage Dockerfiles, redes aisladas (`frontend_net` y `backend_net internal: true`).

---

## 3. Estado de Ejecución del Roadmap (RoadmapV2.md)

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
| **38** | **Cierre de Beta, Auditoría Final y Release 1.0.0 General (GA)** | **SIGUIENTE** | Congelación de código, auditoría final de seguridad y dependencias, corte de versión SemVer 2.0.0 `1.0.0` definitiva, tag git y checklist de lanzamiento público general. |

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

## 5. Ubicación de Documentación Relevante

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



