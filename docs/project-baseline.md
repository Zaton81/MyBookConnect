# MyBookConnect — Baseline Técnico y Auditoría Reproducible

> **Fecha de captura:** 21 de septiembre de 2026  
> **Fase del Roadmap:** FASE 0 — Baseline técnico y auditoría reproducible (P0, RoadmapV2.md)  
> **Commit SHA exacto:** `2c68cfa6d2a973f944de484fe4a966c707cdfc78` (branch `develop`)  
> **Objetivo:** Establecer la fotografía reproducible del estado real del proyecto antes de ejecutar las fases de privacidad, integridad de datos y beta cerrada.

---

## 1. Identificadores y Control de Versiones

- **Repositorio:** `https://github.com/Zaton81/MyBookConnect`
- **Rama principal activa:** `develop`
- **Rama de producción:** `main`
- **SemVer de la API:** `1.0.0`
- **Versión de Frontend:** `1.0.0` (en `frontend/package.json`)
- **Versión de Backend:** `1.0.0` (en `backend/pyproject.toml` y `backend/mybookconnect/version.py`)

---

## 2. Runtimes y Tecnologías Base

| Componente | Versión detectada | Entorno |
|---|---|---|
| **Python** | 3.12.14 | Contenedor Docker `booksocial-backend` |
| **Django** | 5.2.17 | Backend / ORM |
| **Django REST Framework** | 3.15.2 | API REST |
| **Node.js** | 22.16.0 | Host / Contenedor frontend |
| **TypeScript** | 5.9.3 | Modo strict configurado en `tsconfig.json` |
| **React** | 18.3.1 | SPA Frontend |
| **Vite** | 6.4.3 | Bundler / Dev server |
| **PostgreSQL** | 16 (imagen `postgres:15` en docker compose) | Base de datos relacional principal |
| **Redis** | 7.0 (`redis:7`) | Cache, WebSockets (Channels) y Celery broker |
| **Celery** | 5.4.0 | Procesamiento asíncrono y tareas programadas |
| **Daphne / Channels** | 4.1.0 / 4.1.0 | Servidor ASGI para HTTP y WebSockets |
| **Docker** | 28.5.1 | Motor de contenedores |
| **Docker Compose** | v2.40.0-desktop.1 | Orquestación local |

---

## 3. Topología de Servicios Docker y Almacenamiento

### 3.1 Contenedores en Ejecución

| Nombre Contenedor | Servicio | Imagen | Puerto Host:Container | Estado |
|---|---|---|---|---|
| `booksocial-backend` | `backend` | `mybookconnect-backend` | `8000:8000` | Up (Daphne ASGI) |
| `booksocial-db` | `db` | `postgres:15` | `5432:5432` | Up (Healthy) |
| `booksocial-cache` | `cache` | `redis:7` | `6379:6379` | Up (Healthy) |
| `booksocial-celery-worker` | `celery_worker` | `mybookconnect-celery_worker` | Interno (red docker) | Up |
| `booksocial-frontend` | `frontend` | `mybookconnect-frontend` | `5173:5173` | Up (Vite SPA) |

### 3.2 Volúmenes Persistentes

- `postgres_data`: Almacenamiento de datos PostgreSQL.
- `redis_data`: Persistencia de snapshots de Redis.
- `media_volume`: Archivos estáticos y multimedia (portadas, fotos de autores).
- `backups_data`: Almacenamiento de respaldos de base de datos y medios creados por el servicio de backup.

---

## 4. Extensiones PostgreSQL Activas

```sql
SELECT extname, extversion FROM pg_extension;
```

1. **`plpgsql`** (v1.0): Lenguaje procedimental para triggers y funciones internas.
2. **`pg_trgm`** (v1.6): Trigram matching para búsqueda aproximada y similitud en títulos, autores y descripciones.

---

## 5. Modelos de Dominio (34 Modelos Registrados)

### 5.1 Libros y Catálogo (`books`)
- `Book`: Entidad central con título, ISBN, fecha de publicación, sinopsis, portada, autor (FK `Author`), categorías (M2M `Category`), rating promedio y total de reseñas.
- `Author`: Autor con nombre, slug, foto, biografía y fechas biográficas.
- `Category`: Categoría/género literario con nombre, slug canónico y contador de libros.
- `Review`: Reseña pública y valoración (1-5 o 1-10 en ratings históricos) con `SoftDeleteModel` y `UniqueConstraint(user, book)`.
- `ReviewComment`: Comentarios jerárquicos sobre reseñas públicas.
- `ReviewLike`: Likes de usuarios en reseñas con constraint única `(user, review)`.
- `UserBook`: Relación privada personal del usuario con un libro (estado de lectura: `want_to_read`, `currently_reading`, `read`, `dropped`, páginas leídas, notas privadas).

