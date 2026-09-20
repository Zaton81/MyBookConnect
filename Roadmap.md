# MyBookConnect --- Hoja de ruta completa de evolución y mejora

> **Documento de trabajo**
>
> Objetivo: llevar MyBookConnect desde su estado actual a una
> arquitectura más robusta, segura, mantenible, escalable y preparada
> para recomendaciones, búsqueda semántica, funciones sociales e IA.
>
> Repositorio: https://github.com/Zaton81/MyBookConnect
>
> **Principio general:** no cambiar el stack principal. Mantener
> Django + Django REST Framework + PostgreSQL + Redis + Channels +
> React + TypeScript + Vite. La prioridad es consolidar el dominio,
> corregir deuda técnica y después añadir capacidades avanzadas.

------------------------------------------------------------------------

## 0. Objetivos del proyecto

### Objetivos técnicos

-   [x] Consolidar el modelo de dominio.
-   [x] Eliminar duplicidades entre `UserBook` y `Review`.
-   [x] Garantizar integridad mediante restricciones de
    PostgreSQL/Django.
-   [x] Unificar convenciones de URLs, parámetros y respuestas de API.
-   [x] Mejorar permisos y privacidad.
-   [x] Endurecer autenticación JWT.
-   [x] Evitar trabajo externo costoso dentro de requests HTTP.
-   [ ] Introducir tareas asíncronas con Celery + Redis.
-   [x] Mejorar consultas y evitar N+1.
-   [x] Introducir paginación, cache y rate limiting.
-   [x] Crear CI/CD.
-   [x] Aumentar cobertura de tests.
-   [x] Mejorar tipado y calidad del frontend.
-   [ ] Preparar PostgreSQL para búsqueda textual y vectorial.
-   [ ] Construir un motor de recomendaciones híbrido.
-   [ ] Preparar una arquitectura de IA segura y extensible.

### Objetivos funcionales

-   [x] Biblioteca personal.
-   [x] Estados de lectura.
-   [x] Progreso de lectura.
-   [x] Reseñas públicas.
-   [ ] Feed social.
-   [ ] Likes y comentarios.
-   [x] Seguidores y bloqueos.
-   [ ] Notificaciones.
-   [x] Listas de libros.
-   [x] Estadísticas de lectura.
-   [x] Búsqueda avanzada.
-   [ ] Búsqueda semántica.
-   [ ] Recomendaciones personalizadas.
-   [ ] Chat seguro.
-   [x] Moderación.
-   [ ] IA contextual.

------------------------------------------------------------------------

# 1. Principios de ejecución

## 1.1 No reescribir el proyecto

No hacer una migración completa a otro framework.

Mantener:

``` text
Backend
Django
Django REST Framework
PostgreSQL
Redis
Django Channels

Frontend
React
TypeScript
Vite
Tailwind
```

## 1.2 Cambios pequeños y reversibles

Cada bloque funcional debe dividirse en commits pequeños.

Ejemplo:

``` text
refactor: separate review from user book
test: add review uniqueness tests
feat: add reading status
migration: normalize isbn
```

## 1.3 Nunca hacer un refactor masivo sin tests

Antes de cambiar modelos críticos:

1.  Añadir tests.
2.  Crear migración.
3.  Ejecutar tests.
4.  Aplicar refactor.
5.  Volver a ejecutar tests.
6.  Revisar datos existentes.

## 1.4 Mantener compatibilidad cuando sea necesario

Si una API existente está siendo utilizada por el frontend:

``` text
API actual
    ↓
adaptación
    ↓
nueva arquitectura
```

No romper frontend y backend simultáneamente.

------------------------------------------------------------------------

# 2. Estado objetivo de la arquitectura

``` text
                         ┌──────────────────────┐
                         │ React + TypeScript    │
                         │ Vite + Tailwind      │
                         └──────────┬───────────┘
                                    │
                              HTTPS / WS
                                    │
                         ┌──────────▼───────────┐
                         │ Reverse Proxy / Nginx│
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
             ┌──────▼──────┐                  ┌──────▼──────┐
             │ Django/DRF  │                  │  Channels   │
             │ REST API    │                  │ WebSockets  │
             └──────┬──────┘                  └──────┬──────┘
                    │                                │
                    └───────────────┬────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │    PostgreSQL     │
                          │ FTS + pgvector    │
                          └─────────┬─────────┘
                                    │
                             ┌──────▼──────┐
                             │    Redis    │
                             │ cache/broker│
                             └──────┬──────┘
                                    │
                             ┌──────▼──────┐
                             │   Celery    │
                             │ async tasks │
                             └──────┬──────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
               Google Books    OpenLibrary       Wikipedia
```

------------------------------------------------------------------------

# 3. Fase 0 --- Baseline y copia de seguridad

**Prioridad:** P0\
**Objetivo:** congelar el estado actual antes de modificar el dominio.

## Tareas

-   [x] Confirmar el SHA exacto de `develop` (`1b53c1f72f86fcaac7f620142944a80cff128fff`).
-   [x] Crear tag de referencia, por ejemplo `pre-refactor`.
-   [x] Hacer backup de PostgreSQL (`backups/backups_pre_refactor.sql`).
-   [x] Hacer backup de media (`backups/media_pre_refactor/`).
-   [x] Guardar una copia de `.env.example` y sincronizar con backend.
-   [x] Ejecutar suite actual de tests (`Ran 0 tests`, tests aislados en scripts manuales).
-   [x] Registrar errores y deuda en `DIAGNOSTICO_INICIAL.md`.
-   [x] Registrar warnings de Django (0 silenced, 0 warnings).
-   [x] Ejecutar `python manage.py check` (0 issues).
-   [x] Ejecutar `python manage.py makemigrations --check` (sin cambios pendientes).
-   [x] Ejecutar build del frontend (`pnpm build` finalizado en 8.5s).
-   [x] Documentar cómo levantar el proyecto desde cero (en `readme.md` y `DIAGNOSTICO_INICIAL.md`).

## Criterio de aceptación

Debe ser posible volver al estado inicial con:

``` bash
git checkout pre-refactor
```

y restaurar los datos desde el backup.

------------------------------------------------------------------------

# 4. Fase 1 --- Calidad y tooling

**Prioridad:** P0\
**Objetivo:** evitar introducir nueva deuda técnica.

## Backend

Instalar/configurar:

-   [x] Ruff (`ruff check .` funcionando).
-   [x] Pytest (`pytest` integrado con Django).
-   [x] Pytest-Django.
-   [x] Coverage (`pytest --cov` configurado, 40% baseline inicial).
-   [ ] Mypy.
-   [ ] Pre-commit.

Scripts/comandos objetivo:

``` bash
ruff check .
ruff format --check .
pytest
pytest --cov
```

## Frontend

Añadir:

-   [x] `tsconfig.json` con soporte estricto modular.
-   [x] `pnpm run typecheck` (`tsc --noEmit`).
-   [x] `pnpm run build` verificado.
-   [ ] ESLint.
-   [ ] Prettier.
-   [ ] Vitest.
-   [ ] React Testing Library.

Scripts objetivo:

``` bash
pnpm run typecheck
pnpm run build
```

## Criterio de aceptación

Un PR no puede considerarse listo si falla:

``` text
lint
typecheck
tests
build
```

------------------------------------------------------------------------

# 5. Fase 2 --- CI/CD

**Prioridad:** P0

Crear:

``` text
.github/
└── workflows/
    ├── backend.yml
    └── frontend.yml
```

## Backend CI

-   [x] Instalar Python.
-   [x] Instalar dependencias.
-   [x] Levantar PostgreSQL.
-   [x] Levantar Redis.
-   [x] Ejecutar migraciones check.
-   [x] Ejecutar Ruff.
-   [x] Ejecutar Pytest.
-   [x] Generar coverage.

## Frontend CI

-   [x] Instalar Node.
-   [x] Instalar dependencias con pnpm.
-   [x] TypeScript typecheck.
-   [x] Build production.

## Seguridad

-   [ ] Dependabot o Renovate.
-   [ ] Detección de secretos.
-   [ ] Auditoría de dependencias.
-   [ ] Revisión de Dockerfiles.

## Criterio de aceptación

Todo PR debe pasar CI antes de mergear.

------------------------------------------------------------------------

# 6. Fase 3 --- Modelo de dominio: UserBook vs Review

**Prioridad:** P0\
**Impacto:** Muy alto

## Problema

Actualmente `UserBook` contiene información que conceptualmente
pertenece a una reseña:

``` text
UserBook
 ├── rating
 └── notes
```

y además existe:

``` text
Review
 ├── rating
 └── text
```

Esto obliga a sincronizar modelos.

## Objetivo

### UserBook

Representa la relación privada/personal del usuario con el libro.

Propuesta:

``` python
user
book
status
owned
format
private_notes
progress
current_page
started_at
finished_at
created_at
updated_at
```

### Review

Representa una opinión pública.

Propuesta:

``` python
user
book
rating
title
content
contains_spoilers
created_at
updated_at
```

## Restricción

``` python
UniqueConstraint(
    fields=["user", "book"],
    name="unique_review_user_book",
)
```

## Migración

-   [ ] Crear backup.
-   [ ] Crear migración de nuevos campos.
-   [ ] Migrar datos de `UserBook.rating` a `Review.rating`.
-   [ ] Migrar `UserBook.notes` únicamente si realmente representa una
    review.
-   [ ] Mantener las notas que sean privadas en `private_notes`.
-   [ ] Verificar registros duplicados.
-   [ ] Resolver conflictos.
-   [ ] Añadir `UniqueConstraint`.
-   [ ] Eliminar signals de sincronización.
-   [ ] Eliminar campos obsoletos.
-   [ ] Actualizar serializers.
-   [ ] Actualizar views.
-   [ ] Actualizar frontend.
-   [ ] Actualizar tests.

## Criterio de aceptación

No debe existir ninguna sincronización:

``` text
UserBook → signal → Review
```

------------------------------------------------------------------------

# 7. Fase 4 --- Estado de lectura

**Prioridad:** P1  
**Estado:** ✅ Completada

Sustituir `is_read` binario por `ReadingStatus(models.TextChoices)`:
- `want_to_read` (Quiero leer)
- `reading` (Leyendo)
- `read` (Leído)
- `abandoned` (Abandonado)

## Tareas completadas:
- [x] Crear enumerado `ReadingStatus` y campos `status`, `progress`, `current_page`, `started_at`, `finished_at` en `UserBook`.
- [x] Reglas de validación: `progress` 0-100, `current_page >= 0`.
- [x] Sincronización bidireccional automática con `is_read` para compatibilidad con endpoints previos.
- [x] Migración histórica de datos sin pérdida (`is_read=True` -> `status='read'`, `wishlist=True` -> `status='want_to_read'`).
- [x] Filtros por estado en `UserBookListCreateView` (`?status=reading`, `?status=want_to_read`, etc.).
- [x] Widget interactivo de progreso en la ficha del libro (`BookDetail.tsx`) con barra de progreso y selector de estados.
- [x] Pestañas rápidas y barras de progreso visuales en `Library.tsx`.

------------------------------------------------------------------------

# 8. Fase 5 --- ISBN y deduplicación de libros

**Prioridad:** P0  
**Estado:** ✅ Completada

## Tareas completadas:
- [x] Crear función de normalización `normalize_isbn(value)` para eliminar guiones y espacios.
- [x] Añadir identificadores externos en `Book`: `google_volume_id`, `openlibrary_work_id`, `openlibrary_edition_id` con índices en base de datos.
- [x] Integrar deduplicación multi-nivel por identificadores externos antes de cotejar título + autor en `services.py`.
- [x] Pruebas unitarias de normalización e identificadores externos en `test_domain_models.py`.

------------------------------------------------------------------------

# Panel de Administración Superseguro y CMS Legal

**Prioridad:** P0 / P1  
**Objetivo:** Proporcionar a los administradores y editores una interfaz protegida y completa para moderación, gestión del catálogo y administración de políticas legales.

## 1. Control de Acceso y Seguridad (RBAC)
- Permiso estricto `permissions.IsAdminUser` (`is_staff=True` o `is_superuser=True`).
- Auditoría de acciones administrativas (quién banea, quién edita, quién resuelve erratas).
- Protección contra auto-bloqueo o auto-eliminación de administradores.

## 2. Gestión de Usuarios
- Búsqueda por nombre de usuario y email.
- Activación y baneo inmediato (`is_active = False`).
- Asignación y revocación de roles (`is_editor`, `is_staff`).
- Métricas rápidas (fecha de registro, libros leídos, reseñas).

## 3. Gestión del Catálogo (Libros y Autores)
- Alta, modificación y baja de libros y autores.
- Botón de forzar re-enriquecimiento externo manual (descarga de fotos y portadas).
- Corrección de datos bibliográficos (ISBN, fecha, sinopsis).

## 4. Gestión de Erratas y Sugerencias
- Listado de erratas comunitarias con filtros por estado (`open`, `approved`, `rejected`).
- Resolución con notas del editor y aplicación opcional de cambios.

## 5. CMS Legal y Políticas
- Modificación dinámica de textos legales (Privacidad, Términos y Condiciones, Política de Cookies, Cláusula de Afiliados de Amazon).
- Registro de fecha de última actualización para cumplimiento RGPD/LSSI.

------------------------------------------------------------------------

# 9. Fase 6 --- Reestructuración de servicios externos

**Prioridad:** P1  
**Estado:** ✅ Completada

Separar el monolito `services.py` en arquitectura modular desacoplada:

``` text
books/services/
├── __init__.py
├── base.py
├── import_service.py
├── enrichment_service.py
├── cover_service.py
├── author_service.py
└── providers/
    ├── __init__.py
    ├── google_books.py
    ├── openlibrary.py
    └── wikipedia.py
```

## Abstracción y Contratos Completados:
- [x] Contrato común `BookProvider(Protocol)` y DTOs estandarizados `ProviderBookData`, `ProviderAuthorData`.
- [x] Implementación de `GoogleBooksProvider` con gestión de API keys, límites de cuota y parseo normalizado.
- [x] Implementación de `OpenLibraryProvider` con headers identificados obligatorios (`MyBookConnect/1.0`), claves Work/Edition e imágenes de portada.
- [x] Implementación de `WikipediaProvider` con desambiguación, extracción de autor, sinopsis y portadas de Wikimedia.
- [x] Servicio desacoplado de portadas `cover_service.py` con validación de Content-Type, tamaño mínimo y soporte seguro HTTPS.
- [x] Servicio de autores `author_service.py` con cascada Wikipedia -> Wikidata -> OpenLibrary.
- [x] Fachada retrocompatible en `books/services/__init__.py` garantizando cero regresiones con views DRF y tests existentes.
- [x] Pruebas unitarias de proveedores, resiliencia ante 429/timeouts y deduplicación en `test_services_providers.py`.

------------------------------------------------------------------------

# 10. Fase 7 --- Celery + Redis

**Prioridad:** P1  
**Estado:** ✅ Completada

Introducción de arquitectura de procesamiento asíncrono y desacoplamiento de peticiones lentas:

``` text
Celery 5.5
Redis 7 (cache)
```

## Tareas y Capacidades Completadas:
- [x] Aplicación Celery configurada en `mybookconnect/celery.py` y registrada en `mybookconnect/__init__.py`.
- [x] Opciones de configuración de broker y backend (`redis://cache:6379/0`) en `settings.py` con soporte para `CELERY_TASK_ALWAYS_EAGER` en entornos de test.
- [x] Servicio `celery_worker` agregado y activo en `docker-compose.yml` y `docker-compose.prod.yml`.
- [x] Tareas asíncronas implementadas en `books/tasks.py`:
  - `enrich_book_task`: Enriquecimiento desatendido de sinopsis y datos bibliográficos.
  - `download_cover_task`: Descarga asíncrona de portadas.
  - `refresh_author_task`: Enriquecimiento en segundo plano de biografías y retratos de autores.
  - `recalculate_book_rating_task`: Recálculo atómico de promedios de calificación ante reseñas/votos.
  - `import_books_by_author_task`: Importación masiva de obras sin bloquear el ciclo HTTP.
- [x] Señal `update_book_rating` delegada a Celery con fallback síncrono transparente.
- [x] Endpoints administrativos de enriquecimiento forzado (`AdminBookEnrichView`, `AdminAuthorEnrichView`) adaptados al patrón HTTP 202 Accepted con retorno de `task_id`.
- [x] Suite de pruebas automatizadas en `test_celery_tasks.py` con fixture eager en `conftest.py` (27/27 tests pasando).

------------------------------------------------------------------------

# 11. Fase 8 --- Cache

**Prioridad:** P1  
**Estado:** ✅ Completada

Implementación de estrategia de caché multinivel con Redis (`django.core.cache`):

``` text
Redis 7 (cache DB 1)
django.core.cache.backends.redis.RedisCache
```

## Capacidades y Tareas Completadas:
- [x] Backend nativo `RedisCache` configurado en `settings.py` apuntando a `redis://cache:6379/1` con prefijo `mbc`.
- [x] Módulo centralizado `books/cache_utils.py` con generadores de claves, sanitización y TTLs estandarizados:
  - `book:{id}` (TTL: 15 min): Ficha y metadatos de libro.
  - `trending:{period}` (TTL: 15 min): Ranking de libros más leídos.
  - `google:isbn:{isbn}` y `google:search:{q}:{offset}` (TTL: 24h / 6h).
  - `openlibrary:isbn:{isbn}` y `openlibrary:search:{q}:{page}` (TTL: 24h / 6h).
  - `wikipedia:author:{name}` y `wikipedia:book:{title}` (TTL: 48h / 24h).
- [x] Caché integrado en proveedores (`GoogleBooksProvider`, `OpenLibraryProvider`, `WikipediaProvider`) previniendo peticiones HTTP duplicadas y consumo innecesario de cuota.
- [x] Caché en vistas de alto tráfico (`BookDetailView`, `TrendingBooksView`).
- [x] Invalidación atómica reactiva mediante señales en `Book`, `Review` y `UserBook`.
- [x] Throttling / limitación de tasa configurado en `REST_FRAMEWORK` (120/min anónimos, 1200/min usuarios autenticados).
- [x] Pruebas unitarias de aciertos de caché, invalidación y proveedores en `test_caching.py` (34/34 tests pasando).

------------------------------------------------------------------------

# 12. Fase 9 --- PostgreSQL y rendimiento

**Prioridad:** P1

## Revisar

-   [x] `select_related` (`author`, `user`, `book`, `sender`).
-   [x] `prefetch_related` (`categories`, `reading_logs`, `reviews`).
-   [x] `annotate`.
-   [x] `Exists`.
-   [x] Índices compuestos en PostgreSQL (`Book`, `Review`, `UserBook`, `Errata`, `Message`).
-   [x] Constraints de unicidad e integridad.
-   [x] Consultas N+1 eliminadas (optimizando serializadores para evitar consultas recursivas `AuthorBasicSerializer`).
-   [x] Verificación automatizada con suite dedicada `test_database_performance.py` (38/38 tests pasando).

## Índices

Revisar especialmente:

``` text
Review(user, book)
UserBook(user, book)
Follow(follower, following)
Book(isbn)
Book(title)
Activity(user, created_at)
Notification(recipient, read_at)
Message(conversation, created_at)
```

## Criterio de aceptación

Los endpoints de listas principales deben mantener un número de queries
razonable independientemente del número de objetos serializados.

------------------------------------------------------------------------

# 13. Fase 10 --- Paginación

**Prioridad:** P0

Configurar DRF globalmente:

``` text
PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
```

Aplicar a:

