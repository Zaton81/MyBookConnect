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
-   [ ] Listas de libros.
-   [ ] Estadísticas de lectura.
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

Usar Redis para:

``` text
external API cache
book detail cache
recommendations
trending
rate limiting
```

Namespaces:

``` text
google:isbn:{isbn}
openlibrary:work:{id}
wikipedia:author:{id}
book:{id}
recommendations:user:{id}
trending:{period}
```

Definir TTLs.

No cachear indiscriminadamente información privada.

------------------------------------------------------------------------

# 12. Fase 9 --- PostgreSQL y rendimiento

**Prioridad:** P1

## Revisar

-   [ ] `select_related`.
-   [ ] `prefetch_related`.
-   [ ] `annotate`.
-   [ ] `Exists`.
-   [ ] índices.
-   [ ] constraints.
-   [ ] consultas N+1.

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

-   [ ] Libros.
-   [ ] Reviews.
-   [ ] Usuarios.
-   [ ] Seguidores.
-   [ ] Following.
-   [ ] Feed.
-   [ ] Trending.
-   [ ] Notificaciones.
-   [ ] Mensajes.
-   [ ] Resultados de búsqueda.

Preferir cursor pagination para:

``` text
feed
activity
messages
notifications
```

cuando sea apropiado.

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

si el flujo de autenticación lo permite.

## Almacenamiento

Preferencia:

``` text
access token → memoria
refresh token → HttpOnly + Secure + SameSite cookie
```

Evitar refresh tokens persistentes en `localStorage`.

## WebSocket

No enviar JWT como query string:

``` text
ws://host/ws/?token=...
```

Preferir un mecanismo basado en cookie segura o handshake controlado.

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

## CORS

Lista explícita de orígenes.

No usar:

``` text
*
```

con credenciales.

## Secretos

Nunca almacenar:

``` text
.env
passwords
API keys
JWT secrets
```

en Git.

------------------------------------------------------------------------

# 16. Fase 13 --- Docker y producción

**Prioridad:** P0

## Regla

En producción no exponer:

``` text
5432
6379
```

a Internet.

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

## Variables

Eliminar fallbacks peligrosos como:

``` text
POSTGRES_PASSWORD=postgres
```

en producción.

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

sin depender de servicios de IA externos.

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

## Bloqueos

Definir explícitamente qué ocurre al bloquear:

-   [ ] Ver perfil.
-   [ ] Buscar usuario.
-   [ ] Seguir.
-   [ ] Ver reviews.
-   [ ] Ver actividad.
-   [ ] Enviar mensajes.
-   [ ] Aparecer en recomendaciones.
-   [ ] Aparecer en búsquedas.

## Criterio de aceptación

Las reglas de privacidad no deben estar duplicadas en múltiples views.

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

no creen dos conversaciones.

## Modelo

Considerar:

``` text
Conversation
    user_a
    user_b
```

con una representación normalizada.

## Mensajes

Para chat 1:1 considerar:

``` text
ConversationMember
    user
    last_read_message
```

en lugar de un único:

``` text
Message.read
```

## Si habrá grupos

Usar:

``` text
ConversationMember
MessageRead
```

## ViewSets

No utilizar `ModelViewSet` si no son necesarias todas las operaciones.

Preferir:

``` text
ReadOnlyModelViewSet
+
acciones específicas
```

## Tests

-   [ ] Acceso autorizado.
-   [ ] Acceso no autorizado.
-   [ ] Usuario bloqueado.
-   [ ] Mensaje ajeno.
-   [ ] Conversación ajena.
-   [ ] WebSocket autenticado.
-   [ ] WebSocket sin autenticación.
-   [ ] Reconexión.

------------------------------------------------------------------------

# 19. Fase 16 --- Búsqueda textual avanzada

**Prioridad:** P1

Usar PostgreSQL:

``` text
pg_trgm
GIN/GiST
SearchVector
SearchQuery
SearchRank
```

Buscar:

``` text
title
author
ISBN
description
categories
```

## Resultado

Ordenar por:

``` text
exact match
trigram similarity
full text rank
rating
popularity
```

## Criterio de aceptación

Búsquedas parciales y con errores razonables deben devolver resultados
relevantes sin depender de `icontains` sobre grandes volúmenes.

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

