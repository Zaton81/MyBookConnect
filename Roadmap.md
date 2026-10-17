# Hoja de Ruta Maestra de Ingeniería y Evolución (Post-GA) — MyBookSocial

> **Estado del Proyecto:** General Availability (GA) alcanzado (72 Fases / 20 Sprints completados).
> **Objetivo de este Documento:** Servir como guía técnica operativa y exhaustiva para eliminar la deuda técnica acumulada durante la construcción acelerada, desacoplar dominios monolíticos, limpiar el historial y árbol de archivos, consolidar la capa de IA/Recomendaciones y preparar la arquitectura para escalar a decenas de miles de usuarios concurrentes.

---

## Índice de Épicas

1. [Diagnóstico de Línea Base (Auditoría del Repositorio Actual)](#1-diagnóstico-de-línea-base-auditoría-del-repositorio-actual)
2. [Fase 1: Higiene de Git, Activos Estáticos y Almacenamiento Multimedia](#2-fase-1-higiene-de-git-activos-estáticos-y-almacenamiento-multimedia)
3. [Fase 2: Deconstrucción del Monolito `backend/books/` (Modularización sin Downtime)](#3-fase-2-deconstrucción-del-monolito-backendbooks-modularización-sin-downtime)
4. [Fase 3: Consolidación de IA, Embeddings (`pgvector`) y Motor de Recomendaciones](#4-fase-3-consolidación-de-ia-embeddings-pgvector-y-motor-de-recomendaciones)
5. [Fase 4: Refactorización Arquitectónica del Frontend (`frontend/src/`)](#5-fase-4-refactorización-arquitectónica-del-frontend-frontendsrc)
6. [Fase 5: Reestructuración y Optimización de la Suite de Testing y QA](#6-fase-5-reestructuración-y-optimización-de-la-suite-de-testing-y-qa)
7. [Fase 6: Rendimiento en PostgreSQL, Redis, Celery y WebSockets](#7-fase-6-rendimiento-en-postgresql-redis-celery-y-websockets)
8. [Fase 7: Seguridad Defensiva Avanzada, Privacidad y Cumplimiento Legal](#8-fase-7-seguridad-defensiva-avanzada-privacidad-y-cumplimiento-legal)
9. [Fase 8: Evolución de Producto y Monetización Real](#9-fase-8-evolución-de-producto-y-monetización-real)
10. [Planificación por Sprints y Métricas de Éxito (SLAs / KPIs)](#10-planificación-por-sprints-y-métricas-de-éxito-slas--kpis)

---

## 1. Diagnóstico de Línea Base (Auditoría del Repositorio Actual)

| Dimensión | Estado Actual en el Repositorio | Problema / Deuda Técnica Detectada | Impacto |
| :--- | :--- | :--- | :--- |
| **Control de Versiones y Binarios** | `backend/media/` rastreado en Git + PNGs pesados en `frontend/src/assets/` | Más de 50 imágenes de portadas, avatares y fotos de autores con duplicados de sufijo aleatorio (`_F7TCjR9`, `_70FpCru`, `_joxidbD`, `_it7j7NR`) inflando el repositorio. | Alto (Clonado lento, builds pesados, suciedad en Git). |
| **Acoplamiento Backend** | `backend/books/` acumula **42 migraciones** y 6 dominios distintos | Catálogo, Clubes de Lectura, Gamificación, Audiolibros, Marketplace, Portal de Autores y comandos de Backup viven dentro de la misma app `books`. | Alto (Riesgo de colisiones en migraciones y alto acoplamiento). |
| **Servicios de IA y Recomendaciones** | Coexistencia de múltiples versiones (`v1`, `v2`, `v3`) y servicios duplicados | `backend/mybookconnect/ai_service.py` duplica responsabilidades de `backend/ai/services.py`. Coexisten `0019_book_embedding` y `0022_bookembedding`. | Medio-Alto (Confusión sobre cuál es la fuente de verdad). |
| **Estructura Frontend** | Doble árbol de rutas y componentes (`src/pages/` y `src/components/` vs `src/features/`) | Más de 35 archivos puente (*re-exports* de 1 línea) en `src/pages/*` y `src/components/*`, además de clientes API duplicados (`services/api.ts` vs `api/client.ts`). | Medio (Fricción cognitiva, *imports* inconsistentes). |
| **Organización de Tests** | **95+ archivos** en `backend/tests/` con 4 nomenclaturas mezcladas | Conviven `test_phase01..72`, `test_phase_a2..e3`, `test_sprint1..20` y tests temáticos, más archivos vacíos (`users/tests.py`, `messages_app/tests.py`). | Alto (Solapamiento de pruebas, difícil mantenimiento). |
| **Scripts Operativos** | Scripts duplicados en `scripts/` | `scripts/locustfile.py` vs `scripts/load_testing/locustfile.py`; `preflight_check.sh` vs `preflight_prod.sh`. | Bajo-Medio (Riesgo de ejecutar el script desactualizado en CI/CD). |

---

## 2. Fase 1: Higiene de Git, Activos Estáticos y Almacenamiento Multimedia

### 2.1. Purga de `backend/media/` del Control de Versiones
Actualmente Git rastrea archivos generados en tiempo de ejecución dentro de `backend/media/author_photos/`, `backend/media/avatars/` y `backend/media/covers/`, incluyendo colisiones de nombres de Django como:
* `backend/media/author_photos/jordi-ortiz.jpg` y `jordi-ortiz_F7TCjR9.jpg`
* `backend/media/author_photos/peter-connolly.jpg` y `peter-connolly_it7j7NR.jpg`
* `backend/media/author_photos/santiago-posteguillo.jpg` y `santiago-posteguillo_70FpCru.jpg`
* `backend/media/author_photos/stephen-dando-collins.jpg` y `stephen-dando-collins_joxidbD.jpg`
* `backend/media/covers/cronicas-y-debates..._8Pae1J3.jpg`, `_RpSqb8Z.jpg`, `_bl1bShc.jpg`

**Plan de Acción:**
- [ ] **Actualizar `.gitignore` raíz:**
  Añadir reglas estrictas para ignorar cualquier archivo subido por usuarios o descargado por proveedores:
  ```gitignore
  backend/media/*
  !backend/media/.gitkeep
  ```
- [x] **Desindexar archivos actuales sin borrarlos del entorno local:**
  ```bash
  git rm -r --cached backend/media/
  touch backend/media/.gitkeep
  git add .gitignore backend/media/.gitkeep
  git commit -m "chore(repo): stop tracking runtime media files in git"
  ```
- [ ] **Limpiar historial de Git (Opcional pero recomendado antes de escalar el equipo):**
  Ejecutar `git filter-repo --path backend/media/ --invert-paths` para reducir el tamaño de `.git` en más de un $85\%$.
- [x] **Crear comando de *seed* determinista para entorno local:**
  Crear `backend/books/management/commands/seed_dev_catalog.py` que genere portadas sintéticas WebP en memoria para desarrollo local sin ensuciar Git.

### 2.2. Deduplicación de Archivos Multimedia por Hash Criptográfico
Para evitar que Django cree copias como `foto_F7TCjR9.jpg` cuando se sube o hidrata la misma imagen dos veces:
- [x] **Modificar `backend/books/media_utils.py` y `backend/mybookconnect/media_security.py`:**
  - Implementar un `UploadToHashedPath` que calcule el hash $\text{SHA-256}$ del binario ya procesado/re-codificado en formato WebP.
  - Guardar la imagen como `covers/< primeros_2_chars_hash >/< sha256 >.webp`.
  - Si el archivo ya existe en el almacenamiento, reutilizar la ruta existente en complejidad $O(1)$ sin escribir de nuevo en disco ni generar sufijos aleatorios.
- [x] **Conversión automática a WebP:**
  - En `backend/mybookconnect/media_security.py`, tras validar y limpiar metadatos EXIF con Pillow, convertir sistemáticamente portadas y avatares a `.webp` (calidad $82\%$, dimensiones máximas según presets optimizados).

### 2.3. Optimización de Activos Estáticos del Frontend
Los archivos en `frontend/src/assets/` y `frontend/public/` tienen un peso excesivo para el primer renderizado (*First Contentful Paint*):
- [x] **Optimizar logotipos e iconos:**
  - Optimizar `frontend/src/assets/logo-horizontal.png`, `logo-libro.png` y `logo-principal.png` (reducción de $\sim 3.2\text{ MB}$ a $< 25\text{ KB}$ cada uno).
  - Reemplazar `frontend/public/favicon.ico` por un conjunto limpio: `favicon.ico` multi-resolución ($16\times 16, 32\times 32, 48\times 48$, $< 4\text{ KB}$) y `apple-touch-icon.png` ($180\times 180$, $< 13\text{ KB}$).

### 2.4. Abstracción de Almacenamiento S3 / Cloudflare R2 para Producción
- [x] **Integrar `django-storages[s3]` en `backend/requirements.txt` y `backend/mybookconnect/settings.py`:**
  - Configurar variable de entorno `STORAGE_BACKEND=local|s3`.
  - Implementar `DeduplicatedFileSystemStorage` y `DeduplicatedS3Storage` en `backend/mybookconnect/storage.py`.
  - En local/CI mantiene `FileSystemStorage` deduplicado; en producción permite conmutar a AWS S3, Cloudflare R2 o MinIO sin tocar una sola línea de código de los modelos.

### 2.5. Consolidación de Scripts Operativos Duplicados
- [x] **Unificar pruebas de carga:**
  - Eliminar `scripts/locustfile.py` (raíz) y mantener únicamente la suite estructurada en `scripts/load_testing/locustfile.py`, `scripts/load_testing/run_locust_headless.py` y `scripts/load_testing/load_test_benchmark.py`.
- [x] **Unificar scripts de *Preflight* de Producción:**
  - Fusionar las validaciones de `scripts/production/preflight_check.sh` y `scripts/production/preflight_prod.sh` en un único `scripts/production/preflight_prod.sh` parametrizado. Actualizar las referencias en `docs/deployment/`.

---

## 3. Fase 2: Deconstrucción del Monolito `backend/books/` (Modularización sin Downtime)

Actualmente `backend/books/` concentra **42 migraciones** y múltiples dominios de negocio. El objetivo es extraer los dominios periféricos en aplicaciones Django independientes **manteniendo intactos los nombres de las tablas en PostgreSQL** (`Meta.db_table = 'books_<modelo>'`) mediante `migrations.SeparateDatabaseAndState`, garantizando cero pérdida de datos y cero tiempo de inactividad.

### 3.1. Extracción de la App `backend/clubs/` (Clubes de Lectura)
- [x] Crear el paquete `backend/clubs/` y registrarlo en `INSTALLED_APPS`.
- [x] Mover desde `backend/books/`:
  - `club_models.py` $\rightarrow$ `backend/clubs/models.py` (`ReadingClub`, `ReadingClubMembership`, `ReadingClubBook`, `ReadingClubDiscussion`, etc., fijando `db_table = 'books_readingclub'`, etc.).
  - `club_serializers.py` $\rightarrow$ `backend/clubs/serializers.py`.
  - `club_views.py` $\rightarrow$ `backend/clubs/views.py`.
  - `club_urls.py` $\rightarrow$ `backend/clubs/urls.py` (manteniendo el mismo prefijo de ruta en `mybookconnect/urls.py`).
- [x] Generar migración con `SeparateDatabaseAndState` en `books` (eliminando del estado de `books`) y en `clubs` (creando el estado en `clubs` sin ejecutar `DROP/CREATE TABLE`).

### 3.2. Extracción de la App `backend/gamification/` (Retos, Rachas e Insignias)
- [x] Crear el paquete `backend/gamification/`.
- [x] Mover desde `backend/books/`:
  - `gamification_models.py` $\rightarrow$ `backend/gamification/models.py` (`Badge`, `UserBadge`, `ReadingChallenge`, `ReadingStreak`, `DailyReadingLog`).
  - `gamification_serializers.py` $\rightarrow$ `backend/gamification/serializers.py`.
  - `gamification_views.py` $\rightarrow$ `backend/gamification/views.py`.
  - `gamification_urls.py` $\rightarrow$ `backend/gamification/urls.py`.
  - `services/gamification_service.py` $\rightarrow$ `backend/gamification/services.py`.

### 3.3. Extracción de la App `backend/audiobooks/` (Reproductor y TTS)
- [x] Crear el paquete `backend/audiobooks/`.
- [x] Mover desde `backend/books/`:
  - `audiobook_models.py` $\rightarrow$ `backend/audiobooks/models.py` (`AudiobookTrack`, `UserAudiobookProgress`).
  - `services/audiobook_service.py` $\rightarrow$ `backend/audiobooks/services.py`.
  - Vistas y serializadores asociados a pistas de audio y progreso de escucha.

### 3.4. Extracción de la App `backend/marketplace/` (Editoriales, Enlaces de Compra y Afiliados)
- [x] Crear el paquete `backend/marketplace/`.
- [x] Mover desde `backend/books/`:
  - `marketplace_models.py` $\rightarrow$ `backend/marketplace/models.py` (`Publisher`, `BookBuyLink`, `MarketplaceClick`, `AffiliateClick`).
  - `services/marketplace_service.py` y `services/affiliate_service.py` $\rightarrow$ `backend/marketplace/services/`.

### 3.5. Extracción de la App `backend/authors_portal/` (Ecosistema de Escritores)
- [x] Crear el paquete `backend/authors_portal/`.
- [x] Mover la lógica exclusiva para escritores verificados (`AuthorProfile`, `AuthorAnnouncement`, `AuthorEvent`, `AuthorEventAttendee`, `AuthorNewsletter`, `AuthorNewsletterIssue`, `services/author_service.py`, `author_urls.py`), dejando en `backend/books/` únicamente la entidad bibliográfica `Author` del catálogo.

### 3.6. Extracción de Comandos de Infraestructura a `backend/ops/` (o `mybookconnect`)
Los siguientes comandos en `backend/books/management/commands/` no pertenecen al dominio de los libros:
- [x] Mover a una app transversal `backend/ops/management/commands/`:
  - `backup_db.py` y `restore_db.py`
  - `backup_media.py` y `restore_media.py`
  - `check_backup_freshness.py` y `verify_restore_integrity.py`
  - `evaluate_system_alerts.py`
  - `benchmark_queries.py` y `rebuild_cache.py`
  - `services/backup_service.py` $\rightarrow$ `backend/ops/services/backup_service.py`.

---

## 4. Fase 3: Consolidación de IA, Embeddings (`pgvector`) y Motor de Recomendaciones

### 4.1. Eliminación de Duplicidades en la Capa de IA
En el repositorio existen tres puntos de entrada para la IA: `backend/mybookconnect/ai_service.py`, `backend/ai/services.py` y `backend/books/ai_views.py`.
- [x] **Auditar y eliminar `backend/mybookconnect/ai_service.py`:**
  - Migrar cualquier función residual hacia `backend/ai/services.py`.
  - Asegurar que todas las llamadas a LLMs pasen exclusivamente por `backend/ai/clients/factory.py` y respeten las políticas de `backend/ai/policies.py` (prevención de *prompt injection*, límites de tokens, moderación de salida).
- [x] **Mover `backend/books/ai_views.py` $\rightarrow$ `backend/ai/views.py`:**
  - Exponer las rutas de IA desde `backend/ai/urls.py` e incluirlas en `backend/mybookconnect/urls.py`.

### 4.2. Unificación del Sistema de Embeddings Vectoriales
Actualmente coexisten `backend/ai/embeddings.py` y `backend/books/services/embedding_service.py`, además de las migraciones históricas `0019_book_embedding.py` (campo en `Book`) y `0022_bookembedding.py` (modelo separado `BookEmbedding`).
- [x] **Consolidar la generación de embeddings en `backend/ai/embeddings.py`:**
  - `backend/books/services/embedding_service.py` solo debe encargarse de construir el texto canónico del libro (Título + Autor + Categorías + Sinopsis limpia) y delegar la vectorización a `ai.embeddings`.
- [x] **Limpiar campo legado de base de datos:**
  - Verificar si el campo antiguo de la migración `0019` sigue presente en el modelo `Book` y, de ser así, deprecarlo en favor de la tabla dedicada `BookEmbedding` (`0022`), que permite reindexar con distintos modelos dimensionales sin bloquear la tabla principal `books_book`.

### 4.3. Refactorización del Motor de Recomendaciones (`v1`, `v2`, `v3`)
En `backend/books/services/` coexisten 7 archivos de recomendación:
1. `recommendation_service.py`
2. `recommendation_v1_service.py` (Heurísticas básicas / popularidad y géneros)
3. `recommendation_v2_service.py` (Filtrado colaborativo e historial)
4. `recommendation_v3_service.py` (Híbrido semántico con `pgvector` + señales de comportamiento)
5. `recommendation_diversity_service.py` (Re-ranking MMR / penalización de monotonía de autor/género)
6. `recommendation_explanation_service.py` (Generación de motivos legibles para la UI)
7. `recommendation_feedback_service.py` (Pesos positivos/negativos y `dismissed`)

**Plan de Acción:**
- [x] **Crear el subpaquete `backend/books/services/recommendations/`:**
  - Implementar un **Pipeline de Recomendación en 4 etapas**:
    1. `candidates.py`: Recuperación rápida de candidatos ($K = 200$) combinando similitud coseno en `pgvector` (`v3`), filtrado colaborativo (`v2`) y *fallback* para usuarios en frío (*cold-start*, `v1`).
    2. `filtering.py`: Exclusión estricta de libros ya leídos, en lectura o descartados (`RecommendationFeedback.dismissed=True`).
    3. `reranking.py`: Aplicación de diversidad (`recommendation_diversity_service.py`) usando *Maximal Marginal Relevance* (MMR):
       $$\text{MMR} = \arg\max_{d_i \in R \setminus S} \left[ \lambda \cdot \text{Sim}_1(d_i, u) - (1 - \lambda) \max_{d_j \in S} \text{Sim}_2(d_i, d_j) \right]$$
    4. `explanations.py`: Enriquecimiento en lote (*batch*) de las razones de recomendación sin incurrir en consultas $N+1$.
- [x] **Eliminar código muerto:** Si `v1` y `v2` contienen métodos que ya fueron absorbidos por `v3`, purgar las funciones redundantes y dejar solo las estrategias activas en el pipeline.

---

## 5. Fase 4: Refactorización Arquitectónica del Frontend (`frontend/src/`)

El frontend ya cuenta con una excelente estructura basada en *features* (`frontend/src/features/`), pero conserva decenas de archivos puente heredados de una arquitectura anterior que ensucian el árbol de directorios.

### 5.1. Eliminación de Archivos Puente (*Re-export Shims*) en `src/pages/` y `src/components/`
- [x] **Eliminar la carpeta `frontend/src/pages/` por completo:**
  - Actualmente los 14 archivos en `frontend/src/pages/*.tsx` (`AddBook.tsx`, `AdminDashboard.tsx`, `Author.tsx`, `BookDetail.tsx`, `Chat.tsx`, `EditProfile.tsx`, `Friends.tsx`, `Home.tsx`, `Library.tsx`, `Login.tsx`, `Profile.tsx`, `ReadingLists.tsx`, `ReadingStats.tsx`, `Register.tsx`) y los 7 archivos en `frontend/src/pages/legal/*.tsx` son *re-exports* de una sola línea que apuntan a `frontend/src/features/*/pages/*`.
  - Actualizar `frontend/src/app/router.tsx` y los tests para que importen directamente desde `@/features/<feature>` y borrar `frontend/src/pages/`.
- [x] **Eliminar los componentes duplicados en la raíz de `frontend/src/components/`:**
  - Borrar los 16 archivos puente de la raíz de `components/`:
    - `AIAssistantModal.tsx` (vive en `features/ai/components/`)
    - `AmazonAdSlot.tsx`, `BioEditor.tsx`, `CookieBanner.tsx`, `StarRating.tsx` (viven en `components/ui/`)
    - `AuthBox.tsx`, `LoginModal.tsx`, `ProtectedRoute.tsx`, `RegisterModal.tsx`, `login.tsx`, `register.tsx` (viven en `features/auth/components/`)
    - `BookReviewsSection.tsx` (vive en `features/reviews/components/`)
    - `EditProfile.tsx` (vive en `features/profile/pages/`)
    - `footer.tsx`, `header.tsx`, `logo.tsx` (viven en `components/layout/`)
  - Dejar en `frontend/src/components/` únicamente las subcarpetas reales: `audio/`, `layout/` y `ui/`.

### 5.2. Unificación de la Capa de Red (API Client) y Estado de Autenticación
- [x] **Fusionar `frontend/src/services/api.ts` en `frontend/src/api/client.ts`:**
  - Actualmente existen dos clientes HTTP configurados. Migrar cualquier interceptor o *helper* de `src/services/api.ts` hacia `src/api/client.ts`.
  - Mover `frontend/src/services/erratas.ts` a `frontend/src/features/books/services/errataService.ts` y eliminar el directorio `frontend/src/services/`.
- [x] **Unificar `frontend/src/lib/auth.ts`, `frontend/src/lib/useAuth.ts` y `frontend/src/store/auth.ts`:**
  - Consolidar toda la gestión de estado de sesión, refresco silencioso de cookies JWT y permisos de rol dentro de `frontend/src/store/auth.ts` y exportar el hook desde `frontend/src/features/auth/`.

### 5.3. Estandarización de TanStack Query y Particionado de Componentes Grandes
- [x] **Completar la cobertura de Custom Hooks con TanStack Query (`queryKeys.ts`):**
  - Actualmente `books`, `reviews` y `social` tienen carpeta `hooks/` (`useBooksQuery.ts`, `useReviewsQuery.ts`, `useSocialQuery.ts`, `useNotificationsQuery.ts`), pero `admin`, `clubs`, `discovery`, `library` y `profile` realizan llamadas directas en páginas o servicios.
  - Crear `useClubsQuery.ts`, `useDiscoveryQuery.ts`, `useLibraryQuery.ts`, `useProfileQuery.ts` y `useAdminQuery.ts` centralizando todas las claves de invalidación en `frontend/src/api/queryKeys.ts`.
- [x] **Dividir páginas monolíticas (> 350 líneas) en subcomponentes:**
  - `frontend/src/features/admin/pages/AdminDashboard.tsx`: Extraer las pestañas restantes (moderación, métricas de negocio, auditoría y usuarios) al igual que ya se hizo con `AdminAuthorClaimsTab.tsx` o `AdminSystemHealthTab.tsx`.
  - `frontend/src/features/social/pages/Home.tsx`: Separar en `FeedComposer.tsx`, `FeedFilterTabs.tsx`, `FeedActivityCard.tsx` y `TrendingSidebar.tsx`.
  - `frontend/src/features/books/pages/BookDetail.tsx`: Extraer `BookMetadataHeader.tsx`, `ReadingStatusSelector.tsx` y `SimilarBooksCarousel.tsx`.
  - `frontend/src/features/books/pages/ReadingLists.tsx`: Separar el modal de creación/edición, la vista de colaboradores y la tarjeta de lista.

### 5.4. Sincronización Automática de Tipos OpenAPI y *Code-Splitting*
- [x] **Generación automática de tipos TypeScript desde `backend/schema.yaml`:**
  - En lugar de mantener manualmente las más de 600 líneas de `frontend/src/types/api.ts`, añadir `openapi-typescript` en `frontend/package.json`:
    ```json
    "scripts": {
      "generate:types": "openapi-typescript ../backend/schema.yaml -o src/types/openapi.d.ts"
    }
    ```
  - Añadir verificación en `.github/workflows/ci-frontend.yml` para asegurar que el contrato de `schema.yaml` y el frontend nunca diverjan.
- [x] **Lazy Loading en `frontend/src/app/router.tsx`:**
  - Envolver en `React.lazy()` y `<Suspense>` las rutas pesadas o de acceso secundario: `AdminDashboard`, `ReadingStats`, `ChallengesPage`, `ClubDetailPage`, `Chat` y las páginas legales.

---

## 6. Fase 5: Reestructuración y Optimización de la Suite de Testing y QA

La carpeta `backend/tests/` cuenta con una cobertura envidiable, pero su organización cronológica (`test_phase01` a `test_phase72`, `test_phase_a2` a `test_phase_e3`, `test_sprint1` a `test_sprint20`) hace difícil localizar y mantener los tests por dominio funcional.

### 6.1. Nueva Taxonomía de Tests por Dominio en `backend/tests/`
- [x] **Eliminar archivos vacíos de Django:**
  - Borrar `backend/users/tests.py` y `backend/messages_app/tests.py`.
- [x] **Reorganizar los 95+ archivos de `backend/tests/` en subdirectorios semánticos:**
  ```text
  backend/tests/
  ├── conftest.py
  ├── factories/                  # Factory Boy para User, Book, Review, Club, etc.
  ├── fixtures/
  │   └── goodreads_sample.csv
  ├── catalog/                    # Dominio de libros, ingesta, deduplicación y búsqueda
  │   ├── test_models_and_constraints.py      (absorbe phase01, a3, domain_models)
  │   ├── test_catalog_deduplication.py       (absorbe sprint4)
  │   ├── test_csv_and_goodreads_import.py    (absorbe phase55)
  │   ├── test_external_providers.py          (absorbe amazon, services_providers, genre_hydration)
  │   └── test_unified_search_and_trigrams.py (absorbe phase06, phase48, search_postgres)
  ├── recommendations_and_ai/     # IA, pgvector y motor de recomendaciones
  │   ├── test_embeddings_pgvector.py         (absorbe phase25_embeddings)
  │   ├── test_recommendation_pipeline.py     (absorbe phase07, 24, 49, 50, 51, 52, sprint17)
  │   ├── test_ai_assistant_and_tools.py      (absorbe phase24_product_ai, phase26_ai)
  │   ├── test_multimodal_ai.py               (absorbe sprint20)
  │   └── test_ai_security_and_guardrails.py  (absorbe phase05, phase27_ai_security)
  ├── social_and_community/       # Reseñas, listas, muros, clubes y notificaciones
  │   ├── test_reviews_and_comments.py        (absorbe review_social, d3)
  │   ├── test_smart_feed_and_trending.py     (absorbe phase22_social_feed, phase23_trending, phase53, social_feed)
  │   ├── test_reading_lists_and_collab.py    (absorbe phase21, sprint10)
  │   ├── test_reading_clubs.py               (absorbe sprint9)
  │   ├── test_notifications.py               (absorbe phase23_notifications)
  │   └── test_social_sharing.py              (absorbe sprint16)
  ├── creators_and_commerce/      # Autores, eventos, newsletters, audiolibros y marketplace
  │   ├── test_author_portal_and_events.py    (absorbe sprint3, 11, 12, 13, phase32_multiauthor, verified_pubs)
  │   ├── test_audiobooks_and_tts.py          (absorbe sprint18)
  │   └── test_marketplace_and_monetization.py(absorbe phase31_monetization, sprint19)
  ├── reader_experience/          # Gamificación, estadísticas y onboarding
  │   ├── test_gamification_and_challenges.py (absorbe phase54, sprint14)
  │   ├── test_reading_stats.py               (absorbe phase22_reading_stats, sprint15)
  │   └── test_onboarding_and_discovery.py    (absorbe phase19, phase20)
  ├── messaging/                  # Chat en tiempo real
  │   └── test_chat_websockets_and_persistence.py (absorbe chat_websockets, phase04)
  ├── security_and_privacy/       # Auth, permisos, moderación, UGC y legal
  │   ├── test_auth_jwt_and_cookies.py        (absorbe auth_security, phase03, phase47, a2, sprint1)
  │   ├── test_privacy_and_visibility.py      (absorbe permissions_privacy, users_privacy, phase02, phase17, d1)
  │   ├── test_moderation_and_ugc_safety.py   (absorbe phase16, 29, 58, 59, sprint7)
  │   ├── test_media_and_image_security.py    (absorbe phase28_media, phase60)
  │   └── test_legal_and_gdpr.py              (absorbe phase18, sprint8)
  └── platform_and_infra/         # Caché, concurrencia, idempotencia, backups y contratos API
      ├── test_caching_and_invalidation.py    (absorbe caching, phase08, phase65)
      ├── test_transactions_and_concurrency.py(absorbe phase62, 63, 64, 31_soft_delete)
      ├── test_database_and_query_budgets.py  (absorbe database_performance, phase09, 33_query, 43, c1_query)
      ├── test_backups_and_dr.py              (absorbe phase15, 66, 67, b2)
      ├── test_observability_and_health.py    (absorbe healthcheck, phase14, 42, 46, b3)
      └── test_openapi_and_error_contracts.py (absorbe phase32_coherent, 33_openapi, 61_error)
  ```

### 6.2. Aceleración de Ejecución de Pytest
- [x] Incorporar `pytest-xdist` en `backend/requirements.txt` y `backend/pytest.ini` (`-n auto --dist loadscope`) para paralelizar la ejecución de los tests en CI (`.github/workflows/ci-backend.yml`), reduciendo el tiempo de pipeline en un $60\%$.
- [x] Ampliar `frontend/e2e/critical-flows.spec.ts` en una suite modular de Playwright:
  - `e2e/auth-and-onboarding.spec.ts`
  - `e2e/library-and-import.spec.ts`
  - `e2e/clubs-and-social.spec.ts`
  - `e2e/author-portal.spec.ts`

---

## 7. Fase 6: Rendimiento en PostgreSQL, Redis, Celery y WebSockets

### 7.1. Índices HNSW en `pgvector` y Optimización de Consultas SQL
- [ ] **Crear índice HNSW en `BookEmbedding`:**
  - En tablas vectoriales que superan los $10,000$ libros, una búsqueda exacta de vecino más cercano tiene complejidad $O(N)$. Añadir una migración con índice `HnswIndex` (`m=16`, `ef_construction=64`, `vector_cosine_ops`) para búsquedas aproximadas en tiempo logarítmico $O(\log N)$ con un *recall* $> 98\%$.
- [ ] **Desnormalización controlada de métricas de `Book`:**
  - Añadir campos `ratings_count` (`PositiveIntegerField(default=0)`) y `average_rating` (`DecimalField(max_digits=3, decimal_places=2, default=0.00)`) indexados directamente en el modelo `Book` si aún se calculan con `Avg()` al vuelo en ciertos listados, actualizándolos de forma atómica con expresiones `F()` al crear/editar/borrar reseñas.
- [ ] **Connection Pooling en Producción (`docker-compose.prod.yml`):**
  - Añadir un servicio ligero de **PgBouncer** (modo `transaction`) entre los contenedores de Gunicorn/Daphne/Celery y PostgreSQL para evitar el agotamiento de conexiones bajo picos de tráfico o *workers* asíncronos.

### 7.2. Aislamiento de Colas en Celery y Tareas Periódicas (Celery Beat)
- [ ] **Verificar enrutamiento estricto en `backend/mybookconnect/celery.py` y `settings.py`:**
  - Cola `realtime_priority`: Notificaciones, tickets y correos transaccionales de autenticación (latencia objetivo $< 2\text{ s}$).
  - Cola `ai_and_embeddings`: Generación de embeddings, consultas a LLMs y procesamiento multimodal (con *rate-limit* y `acks_late=True`).
  - Cola `catalog_batch`: Importaciones masivas de CSV Goodreads, deduplicación y enriquecimiento con Google Books / OpenLibrary / Amazon.
  - Cola `ops_maintenance`: Backups programados, evaluación de alertas (`evaluate_system_alerts`) y limpieza de registros en `soft_delete`.

### 7.3. Endurecimiento de WebSockets (`backend/messages_app/consumers.py`)
- [ ] **Control de *Backpressure* y *Heartbeat*:**
  - Implementar tramas de `ping/pong` cada $30\text{ s}$ entre `frontend/src/hooks/useChatWebSocket.ts` y `consumers.py` para detectar conexiones zombis.
  - Validar la expiración de permisos y bloqueos de usuarios (`user.blocked_users`) no solo en el `connect()` del WebSocket, sino también en tiempo real si un usuario bloquea a otro mientras el socket ya está abierto (enviando un evento de cierre inmediato al canal del grupo).

---

## 8. Fase 7: Seguridad Defensiva Avanzada, Privacidad y Cumplimiento Legal

### 8.1. Blindaje de Privacidad a Nivel de `QuerySet` (`VisibleToUserManager`)
- [ ] **Reforzar `backend/users/privacy_service.py`:**
  - Crear un `QuerySet` personalizado reutilizable (`PrivacyAwareQuerySet`) con el método `.visible_to(request_user)` para los modelos `UserBook`, `Review`, `ReadingList`, `Activity` y `UserPost`.
  - Garantizar mediante un test de arquitectura automatizado que ningún `ViewSet` público devuelva instancias de estos modelos sin invocar `.visible_to(self.request.user)`.

### 8.2. Cabeceras de Seguridad en Nginx y Sincronización de *Rate Limiting*
- [ ] **Endurecer `frontend/nginx.conf` y `frontend/nginx.ssl.conf.template`:**
  - Definir directivas `limit_req_zone` en Nginx para `/api/auth/` y `/api/ai/` como primera línea de defensa en capa 7 antes de que las peticiones lleguen al *worker* de Python.
  - Refinar la cabecera `Content-Security-Policy` (CSP) eliminando `unsafe-inline` en scripts y restringiendo `connect-src` e `img-src` a los dominios autorizados de proveedores de portadas.

### 8.3. Automatización Completa del Ciclo de Vida GDPR / LOPDGDD
- [ ] **Purga definitiva tras periodo de gracia (`deleted_at`):**
  - Añadir una tarea periódica en `backend/users/tasks.py` que anonimice y elimine físicamente las cuentas cuyo `deleted_at` supere los 30 días de gracia estipulados en `DeletionPolicy.tsx`, conservando únicamente los registros agregados no identificables.

---

## 9. Fase 8: Evolución de Producto y Monetización Real

Una vez saneada la base técnica en las Fases 1 a 7, el producto está listo para activar las palancas de crecimiento y negocio ya modeladas en la base de datos:

- [ ] **Integración de Pasarela de Pagos Real (Stripe Billing & Checkout):**
  - Conectar el modelo `UserSubscription` (`backend/users/migrations/0025_usersubscription.py`) y los anuncios patrocinados de autores (`0041_authorannouncement_moderation_and_paid.py`) con **Stripe Webhooks** firmados (`STRIPE_WEBHOOK_SECRET`), utilizando `backend/mybookconnect/idempotency.py` para procesar eventos `checkout.session.completed` y `customer.subscription.updated`.
- [ ] **Progressive Web App (PWA) y Modo Offline de Lectura:**
  - Añadir `vite-plugin-pwa` en `frontend/vite.config.js` para permitir instalar MyBookSocial en iOS y Android, cacheando la estantería activa del lector y permitiendo registrar avances de lectura (`DailyReadingLog`) sin conexión con sincronización diferida (*Background Sync*).
- [ ] **API Pública para Editoriales y Widgets Embebibles:**
  - Permitir que autores verificados y editoriales (`Publisher`) generen un *widget* interactivo de su libro en MyBookSocial para incrustarlo en sus blogs o webs personales, atrayendo tráfico orgánico de vuelta a la plataforma.

---

## 10. Planificación por Sprints y Métricas de Éxito (SLAs / KPIs)

### Calendario de Ejecución Recomendado (6 Sprints Técnicos)

| Sprint | Foco Principal | Entregables Clave |
| :--- | :--- | :--- |
| **Sprint R1** | **Higiene de Git y Multimedia (Fase 1)** | `backend/media/` fuera de Git, deduplicación $\text{SHA-256}$ WebP activa, logos frontend optimizados, scripts duplicados eliminados. |
| **Sprint R2** | **Limpieza de Frontend (Fase 4)** | Eliminación de `src/pages/` y 16 shims en `src/components/`, fusión de `api/client.ts`, generación automática de tipos desde `schema.yaml`. |
| **Sprint R3** | **Consolidación de IA y Recomendaciones (Fase 3)** | Eliminación de `mybookconnect/ai_service.py`, unificación de embeddings, pipeline de recomendaciones limpio e índice HNSW en `pgvector`. |
| **Sprint R4** | **Desacoplamiento de `books` — Parte 1 (Fase 2)** | Extracción sin downtime (`SeparateDatabaseAndState`) de `clubs`, `gamification` y comandos `ops`. |
| **Sprint R5** | **Desacoplamiento de `books` — Parte 2 (Fase 2)** | Extracción de `audiobooks`, `marketplace` y `authors_portal`. `books` queda reducido exclusivamente al dominio de catálogo y lectura. |
| **Sprint R6** | **Reorganización de Tests y Escala (Fases 5, 6 y 7)** | Reestructuración de los 95 archivos de test por dominio, paralelización con `pytest-xdist`, PgBouncer en producción y auditoría CSP/GDPR. |

### Indicadores Clave de Rendimiento (KPIs Técnicos de Aceptación)

1. **Tamaño del Repositorio Git y Clone Time:** Reducción del peso del archivo `.zip` / clonado en $> 80\%$ tras purgar `backend/media/` y optimizar activos PNG/ICO.
2. **Latencia de API ($p_{95}$ y $p_{99}$):**
   - Endpoints de lectura y *Smart Feed*: $p_{95} < 120\text{ ms}$, $p_{99} < 250\text{ ms}$.
   - Búsqueda unificada y recomendaciones vectoriales con HNSW: $p_{95} < 180\text{ ms}$.
   - Presupuesto estricto de consultas SQL por petición HTTP: $\le 6\text{ queries}$ en vistas de listado ($0$ problemas $N+1$).
3. **Tamaño del Bundle Inicial JS (Frontend):** Chunk principal $< 180\text{ KB}$ (gzipped) tras aplicar `React.lazy()` en `router.tsx`.
4. **Tiempo de Ejecución de CI/CD:** Suite completa de backend (`pytest -n auto`) completada en $< 90\text{ segundos}$.