### 5.2 Listas y Curaduría (`books`)
- `ReadingList`: Lista curada de libros (pública/privada) con título, descripción y propietario.
- `ReadingListItem`: Libro dentro de una lista con orden secuencial y notas contextuales.
- `ReadingListFollow`: Seguidores de listas de lectura.

### 5.3 Hábitos y Gamificación (`books`)
- `ReadingGoal`: Metas de lectura anuales/mensuales de usuarios.
- `ReadingStreak`: Racha de días consecutivos leyendo.
- `DailyReadingLog`: Registro diario de páginas o tiempo de lectura.
- `Badge`: Insignia o logro disponible en la plataforma.
- `UserBadge`: Insignias ganadas por cada usuario con fecha de obtención.
- `ReadingChallenge`: Retos comunitarios de lectura.
- `UserChallenge`: Participación y progreso de usuarios en retos.

### 5.4 Feedback y Calidad (`books`)
- `RecommendationFeedback`: Registro explícito de feedback sobre recomendaciones (`liked`, `disliked`, `ignored`).
- `Errata`: Reporte de errores en metadatos de libros (ISBN erróneo, portada incorrecta).
- `LegalDocument`: Versiones publicadas de documentos legales (términos, cookies, privacidad).

### 5.5 Usuarios, Social y Seguridad (`users`)
- `User`: Modelo de usuario personalizado con email como identificador, nombre de usuario, avatar, bio, preferencias de privacidad granulares (`is_library_private`, `is_activity_private`, etc.) y lista de usuarios bloqueados.
- `Activity`: Registro de eventos sociales (lecturas, reseñas, listas creadas) para el feed.
- `Notification`: Notificaciones dirigidas al usuario (nuevos seguidores, comentarios, likes).
- `Report`: Denuncias de contenido y reportes de abuso contra usuarios, reseñas o listas.
- `AuditLog`: Registro de auditoría para acciones críticas de seguridad y administración.

### 5.6 Mensajería y Tiempo Real (`messages_app`)
- `Conversation`: Sala de chat 1-a-1 o grupal entre participantes autorizados.
- `Message`: Mensaje intercambiado dentro de una conversación con timestamp, estado de lectura y validación de permisos.

### 5.7 Autenticación y Sistema (`token_blacklist`, `django.contrib`)
- `BlacklistedToken`, `OutstandingToken`: Tokens JWT revocados.
- `Session`, `LogEntry`, `ContentType`, `Group`, `Permission`.

---

## 6. Tareas Asíncronas Celery Registradas

1. **`books.tasks.download_cover_task`**: Descarga, valida y optimiza portadas de libros desde URLs externas.
2. **`books.tasks.enrich_book_task`**: Enriquecimiento en cascada de metadatos (Google Books -> OpenLibrary -> Wikipedia).
3. **`books.tasks.generate_book_embedding_task`**: Generación asíncrona de embeddings vectoriales para búsqueda semántica.
4. **`books.tasks.import_books_by_author_task`**: Importación por lotes de bibliografía de autores.
5. **`books.tasks.precompute_trending_task`**: Precálculo de libros en tendencia según reseñas recientes y lecturas.
6. **`books.tasks.precompute_user_recommendations_task`**: Generación offline de recomendaciones personalizadas por usuario.
7. **`books.tasks.recalculate_book_rating_task`**: Recálculo asíncrono y atómico del rating promedio y conteo de reseñas.
8. **`books.tasks.refresh_author_task`**: Actualización de metadatos y bio del autor.
9. **`mybookconnect.celery.debug_task`**: Tarea de diagnóstico de conectividad con Celery worker.

---

## 7. WebSockets y Tiempo Real

- **Endpoint:** `ws://<host>:8000/ws/chat/<conversation_id>/`
- **Consumer:** `messages_app.consumers.ChatConsumer`
- **Middleware:** `mybookconnect.middleware.JwtAuthMiddlewareStack` (validación de JWT en handshake de WebSocket).
- **Backend de canales:** Redis channel layer (`redis:7`).

---

## 8. Catálogo de Endpoints de la API

### 8.1 Monitoreo y Esquema
- `GET /api/v1/health/`: Liveness probe (HTTP 200 con estado y versión).
- `GET /api/v1/ready/`: Readiness probe (verifica DB PostgreSQL y cache Redis).
- `GET /api/v1/version/`: Información SemVer 2.0.0.
- `GET /api/v1/observability/metrics/`: Métricas administrativas de latencia, 4xx/5xx y queries.
- `GET /api/schema/`, `/api/docs/`, `/api/redoc/`: Documentación OpenAPI (Swagger UI y ReDoc).