# 21. Fase 18 --- Feed social

**Prioridad:** P1

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

# 22. Fase 19 --- Likes y comentarios

**Prioridad:** P1

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

-   [ ] Like/unlike.
-   [ ] Duplicado.
-   [ ] Comentario.
-   [ ] Borrado.
-   [ ] Permisos.
-   [ ] Usuario bloqueado.

------------------------------------------------------------------------

# 23. Fase 20 --- Notificaciones

**Prioridad:** P1

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

## Tiempo real

Utilizar Channels para enviar notificaciones nuevas.

## Frontend

Añadir:

``` text
contador
lista
marcar como leído
marcar todas como leídas
```

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

Crear métricas:

``` text
libros leídos
libros empezados
libros abandonados
páginas
valoración media
géneros
autores
libros por mes
```

## Dashboard

``` text
📚 37 libros
⭐ 4,2 media
📖 12 en progreso
📅 8 este año
```

## Datos

No calcular estadísticas pesadas en cada request.

Usar:

``` text
cache
aggregations
background jobs
```

------------------------------------------------------------------------

# 26. Fase 23 --- Trending

**Prioridad:** P2

Crear un score temporal.

Variables:

``` text
reviews recientes
lecturas recientes
wishlists
views
likes
actividad social
```

Aplicar decaimiento temporal.

Ejemplo conceptual:

``` text
score =
    activity_weight * recency_decay
```

Cachear resultados.

------------------------------------------------------------------------

# 27. Fase 24 --- Motor de recomendaciones

**Prioridad:** P2

## Primera versión: basada en reglas

Factores:

``` text
géneros
autores
ratings
historial
wishlist
libros terminados
```

## Segunda versión: social

Añadir:

``` text
usuarios seguidos
libros que leen
libros que valoran
```

## Tercera versión: semántica

Añadir:

``` text
embeddings
```

## Cuarta versión: híbrida

Ejemplo:

``` text
35% preferencias
20% similitud semántica
15% comportamiento social
10% autores
10% popularidad
10% descubrimiento
```

Los pesos deben ser configurables.

------------------------------------------------------------------------

# 28. Fase 25 --- Feedback de recomendaciones

**Prioridad:** P2

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

------------------------------------------------------------------------

# 29. Fase 26 --- IA

**Prioridad:** P2

Separar:

``` text
ai/
├── clients/
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

------------------------------------------------------------------------

# 30. Fase 27 --- Seguridad del asistente IA

**Prioridad:** P1/P2

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

------------------------------------------------------------------------

# 31. Fase 28 --- Media y uploads

**Prioridad:** P1

Validar:

``` text
MIME
extensión
tamaño
dimensiones
contenido
```

Límites sugeridos:

``` text
avatar <= 5 MB
cover <= 10 MB
chat image <= 10 MB
```

## Producción

Considerar migración a:

``` text
S3
Cloudflare R2
MinIO
Cloudinary
```

El filesystem local del contenedor no debe ser la única fuente de media
en producción.

------------------------------------------------------------------------

# 32. Fase 29 --- Moderación

**Prioridad:** P2

Crear:

``` text
Report
```

Aplicable a:

``` text
User
Review
Comment
Message
```

Estados:

``` text
OPEN
UNDER_REVIEW
RESOLVED
REJECTED
```

## Roles

Evolucionar desde un único `is_editor` hacia permisos/roles:

``` text
USER
EDITOR
MODERATOR
ADMIN
```

Preferiblemente aprovechando permisos de Django cuando tenga sentido.

------------------------------------------------------------------------

# 33. Fase 30 --- Auditoría

**Prioridad:** P2

Crear:

``` text
AuditLog
```

Campos:

``` text
actor
action
object_type
object_id
timestamp
metadata
```

Registrar especialmente:

``` text
block
unblock
delete content
moderation
role change
security-sensitive actions
```

------------------------------------------------------------------------

# 34. Fase 31 --- Soft delete

**Prioridad:** P2

Considerar `deleted_at` para:

``` text
Review
Comment
Message
```

Ventajas:

-   auditoría;
-   moderación;
-   recuperación;
-   integridad histórica.

No aplicar soft delete indiscriminadamente a todas las tablas.

------------------------------------------------------------------------

# 35. Fase 32 --- API REST coherente

**Prioridad:** P1

Convención:

``` text
/api/v1/books/
/api/v1/books/{id}/
/api/v1/users/
/api/v1/users/{id}/
/api/v1/reviews/
/api/v1/conversations/
/api/v1/messages/
```

Acciones específicas:

``` text
/books/{id}/recommendations/
/books/import/
/users/{id}/follow/
```

Eliminar progresivamente rutas antiguas duplicadas.

------------------------------------------------------------------------

# 36. Fase 33 --- OpenAPI como contrato

**Prioridad:** P1

Usar `drf-spectacular` para generar:

``` text
/api/schema/
/api/docs/
/api/redoc/
```

Usar OpenAPI para generar tipos TypeScript.

Flujo:

``` text
Django
 ↓