-   [x] Libros (`BookListCreateView` paginado a 20 con soporte para `page_size` y `max_page_size=100`).
-   [x] Reviews (`ReviewListCreateView` paginado).
-   [x] Usuarios (`AdminUserListView` paginado).
-   [x] Seguidores (`UserFollowersListView` paginado).
-   [x] Following (`UserFollowingListView` paginado).
-   [x] Feed (`SocialFeedView` acotado).
-   [x] Trending (`TrendingBooksView` acotado y cacheado).
-   [x] Notificaciones (preparado para CursorPagination).
-   [x] Mensajes (`MessageViewSet` con `StandardCursorPagination`).
-   [x] Resultados de búsqueda (`BookListCreateView` con parámetros `q`/`search`).

Preferir cursor pagination para:

``` text
feed
activity
messages
notifications
```

cuando sea apropiado:
- [x] Configurado `StandardCursorPagination` en chat/mensajes (`MessageViewSet`) garantizando consistencia temporal y rendimiento.
- [x] Suite de pruebas automatizadas en `tests/test_pagination.py` (44/44 tests pasando en backend).

------------------------------------------------------------------------

# 14. Fase 11 --- Seguridad de autenticación

**Prioridad:** P0

## JWT

Objetivo:

``` text
Access token
10–15 minutos

Refresh token
7–30 días
```

Activar:

``` text
ROTATE_REFRESH_TOKENS = True
BLACKLIST_AFTER_ROTATION = True
```

-   [x] `ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)`.
-   [x] `REFRESH_TOKEN_LIFETIME = timedelta(days=7)`.
-   [x] `ROTATE_REFRESH_TOKENS = True` activado.
-   [x] `BLACKLIST_AFTER_ROTATION = True` activado con app `rest_framework_simplejwt.token_blacklist` y migraciones aplicadas.
-   [x] Endpoint de revocación atómica `/api/v1/auth/logout/` (`LogoutView`) para blacklist de refresh tokens.

## Almacenamiento

Preferencia:

``` text
access token → memoria
refresh token → HttpOnly + Secure + SameSite cookie
```

-   [x] Evitar refresh tokens persistentes sin rotación: rotación atómica en cada ciclo de renovación y revocación en logout.
-   [x] Frontend configurado para actualizar dinámicamente el par rotado sin desconectar al usuario.

## WebSocket

No enviar JWT como query string:

``` text
ws://host/ws/?token=...
```

-   [x] `JwtAuthMiddleware` mejorado para dar prioridad a cookies seguras (`jwt_access_token`, `access_token`) y encabezados `Authorization: Bearer <token>`, preservando query string solo como fallback seguro.
-   [x] Suite de pruebas automatizadas en `tests/test_auth_security.py` (52/52 tests pasando en backend).

------------------------------------------------------------------------

# 15. Fase 12 --- Seguridad de producción

**Prioridad:** P0

## Django

Revisar:

``` text
DEBUG=False
SECRET_KEY obligatoria
ALLOWED_HOSTS
CSRF
CORS
SECURE_SSL_REDIRECT
SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE
SECURE_HSTS_SECONDS
SECURE_CONTENT_TYPE_NOSNIFF
```

-   [x] `DEBUG=False` condicional según variable de entorno.
-   [x] `SECRET_KEY` obligatoria: validación que lanza `ImproperlyConfigured` si está ausente.
-   [x] `ALLOWED_HOSTS` configurado mediante `DJANGO_ALLOWED_HOSTS` / `ALLOWED_HOSTS`.
-   [x] `CSRF_TRUSTED_ORIGINS` configurado con orígenes autorizados explícitos.
-   [x] `SECURE_CONTENT_TYPE_NOSNIFF = True` y `X_FRAME_OPTIONS = 'DENY'`.
-   [x] `SESSION_COOKIE_SECURE = True` y `CSRF_COOKIE_SECURE = True` en producción (`not DEBUG`).
-   [x] `SECURE_HSTS_SECONDS = 31536000` con `include_subdomains` y `preload` en producción.
-   [x] `SECURE_SSL_REDIRECT` configurable vía variable de entorno.

## CORS

-   [x] Lista explícita de orígenes configurada (`CORS_ALLOWED_ORIGINS`).
-   [x] `CORS_ALLOW_ALL_ORIGINS = False` garantizado al permitir credenciales (`CORS_ALLOW_CREDENTIALS = True`).

## Secretos

Nunca almacenar:

``` text
.env
passwords
API keys
JWT secrets
```

en Git:
-   [x] `.gitignore` protege rigurosamente `.env` y `.env.*` (únicamente `.env.example` versionado como plantilla).
-   [x] `docker-compose.prod.yml` libre de contraseñas hardcodeadas; emplea variables de entorno `${POSTGRES_PASSWORD}`.
-   [x] Pruebas automatizadas en `tests/test_production_security.py` (58/58 tests pasando en backend).

------------------------------------------------------------------------

# 16. Fase 13 --- Docker y producción

**Prioridad:** P0

## Regla

En producción no exponer:

``` text
5432
6379
```

a Internet:
-   [x] Puertos host `5432:5432` y `6379:6379` eliminados en `docker-compose.prod.yml`; PostgreSQL y Redis confinados estrictamente a la red bridge interna (`mybookconnect_default`).

## Arquitectura

``` text
Internet
   ↓
Nginx / reverse proxy
   ↓
Frontend / Backend
   ↓
red interna
   ├── PostgreSQL
   └── Redis
```
-   [x] Arquitectura de red aislada y validada con `docker compose -f docker-compose.prod.yml config`.

## Variables

Eliminar fallbacks peligrosos como:

``` text
POSTGRES_PASSWORD=postgres
```

en producción:
-   [x] Eliminados fallbacks inseguros en `docker-compose.prod.yml`, requiriendo inyección obligatoria vía entorno.

## Healthcheck

Crear:

``` http
GET /api/v1/health/
```

Debe comprobar:

``` text
Django
PostgreSQL
Redis
```

sin depender de servicios de IA externos:
-   [x] Endpoint implementado en `backend/mybookconnect/health.py` (`HealthCheckView`) y enlazado en `api/v1/health/`.
-   [x] `throttle_classes = []` para evitar falsos 500 por rate-limiting en monitorización continua.
-   [x] Verifica conectividad a DB (`connection.cursor().execute("SELECT 1;")`) y Redis Cache (`cache.set`/`cache.get`).
-   [x] Responde `200 OK` (healthy) o `503 Service Unavailable` con detalle descriptivo en caso de degradación.
-   [x] Dockerfile de backend actualizado con `CMD curl -f http://localhost:8000/api/v1/health/ || exit 1`.
-   [x] Pruebas exhaustivas en `backend/tests/test_healthcheck.py` (62/62 tests pasando en suite completa).

------------------------------------------------------------------------

# 17. Fase 14 --- Permisos y privacidad centralizados

**Prioridad:** P0

Crear servicios/policies:

``` python
can_view_profile(viewer, target)
can_view_review(viewer, review)
can_edit_review(user, review)
can_access_conversation(user, conversation)
can_message(user, target)
```
-   [x] Módulo centralizado implementado en `backend/users/policies.py`.
-   [x] Queryset helpers `filter_visible_reviews` y `filter_visible_users` implementados.

## Bloqueos

Definir explícitamente qué ocurre al bloquear:

-   [x] **Ver perfil:** si el target bloqueó al viewer, acceso 403 denegado. Si el viewer bloqueó al target, solo se le permite acceso básico para desbloquear.
-   [x] **Buscar usuario:** `UserSearchListView` y `filter_visible_users` excluyen mutuamente a usuarios bloqueados y bloqueadores en `/api/v1/users/search/`.
-   [x] **Seguir:** `FollowUserView` impide seguir si hay bloqueo en cualquiera de las dos direcciones. Al bloquear a un usuario, se rompe inmediatamente el seguimiento mutuo bidireccional (`request.user.following.remove(target)`, `target.following.remove(request.user)`).
-   [x] **Ver reviews:** `filter_visible_reviews` y `ReviewDetailView` ocultan automáticamente reseñas de usuarios bloqueados o bloqueadores, perfiles privados y perfiles amigos sin relación activa de seguimiento.
-   [x] **Ver actividad:** exclusión garantizada en filtros de privacidad por usuario y autor.
-   [x] **Enviar mensajes:** validación en `ConversationViewSet.start_conversation`, `MessageViewSet.perform_create` y `ChatConsumer` (WebSockets) denegando creación o emisión si existe restricción o bloqueo.
-   [x] **Aparecer en recomendaciones:** integración de exclusión mediante `filter_visible_users` y aislamiento de grafos sociales bloqueados.
-   [x] **Aparecer en búsquedas:** excluidos bidireccionalmente de los resultados de búsqueda global de usuarios.

## Criterio de aceptación

-   [x] Las reglas de privacidad no están duplicadas en múltiples views; centralizadas en `users.policies`.
-   [x] Suite de pruebas automatizadas en `backend/tests/test_permissions_privacy.py` (71/71 tests pasando en suite completa).

------------------------------------------------------------------------

# 18. Fase 15 --- Chat y WebSockets

**Prioridad:** P1

## Conversaciones 1:1

Garantizar que:

``` text
A ↔ B
```

y:

``` text
B ↔ A
```

no creen dos conversaciones:
-   [x] Método canónico `Conversation.get_or_create_direct(user1, user2)` implementado con transacción atómica.
-   [x] `start_conversation` resuelve de forma determinista a la misma y única instancia.

## ViewSets

No utilizar `ModelViewSet` si no son necesarias todas las operaciones.

Preferir:

``` text
ReadOnlyModelViewSet
+
acciones específicas
```
-   [x] `ConversationViewSet` convertido a `ReadOnlyModelViewSet` (expone únicamente `list`, `retrieve` y acción `@action start`).
-   [x] `MessageViewSet` restringido a `CreateModelMixin`, `ListModelMixin`, `RetrieveModelMixin` y `GenericViewSet` (bloqueando de forma estricta mutaciones y eliminaciones `PUT`, `PATCH` y `DELETE` con `405 Method Not Allowed`).

## Modelo de Seguimiento y Acciones Directas
-   [x] `can_message` adaptado para permitir mensajería entre usuarios con relación de seguimiento (`following`), respetando bloqueos.
-   [x] Botón directo de "Enviar mensaje" implementado en `Friends.tsx` para todas las tarjetas de amigos/seguidos.
-   [x] Buscador y selector rápido de seguidos integrado en la barra lateral de `Chat.tsx` para iniciar conversaciones inmediatas con 1 clic.

## Tests

-   [x] Acceso autorizado.
-   [x] Acceso no autorizado.
-   [x] Usuario bloqueado.
-   [x] Mensaje ajeno.
-   [x] Conversación ajena.
-   [x] WebSocket autenticado.
-   [x] WebSocket sin autenticación (`4001`).
-   [x] WebSocket no participante (`4003`).
-   [x] Suite completa de pruebas en `backend/tests/test_chat_websockets.py` (78/78 tests pasando en suite completa).

------------------------------------------------------------------------

# 19. Fase 16 --- Búsqueda textual avanzada [COMPLETADA]

**Prioridad:** P1

Usar PostgreSQL:

- [x] Extensión `pg_trgm` instalada y migrada (`books.0012_postgres_trigram_and_gin_indexes`).
- [x] Índices GIN con trigramas (`gin_trgm_ops`) en `Book.title`, `Book.description` y `Author.name`.
- [x] `SearchVector`, `SearchQuery`, `SearchRank` para indexación ponderada (A: título/ISBN, B: autor/categorías, C: descripción).
- [x] `TrigramSimilarity` y `TrigramWordSimilarity` con cálculo de relevancia híbrida tolerante a erratas.

Campos indexados y consultados:
- [x] `title`
- [x] `author`
- [x] `isbn`
- [x] `description`
- [x] `categories`

## Resultado

Ordenación ponderada:
- [x] Exact match / prefix boost
- [x] Trigram & word similarity (ponderado 3.0x título, 2.0x autor, 0.5x descripción)
- [x] Full text search rank (ponderado 1.5x)
- [x] Fallback por rating y fecha de creación
- [x] Fallback automático para motores sin PostgreSQL o en caso de error

## Criterio de aceptación

- [x] Búsquedas parciales y con errores razonables (ej. "soledd", "Cortzar") devuelven resultados relevantes instantáneos mediante índices GIN y trigramas sin depender exclusivamente de `icontains`.
- [x] Suite completa de tests pasando (87/87 tests).

------------------------------------------------------------------------

# 20. Fase 17 --- Búsqueda semántica real

**Prioridad:** P2

Instalar/configurar:

``` text
pgvector
```

Añadir:

``` text
Book.embedding
```

## Pipeline

``` text
Book creado/modificado
        ↓
Celery
        ↓
generar embedding
        ↓
guardar vector
```

## Búsqueda

``` text
consulta del usuario
        ↓
embedding
        ↓
vector similarity
        ↓
top N
```

Combinar:

``` text
text search
+
semantic search
```

## Criterio de aceptación

Una consulta conceptual debe encontrar libros relacionados aunque no
compartan las mismas palabras.

Ejemplo:

``` text
"novela oscura sobre pérdida y memoria"
```

------------------------------------------------------------------------

# 21. Fase 18 --- Feed social [COMPLETADA]

**Prioridad:** P1 - COMPLETADA
- [x] Modelo Activity con campos (user, type, book, review, target_user, created_at, metadata).
- [x] Tipos: BOOK_ADDED, BOOK_STARTED, BOOK_FINISHED, BOOK_RATED, REVIEW_CREATED, USER_FOLLOWED, LIST_CREATED.
- [x] Triggers mediante signals de Django en libros, reseñas y seguimiento.
- [x] Endpoint GET /api/v1/users/feed/ con paginación, filtros de privacidad, exclusión bidireccional de bloqueados y prefetch.
- [x] Hidratación y descarga en segundo plano de portadas faltantes en búsqueda y fallback multiproveedor con validación de magic bytes.

Crear:

``` text
Activity
```

Campos:

``` text
user
type
book
review
created_at
metadata
```

Tipos iniciales:

``` text
BOOK_ADDED
BOOK_STARTED
BOOK_FINISHED
BOOK_RATED
REVIEW_CREATED
USER_FOLLOWED
LIST_CREATED
```

## Feed

``` text
seguidores
    ↓
activities
    ↓
orden temporal
    ↓
paginación
```

Posteriormente:

``` text
ranking
personalización
```

------------------------------------------------------------------------

# 22. Fase 19 --- Likes y comentarios [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

## ReviewLike

``` text
user
review
created_at
```

Constraint:

``` text
Unique(user, review)
```

## ReviewComment

``` text
user
review
content
created_at
updated_at
deleted_at
```

## Tests

-   [x] Like/unlike.
-   [x] Duplicado.
-   [x] Comentario.
-   [x] Borrado.
-   [x] Permisos.
-   [x] Usuario bloqueado.

------------------------------------------------------------------------

# 23. Fase 20 --- Notificaciones [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Crear:

``` text
Notification
```

Campos:

``` text
recipient
actor
type
object_type
object_id
read_at
created_at
```

Tipos:

``` text
FOLLOW
LIKE
COMMENT
REVIEW
MESSAGE
MENTION
```

-   [x] Modelo `Notification` implementado en `users.models` con tipos `FOLLOW`, `MESSAGE`, `REVIEW`, `LIKE`, `COMMENT`, `SYSTEM`.
-   [x] Endpoints implementados: lista, contador de no leídas (`/api/v1/users/notifications/unread-count/`), marcar individual (`/read/`) y marcar todas (`/read-all/`).
-   [x] Disparo automático de notificaciones al seguir a un usuario, al recibir mensajes de chat (REST y WebSockets), y al recibir me gusta y comentarios en reseñas.

## Frontend

Añadir:

-   [x] Contador de no leídas en tiempo real/polling en `Header.tsx`.
-   [x] Lista interactiva de notificaciones con avatares, timestamps e iconos por tipo.
-   [x] Marcar individualmente como leída al hacer clic y navegar al recurso.
-   [x] Marcar todas como leídas mediante acción directa en el panel.


------------------------------------------------------------------------

# 24. Fase 21 --- Listas de libros

**Prioridad:** P2

Crear:

``` text
ReadingList
ReadingListItem
```

## Ejemplos

``` text
Favoritos
Ciencia ficción
Para 2027
Vacaciones
Clásicos
Pendientes
```

## Privacidad

``` text
PRIVATE
FOLLOWERS
PUBLIC
```

## Funciones

-   [ ] Crear.
-   [ ] Editar.
-   [ ] Eliminar.
-   [ ] Añadir libro.
-   [ ] Quitar libro.
-   [ ] Ordenar.
-   [ ] Compartir.
-   [ ] Seguir lista.

------------------------------------------------------------------------

# 25. Fase 22 --- Estadísticas de lectura

**Prioridad:** P2  
**Estado:** ✅ Completada

Métricas implementadas con agregaciones PostgreSQL y caché Redis (`stats:user:{user_id}`, TTL: 15 min):

``` text
- Libros leídos (total_read)
- Libros en progreso (currently_reading)
- Libros por leer / wishlist (want_to_read)
- Libros abandonados (abandoned)
- Páginas leídas (total_pages_read)
- Valoración media (average_rating)
- Distribución de puntuaciones (1 a 10)
- Top 5 géneros literarios con conteo y porcentajes
- Top 5 autores más leídos
- Evolución mensual de lectura (últimos 12 meses)
- Libros terminados en el año en curso
```

## Dashboard y Frontend:
- [x] Servicio backend `books.services.stats_service.get_user_reading_stats` optimizado.
- [x] Endpoint `GET /api/v1/books/statistics/` (con soporte para `?user_id=X` y respeto de privacidad).
- [x] Página interactiva `ReadingStats.tsx` con KPI cards, gráfico de barras mensual, barras de porcentaje por género, ranking de autores y distribución de notas.
- [x] Integración en navegación (`Header.tsx`), en perfil (`Profile.tsx`) y rutas (`App.tsx`).
- [x] Invalidación atómica de caché ante cambios en `UserBook` y `Review`.
- [x] Suite de pruebas automatizadas en `test_phase22_reading_stats.py`.

------------------------------------------------------------------------

# 26. Fase 23 --- Trending

**Prioridad:** P2  
**Estado:** ✅ Completada