### 8.2 Autenticación y Cuentas
- `POST /api/v1/auth/token/`: Obtención de par de tokens JWT (access + refresh con rotación).
- `POST /api/v1/auth/token/refresh/`: Refresco de access token.
- `POST /api/v1/auth/register/`: Registro de nuevos usuarios con validación de contraseña.
- `GET /api/v1/auth/me/`: Perfil del usuario autenticado.

### 8.3 Administración Ofuscada
- `GET /panel-control-mbc/`: Django Admin protegido en ruta no estándar (`ADMIN_URL`).
- `ALL /admin/`: Señuelo (honeypot) que devuelve HTTP 404 estricto y registra la IP en logs de seguridad.
- `GET|POST /api/v1/admin/books/`: Gestión y listado administrativo de libros.
- `GET|POST /api/v1/admin/categories/`: Gestión de categorías (soporta `?all=true`).
- `GET|POST /api/v1/admin/authors/`: Gestión de autores (soporta `?all=true`).

### 8.4 Libros, Biblioteca y Reseñas
- `/api/v1/books/`: Búsqueda, filtrado, detalle de libros, recomendaciones, trending.
- `/api/v1/books/library/`: Gestión de la biblioteca personal del usuario (`UserBook`).
- `/api/v1/reviews/`: CRUD de reseñas, comentarios, likes y feed de reseñas.
- `/api/v1/gamification/`: Retos, metas, rachas y medallas.

### 8.5 Social, Feed y Mensajería
- `/api/v1/users/`: Perfiles públicos, seguimiento social, bloqueos de usuarios.
- `/api/v1/chat/`: Listado y creación de conversaciones privadas.
- `/api/v1/reports/`: Envío de reportes de moderación contra contenido inapropiado.

---

## 9. Variables de Entorno Auditadas (`.env.example`)

| Variable | Tipo | Propósito |
|---|---|---|
| `SECRET_KEY` | String | Clave criptográfica para firmas de Django |
| `DEBUG` | Boolean | Activa/desactiva modo depuración (debe ser `False` en prod) |
| `ALLOWED_HOSTS` | List | Nombres de dominio permitidos |
| `CORS_ALLOWED_ORIGINS` | List | Orígenes web autorizados para CORS |
| `DATABASE_URL` | URL | Cadena de conexión completa para PostgreSQL |
| `POSTGRES_DB`, `USER`, `PASSWORD`, `HOST`, `PORT` | Strings | Parámetros individuales de DB |
| `REDIS_URL` | URL | Conexión a Redis para cache y channels |
| `CELERY_BROKER_URL`, `RESULT_BACKEND` | URL | Broker y backend para Celery |
| `JWT_SECRET_KEY` | String | Clave específica para firma HMAC-SHA256 de tokens JWT |
| `JWT_ACCESS_TOKEN_LIFETIME` | Integer | Minutos de validez del access token |
| `JWT_REFRESH_TOKEN_LIFETIME` | Integer | Días de validez del refresh token |
| `ADMIN_URL` | String | Ruta ofuscada para el panel de Django Admin |
| `GOOGLE_BOOKS_API_KEY` | String | Clave de API para enriquecimiento de libros |
| `GEMINI_API_KEY`, `OPENAI_API_KEY` | String | Proveedores de IA y embeddings |
| `EMAIL_HOST`, `PORT`, `USER`, `PASSWORD` | String | Servidor SMTP para notificaciones |

---

## 10. Resultados de las Comprobaciones Automatizadas

| Comprobación | Comando | Resultado |
|---|---|---|
| **Sintaxis Compose** | `docker compose config` | **VÁLIDO** (5 servicios declarados correctamente) |
| **Integridad Django** | `python manage.py check` | **0 issues** identificados |
| **Migraciones DB** | `python manage.py makemigrations --check` | **No changes detected** (migraciones al día) |
| **Suite Backend** | `pytest tests/` | **572 tests recopilados, 100% pasando** |
| **Frontend TypeScript** | `npm run typecheck` (`tsc --noEmit`) | **0 errores** de tipos en modo estricto |
| **Frontend Vitest** | `npx vitest run` | **7 archivos, 21 tests PASSED (100%)** |
| **Frontend Build** | `npm run build` (`vite build`) | **Exitoso** (artefactos compilados en `dist/`) |

---

## 11. Conclusión de la Auditoría

El baseline técnico del proyecto es **estable, reproducible y verificado al 100%**. Todas las dependencias, servicios orquestados, pruebas unitarias y de integración se encuentran operativas sin errores de regresión. El proyecto se encuentra en condiciones óptimas para acometer el **Sprint 1 (Privacy & Integrity)** de acuerdo con las directrices de `RoadmapV2.md`.