OpenAPI
 ↓
TypeScript types/client
 ↓
React
```

Esto reduce divergencia frontend/backend.

------------------------------------------------------------------------

# 37. Fase 34 --- Frontend por features

**Prioridad:** P1

Estructura objetivo:

``` text
src/
├── app/
│   ├── router.tsx
│   ├── providers.tsx
│   └── queryClient.ts
│
├── features/
│   ├── auth/
│   ├── books/
│   ├── library/
│   ├── reviews/
│   ├── social/
│   ├── chat/
│   ├── notifications/
│   └── ai/
│
├── components/
│   ├── ui/
│   └── layout/
│
├── api/
├── hooks/
├── lib/
└── types/
```

------------------------------------------------------------------------

# 38. Fase 35 --- React Router

**Prioridad:** P2

Utilizar layouts:

``` text
ProtectedLayout
PublicLayout
AdminLayout
```

Con:

``` tsx
<Outlet />
```

Evitar repetir:

``` tsx
<ProtectedRoute>
    ...
</ProtectedRoute>
```

en cada ruta.

------------------------------------------------------------------------

# 39. Fase 36 --- React Query vs Zustand

**Prioridad:** P1

Regla:

``` text
Server state → TanStack Query
Client/UI state → Zustand
```

TanStack Query:

``` text
books
reviews
users
feed
notifications
```

Zustand:

``` text
auth UI state
theme
sidebar
modals
drafts
```

No duplicar cache del servidor en Zustand.

------------------------------------------------------------------------

# 40. Fase 37 --- Formularios

**Prioridad:** P2

Añadir:

``` text
React Hook Form
Zod
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

------------------------------------------------------------------------

# 41. Fase 38 --- Tipado frontend

**Prioridad:** P1

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

------------------------------------------------------------------------

# 42. Fase 39 --- Testing frontend

**Prioridad:** P1

Añadir Vitest + React Testing Library.

Tests prioritarios:

-   [ ] Login.
-   [ ] Registro.
-   [ ] Rutas protegidas.
-   [ ] Libro.
-   [ ] Biblioteca.
-   [ ] Review.
-   [ ] Follow/unfollow.
-   [ ] Bloqueo.
-   [ ] Chat.
-   [ ] Notificaciones.
-   [ ] Feed.
-   [ ] Recomendaciones.

------------------------------------------------------------------------

# 43. Fase 40 --- Testing backend

**Prioridad:** P0/P1

## Seguridad

-   [ ] Usuario no puede editar `UserBook` ajeno.
-   [ ] Usuario no puede editar Review ajena.
-   [ ] Usuario bloqueado.
-   [ ] Perfil privado.
-   [ ] Conversación ajena.
-   [ ] Mensaje ajeno.

## Integridad

-   [ ] Review duplicada.
-   [ ] ISBN duplicado.
-   [ ] Rating inválido.
-   [ ] Estado inválido.
-   [ ] Progreso inválido.

## Social

-   [ ] Follow.
-   [ ] Unfollow.
-   [ ] Block.
-   [ ] Unblock.
-   [ ] Follow bloqueado.

## Integración

-   [ ] Importación.
-   [ ] Providers externos.
-   [ ] Chat.
-   [ ] IA.
-   [ ] Recomendaciones.

------------------------------------------------------------------------

# 44. Fase 41 --- Tests de integración con PostgreSQL y Redis

**Prioridad:** P1

No depender únicamente de SQLite.

CI debe utilizar:

``` text
PostgreSQL
Redis
```

reales en contenedores.