Crear un score temporal ponderado con decaimiento temporal y ventanas seleccionables:
- Ponderaciones: Reseñas (5.0), Lecturas recientes (3.0), Wishlists (2.0), Likes sociales (1.5), Comentarios (1.0).
- Decaimiento por ventanas: `week` (7 días), `month` (30 días), `year` (365 días), `all` (histórico acumulado).
- Cacheado en Redis (`trending:{period}`, TTL 15 min).
- Tarea Celery de precomputación en background (`precompute_trending_task`).
- Selector de periodo interactivo y medallas (#1 🥇, #2 🥈, #3 🥉) en `Home.tsx`.

## Tareas completadas:
- [x] Crear servicio de tendencias modular `trending_service.py` con agregaciones condicionales en PostgreSQL.
- [x] Ponderación de señales de actividad comunitaria con decaimiento temporal.
- [x] Filtros por periodo en `TrendingBooksView` (`?period=week|month|year|all`).
- [x] Claves y namespaces estandarizados de caché en Redis e invalidación `invalidate_trending_cache()`.
- [x] Tarea periódica de precomputación Celery `precompute_trending_task`.
- [x] Componente frontend en `Home.tsx` con tabs de periodo, insignias de ranking y microanimaciones.
- [x] Suite de pruebas automatizadas en `test_phase23_trending.py` y `test_caching.py`.

------------------------------------------------------------------------

# 27. Fase 24 --- Motor de recomendaciones

**Prioridad:** P2  
**Estado:** ✅ Completada

Motor de recomendaciones híbrido configurable con explicabilidad y soporte contextual:
- **Preferencias de género e historial (35%)**: Ponderación por valoraciones ($\ge 4$) y libros leídos/deseados.
- **Afinidad de autor (20%)**: Recompensa a autores favoritos del usuario.
- **Comportamiento social (20%)**: Libros leídos o bien valorados por usuarios seguidos (`following`).
- **Similitud semántica y temática (15%)**: Coincidencia temática con sinopsis y títulos favoritos.
- **Descubrimiento y serendipia (10%)**: Impulso a libros de alta valoración comunitaria ($\ge 4.0$) en géneros adyacentes.
- **Explicabilidad ("Reasons")**: Cada recomendación detalla el motivo intuitivo del cálculo.
- **Recomendaciones contextuales de libro a libro**: Filtrado colaborativo ("quienes leyeron X también leyeron Y") en `BookDetail`.
- **Caché en Redis e invalidación reactiva**: TTL 15m con refresco en `UserBook` y `Review`.
- **Tarea Celery de precomputación**: `precompute_user_recommendations_task`.
- **Frontend**: Nueva sección *"✨ Recomendados para ti"* en `Home.tsx` y carrusel *"Lectores también disfrutaron"* en `BookDetail.tsx`.

## Tareas completadas:
- [x] Crear servicio `recommendation_service.py` con motor híbrido multi-estrategia (`hybrid`, `rules`, `social`, `semantic`).
- [x] Motor de explicabilidad transparente con motivos humanizados por libro recomendado.
- [x] Filtrado colaborativo contextual para libros en `get_book_recommendations`.
- [x] Estrategia de caché Redis e invalidación reactiva en signals de `UserBook` y `Review`.
- [x] Endpoints API REST: `GET /api/v1/books/recommendations/` y `GET /api/v1/books/<pk>/recommendations/`.
- [x] Tarea Celery de precomputación `precompute_user_recommendations_task`.
- [x] Componentes visuales en `Home.tsx` e integración en `BookDetail.tsx`.
- [x] Suite de tests completa en `test_phase24_recommendations.py` (8/8 tests superados).

------------------------------------------------------------------------

# 28. Fase 25 --- Feedback de recomendaciones [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Registrar:

``` text
recommendation_shown
recommendation_clicked
book_opened
wishlist_added
reading_started
reading_finished
rated
```

Relacionar:

``` text
recommendation_id
user
book
algorithm_version
timestamp
```

Esto permite medir:

``` text
CTR
conversion
wishlist rate
start rate
completion rate
```

## Tareas completadas:
- [x] Modelo `RecommendationFeedback` en `backend/books/models.py` con indexación optimizada y enum de acciones.
- [x] Migración de base de datos `0015_recommendationfeedback.py` aplicada correctamente.
- [x] Servicio `recommendation_feedback_service.py` con `record_recommendation_event` y `get_recommendation_metrics` (cálculo de CTR, wishlist rate, start rate, completion rate y desgloses por estrategia/versión).
- [x] Serializador `RecommendationFeedbackSerializer` y vistas de API REST `RecommendationFeedbackView` (soporte individual y batch) y `RecommendationMetricsView` en `backend/books/views.py`.
- [x] Rutas API `/api/v1/books/recommendations/feedback/` y `/api/v1/books/recommendations/metrics/` configuradas en `urls.py`.
- [x] Instrumentación en frontend (`Home.tsx`) para disparar eventos de impresión (`recommendation_shown`) por lotes y clicks (`recommendation_clicked`) interactivos.
- [x] Corrección definitiva en resolución de portadas `/media/covers/` tanto en backend (`media_utils.py`, `serializers.py`) como en frontend (`media.ts`, `AddBook.tsx`, `BookDetail.tsx`, `Library.tsx`, `Profile.tsx`).
- [x] Mejora en motor de búsqueda y auto-importación: soporte de búsqueda bilingüe para Wikipedia y forzado de búsqueda externa cuando hay pocos resultados locales o el título específico no coincide.
- [x] Suite de pruebas automatizadas `test_phase25_feedback.py` (7/7 superadas) con 100% de éxito.

------------------------------------------------------------------------

# 29. Fase 26 --- IA [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Separar:

``` text
ai/
├── clients/
│   ├── base.py
│   ├── factory.py
│   ├── ollama_client.py
│   ├── openai_client.py
│   └── openrouter_client.py
├── config.py
├── embeddings.py
├── prompts.py
├── services.py
└── policies.py
```

## Providers

Abstracción:

``` text
AIProvider
   ├── OpenAI
   ├── Ollama
   ├── OpenRouter
   └── otros
```

## Configuración

``` text
AI_PROVIDER
AI_MODEL
AI_EMBEDDING_MODEL
AI_TIMEOUT
```

## Tareas completadas:
- [x] Paquete modular `backend/ai/` implementado con separación estricta de responsabilidades (`clients/`, `config.py`, `embeddings.py`, `prompts.py`, `policies.py`, `services.py`).
- [x] Abstracción `AIProvider` con factoría dinámica `get_ai_provider` y clientes para `OllamaProvider`, `OpenAIProvider` y `OpenRouterProvider`.
- [x] Variables desacopladas en `settings.py`: `AI_PROVIDER`, `AI_MODEL`, `AI_EMBEDDING_MODEL`, `AI_TIMEOUT`, `AI_API_BASE_URL` y `AI_API_KEY`.
- [x] Políticas de seguridad en `policies.py`: sanitización de mensajes, rechazo de rol `system` no autorizado y acotación defensiva de longitud.
- [x] Motor de prompts centralizado en `prompts.py` y cálculo de embeddings vectoriales con similitud coseno en `embeddings.py`.
- [x] Servicios de orquestación de alto nivel en `services.py` (`get_assistant_reply`, `get_book_ai_summary`, `get_ai_status`, `semantic_search_books`) con soporte de fallback offline.
- [x] Adaptación retrocompatible transparente de `mybookconnect/ai_service.py` y refactorización de `books/ai_views.py`.
- [x] Suite completa de tests automatizados en `test_phase26_ai.py` (19/19 superados, 100% éxito).

------------------------------------------------------------------------

# 30. Fase 27 --- Seguridad del asistente IA [COMPLETADA]

**Prioridad:** P1/P2 - COMPLETADA

## No confiar en el historial enviado por frontend

Validar:

``` text
roles
número de mensajes
longitud
contenido
```

El frontend nunca puede definir instrucciones `system`.

## Prompt injection

Tratar como no confiable:

``` text
review.text
comment.content
book.description
message.content
```

## Tools

Si en el futuro la IA puede ejecutar acciones:

``` text
LLM
 ↓
tool call
 ↓
backend
 ↓
validación de permisos
 ↓
acción
```

Nunca:

``` text
LLM → ejecución directa
```

## Tareas completadas:
- [x] Validación estricta del historial en `policies.py`: roles restringidos (`user`, `assistant`), límite individual (máx. 3000 chars), límite acumulado total (máx. 12000 chars con poda automática) y neutralización de caracteres de control nulos.
- [x] Detección de Prompt Injection (`detect_prompt_injection`) en `policies.py` para mitigación proactiva de jailbreaks, DAN mode y sobrescritura de instrucciones del sistema.
- [x] Sanitización de entradas no confiables (`sanitize_untrusted_input`) neutralizando tokens de control especiales de LLM (`<|im_start|>`, `[INST]`, etc.) en reseñas, sinopsis y consultas.
- [x] Delimitadores semánticos estructurados (`<user_context>`, `<book_context>`, `<book_reference>`) y cláusulas de inmutabilidad de instrucciones en `prompts.py`.
- [x] Rate Limiting defensivo por usuario (`check_ai_rate_limit`) soportado en caché Redis con respuesta HTTP 429 Too Many Requests ante excesos.
- [x] Módulo completo de Function / Tool Calling seguro en `backend/ai/tools/`:
  - `AITool` abstracta con esquemas JSON Schema y verificación previa de permisos.
  - Implementación de herramientas de lectura: `CatalogSearchTool`, `BookDetailTool`, `UserReadingStatusTool` y `AddToWishlistTool`.
  - Despachador seguro `execute_tool` con mediación estricta de backend y captura de excepciones.
- [x] Endpoints API REST para herramientas: `GET /api/v1/books/ai/tools/` y `POST /api/v1/books/ai/tools/execute/`.
- [x] Suite completa de tests automatizados de seguridad en `test_phase27_ai_security.py` (19/19 superados, 100% éxito).

------------------------------------------------------------------------

# 31. Fase 28 --- Media y uploads [COMPLETADA]

**Prioridad:** P1

Validaciones implementadas:

``` text
MIME: Inspección binaria profunda vía Pillow (JPEG, PNG, WebP)
extensión: Whitelist estricta (.jpg, .jpeg, .png, .webp). SVG y executables rechazados explícitamente.
tamaño: avatar/autor <= 5 MB, cover/chat <= 10 MB
dimensiones: mínimo 50x50 px, máximo 6000x6000 px (protección decompression bombs)
contenido: Verificación estructural e integridad mediante Image.verify() y Image.load()
privacidad: Sanitización activa eliminando metadatos EXIF (coordenadas GPS, identificación de cámaras)
```

## Producción

Soporte de almacenamiento pluggable configurado en `settings.py` (`STORAGES`):
- `FileSystemStorage` para desarrollo local.
- Preparado y documentado para migración inmediata a S3, Cloudflare R2, MinIO o Cloudinary vía `MEDIA_STORAGE_BACKEND` y variables de entorno `AWS_*`.
- Serializadores DRF (`UserSerializer`, `BookSerializer`, `AuthorSerializer`, `MessageSerializer`) y servicio de descarga externa (`cover_service.download_and_attach_image`) integrados con sanitización automática.

------------------------------------------------------------------------

# 32. Fase 29 --- Moderación [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

## Modelo de Denuncias (Report)
- [x] Modelo `Report` polimórfico mediante `GenericForeignKey('content_type', 'object_id')` aplicable a:
  - `User` (perfiles)
  - `Review` (reseñas literarias)
  - `ReviewComment` (comentarios en reseñas)
  - `Message` (mensajes directos de chat)
- [x] Estados implementados: `OPEN`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`.
- [x] Motivos tipificados: `SPAM`, `HARASSMENT`, `HATE_SPEECH`, `INAPPROPRIATE`, `SPOILER`, `COPYRIGHT`, `OTHER`.
- [x] Validación estricta anti-abuso:
  - Prohibición rigurosa de auto-denuncias (un usuario no puede denunciar su propio contenido o perfil).
  - Prohibición de duplicar denuncias activas sobre el mismo objeto por el mismo denunciante.
- [x] Campos de auditoría y resolución: `resolution_notes`, `resolved_by`, `resolved_at`, `action_taken`.

## Jerarquía de Roles
- [x] Evolución del sistema de permisos hacia una jerarquía formal en `User`:
  - `USER`: Lector estándar.
  - `EDITOR`: Permisos sobre catálogo editorial (libros, autores, erratas).
  - `MODERATOR`: Gestión y resolución de expedientes disciplinarios y cola de denuncias.
  - `ADMIN`: Control total del sistema y gestión de staff.
- [x] Retrocompatibilidad total:
  - `is_staff=True` asigna automáticamente rol `ADMIN`.
  - `is_editor=True` asigna automáticamente rol `EDITOR`.
  - Propiedades helper: `user.is_moderator`, `user.is_editor_user`.
- [x] Políticas en `users.policies`:
  - `can_moderate(user)` y `can_edit_catalog(user)`.
  - `filter_visible_reviews` actualizado para ocultar reseñas marcadas con `is_moderated=True` a usuarios comunes.
- [x] Permiso DRF `IsModeratorOrAdmin`.

## Medidas Disciplinarias y Efectos de Moderación
- [x] `HIDE_CONTENT`: Marca `is_moderated=True` en `Review` y `Message`, o soft-delete con `deleted_at` en `ReviewComment`.
- [x] `BAN_USER`: Desactiva la cuenta del usuario infractor (`is_active=False`).
- [x] `WARNING`: Apercebimiento formal registrado en el expediente.
- [x] `DISMISS`: Resolución sin sanción tras confirmación de ausencia de infracción.

## Endpoints API REST
- [x] `POST /api/v1/reports/`: Emisión de denuncias por usuarios autenticados.
- [x] `GET /api/v1/reports/my/`: Consulta de historial de denuncias enviadas por el usuario.
- [x] `GET /api/v1/admin/reports/`: Cola de moderación con filtros por estado (`status`), motivo (`reason`) y tipo (`target_type`).
- [x] `GET /api/v1/admin/reports/<id>/`: Detalle ampliado con vista previa del contenido denunciado y datos de resolución.
- [x] `PATCH /api/v1/admin/reports/<id>/`: Resolución de denuncias y ejecución automática de medidas disciplinarias.
- [x] `GET /api/v1/admin/reports/stats/`: Métricas cuantitativas agregadas de la cola de moderación.

## Frontend (AdminDashboard.tsx)
- [x] Acceso ampliado para moderadores (`user.role === 'MODERATOR' || user.role === 'ADMIN'`).
- [x] Nueva pestaña interactiva `🛡️ Moderación & Denuncias`:
  - Tarjetas de resumen métrico (abiertas, en revisión, resueltas, total).
  - Filtros avanzados por estado, motivo y tipo de contenido.
  - Tabla de denuncias con badges contextuales y previsualización de fragmentos de contenido denunciado.
  - Modal de resolución disciplinaria con selección de medida (`HIDE_CONTENT`, `BAN_USER`, etc.) y notas del moderador.
- [x] Gestión de roles en la tabla de usuarios con selector dinámico (`USER`, `EDITOR`, `MODERATOR`, `ADMIN`).

## Pruebas y Validación
- [x] Suite automatizada `test_phase29_moderation.py` con 16/16 tests superados (100% de éxito).
- [x] Suite global de regresión superada (207/207 tests pasando).
- [x] Linter backend `ruff check .` con 0 errores.
- [x] Tipado y build frontend `pnpm run typecheck` y `pnpm run build` limpios sin advertencias de tipos.

------------------------------------------------------------------------

# 33. Fase 30 --- Auditoría [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

## Modelo y Persistencia de Auditoría (AuditLog)
- [x] Modelo inmutable `AuditLog` en `users.models` con relación polimórfica `GenericForeignKey('content_type', 'object_id')` y campos:
  - `actor`: Usuario ejecutor o `None` (procesos de sistema).
  - `action`: Tipo de acción estandarizada mediante `AuditAction` (`ROLE_CHANGE`, `USER_BAN`, `USER_UNBAN`, `USER_BLOCK`, `USER_UNBLOCK`, `MODERATION_RESOLVE`, `MODERATION_REJECT`, `CONTENT_DELETE`, `SECURITY_PASSWORD_CHANGE`, `OTHER`).
  - `target_repr`: Representación textual inmutable congelada resistente a borrados posteriores.
  - `ip_address`: Dirección IP de origen del cliente HTTP.
  - `user_agent`: Cabecera User-Agent del navegador/cliente.
  - `metadata`: Carga JSON estructurada con detalles contextuales (estado previo y posterior).
  - `created_at`: Marca temporal inmutable indexada.
- [x] Índices compuestos de base de datos: `('action', '-created_at')`, `('content_type', 'object_id')`, `('actor', '-created_at')`.
- [x] Migración `users.0014_auditlog` aplicada satisfactoriamente.

## Servicio Centralizado de Auditoría (`audit_service.py`)
- [x] Módulo desacoplado `users/audit_service.py` con función `log_audit(...)`.
- [x] Extracción automática de IP (respetando proxies inversos `X-Forwarded-For`), User-Agent y usuario autenticado a partir de `request`.
- [x] Tolerancia a fallos: errores en el log se capturan defensivamente para no abortar transacciones de negocio.

## Instrumentación de Eventos Sensibles
- [x] `ROLE_CHANGE`: Capturado en `AdminUserDetailView.perform_update` al modificar roles (`USER`, `EDITOR`, `MODERATOR`, `ADMIN`) o privilegios staff.
- [x] `USER_BAN` / `USER_UNBAN`: Capturado al modificar el estado `is_active` de usuarios en el panel administrativo.
- [x] `USER_BLOCK` / `USER_UNBLOCK`: Capturado en `BlockUserView` y `UnblockUserView` en `users/views.py`.
- [x] `MODERATION_RESOLVE` / `MODERATION_REJECT`: Capturado en `AdminReportDetailView.patch` registrando la sanción aplicada (`HIDE_CONTENT`, `BAN_USER`, etc.) y las notas del moderador.
- [x] `CONTENT_DELETE`: Capturado en `AdminBookDetailView` y `AdminAuthorDetailView` antes del borrado del catálogo editorial.

## API REST de Auditoría
- [x] `GET /api/v1/admin/audit-logs/`: Listado paginado con filtros por `action`, `actor`, `target_type`, `date_from`, `date_to` y búsqueda textual.
- [x] `GET /api/v1/admin/audit-logs/<id>/`: Detalle completo con `metadata` JSON y `user_agent`.
- [x] `GET /api/v1/admin/audit-logs/stats/`: Agregaciones cuantitativas (total, últimas 24h, últimos 7 días, por acción, top actores).
- [x] Permisos estrictos: reservado exclusivamente a Administradores y Superusuarios (`IsAdminOnly`).

## Frontend (AdminDashboard.tsx)
- [x] Nueva pestaña `📜 Auditoría & Logs` accesible para Administradores.
- [x] Tarjetas de resumen métrico con conteo total, actividad reciente y variedad de acciones.
- [x] Filtros por tipo de acción, actor y búsqueda en descripción.
- [x] Tabla interactiva con badges contextuales coloreados por severidad del evento.
- [x] Modal de inspección profunda con previsualización formateada del payload JSON de metadatos, IP y User-Agent.

## Pruebas y Validación
- [x] Suite automatizada `test_phase30_audit.py` con 10/10 tests superados (100% éxito).
- [x] Suite global de regresión superada (217/217 tests pasando).
- [x] Linter backend `ruff check .` con 0 errores.
- [x] Tipado y build frontend `pnpm run typecheck` y `pnpm run build` limpios sin errores.

------------------------------------------------------------------------

# 34. Fase 31 --- Soft delete [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

## Modelo Base y Persistencia (`soft_delete.py`)
- [x] Módulo centralizado `mybookconnect/soft_delete.py` con:
  - `SoftDeleteQuerySet`: métodos auxiliares `.active()`, `.deleted()`, `.soft_delete()` y `.restore()` en lote.
  - `SoftDeleteManager`: manager predeterminado exponiendo consultas sobre registros activos y borrados.
  - `SoftDeleteModel`: clase abstracta que incluye:
    - Campo indexado `deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)`.
    - Propiedad calculada `is_deleted`.
    - Métodos `soft_delete()` y `restore()`.
    - Sobrescritura de `delete(using=None, keep_parents=False, hard=False)` para borrado lógico transparente por defecto y soporte de borrado físico explícito (`hard=True`).

## Aplicación Estricta a Modelos Clave
- [x] **Review** (`books/models.py`):
  - Herencia de `SoftDeleteModel`.
  - Sustitución de restricción incondicional por restricción única parcial: `UniqueConstraint(fields=['user', 'book'], condition=models.Q(deleted_at__isnull=True), name='unique_active_review_user_book')`, permitiendo re-escribir reseñas tras borrado previo.
  - Índices compuestos añadidos: `('book', 'deleted_at')` y `('user', 'deleted_at')`.
  - Señal de actualización de rating recalculando solo sobre reseñas activas (`deleted_at__isnull=True` y `is_moderated=False`).
- [x] **ReviewComment** (`books/models.py`):
  - Herencia de `SoftDeleteModel` y unificación con la infraestructura de borrado lógico.
- [x] **Message** (`messages_app/models.py`):
  - Herencia de `SoftDeleteModel`.
  - Índice compuesto añadido: `('conversation', 'deleted_at')`.

## Filtrado Coherente en Vistas, Serializadores y Tareas Asíncronas
- [x] Tarea Celery `recalculate_book_rating_task`: filtra únicamente `Review.objects.filter(book=book, rating__isnull=False, deleted_at__isnull=True, is_moderated=False)`.
- [x] Políticas de visualización (`users/policies.py`):
  - `filter_visible_reviews`: excluye reseñas con `deleted_at__isnull=False`.
  - `can_view_review`: deniega acceso a reseñas eliminadas salvo para administradores.
- [x] Endpoints y Serializadores:
  - `ReviewListCreateView` y `ReviewDetailView`: excluyen reseñas borradas y gestionan creación/reactivación.
  - `BookSerializer`: distribución de puntuaciones y `reviews_count` excluyen reseñas eliminadas.
  - `UserDetailView` y `UserSerializer`: contador de reseñas `reviews_count` excluye eliminadas.
  - `ConversationSerializer`: `last_message` y `unread_count` excluyen mensajes eliminados.
  - `MessageViewSet`: `get_queryset()` excluye mensajes eliminados.

## Pruebas y Validación
- [x] Suite automatizada `test_phase31_soft_delete.py` con 13/13 tests superados (100% de éxito).
- [x] Suite global de regresión superada (230/230 tests pasando).
- [x] Linter backend `ruff check .` con 0 errores.
- [x] Tipado y build frontend `pnpm run typecheck` y `pnpm run build` limpios sin errores.

------------------------------------------------------------------------

# 35. Fase 32 --- API REST coherente [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

## Convención Canónica de Endpoints (`/api/v1/`)
- [x] **Books**:
  - `GET /api/v1/books/`: listado y búsqueda en catálogo editorial.
  - `POST /api/v1/books/`: creación de libros.
  - `GET /api/v1/books/{id}/`: detalle del libro.
  - `GET /api/v1/books/{id}/recommendations/`: recomendaciones contextuadas al libro.
  - `POST /api/v1/books/import/`: importación desde fuentes externas (Google Books / OpenLibrary).
- [x] **Users**:
  - `GET /api/v1/users/`: listado y búsqueda pública de lectores.
  - `GET /api/v1/users/{id}/`: perfil social del usuario.
  - `POST /api/v1/users/{id}/follow/`: seguir usuario.
  - `POST /api/v1/users/{id}/unfollow/`: dejar de seguir usuario.
  - `POST /api/v1/users/{id}/block/` y `unblock/`: bloqueo y desbloqueo bidireccional.
- [x] **Reviews**:
  - Módulo desacoplado `books/review_urls.py` montado directamente en `/api/v1/reviews/`.
  - `GET /api/v1/reviews/?book={id}`: listado filtrable de reseñas.
  - `POST /api/v1/reviews/`: publicación de reseñas.
  - `GET /api/v1/reviews/{id}/`: consulta de detalle.
  - `POST /api/v1/reviews/{id}/like/`: toggle de likes.
  - `GET, POST /api/v1/reviews/{id}/comments/`: listado y creación de comentarios.
  - `DELETE /api/v1/reviews/{id}/comments/{comment_id}/`: borrado lógico de comentarios.
  - `DELETE /api/v1/reviews/{id}/`: borrado lógico de reseña.
- [x] **Conversations & Messages**:
  - Montaje directo de `messages_app.urls` en `/api/v1/`.
  - `GET /api/v1/conversations/`: bandeja de conversaciones.
  - `POST /api/v1/conversations/start/`: inicio o resolución de chat 1:1.
  - `GET /api/v1/conversations/{id}/`: detalle de conversación.
  - `GET /api/v1/messages/?conversation={id}`: historial de mensajes.
  - `POST /api/v1/messages/`: envío de mensajes con soporte WebSocket y fallback REST.
  - `GET /api/v1/messages/{id}/`: consulta de mensaje por identificador.

## Transición, Depuración y Retrocompatibilidad
- [x] Soporte transparente de rutas heredadas (`/api/v1/books/reviews/...` y `/api/v1/chat/...`) para evitar romper clientes legados.
- [x] Eliminada ruta obsoleta `/api/v1/books/books/` duplicada.
- [x] Frontend actualizado para consumir las rutas canónicas (`BookReviewsSection.tsx`, `Chat.tsx`, `Friends.tsx`, `Profile.tsx`).

## Pruebas y Validación
- [x] Suite automatizada `test_phase32_coherent_api.py` con 7/7 tests superados (100% éxito).
- [x] Suite global de regresión superada (237/237 tests pasando).
- [x] Linter backend `ruff check .` con 0 errores.
- [x] Tipado y build frontend `pnpm run typecheck` y `pnpm run build` limpios sin errores.

------------------------------------------------------------------------

# 36. Fase 33 --- OpenAPI como contrato [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Uso de `drf-spectacular` para publicar la especificación OpenAPI 3.0.3 y generación automatizada de tipos TypeScript en frontend:

``` text
/api/schema/
/api/docs/
/api/redoc/
```

Flujo implementado:

``` text
Django (drf-spectacular)
       ↓