Probar:

-   [ ] migrations;
-   [ ] constraints;
-   [ ] indexes;
-   [ ] transactions;
-   [ ] cache;
-   [ ] Channels.

------------------------------------------------------------------------

# 45. Fase 42 --- Observabilidad

**Prioridad:** P2

Añadir logging estructurado.

Registrar:

``` text
request_id
user_id
endpoint
status_code
duration
exception
external_provider
```

No registrar:

``` text
passwords
JWT
refresh tokens
API keys
contenido privado innecesario
```

## Métricas

Controlar:

``` text
request latency
5xx rate
database queries
Celery failures
external API errors
WebSocket connections
cache hit rate
recommendation CTR
```

------------------------------------------------------------------------

# 46. Fase 43 --- Rendimiento

**Prioridad:** P2

Definir objetivos.

Ejemplo inicial:

``` text
API normal p95 < 300 ms
API compleja p95 < 800 ms
búsqueda p95 < 500 ms
```

Medir antes de optimizar.

Herramientas posibles:

``` text
Django Debug Toolbar
pytest-django
PostgreSQL EXPLAIN ANALYZE
Locust
k6
```

------------------------------------------------------------------------

# 47. Fase 44 --- Gestión de dependencias

**Prioridad:** P2

No hacer upgrades masivos.

Procedimiento:

``` text
1 dependencia
 ↓
tests
 ↓
build
 ↓
merge
```

Revisar especialmente:

``` text
Django
DRF
React
React Router
Vite
TypeScript
Tailwind
Tiptap
Flowbite
Redis
PostgreSQL
```

Eliminar dependencias innecesarias.

------------------------------------------------------------------------

# 48. Fase 45 --- Documentación

**Prioridad:** P1

Actualizar:

``` text
README.md
architecture.md
structure.md
```

Añadir:

``` text
docs/
├── architecture/
├── api/
├── development/
├── deployment/
├── security/
└── decisions/
```

## ADRs

Crear decisiones arquitectónicas:

``` text
ADR-001 Django + React
ADR-002 PostgreSQL como fuente de verdad
ADR-003 Redis
ADR-004 Celery
ADR-005 JWT strategy
ADR-006 Review/UserBook
ADR-007 Semantic search
ADR-008 Recommendation engine
```

------------------------------------------------------------------------

# 49. Fase 46 --- API de salud y readiness

Crear:

``` text
/api/v1/health/
/api/v1/ready/
```

`health`:

``` text
process alive
```

`ready`:

``` text
database available
redis available
```

Esto facilita Docker, reverse proxy y futuras plataformas de despliegue.

------------------------------------------------------------------------

# 50. Fase 47 --- Seguridad de contraseñas y autenticación

Revisar:

-   [ ] Password validators.
-   [ ] Protección contra brute force.
-   [ ] Rate limiting.
-   [ ] Password reset.
-   [ ] Email verification.
-   [ ] Google OAuth.
-   [ ] Revocación de sesiones.
-   [ ] Logout.
-   [ ] Rotación de refresh tokens.

Opcional posteriormente:

``` text
2FA
```

------------------------------------------------------------------------

# 51. Fase 48 --- Sistema de búsqueda unificado

Objetivo final:

``` text
                     SEARCH
                       │
          ┌────────────┼────────────┐
          │            │            │
       textual       fuzzy      semantic
          │            │            │
       PostgreSQL    pg_trgm      pgvector
          │            │            │
          └────────────┼────────────┘
                       │
                    ranking
                       │
                    results
```

------------------------------------------------------------------------

# 52. Fase 49 --- Motor de recomendaciones v1

Algoritmo inicial sin ML complejo.

Variables:

``` text
género
autor
rating
historial
wishlist
```

Resultado:

``` text
score = weighted_sum(...)
```

Guardar versión:

``` text
algorithm_version = "v1"
```

------------------------------------------------------------------------

# 53. Fase 50 --- Motor de recomendaciones v2

Añadir:

``` text
usuarios similares
```

Ejemplo:

``` text
Jorge
 ↓
usuarios con gustos similares
 ↓
libros que Jorge no ha leído
 ↓
ranking
```

Método inicial:

``` text
user-user similarity
```

------------------------------------------------------------------------

# 54. Fase 51 --- Motor de recomendaciones v3

Añadir:

``` text
embeddings
```

Representación:

``` text
book embedding
user preference embedding
```

Usuario:

``` text
vector = weighted average(
    liked books,
    highly rated books,
    finished books
)
```

Comparar contra libros no consumidos.

------------------------------------------------------------------------

# 55. Fase 52 --- Recomendaciones explicables

Cada recomendación debe poder explicar:

``` text
¿Por qué?
```

Ejemplo:

``` text
Te recomendamos Dune porque:

✓ te han gustado 5 libros de ciencia ficción;
✓ has valorado 1984 con 5 estrellas;
✓ tiene similitud semántica alta con Fundación;
✓ 3 usuarios que sigues lo han leído.
```

------------------------------------------------------------------------

# 56. Fase 53 --- Feed inteligente

Primera versión:

``` text
cronológico
```

Después:

``` text
engagement
recency
relationship
content relevance
```

No introducir ML antes de tener datos suficientes.

------------------------------------------------------------------------

# 57. Fase 54 --- Gamificación opcional

Solo después de estabilizar el núcleo.

Posibilidades:

``` text
reto mensual
racha de lectura
objetivo anual
insignias
```

Ejemplo:

``` text
📚 10 libros en verano
⭐ 5 reseñas publicadas
🔥 7 días leyendo
```

Debe ser opcional y no interferir con la experiencia principal.

------------------------------------------------------------------------

# 58. Fase 55 --- Importación avanzada

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

------------------------------------------------------------------------

# 59. Fase 56 --- Importación idempotente

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

------------------------------------------------------------------------

# 60. Fase 57 --- Administración

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

------------------------------------------------------------------------

# 61. Fase 58 --- Moderación de contenido

Añadir herramientas para:

``` text
report
review
hide
restore
ban
mute
block
```

Definir políticas antes de implementar automatización IA.

------------------------------------------------------------------------

# 62. Fase 59 --- Seguridad de contenido generado por usuarios

Todo contenido HTML debe sanitizarse.

Especialmente:

``` text
reviews
comments
profiles
chat
```

Si se usa Tiptap:

``` text
frontend sanitization
+
backend sanitization
```

No confiar únicamente en el frontend.

------------------------------------------------------------------------

# 63. Fase 60 --- Seguridad de imágenes

Procesar imágenes:

``` text
resize
strip metadata
validate MIME
validate dimensions
```

Considerar antivirus/scanner si el proyecto crece.

------------------------------------------------------------------------

# 64. Fase 61 --- Contrato de errores API

Unificar errores.

Formato recomendado:

``` json
{
  "error": {
    "code": "REVIEW_ALREADY_EXISTS",
    "message": "El usuario ya tiene una reseña para este libro.",
    "details": {}
  }
}
```

Códigos estables:

``` text
AUTH_INVALID
PERMISSION_DENIED
NOT_FOUND
VALIDATION_ERROR
REVIEW_ALREADY_EXISTS
BOOK_DUPLICATE
USER_BLOCKED
RATE_LIMITED
```

------------------------------------------------------------------------

# 65. Fase 62 --- Idempotencia

Añadir idempotency keys a operaciones sensibles/costosas cuando sea
necesario:

``` text
POST /books/import
POST /notifications
POST /external sync
```

Especialmente cuando haya retries automáticos.

------------------------------------------------------------------------

# 66. Fase 63 --- Transacciones

Usar:

``` python
transaction.atomic()
```

en operaciones que actualizan varias entidades.

Ejemplos:

``` text
crear review + actualizar estadísticas
follow + activity
block + limpieza de relación
import book + author + categories
```

------------------------------------------------------------------------

# 67. Fase 64 --- Concurrencia

Proteger operaciones sensibles con:

``` text
select_for_update()
constraints
transactions
```

cuando sea necesario.

Ejemplos:

``` text
duplicación de reviews
importación simultánea
contadores
listas
```

------------------------------------------------------------------------

# 68. Fase 65 --- Cache invalidation

Definir explícitamente cuándo invalidar:

``` text
book cache
profile cache
recommendation cache
trending cache
```

Ejemplo:

``` text
new review
 ↓
invalidate book rating
 ↓
invalidate recommendations
 ↓
invalidate trending
```

No usar TTL como única estrategia.

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