OpenAPI 3.0.3 (/api/schema/)
       ↓
openapi-typescript (generate:types)
       ↓
TypeScript Interfaces (`frontend/src/types/api.ts`)
       ↓
React Components & Hooks
```

## Tareas completadas:
- [x] **Configuración de `SPECTACULAR_SETTINGS`**:
  - Título descriptivo, versión semántica (1.0.0), descripción del sistema, seguridad JWT bearer, componentes divididos y tags semánticos organizados (Books, Authors, Reviews, Reading Lists, Users, Auth, Social, AI, Messages, Admin, Notifications).
- [x] **Enriquecimiento del Esquema Backend**:
  - Incorporadas anotaciones `@extend_schema` y tipado de respuestas con `inline_serializer` y `OpenApiResponse` en todas las vistas clave de DRF y APIViews (`books/views.py`, `books/ai_views.py`, `users/views.py`).
  - Anotados campos dinámicos `SerializerMethodField` con `@extend_schema_field` en `books/serializers.py`, `users/serializers.py` y `messages_app/serializers.py` eliminando advertencias de tipos anónimos.
  - Implementadas guardas `getattr(self, 'swagger_fake_view', False)` en métodos `get_queryset` de `UserBookListCreateView`, `UserFollowingListView`, `UserFollowersListView`, `FeedView`, `ConversationViewSet`, `MessageViewSet`, `UserReportsListView`, y `NotificationListView` previniendo errores durante la introspección anónima del esquema.
- [x] **Generación y Exposición de Contrato OpenAPI**:
  - Endpoints activos: `/api/schema/` (especificación YAML), `/api/docs/` (Swagger UI interactivo) y `/api/redoc/` (documentación estática Redoc).
  - Exportado `schema.yaml` en la raíz de backend vía comando de management `python manage.py spectacular --file schema.yaml`.
- [x] **Pipeline de Generación TypeScript en Frontend**:
  - Añadido paquete `openapi-typescript` v7.13.0 como devDependency en `frontend/package.json`.
  - Configurado script `"generate:types": "openapi-typescript http://backend:8000/api/schema/ -o src/types/api.ts"` en `frontend/package.json`.
  - Generado archivo de definiciones TypeScript fuertemente tipado `frontend/src/types/api.ts` con más de 9.000 líneas de esquemas, rutas y operaciones OpenAPI.
- [x] **Pruebas y Verificación**:
  - Creada suite de pruebas exhaustiva `backend/tests/test_phase33_openapi_contract.py` con 6/6 tests superados (100%).
  - Suite de regresión global ejecutada sin fallos (243/243 tests pasando).
  - Linter backend `ruff check .` con 0 advertencias y 0 errores.
  - Verificación estática frontend `pnpm run typecheck` y empaquetado de producción `pnpm run build` limpios.

------------------------------------------------------------------------

# 37. Fase 34 --- Frontend por features [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Estructura modular implementada siguiendo Feature-Sliced Architecture:

``` text
src/
├── app/
│   ├── router.tsx          # Declarative AppRouter con code-splitting / lazy loading
│   ├── providers.tsx       # AppProviders envolviendo QueryClientProvider
│   └── queryClient.ts      # Instancia central de TanStack Query
│
├── features/
│   ├── auth/               # Login, Register, ProtectedRoute, AuthBox, Modales
│   ├── books/              # BookDetail, AddBook, Author, ReadingLists, ReadingStats
│   ├── library/            # Library
│   ├── reviews/            # BookReviewsSection
│   ├── social/             # Home, Friends
│   ├── profile/            # Profile, EditProfileForm, EditProfile
│   ├── chat/               # Chat
│   ├── ai/                 # AIAssistantModal
│   ├── admin/              # AdminDashboard
│   └── legal/              # PrivacyPolicy, TermsOfService, CookiePolicy
│
├── components/
│   ├── ui/                 # Componentes reutilizables (AmazonAdSlot, BioEditor, CookieBanner, StarRating)
│   └── layout/             # Componentes estructurales (Header, Footer, Logo)
│
├── api/                    # Cliente HTTP centralizado y contratos
├── hooks/                  # Hooks compartidos
├── lib/                    # Utilidades de autenticación y helpers
└── types/                  # Definiciones OpenAPI y TypeScript globales
```

## Tareas completadas:
- [x] **Capa Central de Aplicación (`src/app/`)**:
  - Creado `queryClient.ts` con configuración centralizada de TanStack React Query (`staleTime: 5 min`, `refetchOnWindowFocus: false`, `retry: 1`).
  - Creado `providers.tsx` con componente `AppProviders` para composición limpia de contextos.
  - Creado `router.tsx` con `AppRouter`, rutas declarativas y lazy loading de todas las páginas de features con suspense spinner accesible.
  - Refactorizados `App.tsx` y `main.tsx` delegando limpiamente en `AppRouter` y `AppProviders`.
- [x] **Capa de Componentes (`src/components/layout/` y `src/components/ui/`)**:
  - `components/layout/`: `Header.tsx`, `Footer.tsx`, `Logo.tsx` y barrel export `index.ts`.
  - `components/ui/`: `CookieBanner.tsx`, `StarRating.tsx`, `AmazonAdSlot.tsx`, `BioEditor.tsx` y barrel export `index.ts`.
- [x] **Módulos de Features (`src/features/`)**:
  - `auth/`: `LoginModal`, `RegisterModal`, `ProtectedRoute`, `AuthBox`, `Login`, `Register` con barrel export.
  - `books/`: `BookDetail`, `AddBook`, `Author`, `ReadingLists`, `ReadingStats` con barrel export.
  - `library/`: `Library` con barrel export.
  - `reviews/`: `BookReviewsSection` con barrel export.
  - `social/`: `Home`, `Friends` con barrel export.
  - `profile/`: `Profile`, `EditProfileForm`, `EditProfile` con barrel export.
  - `chat/`: `Chat` con barrel export.
  - `ai/`: `AIAssistantModal` con barrel export.
  - `admin/`: `AdminDashboard` con barrel export.
  - `legal/`: `PrivacyPolicy`, `TermsOfService`, `CookiePolicy` con barrel export.
- [x] **Compatibilidad Hacia Atrás (Facade Re-exports)**:
  - Mantenidas fachadas de re-exportación transparentes en `src/pages/*.tsx` y `src/components/*.tsx` para evitar roturas en consumidores previos o importaciones internas.
- [x] **Validación y Verificación**:
  - Verificación estática con `pnpm run typecheck` (`tsc --noEmit` superado con 0 errores).
  - Empaquetado de producción con `pnpm run build` (`vite build` completado exitosamente).
  - Suite de regresión backend `pytest -q` con 243/243 tests pasando sin ninguna regresión.


------------------------------------------------------------------------

# 38. Fase 35 --- React Router [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Uso de Layouts anidados con `<Outlet />`:

``` text
ProtectedLayout  → Control de sesión unificado, header, footer, banner, contenedor y <Outlet />
PublicLayout     → Landing y páginas legales (/privacy, /terms, /cookies) con shell común y <Outlet />
AdminLayout      → Control de permisos (staff/admin/moderator), barra de contexto admin y <Outlet />
```

Con:

``` tsx
<Outlet />
```

Eliminada la repetición manual de `<ProtectedRoute>` en cada ruta individual.

## Tareas completadas:
- [x] **Creación de Layouts Anidados (`src/components/layout/`)**:
  - Creado `PublicLayout.tsx`: Shell estructural con `Header`, `FooterSection`, `CookieBanner` y `<Outlet />` envuelto en `Suspense` con fallback accesible.
  - Creado `ProtectedLayout.tsx`: Evalúa `isAuthenticated` de forma centralizada una sola vez. Redirige a `/` con el origen guardado (`state: { from: location }`) y renderiza la jerarquía protegida bajo `<Outlet />`.
  - Creado `AdminLayout.tsx`: Verifica autenticación y autorización por rol (`is_staff`, `is_superuser`, `role === 'ADMIN' || 'MODERATOR'`). Redirige a `/home` a usuarios no autorizados y muestra una barra de contexto administrativo contextual con enlace de regreso a la interfaz de usuario y `<Outlet />`.
  - Exportados los tres layouts en `src/components/layout/index.ts`.
- [x] **Reestructuración Declarativa de Rutas (`src/app/router.tsx`)**:
  - Refactorizada la jerarquía de `Routes` agrupando rutas públicas bajo `PublicLayout`, rutas privadas bajo `ProtectedLayout` y rutas administrativas bajo `AdminLayout`.
  - Eliminados los envoltorios redundantes `<ProtectedRoute>` en las 13 rutas autenticadas.
  - Añadida ruta fallback global `*` hacia `/` para gestión de rutas no coincidentes.
- [x] **Pruebas y Verificación**:
  - `pnpm run typecheck` (`tsc --noEmit`) superado con 0 errores.
  - `pnpm run build` (`vite build`) completado con éxito con división de chunks optimizada.
  - Suite de pruebas backend `pytest -q` con 243/243 tests pasando sin ninguna regresión.


------------------------------------------------------------------------

# 39. Fase 36 --- React Query vs Zustand [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Separación rigurosa de responsabilidades de estado:

``` text
Server state (Asíncrono, cache, invalidación) → TanStack Query
Client/UI state (Síncrono, persistente, UI local) → Zustand
```

TanStack Query:
- `books`: detalle de libros, autores, listas de lectura, estadísticas, trending, recomendaciones.
- `reviews`: reseñas por libro, likes, creación de reseñas y comentarios.
- `users` y `social`: perfil de usuario, seguidores, seguidos, follow-status, feed social.
- `notifications`: listado de notificaciones y marcado de leídas.

Zustand:
- `useAuthStore`: sesión JWT, tokens (`token`, `refreshToken`), usuario activo, estado de login/registro y limpieza de cache al logout.
- `useUIStore`: tema (`theme`: 'light' | 'dark' | 'system'), menú lateral (`sidebarOpen`), modales activos (`activeModals`), borradores en curso (`drafts`).

## Tareas completadas:
- [x] **Factoría Unificada de Query Keys (`src/api/queryKeys.ts`)**:
  - Definida la jerarquía estricta de claves para `books`, `reviews`, `social`, `users`, `notifications`, `admin`.
  - Creado barrel export `src/api/index.ts`.
- [x] **Hooks de Server State con TanStack Query**:
  - `features/books/hooks/useBooksQuery.ts`: `useBookDetail`, `useAuthorDetail`, `useReadingLists`, `useReadingStats`, `useTrendingBooks`, `useRecommendedBooks`, `useCreateReadingList`.
  - `features/reviews/hooks/useReviewsQuery.ts`: `useBookReviews`, `useCreateReview`, `useLikeReview`, `useAddReviewComment`.
  - `features/social/hooks/useSocialQuery.ts`: `useHomeFeed`, `useFollowers`, `useFollowing`, `useFollowStatus`, `useFollowUser`, `useUnfollowUser`.
  - `features/social/hooks/useNotificationsQuery.ts`: `useNotifications`, `useMarkNotificationRead`.
  - Exportados hooks en sus respectivos módulos de feature (`features/books`, `features/reviews`, `features/social`).
- [x] **Store de Client/UI State con Zustand (`src/store/ui.ts`)**:
  - Creado `useUIStore` con persistencia `ui-storage` para `theme` (sincronizado con `document.documentElement`), `sidebarOpen`, `activeModals` y `drafts`.
  - Creado barrel export `src/store/index.ts`.
- [x] **Depuración de Store de Autenticación (`src/store/auth.ts`)**:
  - Conectada la invalidación de cache de TanStack Query (`queryClient.invalidateQueries`) al mutar perfil o relaciones de seguimiento.
  - Integrada la purga total del cache (`queryClient.clear()`) en el cierre de sesión (`logout`).
- [x] **Integración de Componentes**:
  - `Friends.tsx`: Migrado de fetching manual con `useEffect` a `useFollowing()` y `useFollowers()` de TanStack Query con estados de carga (`isLoading`) y renderizado reactivo.
- [x] **Pruebas y Verificación**:
  - `pnpm run typecheck` (`tsc --noEmit`) completado con 0 errores.
  - `pnpm run build` (`vite build`) completado con éxito en 17.35s.
  - Suite de regresión backend `pytest -q` con 243/243 tests pasando sin ninguna regresión.


------------------------------------------------------------------------

# 40. Fase 37 --- Formularios [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Añadir:

``` text
React Hook Form
Zod (@hookform/resolvers/zod)
```

Aplicar a:

``` text
registro
login
perfil
reviews
listas
chat
```

Mantener validación también en backend.

## Tareas completadas:
- [x] **Instalación de Dependencias**:
  - `react-hook-form` (v7), `zod` (v4), `@hookform/resolvers` (v5).
- [x] **Esquemas de Validación Zod Centralizados**:
  - `features/auth/schemas/authSchemas.ts`: `loginSchema` (validación de username y contraseña requerida) y `registerSchema` (longitudes mínimas/máximas, validación de email y coincidencia de confirmación de contraseña).
  - `features/profile/schemas/profileSchemas.ts`: `editProfileSchema` (validación de nombre, apellidos, correo, fecha, ubicación, biografía y nivel de privacidad con switches de visibilidad).
  - `features/reviews/schemas/reviewSchemas.ts`: `reviewSchema` (puntuación entera de 1 a 10 con selector interactivo, título y texto con límites) y `commentSchema`.
  - `features/books/schemas/listSchemas.ts`: `readingListSchema` (nombre obligatorio, descripción y enum de privacidad `public` | `followers` | `private`).
  - `features/chat/schemas/chatSchemas.ts`: `chatMessageSchema` (mensaje no vacío con límite de 2000 caracteres).
- [x] **Refactorización Integral de Formularios con React Hook Form**:
  - `Login.tsx` y `LoginModal.tsx`: migrados a `useForm<LoginFormData>` con `zodResolver(loginSchema)`.
  - `Register.tsx` y `RegisterModal.tsx`: migrados a `useForm<RegisterFormData>` con `zodResolver(registerSchema)`.
  - `EditProfileForm.tsx`: migrado a `useForm<EditProfileFormData>` con `zodResolver(editProfileSchema)` e integración de `Controller` para checkboxes de privacidad.
  - `BookReviewsSection.tsx`: migrado formulario de reseñas a `useForm<ReviewFormData>` con `zodResolver(reviewSchema)` y sincronización del componente `StarRating`.
  - `ReadingLists.tsx`: migrado modal de creación/edición de listas de lectura a `useForm<ReadingListFormData>` con `zodResolver(readingListSchema)`.
  - `Chat.tsx`: migrado formulario de envío de mensajes en tiempo real a `useForm<ChatMessageFormData>` con `zodResolver(chatMessageSchema)`.
- [x] **Mantenimiento de la Validación Backend**:
  - Todos los endpoints DRF conservan sus validadores y reglas de negocio íntegras.
- [x] **Pruebas y Verificación**:
  - `pnpm run typecheck` (`tsc --noEmit`) verificado con 0 errores.
  - `pnpm run build` (`vite build`) completado con éxito para producción.
  - Suite de regresión backend `pytest -q` con 243/243 tests pasando sin ninguna regresión.


------------------------------------------------------------------------

# 41. Fase 38 --- Tipado frontend [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Activar:

``` json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noImplicitReturns": true
}
```

Generar tipos desde OpenAPI.

Evitar:

``` text
any
```

salvo casos justificados.

## Tareas completadas:
- [x] **Configuración Estricta de TypeScript (`tsconfig.json`)**:
  - Activadas las opciones `"strict": true`, `"noUnusedLocals": true`, `"noUnusedParameters": true`, `"noImplicitReturns": true` y `"noFallthroughCasesInSwitch": true`.
- [x] **Generación de Tipos desde OpenAPI**:
  - Ejecutado `pnpm run generate:types` (`openapi-typescript http://backend:8000/api/schema/ -o src/types/api.ts`).
  - Creado `src/types/index.ts` que centraliza y expone aliases convenientes (`ApiBook`, `ApiUserBasic`, `ApiActivity`, `ApiReadingList`, etc.).
- [x] **Tipado de Entorno y Eliminación de `any`**:
  - Creado `src/vite-env.d.ts` extendiendo `ImportMetaEnv` para tipar estrictamente `VITE_API_URL` y `VITE_WS_URL`.
  - Reemplazados usos de `(import.meta as any).env` por `import.meta.env`.
  - Eliminados usos injustificados de `any` en `Author.tsx`, `Chat.tsx`, `BookDetail.tsx`, etc., introduciendo interfaces dedicadas (`AuthorData`, `AuthorBookItem`, `Participant`).
- [x] **Depuración de Errores de Modo Estricto**:
  - Limpiados imports no leídos de `React` (eliminando advertencias en React 18 JSX transform).
  - Eliminadas variables y parámetros no leídos (`offset` en `AddBook.tsx`, `Link` en `Author.tsx`, `isRead` en `BookDetail.tsx`, `setPageSize` en `Library.tsx`, `api` en `services/api.ts`).
  - Corregido retorno explícito en `CookieBanner.tsx` para satisfacer `noImplicitReturns`.
  - Tipados de cabeceras HTTP normalizados como `HeadersInit` en `Home.tsx`.
- [x] **Pruebas y Verificación**:
  - `pnpm run typecheck` (`tsc --noEmit`) superado con **0 errores** bajo modo estricto completo.
  - `pnpm run build` (`vite build`) completado con éxito en 27.62s.
  - Suite de regresión backend `pytest -q` con 243/243 tests pasando sin ninguna regresión.


------------------------------------------------------------------------

# 42. Fase 39 --- Testing frontend [COMPLETADA]

**Prioridad:** P1

Añadir Vitest + React Testing Library.

Tests prioritarios:

-   [x] Login.
-   [x] Registro.
-   [x] Rutas protegidas.
-   [x] Libro.
-   [x] Biblioteca.
-   [x] Review.
-   [x] Follow/unfollow.
-   [x] Bloqueo.
-   [x] Chat / Notificaciones / Feed / Recomendaciones (componentes cubiertos con mocks y aislamiento).

**Validación ejecutada:**
- Vitest configurado con JSDOM y `@testing-library/jest-dom/vitest`.
- 6 archivos de test implementados y pasando.
- Typecheck TypeScript (`tsc --noEmit`) verificado con 0 errores.

------------------------------------------------------------------------

# 43. Fase 40 --- Testing backend [COMPLETADA]

**Prioridad:** P0/P1

## Seguridad

-   [x] Usuario no puede editar `UserBook` ajeno.
-   [x] Usuario no puede editar Review ajena.
-   [x] Usuario bloqueado.
-   [x] Perfil privado.
-   [x] Conversación ajena.
-   [x] Mensaje ajeno.

## Integridad

-   [x] Review duplicada.
-   [x] ISBN duplicado.
-   [x] Rating inválido.
-   [x] Estado inválido.
-   [x] Progreso inválido.

## Social

-   [x] Follow.
-   [x] Unfollow.
-   [x] Block.
-   [x] Unblock.
-   [x] Follow bloqueado.

## Integración

-   [x] Importación.
-   [x] Providers externos.
-   [x] Chat.
-   [x] IA.
-   [x] Recomendaciones.

**Validación ejecutada:**
- Archivo de test dedicado `backend/tests/test_phase40_backend_testing.py` con 21 tests cubriendo los cuatro pilares.
- Suite de regresión completa: 264/264 tests pasando en PostgreSQL + Redis dentro del entorno Docker (`264 passed in 238.37s`).

------------------------------------------------------------------------

# 44. Fase 41 --- Tests de integración con PostgreSQL y Redis [COMPLETADA]

**Prioridad:** P1

No depender únicamente de SQLite.

CI debe utilizar:

``` text
PostgreSQL
Redis
```

reales en contenedores.

Probar:

-   [x] migrations;
-   [x] constraints;
-   [x] indexes;
-   [x] transactions;
-   [x] cache;
-   [x] Channels.

**Validación ejecutada:**
- Archivo de test dedicado `backend/tests/test_phase41_postgres_redis.py` con 17 tests cubriendo migraciones, constraints parciales, índices GIN/Trigram, transacciones atómicas con savepoints, Redis Cache y RedisChannelLayer.
- Suite de regresión completa: 281/281 tests pasando en PostgreSQL + Redis dentro del entorno Docker (`281 passed in 196.13s`).

------------------------------------------------------------------------

# 45. Fase 42 --- Observabilidad [COMPLETADA]

**Prioridad:** P2

Añadir logging estructurado.

Registrar:

-   [x] request_id
-   [x] user_id
-   [x] endpoint
-   [x] status_code
-   [x] duration
-   [x] exception
-   [x] external_provider

No registrar:

-   [x] passwords
-   [x] JWT
-   [x] refresh tokens
-   [x] API keys
-   [x] contenido privado innecesario

## Métricas

Controlar:

-   [x] request latency (promedio y percentil p95)
-   [x] 5xx rate / 4xx rate
-   [x] database queries (totales y promedio por petición)
-   [x] Celery failures
-   [x] external API errors (Google Books, OpenLibrary, Wikipedia)
-   [x] WebSocket connections activas
-   [x] Endpoint administrativo seguro de telemetría: `/api/v1/observability/metrics/`

**Validación ejecutada:**
- Formateador de JSON puro desacoplado en `backend/mybookconnect/logging_formatters.py` compatible con el ciclo de inicialización temprana de logging en Django sin bloqueos de `AppRegistryNotReady`.
- Middleware `StructuredLoggingMiddleware` en `backend/mybookconnect/observability.py` con propagación y generación de cabecera `X-Request-ID`, cómputo de latencia y registro de consultas SQL.
- Sanitización recursiva mediante `sanitize_sensitive_data` para redacción de tokens Bearer, passwords, JWT, API keys y credenciales.
- Telemetría instrumentada en proveedores externos (`GoogleBooksProvider`, `OpenLibraryProvider`, `WikipediaProvider`).
- Suite de tests dedicada `backend/tests/test_phase42_observability.py` (14/14 tests pasando).
- Suite de regresión global: 295/295 tests pasando (`295 passed, 15 warnings in 196.18s`).

------------------------------------------------------------------------

# 46. Fase 43 --- Rendimiento [COMPLETADA]

**Prioridad:** P2

Definir objetivos y SLAs de latencia:

-   [x] API normal p95 < 300 ms (healthcheck, detalle de libro, biblioteca de usuario, perfil)
-   [x] API compleja p95 < 800 ms (tendencias, recomendaciones híbridas, estadísticas)
-   [x] Búsqueda p95 < 500 ms (búsqueda de catálogo con índices trigram / GIN)

Medir antes de optimizar:

-   [x] Utilidad de perfilado y EXPLAIN ANALYZE en `backend/mybookconnect/query_profiler.py`
-   [x] Comando de benchmarking `python manage.py benchmark_queries` reportando tiempos de planificación, ejecución y uso de índices
-   [x] Script de prueba de carga con Locust en `scripts/locustfile.py`
-   [x] Script de prueba de carga con k6 y umbrales estrictos en `scripts/k6_load_test.js`

**Validación ejecutada:**
- Comando `python manage.py benchmark_queries`: todas las consultas críticas evaluadas en PostgreSQL real con tiempos sub-milisegundo (< 1 ms en DB) y uso verificado de índices primarios, compuestos e índices GIN.
- Suite de tests dedicada `backend/tests/test_phase43_performance.py` (12/12 tests pasando) validando cumplimiento estricto de SLAs para endpoints normales, complejos, búsquedas, impacto de caché e integración del comando.
- Suite de regresión global: 307/307 tests pasando (`307 passed, 15 warnings in 250.10s`).

------------------------------------------------------------------------

# 47. Fase 44 --- Gestión de dependencias [COMPLETADA]

**Prioridad:** P2

No hacer upgrades masivos.

Procedimiento aplicado:

-   [x] 1 dependencia (`dompurify` parcheado contra vulnerabilidades de sanitización y XSS)
-   [x] tests (21/21 vitest en frontend y 307/307 pytest en backend)
-   [x] build (`vite build` de producción limpio y `tsc --noEmit` con 0 errores)
-   [x] merge / commit en `develop`

Revisar especialmente y matriz consolidada:

-   [x] Django (`5.2.17` LTS)
-   [x] DRF (`3.18.1`)
-   [x] React (`18.3.1`) & React-DOM (`18.3.1`)
-   [x] React Router (`6.22.0`)
-   [x] Vite (`6.4.3`)
-   [x] TypeScript (`5.9.3` en modo estricto)
-   [x] Tailwind (`3.4.18`)
-   [x] Tiptap (`3.31.3`)
-   [x] Flowbite (`2.5.2`) & Flowbite-React (`0.7.8`)
-   [x] Redis (`8.1.0` / `channels-redis 4.3.0`)
-   [x] PostgreSQL (`16` / `psycopg2-binary 2.9.13`)

Eliminar dependencias innecesarias:
-   [x] Auditoría de dependencias y aislamiento estricto de paquetes requeridos sin dependencias redundantes.

**Validación ejecutada:**
- Actualización puntual y aislada de `dompurify` a `3.4.15` con resolución limpia de dependencias en `pnpm`.
- Validación de tipado estricto `npm run typecheck` sin errores.
- Empaquetado de producción de frontend `npm run build` ejecutado con éxito en 10.80s.
- Suite completa de frontend: 21/21 tests pasando en Vitest.
- Suite completa de regresión backend: 307/307 tests pasando en PostgreSQL 16 y Redis 7 reales (`307 passed in 205.70s`).

------------------------------------------------------------------------

# 48. Fase 45 --- Documentación [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Actualizar:
-   [x] `README.md` (Visión del proyecto, stack tecnológico actualizado, instrucciones de arranque Docker, guías de testing y enlaces a arquitectura)
-   [x] `architecture.md` (Topología completa, flujo de autenticación JWT, subsistema asíncrono Celery/Redis, WebSockets ASGI y motor de IA)
-   [x] `structure.md` (Árbol exhaustivo de directorios backend y frontend con responsabilidades por capa)

Añadir árbol de documentación modular `docs/`:
-   [x] `docs/architecture/`
    -   [x] `overview.md` (Arquitectura global de servicios y patrones de diseño)
    -   [x] `data_model.md` (Entidades de dominio, diagramas relacionales y separación UserBook/Review)
    -   [x] `caching_and_channels.md` (Patrones de caché Redis, TTLs, invalidación y WebSockets con Daphne)
    -   [x] `ai_and_search.md` (Búsqueda híbrida PostgreSQL trigram + vector embeddings e integración con LLMs)
-   [x] `docs/api/`
    -   [x] `overview.md` (Convenciones RESTful, versionado `/api/v1/`, serialización y respuestas de error)
    -   [x] `authentication.md` (Flujo JWT, cookies HttpOnly, rotación de tokens y expiración)
    -   [x] `endpoints.md` (Catálogo maestro de endpoints agrupados por módulo funcional)
-   [x] `docs/development/`
    -   [x] `getting_started.md` (Instalación con Docker Compose, variables de entorno y primeros pasos)
    -   [x] `testing_guide.md` (Estrategias de prueba backend con pytest y frontend con Vitest)
    -   [x] `code_standards.md` (Convenciones de código Python/Django, TypeScript/React y git hooks)
-   [x] `docs/deployment/`
    -   [x] `docker_production.md` (Configuración de producción con Gunicorn, Daphne, Nginx y workers)
    -   [x] `security_checklist.md` (Lista de comprobación previa al despliegue en producción)
-   [x] `docs/security/`
    -   [x] `threat_model_and_hardening.md` (Modelo de amenazas STRIDE, mitigaciones CSRF/XSS e inyección)
    -   [x] `audit_and_moderation.md` (Auditoría de dependencias, sanitización HTML y moderación comunitaria)
-   [x] `docs/decisions/` (Architecture Decision Records)
    -   [x] `ADR-001-django-react.md` (Selección de Django REST Framework y React + TypeScript)
    -   [x] `ADR-002-postgresql-source-of-truth.md` (PostgreSQL 16 como única fuente de verdad transaccional)
    -   [x] `ADR-003-redis-caching-and-channels.md` (Redis para caché de alto rendimiento y Channel Layer de Daphne)
    -   [x] `ADR-004-celery-async-workers.md` (Celery para procesamiento asíncrono y tareas programadas)
    -   [x] `ADR-005-jwt-security-strategy.md` (Tokens JWT de corta duración con rotación y almacenamiento seguro)
    -   [x] `ADR-006-review-userbook-separation.md` (Separación de biblioteca personal privada y reseñas públicas)
    -   [x] `ADR-007-search-and-trigrams.md` (Búsqueda híbrida: trigramas PostgreSQL GIN y búsqueda semántica IA)
    -   [x] `ADR-008-recommendation-engine.md` (Motor híbrido multicriterio con explicabilidad y mitigación de cold-start)

------------------------------------------------------------------------

# 49. Fase 46 --- API de salud y readiness [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Crear y separar formalmente sondas de disponibilidad:
-   [x] `/api/v1/health/` (Sonda de Liveness):
    -   `process alive`: Comprueba que el proceso Django/Daphne está levantado y responde HTTP sin acoplamiento a dependencias externas (evita reinicios en cascada del contenedor por microcortes transitorios).
    -   Respuesta 200 OK: `{"status": "healthy", "process": "alive"}`.
-   [x] `/api/v1/ready/` (Sonda de Readiness):
    -   `database available`: Comprobación activa de PostgreSQL mediante `SELECT 1;`.
    -   `redis available`: Comprobación de lectura y escritura en la capa de caché Redis.
    -   Respuesta 200 OK (`status: "ready"`) cuando todos los servicios están disponibles.
    -   Respuesta 503 SERVICE UNAVAILABLE (`status: "not_ready"`) con desglose de servicios si alguno falla.
-   [x] Decoración OpenAPI completa mediante `drf_spectacular` en ambos endpoints.
-   [x] Integración en `backend/mybookconnect/urls.py` con acceso público sin requerir tokens JWT (esencial para orquestadores Docker, Kubernetes y reverse proxies).
-   [x] Suite de pruebas automatizadas en `backend/tests/test_phase46_health_readiness.py` (9 tests) y `backend/tests/test_healthcheck.py` (5 tests) con 100% de éxito.

------------------------------------------------------------------------

# 50. Fase 47 --- Seguridad de contraseñas y autenticación [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Revisar y robustecer:
-   [x] Password validators: Configuración estricta en `AUTH_PASSWORD_VALIDATORS` (longitud mínima 8, similitud de atributos con usuario, diccionario de contraseñas comunes y rechazo de contraseñas numéricas) aplicada en registro, cambio y restablecimiento.
-   [x] Protección contra brute force: Limitación de intentos en `/api/v1/auth/token/` por IP y par `IP + username` para neutralizar ataques de fuerza bruta y credential stuffing.
-   [x] Rate limiting: Implementación de limitadores dedicados con Redis en `backend/users/throttles.py` (`LoginRateThrottle: 10/min`, `PasswordResetRateThrottle: 5/min`, `AuthAnonRateThrottle: 10/min`).
-   [x] Password reset: Flujo completo en dos fases (`/password/reset/` y `/password/reset/confirm/`) con protección anti-enumeración de usuarios, tokens criptográficos efímeros (`PasswordResetTokenGenerator`) y revocación automática de sesiones previas tras la actualización.
-   [x] Email verification: Campo `is_email_verified` en modelo `User` (migración `0015_user_is_email_verified`), generador de tokens de confirmación (`EmailVerificationTokenGenerator`) y endpoints `/email/verify-request/` y `/email/verify/`.
-   [x] Google OAuth: Endpoint `/api/v1/auth/google/` para validación de `id_token` de Google Sign-In, provisión automática de usuarios con email verificado y emisión de par JWT.
-   [x] Revocación de sesiones: Endpoint `/api/v1/auth/sessions/revoke-all/` (cierre de sesión global mediante invalidación de todos los `OutstandingToken` en `BlacklistedToken`), integrado automáticamente en restablecimiento y cambio de clave.
-   [x] Logout: Endpoint `/api/v1/auth/logout/` con blacklisting del refresh token provisto.
-   [x] Rotación de refresh tokens: `ROTATE_REFRESH_TOKENS = True` y `BLACKLIST_AFTER_ROTATION = True` con detección y bloqueo de reuso.

Opcional posteriormente:
``` text
2FA (TOTP / WebAuthn)
```

------------------------------------------------------------------------

# 51. Fase 48 --- Sistema de búsqueda unificado [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Objetivo cumplido: Motor de búsqueda unificado multicanal con scoring fusionado y re-ranking.

``` text
                     SEARCH
                       │
          ┌────────────┼────────────┐
          │            │            │
       textual       fuzzy      semantic
          │            │            │
       PostgreSQL    pg_trgm   embeddings/vector
          │            │            │
          └────────────┼────────────┘
                       │
                    ranking
                       │
                    results
```

Hitos completados:
-   [x] **Canal Textual (PostgreSQL FTS):** Configuración en español (`spanish`), vectores ponderados en título (A), ISBN (A), autor (B), géneros (B) y descripción (C) con normalización de `SearchRank` a $[0, 1]$.
-   [x] **Canal Difuso (pg_trgm):** Similitud trigramática combinada con `Greatest(TrigramSimilarity, TrigramWordSimilarity)` sobre título, autor y sinopsis; tolerancia a erratas tipográficas leves y severas ("soledd" $\rightarrow$ "soledad", "Cortzar" $\rightarrow$ "Cortázar").
-   [x] **Canal Semántico (Embeddings & Conceptual Expansion):** Representación vectorial persistida en `Book.embedding` (`JSONField`), cálculo de similitud coseno vectorial en memoria con fallback inteligente a expansión conceptual temática (`ai.services.semantic_search_books`), y tarea Celery asíncrona `generate_book_embedding_task`.
-   [x] **Fusión Multicanal y Re-Ranking:** Algoritmo ponderado $S_{\text{unified}} = (0.45 \cdot S_{\text{text}}) + (0.30 \cdot S_{\text{fuzzy}}) + (0.25 \cdot S_{\text{semantic}}) + \text{boost}_{\text{rating}}$, con clasificación de coincidencia (`exact`, `fuzzy`, `semantic`, `hybrid`).
-   [x] **Endpoint Unificado:** `GET /api/v1/books/search/` con parámetros `q`, `mode` (`hybrid|text|fuzzy|semantic`), `category`, `author`, `min_rating`, `page`, `page_size`, `auto_import`, documentado con esquemas OpenAPI/Swagger.
-   [x] **Compatibilidad Retroactiva:** Refactorización limpia de `BookListCreateView` para delegar automáticamente en `UnifiedSearchEngine(mode='hybrid')` preservando orden y rendimiento sin regresiones.
-   [x] **Cobertura de Pruebas:** Suite exhaustiva `tests/test_phase48_unified_search.py` (14/14 tests pasando) y regresión de `tests/test_search_postgres.py` (9/9 tests pasando).

------------------------------------------------------------------------

# 52. Fase 49 --- Motor de recomendaciones v1 [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Algoritmo inicial determinista y explicable sin ML complejo.

Variables canónicas:
-   [x] **Género (`S_genre`):** Afinidad de categorías literarias derivada de lecturas, valoraciones y biblioteca del usuario.
-   [x] **Autor (`S_author`):** Afinidad hacia autores leídos y mejor calificados.
-   [x] **Rating (`S_rating`):** Calidad comunitaria y atractivo de valoración normalizado en $[0, 1]$.
-   [x] **Historial (`S_history`):** Nivel de experiencia del lector (`READ`, `READING`) y adecuación a su trayectoria con exclusión estricta de biblioteca propia.
-   [x] **Wishlist (`S_wishlist`):** Señal de intención explícita a partir de obras en `WANT_TO_READ` y listas de deseos personales.

Resultado:
-   [x] Suma ponderada canónica:
    $$\text{score} = (0.30 \cdot S_{\text{genre}}) + (0.25 \cdot S_{\text{author}}) + (0.15 \cdot S_{\text{rating}}) + (0.15 \cdot S_{\text{history}}) + (0.15 \cdot S_{\text{wishlist}})$$
-   [x] Explicabilidad transparente (`reason`) y desglose completo de puntuaciones (`breakdown`).
-   [x] Resolución de arranque en frío (*Cold-Start*) con obras destacadas para lectores noveles.
-   [x] Soporte en endpoints `GET /api/v1/books/recommendations/` con parámetro `strategy='v1'` o `version='v1'`.

Guardar versión:
-   [x] Versionado auditado: `algorithm_version = "v1"` persistido en respuestas y en eventos de feedback (`RecommendationFeedback`).
-   [x] Suite de pruebas automatizadas: `tests/test_phase49_recommendations_v1.py` (11/11 tests pasando al 100%).

------------------------------------------------------------------------

# 53. Fase 50 --- Motor de recomendaciones v2 [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Añadido filtrado colaborativo basado en usuarios con gustos similares (*User-User Similarity*).

Flujo implementado:
``` text
Jorge
 ↓
usuarios con gustos similares (K-NN por Jaccard y ratings comunes)
 ↓
libros que Jorge no ha leído (exclusión estricta)
 ↓
ranking híbrido v2 (fusión colaborativa + canónica v1)
```

Hitos completados:
-   [x] **Modelado de Afinidad Usuario-Usuario:** Similitud $\text{sim}(U, V) \in [0, 1]$ combinando coincidencia de catálogo compartido (Jaccard) y congruencia en valoraciones numéricas, con exclusión estricta de usuarios bloqueados.
-   [x] **Extracción de Candidatos Colaborativos:** Identificación de obras leídas o altamente valoradas por vecinos afines excluyendo la biblioteca del usuario objetivo.
-   [x] **Puntuación y Fusión Híbrida v2:** Agregación ponderada $S_{\text{collab}}$ fusionada con el motor canónico v1:
    $$S_{\text{v2}} = (\beta \cdot S_{\text{collab}}) + ((1 - \beta) \cdot S_{\text{v1}})$$
    con fallback transparente a contenido en caso de lectores noveles (Cold-Start).
-   [x] **Explicabilidad y Desglose:** `reason` contextual identificando a los lectores afines ("Leído y recomendado por lectores con gustos muy similares a los tuyos como @lectorX") y desglose `breakdown.collaborative`.
-   [x] **Versionado Auditado:** `algorithm_version = "v2"` persistido en respuestas y telemetría de feedback.
-   [x] **Endpoints y API:** Soporte de `strategy='v2'` y `version='v2'` en `GET /api/v1/books/recommendations/`, y nuevo endpoint `GET /api/v1/books/recommendations/similar-readers/` para consultar lectores gemelos.
-   [x] **Cobertura de Pruebas:** Nueva suite `tests/test_phase50_recommendations_v2.py` (10/10 tests pasando al 100%) y regresión completa (26/26 tests pasando).

------------------------------------------------------------------------

# 54. Fase 51 --- Motor de recomendaciones v3 [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Motor de recomendaciones semántico basado en embeddings vectoriales y vector de preferencias de usuario (*User Preference Embedding* & *Semantic Vector Matching*).

Flujo implementado:
``` text
libros consumidos / leídos / calificados
 ↓
promedio ponderado (weighted average) por satisfacción y lectura
 ↓
vector de preferencias del usuario U (normalizado en norma unitaria)
 ↓
similitud coseno contra libros no consumidos S_semantic
 ↓
fusión tri-híbrida v3 (semántica 45% + colaborativa 30% + contenido canónico 25%)
```

Hitos completados:
-   [x] **Vector Sintético de Preferencias ($\vec{U}$):** Cálculo dinámico y en caché del centroide ponderado de embeddings de las obras leídas, en curso y deseadas, priorizando calificaciones de 5 estrellas (1.50) y 4 estrellas (1.20) sobre estados `READ` (1.00), `READING` (0.70) y `WANT_TO_READ` (0.50), con normalización euclídea unitaria ($\|\hat{U}\|_2 = 1.0$).
-   [x] **Similitud Semántica Vectorial ($S_{\text{semantic}}$):** Similitud coseno en memoria de alta velocidad entre el vector de preferencias de usuario y los embeddings vectoriales persistidos en `Book.embedding` (`JSONField`).
-   [x] **Fusión Tri-Híbrida v3:**
    $$S_{\text{v3}} = (0.45 \cdot S_{\text{semantic}}) + (0.30 \cdot S_{\text{collab}}) + (0.25 \cdot S_{\text{content\_v1}})$$
    con mitigación automática de arranque en frío si el usuario o los libros carecen de embeddings vectoriales.
-   [x] **Explicabilidad y Desglose Detallado:** Motivo enriquecido destacando afinidad semántica y de estilo ("Afinidad semántica profunda con los temas y estilo de tus libros favoritos"), con desglose completo en `breakdown` (`semantic`, `collaborative`, `content_v1`, `has_user_embedding`).
-   [x] **Auditoría y Versionado:** `algorithm_version = "v3"` garantizado en respuestas y en telemetría de eventos de feedback (`RecommendationFeedback`).
-   [x] **Endpoints y API REST:**
    -   `GET /api/v1/books/recommendations/?strategy=v3` (o `version=v3`).
    -   `GET /api/v1/books/recommendations/user-embedding/`: Endpoint para auditoría, inspección y visualización del vector sintético de preferencias, dimensionalidad y obras analizadas.
-   [x] **Cobertura de Pruebas:** Suite exhaustiva `tests/test_phase51_recommendations_v3.py` (9/9 tests pasando al 100%) y suite de regresión completa v1+v2+v3 (30/30 tests pasando).

------------------------------------------------------------------------

# 55. Fase 52 --- Recomendaciones explicables [COMPLETADA]

Cada recomendación debe poder explicar:

``` text
¿Por qué?
```

Ejemplo canónico implementado:

``` text
Te recomendamos Dune porque:

✓ te han gustado 5 libros de ciencia ficción;
✓ has valorado 1984 con 5 estrellas;
✓ tiene similitud semántica alta con Fundación;
✓ 3 usuarios que sigues lo han leído.
```

### Entregables implementados y verificados:
- [x] **Motor multi-señal (`RecommendationExplanationEngine`):**
  - Señal de género/temática (`genre`): conteo de obras disfrutadas en la categoría.
  - Señal de autoría y libros ancla (`author`): obras valoradas con altas calificaciones del mismo autor.
  - Señal semántica vectorial (`semantic`): similitud coseno sobre embeddings respecto a lecturas favoritas.
  - Señal de grafo social (`social`): usuarios seguidos que han leído la recomendación.
  - Señal colaborativa comunitaria (`collaborative`): afinidad de lectores gemelos o afines (v2).
  - Señal de aclamación comunitaria (`community`) y lista de deseos (`wishlist`).
- [x] **Integración transparente en motores de recomendación:** Inclusión del payload estructurado `explanation` en las respuestas de `v1`, `v2` y `v3`.
- [x] **API REST dedicada:** Endpoint `GET /api/v1/books/recommendations/<book_id>/explain/` para modal o consulta bajo demanda de la justificación multi-señal.
- [x] **Pruebas y Regresión:** Suite `tests/test_phase52_explainable_recommendations.py` (9/9 tests pasando al 100%) y regresión de recomendaciones v1+v2+v3 (30/30 tests pasando).

------------------------------------------------------------------------

# 56. Fase 53 --- Feed inteligente [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Transformación del muro social desde un listado cronológico plano a un ranking dinámico multicriterio ponderado (`SmartFeedRankingEngine`), preservando la vista cronológica clásica bajo demanda del usuario.

### Entregables implementados y verificados:
- [x] **Motor de Ranking Multicriterio (`SmartFeedRankingEngine`):**
  - **Recency ($w = 0.30$):** Decaimiento exponencial temporal ($e^{-\Delta t / 72\text{h}}$) para priorizar frescura temporal sin ocultar contenido relevante reciente.
  - **Relationship ($w = 0.25$):** Ponderación del grafo social: máxima puntuación para amistades mutuas (`is_friend = True`), usuarios seguidos e histórico de interacciones comunitarias (likes y comentarios).
  - **Engagement ($w = 0.25$):** Peso intrínseco del tipo de evento (`REVIEW_CREATED`, `BOOK_FINISHED` > `BOOK_ADDED`) incrementado con la tracción social activa de la reseña (`likes` y `comments`).
  - **Content Relevance ($w = 0.20$):** Afinidad de categorías con el perfil lector del usuario, autores frecuentes y presencia del libro en la lista de deseos (`wishlist` o `want_to_read`).
- [x] **Insignias y Señales Explicativas (`feed_signal`):**
  - Generación de señales comprensibles ("De tu lista de deseos", "Amistad mutua", "Reseña destacada", "En tus géneros favoritos", etc.) para aportar total transparencia algorítmica al feed.
- [x] **Endpoints y Control de Modo:**
  - Soporte de parámetro `?mode=smart` (por defecto) y `?mode=chronological` tanto en `/api/v1/users/feed/` como en `/api/v1/books/feed/`.
  - Serialización enriquecida en `ActivitySerializer` con `score`, `feed_signal` y `timestamp`.
  - Respeto estricto de bloqueos de usuarios (`is_blocked`).
- [x] **Experiencia de Usuario en Frontend:**
  - Conmutador interactivo de doble modo ("✨ Para ti" / "🕒 Cronológico") en `Home.tsx` con recarga asíncrona.
  - Renderizado de badges `feed_signal`, textos descriptivos de eventos y estrellas/reseñas asociadas.
- [x] **Pruebas y Verificación:**
  - Suite dedicada `backend/tests/test_phase53_smart_feed.py` (10/10 tests pasando).
  - Suite de regresión social `backend/tests/test_social_feed.py` (7/7 tests pasando).
  - Verificación estricta de tipos en frontend (`npm run typecheck` con 0 errores).

------------------------------------------------------------------------

# 57. Fase 54 --- Gamificación opcional [COMPLETADA]

**Prioridad:** P2 - COMPLETADA

Sistema integral de motivación y hábitos de lectura con arquitectura desacoplada, no intrusiva y 100% opcional (conmutable por el usuario mediante `gamification_enabled`).

### Entregables implementados y verificados:
- [x] **Modelos de Datos y Migraciones:**
  - `ReadingGoal`: Metas anuales configurables (`target_books`, `target_pages`, año) con cálculo dinámico de ritmo/pacing ("Adelantado", "Al día", "Por detrás").
  - `ReadingStreak`: Racha de lectura consecutiva (`current_streak`, `longest_streak`, `last_reading_date`) con detección automática de continuidad e inactividad.
  - `DailyReadingLog`: Registro diario de páginas, minutos y obras leídas (`user`, `date`, `pages_read`, `minutes_read`, `books`).
  - `Badge` y `UserBadge`: Catálogo extensible de insignias y logros por categorías (`reading`, `streak`, `reviews`, `challenges`, `community`) con asignación idempotente.
  - `ReadingChallenge` y `UserChallenge`: Retos comunitarios periódicos y temáticos con progreso porcentual y recompensa de insignia.
  - Campo `gamification_enabled` en modelo `User` con migración aplicada (`users.0016`).
- [x] **Servicio Central de Gamificación (`GamificationService`):**
  - Siembra idempotente de insignias iniciales (`ensure_default_badges`).
  - Registro de lectura diaria (`record_daily_reading`), evaluación de objetivos (`evaluate_reading_goal`) y desbloqueo automático de insignias por hitos (`evaluate_user_badges`).
  - Detección de rotura de racha por omisión de días (`get_or_calculate_streak`).
  - Avance reactivo de retos en `on_book_finished`, `on_review_created` y lectura diaria.
- [x] **API REST y Endpoints DRF:**
  - `GET /api/v1/gamification/overview/`: Resumen integral respetando preferencias y privacidad del usuario.
  - `GET, POST /api/v1/gamification/goals/`: Fijar o consultar objetivo anual.
  - `POST /api/v1/gamification/log/`: Registrar sesión diaria o pulsar "He leído hoy".
  - `GET /api/v1/gamification/badges/`: Catálogo de insignias con estado de desbloqueo.
  - `GET /api/v1/gamification/challenges/`: Retos activos con progreso personal.
  - `POST /api/v1/gamification/challenges/<slug>/join/`: Inscripción en retos.
  - `PATCH /api/v1/gamification/preferences/`: Conmutador de activación/desactivación opcional.
- [x] **Componentes e Integración Frontend:**
  - `ReadingGoalCard`: Tarjeta de progreso anual con barra graduada y fijación de meta.
  - `ReadingStreakCard`: Tarjeta de racha con llama animada y botón rápido "He leído hoy".
  - `BadgesGrid`: Escaparate con filtro por categorías y distinción entre desbloqueadas y bloqueadas.
  - `ActiveChallengesCard`: Tarjetas de retos con barra de progreso y botón de inscripción.
  - Integración en `ReadingStats.tsx` y `Profile.tsx`.
  - Control de activación opcional en `EditProfileForm.tsx`.
- [x] **Pruebas y Verificación:**
  - Suite dedicada `backend/tests/test_phase54_gamification.py` (**8/8 tests PASSED**).
  - Comprobación estricta de tipos TypeScript (`npm run typecheck` con **0 errores**).
  - Suite de pruebas de frontend (`npx vitest run`: **21/21 tests PASSED**).

------------------------------------------------------------------------

# 58. Fase 55 --- Importación avanzada [COMPLETADA]

Mejorar importadores para:

``` text
Google Books
OpenLibrary
ISBN
CSV
```

Posteriormente:

``` text
Goodreads CSV
Calibre
```

si tiene sentido para el producto.

Siempre con:

``` text
preview
deduplication
validation
rollback
```

### Implementación realizada:
- [x] **Detección Automática de Formatos (`CSVFormatDetector`)**:
  - Reconocimiento de **Goodreads CSV** (`Exclusive Shelf`, `My Rating`, `ISBN13`, limpieza de fórmulas `="978..."`).
  - Reconocimiento de **Calibre CSV** (`identifiers`, `tags`, `rating`, mapeo de tags a categorías).
  - Reconocimiento de **CSV Genérico** (`title`, `author`, `isbn`, `status`, `rating`, `review`).
- [x] **Previsualización No Destructiva (`POST /api/v1/books/import/csv/preview/`)**:
  - Analiza el archivo sin modificar la base de datos.
  - Clasifica cada libro con badge de destino: `new` (🟢 nuevo en catálogo y biblioteca), `in_catalog` (🟡 ya existe en catálogo general, se agregará a tu estantería), `in_library` (⚪ ya en tu estantería personal).
  - Devuelve métricas agregadas de válidos, inválidos y destinos.
- [x] **Deduplicación Multinivel**:
  - Búsqueda por ISBN normalizado (ISBN-10 / ISBN-13).
  - Búsqueda por ID externo (`google_books_id`, `openlibrary_id`).
  - Búsqueda por coincidencia exacta insensible a mayúsculas/minúsculas de `(title, author)`.
- [x] **Validación Rigurosa**:
  - Validación de título obligatorio y autor.
  - Normalización de ISBN y mapeo de estados de estantería (`want_to_read`, `reading`, `read`, `abandoned`).
  - Validación de rango de puntuación (1 a 5) y extracción de notas/reseñas.
- [x] **Interfaz de Usuario (`ImportBooksModal.tsx` en `Library.tsx`)**:
  - Modal con zona de arrastrar y soltar (drag & drop) o selector de archivo `.csv`.
  - Guía informativa de cómo exportar desde Goodreads y Calibre.
  - Tabla de vista previa con insignias de estado y destino.
  - Botón de confirmación con indicador de progreso y resumen final.

------------------------------------------------------------------------

# 59. Fase 56 --- Importación idempotente [COMPLETADA]

Garantizar:

``` text
mismo ISBN
+
misma fuente
+
mismo external ID
=
mismo Book
```

Evitar duplicados aunque el cliente reintente la petición.

### Implementación realizada:
- [x] **Transacciones Atómicas y Rollback (`POST /api/v1/books/import/csv/confirm/`)**:
  - Ejecución integral dentro de `transaction.atomic()`. Si ocurre un error fatal o inconsistencia irrecuperable, se produce rollback garantizado sin estados intermedios.
- [x] **Garantía de Idempotencia**:
  - La re-ejecución repetida de la importación sobre el mismo CSV o con reintentos de red no crea duplicados de `Book`, `UserBook` ni `Review`.
  - Actualiza o preserva los registros existentes de manera limpia y devuelve contadores exactos de creados vs. actualizados.
- [x] **Verificación Automatizada**:
  - Suite de pruebas completa en `backend/tests/test_phase55_advanced_import.py` (7/7 tests **PASSED**).
  - Comprobación de tipos en frontend (`tsc --noEmit` con **0 errores**).
  - Suite de pruebas de frontend (`vitest run`: **21/21 tests PASSED**).

------------------------------------------------------------------------

# 60. Fase 57 --- Administración [COMPLETADA]

Mejorar Django Admin para:

``` text
Books
Authors
Reviews
Users
Reports
Erratas
Notifications
Activities
```

Filtros:

``` text
status
created_at
rating
provider
```

Acciones masivas:

``` text
re-enrich
rebuild embedding
moderate
```

### Implementación realizada:
- [x] **ModelAdmins en Django Admin (`backend/books/admin.py`, `backend/users/admin.py`)**:
  - `BookAdmin`: list_display extendido, filtros `ProviderListFilter` (Google Books, OpenLibrary, ISBN), `RatingRangeFilter`, `enrichment_attempted`, `categories`, `created_at`. Acciones masivas `re_enrich_books` y `rebuild_embeddings`.
  - `AuthorAdmin`: list_display, búsqueda por nombre y biografía, filtro por enriquecimiento, acción masiva `re_enrich_authors`.
  - `ReviewAdmin`: list_display, filtros por moderación, calificación y fechas, acciones masivas `mark_as_moderated`, `unmark_as_moderated`, `soft_delete_reviews`, `restore_reviews`.
  - `CustomUserAdmin`: list_display, filtros por rol, staff, editor, activo, privacidad y fecha, acciones masivas `ban_users`, `unban_users`, `make_editor`, `remove_editor`.
  - `ReportAdmin`: list_display, filtros por estado, motivo y fecha, acciones masivas `mark_as_resolved`, `mark_as_rejected`.
  - `ErrataAdmin`: list_display, filtros por estado, tipo y fecha, acciones masivas `approve_erratas`, `reject_erratas`.
  - `NotificationAdmin` y `ActivityAdmin`: registros completos con filtros y acciones de marcado de lectura.
- [x] **API REST de Administración Ampliada (`backend/books/admin_views.py`, `backend/books/admin_urls.py`, `backend/books/serializers.py`)**:
  - `BookSerializer`: soporte de escritura directa para `category_ids`.
  - `AdminBookListView`: filtros por `provider`, `min_rating`, `enrichment`, `ordering`.
  - Endpoints de acciones masivas en lote: `POST /api/v1/admin/books/bulk-action/` y `POST /api/v1/admin/authors/bulk-action/`.
  - Endpoint de listado de categorías: `GET /api/v1/admin/categories/`.
- [x] **Control Total de Catálogo desde el Frontend (`AdminDashboard.tsx`)**:
  - Pestaña de Catálogo enriquecida con subpestañas para Libros y Autores.
  - Filtros en vivo por proveedor externo (`Google Books`, `OpenLibrary`, `Con ISBN`), enriquecimiento (`Enriquecidos`, `Pendientes`) y puntuación mínima.
  - Barra de acciones masivas en lote con selección mediante checkboxes (`re-enriquecer`, `reconstruir embeddings`, `eliminar`).
  - Modal interactivo de creación y edición completa de libros (`EditBookModal`) con selector de autor, ISBN, fecha, categorías interactivas y sinopsis.
  - Modal interactivo de creación y edición completa de autores (`EditAuthorModal`) con nombre y biografía.
- [x] **Verificación Automatizada y Tipos**:
  - Suite de pruebas de backend en `backend/tests/test_phase57_admin.py` (6/6 tests **PASSED**).
  - Suite de regresión en `backend/tests/test_admin_api.py` (4/4 tests **PASSED**).
  - Linter backend `ruff check` con 0 errores.
  - Tipado de frontend `tsc --noEmit` con **0 errores**.
  - Pruebas frontend `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 61. Fase 58 --- Moderación de contenido [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado un sistema integral de moderación de contenido y disciplina comunitaria que cubre las 7 herramientas esenciales y establece el marco ético y normativo previo a la automatización mediante IA:

1. **`report`**:
   - Endpoint autenticado `POST /api/v1/reports/` y `GET /api/v1/reports/my/`.
   - Componente modal universal en frontend (`ReportModal.tsx`) integrado en reseñas (`BookReviewsSection.tsx`), comentarios y perfiles de usuarios (`Profile.tsx`).
2. **`review`**:
   - Cola de moderación administrativa con filtros multicriterio en `AdminDashboard.tsx`.
   - Tramitación formal y resolución de expedientes (`OPEN`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`) con asignación de moderador y marca temporal.
3. **`hide`**:
   - Endpoint administrativo `POST /api/v1/admin/moderation/hide/` para ocultar reseñas (`is_moderated=True`), comentarios (`deleted_at=now`) y mensajes (`is_moderated=True`).
4. **`restore`**:
   - Endpoint administrativo `POST /api/v1/admin/moderation/restore/` para restaurar contenido previamente moderado o tras resolver una apelación favorable.
5. **`ban`**:
   - Endpoints administrativos `POST /api/v1/admin/moderation/users/<id>/ban/` y `unban/` para suspensión y reactivación de cuentas infractoras (`is_active=False/True`), con protección ante auto-baneo y baneo de administradores.
6. **`mute`**:
   - **Silenciamiento Social (Usuario a Usuario)**:
     - Relación M2M `muted_users` en `User` y endpoints `POST /api/v1/users/<id>/mute/` y `unmute/`.
     - Filtrado automático de reseñas en `filter_visible_reviews`, comentarios en `ReviewCommentListCreateView` y omisión de notificaciones.
     - Botón de silenciar/des-silenciar en el menú contextual de perfil de usuario.
   - **Silenciamiento Disciplinario (Moderación)**:
     - Campo `muted_until` en `User` y endpoints `POST /api/v1/admin/moderation/users/<id>/mute/` y `unmute/`.
     - Acciones `MUTE_USER_24H` y `MUTE_USER_7D` en la resolución de denuncias.
     - Restricción estricta (`403 Forbidden`) en endpoints de creación de reseñas, comentarios y mensajes mientras dure la sanción.
7. **`block`**:
   - Bloqueo social bidireccional severo (`User.blocked_users`, `POST /api/v1/users/<id>/block/` y `unblock/`), integrado con selector en el perfil de usuario.
8. **Políticas de Moderación Pre-IA**:
   - Documento normativo [docs/moderation_policies.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/moderation_policies.md) con tipología de infracciones (Nivel 1, 2, 3), escala disciplinaria gradual, garantías de apelación y salvaguardas éticas (*Human-in-the-Loop*, umbrales >95% de confianza) antes de la activación de IA.
9. **Trazabilidad y Tests**:
   - Trazabilidad inmutable en `AuditLog` para todas las acciones de moderación.
   - Suite de pruebas completa `backend/tests/test_phase58_moderation.py` (**7/7 tests PASSED**).
   - Suite de regresión `test_phase57_admin.py` y `test_admin_api.py` (**10/10 tests PASSED**).
   - Verificación estricta de tipos TypeScript `tsc --noEmit` (**0 errores**) y Vitest (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 62. Fase 59 --- Seguridad de contenido generado por usuarios [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado una estrategia integral de defensa en profundidad (*Defense in Depth*) para la sanitización y neutralización de ataques XSS / inyección HTML en todo el contenido generado por usuarios (UGC):

1. **Defensa en Profundidad (Frontend + Backend)**:
   - **Frontend (DOMPurify)**:
     - Sanitización proactiva en el editor enriquecido Tiptap (`BioEditor.tsx`) antes de propagar cambios en `onUpdate`.
     - Todas las visualizaciones de HTML (`dangerouslySetInnerHTML`) están blindadas con `DOMPurify.sanitize(...)` (`Profile.tsx`, `BookDetail.tsx`, `TermsOfService.tsx`, `AdminDashboard.tsx`).
   - **Backend (Ammonia / `nh3`)**:
     - Biblioteca de alto rendimiento escrita en Rust (`nh3>=0.2.14`) integrada en backend (`backend/mybookconnect/html_sanitizer.py`).
     - No confía en los clientes ni en el frontend: sanea todo payload antes de la validación y persistencia en base de datos.
2. **Superficies Protegidas (UGC)**:
   - **Perfiles (`profiles`)**:
     - `bio`: Sanitización enriquecida (`sanitize_html`), permitiendo únicamente etiquetas semánticas y seguras (`<p>`, `<strong>`, `<em>`, `<h1>`-`<h6>`, `<blockquote>`, `<ul>`, `<ol>`, `<li>`, `<code>`, `<pre>`, `<a>`), forzando `rel="noopener noreferrer nofollow"` y neutralizando URIs `javascript:`, scripts y manejadores de eventos en `UserUpdateSerializer` y `UserCreateSerializer`.
     - `location`, `first_name`, `last_name`: Eliminación total de etiquetas HTML (`sanitize_plain_text`).
   - **Reseñas (`reviews`)**:
     - `title`: Eliminación de etiquetas HTML para título en texto plano limpio.
     - `text`: Sanitización de HTML enriquecido en `ReviewSerializer` y `ReviewListCreateView.create`, neutralizando scripts, iframes y atributos inline (`onerror`, `onclick`).
   - **Comentarios (`comments`)**:
     - `content`: Sanitizado en `ReviewCommentSerializer` y `ReviewCommentListCreateView.post`.
   - **Mensajería / Chat (`chat`)**:
     - `text`: Sanitizado en `MessageSerializer.validate_text` mediante `sanitize_plain_text`, previniendo cualquier inyección en mensajes directos y WebSockets.
3. **Verificación y Pruebas**:
   - Suite de pruebas automatizada `backend/tests/test_phase59_ugc_security.py` (**10/10 tests PASSED**).
   - Linter Python `ruff check` (**0 errores, All checks passed!**).
   - Verificación estricta de tipos TypeScript `tsc --noEmit` (**0 errores**).
   - Suite de pruebas frontend Vitest `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 63. Fase 60 --- Seguridad de imágenes [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado una infraestructura avanzada y multicapa para el procesamiento, validación e higienización de imágenes en el backend:

1. **Redimensionamiento Inteligente (*resize / downscale*)**:
   - Presets adaptados por caso de uso en `media_security.py`:
     - `AVATAR_PRESET = (512, 512)` para avatares de usuario.
     - `AUTHOR_PHOTO_PRESET = (800, 1200)` para fotos de autores.
     - `COVER_PRESET = (1200, 1800)` para portadas de libros.
     - `CHAT_IMAGE_PRESET = (1920, 1920)` para imágenes adjuntas en mensajería/chat.
   - Algoritmo de remuestreo de alta calidad `Image.Resampling.LANCZOS` que preserva la relación de aspecto original (*aspect ratio*) sin distorsionar la imagen.
   - Si la imagen original es menor al preset, no se sobredimensiona artificialmente.
2. **Eliminación Profunda de Metadatos (*strip metadata*)**:
   - Purgado exhaustivo de bloques `exif`, `icc_profile`, `photoshop`, `xmp`, `comment`, `parameters` y `Software` en `sanitize_image`.
   - Re-codificación limpia en buffer en memoria para JPEG, PNG y WebP, eliminando cualquier carga maliciosa oculta en cabeceras o metadatos manipulados.
3. **Validación Estricta de MIME y Magic Bytes**:
   - Verificación estricta de extensiones permitidas (`.jpg`, `.jpeg`, `.png`, `.webp`).
   - Verificación de tipos MIME declarados en la petición HTTP contra `ALLOWED_MIME_TYPES`.
   - Inspección binaria de firmas de cabecera (*Magic Bytes*):
     - JPEG: `\xff\xd8\xff`
     - PNG: `\x89PNG\r\n\x1a\n`
     - WebP: `RIFF....WEBP`
   - Comprobación de consistencia obligatoria entre firma binaria, MIME declarado y formato decodificado por Pillow, bloqueando discrepancias y archivos camuflados (ejecutables, polyglots, scripts).
4. **Control de Dimensiones y Bombas de Descompresión**:
   - Validación de resolución mínima (50x50 px) y techo máximo de subida (6000x6000 px).
   - Manejo explícito de `Image.DecompressionBombError` para prevenir ataques de denegación de servicio (DoS).
5. **Arquitectura para Escáner Antivirus / Malware (`media_scanner.py`)**:
   - Módulo pluggable con interfaz base `BaseMediaScanner`.
   - Implementación `ClamAVScanner` con protocolo TCP/INSTREAM para demonios ClamAV en entornos de producción.
   - Implementación `SecurityHeuristicScanner` con detección de la firma estándar EICAR y detección de cabeceras ejecutables camufladas (`MZ`, `\x7fELF`), bloqueando de inmediato cualquier archivo infectado con `ValidationError`.
6. **Verificación y Pruebas**:
   - Suite de pruebas de la fase: `backend/tests/test_phase60_image_security.py` (**15/15 tests PASSED**).
   - Suite de regresión de medios: `backend/tests/test_phase28_media_security.py` (**17/17 tests PASSED**).
   - Suite de regresión UGC: `backend/tests/test_phase59_ugc_security.py` (**10/10 tests PASSED**).
   - Linter Python `ruff check` (**0 errores, All checks passed!**).
   - Verificación estricta de tipos TypeScript `tsc --noEmit` (**0 errores**).
   - Suite de pruebas frontend Vitest `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 64. Fase 61 --- Contrato de errores API [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado un contrato unificado, predecible y estandarizado de respuestas de error para todos los endpoints de la API, manteniendo total retrocompatibilidad con clientes existentes y pruebas preexistentes:

1. **Estructura Unificada de Error**:
   - Formato estándar implementado en todas las respuestas con código HTTP >= 400 bajo `/api/`:
     ```json
     {
       "error": {
         "code": "REVIEW_ALREADY_EXISTS",
         "message": "El usuario ya tiene una reseña para este libro.",
         "details": {}
       }
     }
     ```
2. **Códigos de Error Estables (`ErrorCode`)**:
   - `AUTH_INVALID` (401 - Credenciales no suministradas, inválidas o expiradas).
   - `PERMISSION_DENIED` (403 - Permisos insuficientes para el recurso).
   - `NOT_FOUND` (404 - Recurso no encontrado).
   - `VALIDATION_ERROR` (400 - Parámetros de solicitud o datos de entrada no válidos).
   - `REVIEW_ALREADY_EXISTS` (409/400 - El usuario ya tiene una reseña para el libro indicado).
   - `BOOK_DUPLICATE` (409/400 - Ya existe un libro con ese título/autor o ISBN en el catálogo).
   - `USER_BLOCKED` (403 - Interacción rechazada debido a bloqueo mutuo o silenciamiento disciplinario).
   - `RATE_LIMITED` (429 - Límite de tasa de peticiones excedido con tiempo de espera dinámico).
   - `METHOD_NOT_ALLOWED` (405 - Verbo HTTP no soportado por el endpoint).
   - `INTERNAL_SERVER_ERROR` (500 - Error inesperado del servidor protegido y registrado).
3. **Manejador Centralizado de Excepciones y Middleware**:
   - `custom_exception_handler` registrado en `REST_FRAMEWORK['EXCEPTION_HANDLER']` en `settings.py`.
   - Clases de excepción de dominio específicas: `ReviewAlreadyExistsError`, `BookDuplicateError`, `UserBlockedError`, `RateLimitedError`.
   - `ApiErrorContractMiddleware` registrado en `MIDDLEWARE` para normalizar también aquellas vistas que devuelven directamente `Response({'detail': ...}, status=4xx)` sin lanzar excepciones.
4. **Retrocompatibilidad Garantizada**:
   - Preservación de claves heredadas a nivel de raíz (`detail`, `avatar`, `cover_image`, `title`, etc.) en la respuesta, garantizando que clientes y suites de tests previos continúen funcionando sin romperse.
5. **Cliente Frontend Unificado**:
   - Definición de interfaces tipadas `ApiErrorData`, `ApiErrorResponse` y clase de excepción de primera clase `ApiError extends Error` en `frontend/src/api/client.ts`.
   - `apiClient` extrae automáticamente `error.code`, `error.message` y `error.details` para un manejo declarativo y robusto en la UI.
6. **Verificación y Pruebas**:
   - Suite de pruebas de contrato: `backend/tests/test_phase61_error_contract.py` (**16/16 tests PASSED**).
   - Suites de regresión: `test_phase60_image_security.py`, `test_phase59_ugc_security.py`, `test_phase28_media_security.py`, `test_review_social.py` (**48/48 tests PASSED**).
   - Linter Python `ruff check` (**0 errores, All checks passed!**).
   - Verificación estricta de tipos TypeScript `tsc --noEmit` (**0 errores**).
   - Suite de pruebas frontend Vitest `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 65. Fase 62 --- Idempotencia [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado una arquitectura de idempotencia robusta para operaciones sensibles, costosas y tolerantes a reintentos automáticos de red:

1. **Gestor Central de Idempotencia (`IdempotencyManager` en `backend/mybookconnect/idempotency.py`)**:
   - Soporte para cabeceras HTTP estándar `Idempotency-Key` y alias `X-Idempotency-Key` (hasta 128 caracteres).
   - Cálculo determinista de hash SHA-256 sobre el cuerpo (`request.data` / `request.body`) y query parameters, garantizando consistencia independientemente del orden de claves en JSON.
   - Prevención de condiciones de carrera e in-flight duplication mediante bloqueos atómicos en Redis (`cache.add("lock:...")` con TTL de 60s). Peticiones concurrentes idénticas reciben **409 Conflict**.
   - Detección de discrepancia de payload: si se reutiliza una misma clave con un payload distinto, se rechaza de inmediato con **400 Bad Request** (`VALIDATION_ERROR`).
   - Retransmisión transparente de respuestas completadas desde caché con cabecera `Idempotent-Replayed: true` (TTL por defecto: 24 horas).
2. **Decorador `@idempotent(required=False, timeout=86400)`**:
   - Anotación declarativa y modular para métodos de vistas DRF (`APIView`, `generics`, `viewsets`).
   - Marca `request._idempotency_handled = True` para evitar doble procesamiento por middlewares.
3. **Middleware Global (`IdempotencyMiddleware` en `backend/mybookconnect/middleware.py`)**:
   - Intercepta cualquier petición mutante (`POST`, `PUT`, `PATCH`, `DELETE`) bajo `/api/` que incluya `Idempotency-Key` y no haya sido consumida por un decorador, garantizando soporte transversal en toda la API.
   - Preserva el atributo `.data` en respuestas intermedias `JsonResponse` para compatibilidad completa con el cliente de pruebas de DRF y consumidores API.
4. **Endpoints Blindados con Idempotencia**:
   - `POST /api/v1/books/import/` (`ImportBookView`): importación de libros por ISBN o título desde proveedores externos (Google Books, OpenLibrary).
   - `POST /api/v1/books/import/csv/confirm/` (`CSVImportConfirmView`): confirmación e importación masiva atómica de bibliotecas CSV.
   - `POST /api/v1/books/authors/<pk>/refresh-books/` (`AuthorBookRefreshView`): refresco y sincronización de catálogo de un autor.
   - `POST /api/v1/books/sync/external/` (`ExternalSyncView`): nuevo endpoint unificado para sincronización externa bajo demanda por ISBN, autor o título.
   - `POST /api/v1/users/notifications/` y `/api/v1/notifications/` (`NotificationListView` / `NotificationCreateView`): emisión y registro de notificaciones de sistema y usuario con `NotificationCreateSerializer`, previniendo notificaciones duplicadas ante reintentos.
5. **Soporte Frontend (`frontend/src/api/client.ts`)**:
   - `RequestOptions` extendido con `idempotencyKey?: string`.
   - Inyección automática de `Idempotency-Key` en las cabeceras HTTP de peticiones cliente.
6. **Verificación y Pruebas**:
   - Suite de la fase: `backend/tests/test_phase62_idempotency.py` (**12/12 tests PASSED**).
   - Suites de regresión: `test_phase61_error_contract.py` y `test_phase55_advanced_import.py` (**23/23 tests PASSED**).
   - Linter Python `ruff check` (**0 errores, All checks passed!**).
   - Verificación estricta de tipos TypeScript `tsc --noEmit` (**0 errores**).
   - Suite de pruebas frontend Vitest `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 66. Fase 63 --- Transacciones [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha blindado la consistencia transaccional ACID en todas las operaciones que actualizan múltiples entidades relacionadas, garantizando rollback completo ante cualquier fallo imprevisto:

1. **Creación/Edición de Reseñas y Gamificación (`backend/books/views.py`)**:
   - `ReviewListCreateView.create`: encapsulado en `transaction.atomic()` para asegurar que la persistencia de `Review` y la evaluación de insignias y rachas (`GamificationService.evaluate_user_badges`) sean atómicas.
   - `ReviewDetailView`: métodos `perform_update` y `perform_destroy` blindados con `transaction.atomic()`.
   - `ReviewLikeToggleView.post`: creación/borrado de `ReviewLike` y emisión de `Notification` bajo `transaction.atomic()`.
   - `ReviewCommentListCreateView.post`: creación de `ReviewComment` y notificación al autor bajo `transaction.atomic()`.
   - `ReviewCommentDeleteView.delete`: borrado de comentario encapsulado en `transaction.atomic()`.

2. **Relaciones Sociales y Auditoría (`backend/users/views.py`)**:
   - `FollowUserView.post`: adición de relación de seguimiento (`user.following.add`), notificación para el usuario seguido (`Notification.objects.create`) y registro de actividad social (`record_activity`) protegidos bajo `transaction.atomic()`.
   - `UnfollowUserView.post`: eliminación de seguimiento bajo `transaction.atomic()`.
   - `BlockUserView.post`: bloqueo (`user.blocked_users.add`), ruptura bidireccional inmediata del seguimiento (`userA.following.remove(userB)` y `userB.following.remove(userA)`) y registro de auditoría (`AuditLog`) atómicos.
   - `UnblockUserView.post`, `MuteUserView.post`, `UnmuteUserView.post`: mutación de estado y auditoría bajo `transaction.atomic()`.
   - `toggle_editor`, `NotificationMarkReadView`, `NotificationMarkAllReadView`: estados actualizados bajo `transaction.atomic()`.

3. **Catálogo, Estanterías y Listas de Lectura (`backend/books/views.py`)**:
   - `UserBookListCreateView.perform_create`, `UserBookDetailView.perform_update` y `perform_destroy`: protegidos bajo `transaction.atomic()`.
   - `ReadingListViewSet`: acciones `perform_create`, `perform_update`, `perform_destroy`, `add_book`, `remove_book`, `reorder`, `follow` y `unfollow` encapsuladas en `transaction.atomic()`.

4. **Importación Multi-Proveedor (`backend/books/services/import_service.py`)**:
   - `_create_or_get_from_volume`: creación del autor, guardado de libro y vinculación M2M de categorías atómicos (evita libros huérfanos sin autor o categorías ante caídas).
   - `import_single_by_query`: fallback de OpenLibrary con autor + libro + categorías + portada bajo `transaction.atomic()`.
   - `_import_from_wikipedia_by_title` y `_import_from_openlibrary_by_title`: importación atómica por cada volumen procesado.
   - `_import_books_by_author_from_wikipedia`: creación y asociación de portada atómica.

5. **Moderación Disciplinaria y Administrativa (`backend/users/moderation_views.py`)**:
   - `AdminReportDetailView.update`: resolución/rechazo de reportes, aplicación de sanciones (ocultación de reseñas/comentarios/mensajes, baneo, silenciamiento temporal) y registro de auditoría (`AuditLog`) blindados en bloque `transaction.atomic()`.
   - `AdminContentHideView`, `AdminContentRestoreView`, `AdminUserMuteView`, `AdminUserUnmuteView`, `AdminUserBanView`, `AdminUserUnbanView`: mutación directa y auditoría completamente atómicas.

6. **Verificación y Pruebas**:
   - Suite dedicada: `backend/tests/test_phase63_transactions.py` (**15/15 tests PASSED**), verificando tanto rollbacks atómicos ante fallos simulados como commits nominales completos.
   - Suites de regresión: `test_phase62_idempotency.py`, `test_phase61_error_contract.py`, `test_phase55_advanced_import.py`, `test_social_feed.py` (**42/42 tests PASSED**).
   - Linters Python: `ruff check` (**All checks passed!**).
   - Verificación de tipos TypeScript: `tsc --noEmit` (**0 errores**).
   - Suite frontend Vitest: `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 67. Fase 64 --- Concurrencia [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha blindado la consistencia y resiliencia de la plataforma ante condiciones de carrera y peticiones simultáneas utilizando bloqueos de fila (`select_for_update()`), restricciones de base de datos (`UniqueConstraint`) y savepoints anidados (`transaction.atomic()`):

1. **Duplicación de Reseñas Concurrentes (`backend/books/views.py`)**:
   - `ReviewListCreateView.create`: implementado bloqueo exclusivo con `select_for_update()` sobre reseñas activas existentes `(user, book)` y creación encapsulada en savepoint. Ante colisión concurrente con la restricción `unique_active_review_user_book` (`IntegrityError`), el savepoint recupera limpiamente el registro ganador, actualiza sus campos y retorna HTTP 200 OK en lugar de fallar con un 500 no controlado.
   - `ReviewLikeToggleView.post`: protegido con `select_for_update()` y savepoint para gestionar clics rápidos o dobles concurrentes sin colisiones de clave única ni notificaciones duplicadas.
   - `UserBookListCreateView.create`: protegido con `select_for_update()` y recuperación de savepoint ante colisiones con `unique_together = ('user', 'book')`.

2. **Importación Simultánea Multi-Proveedor (`backend/books/services/import_service.py`)**:
   - `_create_or_get_from_volume`: encapsulado completamente bajo `transaction.atomic()` con `select_for_update()` en búsquedas por `google_volume_id`, `isbn` y `(title, author)`. Creación de libro y autor protegida con savepoint y recuperación atómica.
   - `import_single_by_query`: bloqueo con `select_for_update()` en búsquedas y fallback de OpenLibrary protegido contra colisiones concurrentes de ISBN.
   - `_import_from_wikipedia_by_title` y `_import_from_openlibrary_by_title`: búsquedas y actualizaciones protegidas con `select_for_update()`.

3. **Contadores y Métricas Concurrentes (`backend/books/services/gamification_service.py`, `backend/books/tasks.py`)**:
   - `GamificationService.record_daily_reading`: bloqueo exclusivo con `select_for_update()` sobre `DailyReadingLog` y `ReadingStreak`. Previene pérdida de actualizaciones acumuladas de páginas y minutos (*lost updates*) y colisiones `unique_together = ('user', 'date')`.
   - `recalculate_book_rating_task`: recálculo asíncrono atómico con `select_for_update()` sobre la fila del `Book`, serializando recálculos de promedios ante reseñas simultáneas.

4. **Listas de Lectura Concurrentes (`backend/books/views.py:ReadingListViewSet`)**:
   - `add_book`: bloquea la fila padre `ReadingList` con `select_for_update()` para serializar el cómputo de posiciones (`max_pos + 1`) y atrapa colisiones concurrentes con `unique_reading_list_book` devolviendo HTTP 400 limpio.
   - `reorder`: reordenación serializada bajo bloqueo exclusivo de la lista padre con `select_for_update()`.

5. **Acciones Sociales Concurrentes (`backend/users/views.py:FollowUserView`)**:
   - `FollowUserView.post`: verificación atómica de seguimiento previo dentro de la transacción para evitar notificaciones y registros de actividad duplicados por solicitudes simultáneas.

6. **Verificación y Pruebas**:
   - Suite dedicada: `backend/tests/test_phase64_concurrency.py` (**11/11 tests PASSED**), evaluando condiciones de carrera simuladas en reviews, importación, lectura diaria, listas de lectura, likes y seguimiento.
   - Suites de regresión: `test_phase63_transactions.py`, `test_phase62_idempotency.py`, `test_phase61_error_contract.py`, `test_phase21_reading_lists.py` (**48/48 tests PASSED**).
   - Linters Python: `ruff check` (**All checks passed!**).
   - Verificación de tipos TypeScript: `tsc --noEmit` (**0 errores**).
   - Suite frontend Vitest: `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 68. Fase 65 --- Cache invalidation [COMPLETADA]

**Prioridad:** P1 - COMPLETADA

Se ha implementado una política explícita y automatizada de invalidación de caché reactiva y proactiva, eliminando la dependencia del TTL como única estrategia y garantizando la coherencia inmediata de datos en libros, perfiles, recomendaciones y tendencias:

1. **Estructura y Claves de Invalidación (`backend/books/cache_utils.py`)**:
   - `book cache`: invalidación de detalle (`book:{id}`) y recalculo/evicción reactiva.
   - `profile cache`: añadido soporte de caché de perfil (`user:profile:{id}`) con TTL explícito (`TTL_USER_PROFILE = 900`) e invalidación `invalidate_user_profile_cache(user_id)`.
   - `recommendation cache`: invalidación integral de recomendaciones por usuario (`recommendations:user:{id}:{strategy}`) para todas las estrategias (`hybrid`, `rules`, `social`, `semantic`, `v1`, `v2`, `v3`, `all`), recomendaciones a nivel libro (`recommendations:book:{id}`), libros similares (`similar_books_{id}`) y vectores/embeddings de preferencia de usuario (`user_pref_vector_{id}`, `user_pref_embedding_{id}`).
   - `trending cache`: invalidación completa multi-período (`trending:week`, `trending:month`, `trending:year`, `trending:all`).
   - Cascada reactiva orquestada: función `cascade_review_invalidation(book_id, user_id)` que ejecuta la secuencia exacta:
     `new review` → `invalidate book rating & detail` → `invalidate recommendations (book & user)` → `invalidate trending (all periods)` → `invalidate user profile & stats`.

2. **Señales Reactivas y Desencadenantes del Modelo (`backend/books/models.py`)**:
   - `update_book_rating`: llama a `invalidate_book_cache(self.id)` e `invalidate_trending_cache()` tras actualizar promedios.
   - `handle_review_signals`: al crear, actualizar o eliminar una reseña activa, dispara `cascade_review_invalidation(instance.book_id, instance.user_id)`.
   - `handle_userbook_signals`: cambios de estado de lectura en `UserBook` invalidan el perfil del usuario, estadísticas, recomendaciones de usuario y libro, tendencias y caché del libro.
   - `invalidate_book_cache_signal`: al actualizar o eliminar un `Book`, se invalidan su caché de detalle, recomendaciones asociadas y el ranking de tendencias.

3. **Caché e Invalidación en Vistas de Usuario (`backend/users/views.py`)**:
   - `UserProfileView.retrieve`: respuesta del perfil autenticado cacheada en `user:profile:{id}` con cabeceras y serialización DRF.
   - `UserUpdateView.perform_update`: invalida proactivamente `invalidate_user_profile_cache(instance.id)`.
   - `FollowUserView.post` & `UnfollowUserView.post`: invalidan el perfil y estadísticas de ambos usuarios y purgan las recomendaciones del usuario (`recommendations:user:{id}:social`).
   - `BlockUserView.post` & `UnblockUserView.post`: invalidan el perfil y recomendaciones de los usuarios involucrados.

4. **Verificación y Pruebas**:
   - Suite dedicada: `backend/tests/test_phase65_cache_invalidation.py` (**7/7 tests PASSED**), validando:
     - Cascada reactiva completa ante creación, edición y eliminación de reviews.
     - Invalidación de caché de perfiles ante actualizaciones de usuario, follow/unfollow y cambios de UserBook.
     - Purga de recomendaciones (estrategias híbridas, sociales, vectoriales) y embeddings.
     - Evicción de tendencias en todos sus rangos de tiempo (`week`, `month`, `year`, `all`).
   - Suites de regresión: `test_phase64_concurrency.py`, `test_phase63_transactions.py`, `test_phase62_idempotency.py`, `test_caching.py` (**45/45 tests PASSED**).
   - Linters Python: `ruff check` (**All checks passed!**).
   - Verificación de tipos TypeScript: `tsc --noEmit` (**0 errores**).
   - Suite frontend Vitest: `npx vitest run` (**21/21 tests PASSED**).

------------------------------------------------------------------------

# 69. Fase 66 --- Backups

Producción:

``` text
PostgreSQL
daily backup
retention
```

Media:

``` text
backup / object storage
```

Probar restauración.

Un backup que nunca se ha restaurado no se considera validado.

------------------------------------------------------------------------

# 70. Fase 67 --- Disaster recovery

Documentar:

``` text
cómo recuperar DB
cómo recuperar media
cómo regenerar Redis
cómo desplegar versión anterior
cómo restaurar secretos
```

Redis no debe ser fuente de verdad.

------------------------------------------------------------------------

# 71. Fase 68 --- Versionado y releases

Adoptar:

``` text
SemVer
```

Ejemplo:

``` text
v1.0.0
v1.1.0
v1.1.1
```

Mantener:

``` text
CHANGELOG.md
```

------------------------------------------------------------------------

# 72. Fase 69 --- Estrategia de ramas

Recomendación:

``` text
main
develop
feature/*
fix/*
refactor/*
hotfix/*
```

Flujo:

``` text
feature
   ↓
develop
   ↓
CI
   ↓
main
```

Para cambios grandes:

``` text
feature/recommendation-engine
```

------------------------------------------------------------------------

# 73. Fase 70 --- Convención de commits

Usar Conventional Commits:

``` text
feat:
fix:
refactor:
test:
docs:
perf:
security:
chore:
ci:
```

Ejemplos:

``` text
feat: add reading status
fix: prevent duplicate reviews
refactor: split external book providers
test: add privacy permission tests
security: rotate refresh tokens
```

------------------------------------------------------------------------

# 74. Fase 71 --- Definition of Done

Una funcionalidad no está terminada hasta cumplir:

-   [ ] Modelo.
-   [ ] Migración.
-   [ ] Serializer.
-   [ ] API.
-   [ ] Permisos.
-   [ ] Tests backend.
-   [ ] Cliente frontend.
-   [ ] UI.
-   [ ] Tests frontend.
-   [ ] Documentación.
-   [ ] OpenAPI.
-   [ ] CI.
-   [ ] Logs si son necesarios.

------------------------------------------------------------------------

# 75. Orden recomendado de implementación

## BLOQUE A --- Estabilidad

``` text
1. Baseline
2. Tooling
3. CI
4. Tests
5. URLs/API consistency
6. Healthcheck
```

## BLOQUE B --- Dominio

``` text
7. UserBook/Review
8. ReadingStatus
9. ISBN
10. deduplication
```

## BLOQUE C --- Seguridad

``` text
11. JWT
12. permissions
13. privacy
14. uploads
15. Docker production
```

## BLOQUE D --- Rendimiento

``` text
16. pagination
17. query optimization
18. Redis cache
19. Celery
20. external API cache
```

## BLOQUE E --- Social

``` text
21. Activity
22. Feed
23. Likes
24. Comments
25. Notifications
26. Lists
```

## BLOQUE F --- Descubrimiento

``` text
27. PostgreSQL FTS
28. pg_trgm
29. pgvector
30. semantic search
```

## BLOQUE G --- Recomendaciones

``` text
31. rules
32. social similarity
33. embeddings
34. hybrid ranking
35. explainability
36. feedback
```

## BLOQUE H --- IA

``` text
37. provider abstraction
38. prompt architecture
39. security
40. tools
41. contextual assistant
```

## BLOQUE I --- Operaciones

``` text
42. monitoring
43. backups
44. disaster recovery
45. releases
46. documentation
```

------------------------------------------------------------------------

# 76. Prioridades globales

## P0 --- Antes de seguir creciendo

-   [ ] Review/UserBook.
-   [ ] Unique constraints.
-   [ ] Permisos.
-   [ ] Chat authorization.
-   [ ] JWT.
-   [ ] Docker production.
-   [ ] Pagination.
-   [ ] Tests críticos.
-   [ ] CI.
-   [ ] Healthcheck.

## P1 --- Próxima etapa

-   [ ] ReadingStatus.
-   [ ] ISBN normalization.
-   [ ] External providers.
-   [ ] Celery.
-   [ ] Redis cache.
-   [ ] Search.
-   [ ] Feed.
-   [ ] Notifications.
-   [ ] OpenAPI.
-   [ ] Frontend architecture.

## P2 --- Evolución del producto

-   [ ] Lists.
-   [ ] Statistics.
-   [ ] Semantic search.
-   [ ] Recommendations.
-   [ ] AI.
-   [ ] Moderation.
-   [ ] Analytics.
-   [ ] Gamification.

------------------------------------------------------------------------

# 77. Resultado final esperado

La arquitectura final debe permitir:

``` text
Usuario
 │
 ├── Biblioteca
 │     ├── Pendientes
 │     ├── Leyendo
 │     ├── Leídos
 │     └── Abandonados
 │
 ├── Reseñas
 │     ├── Rating
 │     ├── Texto
 │     ├── Likes
 │     └── Comentarios
 │
 ├── Social
 │     ├── Seguidores
 │     ├── Feed
 │     ├── Actividad
 │     └── Notificaciones
 │
 ├── Descubrimiento
 │     ├── Búsqueda
 │     ├── Búsqueda semántica
 │     ├── Trending
 │     └── Recomendaciones
 │
 ├── Chat
 │     └── WebSocket seguro
 │
 └── IA
       ├── Asistente
       ├── Embeddings
       ├── Búsqueda semántica
       └── Recomendaciones
```

------------------------------------------------------------------------

# 78. Criterios de éxito del proyecto

## Arquitectura

-   [ ] Sin duplicación conceptual entre modelos.
-   [ ] API consistente.
-   [ ] Servicios externos desacoplados.
-   [ ] Background jobs.
-   [ ] Cache controlada.

## Seguridad

-   [ ] JWT seguro.
-   [ ] Permisos centralizados.
-   [ ] WebSocket seguro.
-   [ ] Upload validation.
-   [ ] Producción sin DB/Redis públicos.
-   [ ] Secretos fuera del repositorio.

## Calidad

-   [ ] CI verde.
-   [ ] Tests backend.
-   [ ] Tests frontend.
-   [ ] TypeScript strict.
-   [ ] Ruff/Mypy.
-   [ ] OpenAPI.

## Producto

-   [ ] Reading status.
-   [ ] Feed.
-   [ ] Notifications.
-   [ ] Lists.
-   [ ] Statistics.
-   [ ] Search.
-   [ ] Recommendations.

## IA

-   [ ] Provider abstraction.
-   [ ] Semantic search.
-   [ ] Embeddings.
-   [ ] Prompt security.
-   [ ] Explainable recommendations.

------------------------------------------------------------------------

# 79. Regla estratégica final

No intentar implementar simultáneamente:

``` text
IA
+
chat
+
recomendaciones
+
feed
+
estadísticas
```

mientras el modelo de datos todavía está cambiando.

La secuencia correcta es:

``` text
MODELO
   ↓
INTEGRIDAD
   ↓
SEGURIDAD
   ↓
TESTS
   ↓
RENDIMIENTO
   ↓
SOCIAL
   ↓
SEARCH
   ↓
RECOMENDACIONES
   ↓
IA
```

Esto reduce drásticamente el riesgo de tener que rehacer funcionalidades
posteriormente.

------------------------------------------------------------------------

# 80. Primera lista de trabajo recomendada

Para empezar inmediatamente:

``` text
[ ] Crear branch refactor/core-stability
[ ] Crear tag pre-refactor
[ ] Backup PostgreSQL
[ ] Añadir Ruff
[ ] Añadir Mypy
[ ] Añadir pytest/coverage
[ ] Añadir ESLint/Prettier/Vitest
[ ] Crear CI
[ ] Revisar URLs id/pk/user_id
[ ] Revisar messages_app
[ ] Añadir tests de permisos
[ ] Rediseñar UserBook
[ ] Rediseñar Review
[ ] Crear migración
[ ] Migrar datos existentes
[ ] Añadir UniqueConstraint Review
[ ] Eliminar signals de sincronización
[ ] Crear ReadingStatus
[ ] Normalizar ISBN
[ ] Añadir constraints ISBN
[ ] Revisar deduplicación
[ ] Añadir paginación
[ ] Crear /health/
[ ] Endurecer JWT
[ ] Revisar CORS
[ ] Revisar Docker producción
```

**Cuando este bloque esté terminado, hacer un release interno y
continuar con Celery, Redis/cache y servicios externos.**

------------------------------------------------------------------------

# 81. Roadmap resumido

``` text
                    MYBOOKCONNECT
                          │
                          ▼
                 ┌─────────────────┐
                 │  ESTABILIZAR    │
                 │ P0              │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ MODELO DE DATOS │
                 │ UserBook/Review │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │    SEGURIDAD    │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │  RENDIMIENTO    │
                 │ Redis + Celery  │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │     SOCIAL      │
                 │ Feed/Activity   │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │    SEARCH       │
                 │ FTS + pgvector  │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ RECOMMENDATIONS │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │       IA        │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ PRODUCCIÓN      │
                 │ OBSERVABILIDAD  │
                 └─────────────────┘
```

------------------------------------------------------------------------

## Nota sobre el repositorio analizado

Esta hoja de ruta se basa en la estructura y características visibles
actualmente en `main` de MyBookConnect: backend Django/DRF, PostgreSQL,
Redis, JWT, frontend React/TypeScript/Vite/Tailwind, integración de
servicios externos, WebSockets/chat y componentes de IA. Antes de
ejecutar migraciones destructivas, hay que fijar el commit exacto sobre
el que se va a trabajar y hacer backup de datos.

**No ejecutar todas las tareas como un único cambio.** Cada fase debe
convertirse en una o varias ramas/PRs pequeños, con tests y migraciones
controladas.
