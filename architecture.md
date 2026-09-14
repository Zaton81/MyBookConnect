# Arquitectura de MyBookConnect

## 1. Visión General y Principios de Diseño

**MyBookConnect** adopta una arquitectura desacoplada y orientada a servicios, basada en un backend monolítico modular (Django 5.2 LTS + Django REST Framework + Channels) y una aplicación web de página única (SPA) altamente tipada en el frontend (React 18 + TypeScript 5.9 en modo estricto + Vite 6).

### Principios Fundamentales:
1. **Separación Estricta de Responsabilidades:** El frontend se encarga exclusivamente de la experiencia de usuario, estado visual y presentación reactiva; el backend expone APIs RESTful seguras y canales WebSocket, actuando como la autoridad de validación y reglas de negocio.
2. **PostgreSQL como Fuente Única de Verdad:** Todas las garantías de integridad (claves foráneas, índices de unicidad, restricciones de comprobación de rangos y modelos relacionales) residen en la base de datos relacional.
3. **Desacoplamiento Asíncrono:** Ninguna operación de red externa (búsqueda en APIs de Google Books, OpenLibrary o Wikipedia, descargas de imágenes o llamadas a modelos de IA) bloquea el ciclo de vida HTTP. Se delegan a trabajadores Celery respaldados por Redis.
4. **Caché en Múltiples Niveles:** Redis actúa como acelerador de lectura con invalidación granular basada en eventos del modelo y como capa de transporte para WebSockets (`channels-redis`).
5. **Seguridad y Observabilidad por Defecto:** Endurecimiento con JWT de vida corta (15 min), rotación de refresh tokens con lista negra en base de datos, trazabilidad distribuida mediante cabecera `X-Request-ID` y ofuscación de credenciales en logs JSON.

---

## 2. Diagrama de Arquitectura en Capas

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE CLIENTE                               │
│  React 18 + Vite 6 | TypeScript Strict | TailwindCSS | Flowbite React   │
│  Estado Global: Zustand | Enrutamiento: React Router v6                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTPS / WSS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        REVERSE PROXY & GATEWAY                          │
│  Nginx (Producción) / Traefik: Terminación SSL, Rate Limiting, CORS     │
│  Enrutamiento por path:                                                 │
│    - /api/*        ───>  Django WSGI (Gunicorn / port 8000)             │
│    - /ws/*         ───>  Django ASGI (Daphne / Channels)                │
│    - /*            ───>  Frontend estático                              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│          BACKEND WSGI            │   │          BACKEND ASGI            │
│  Django 5.2 + REST Framework     │   │  Daphne + Django Channels        │
│  - Controladores y Vistas REST   │   │  - Consumers de WebSocket        │
│  - Autenticación SimpleJWT       │   │  - Autenticación JWT en Handshake│
│  - Middleware de Observabilidad  │   │  - Canales de Chat y Presencia   │
└────────────────┬─────────────────┘   └────────────────┬─────────────────┘
                 │                                      │
                 └───────────────────┬──────────────────┘
                                     │
    ┌────────────────────────────────┼────────────────────────────────┐
    ▼                                ▼                                ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│     POSTGRESQL 16    │  │       REDIS 7        │  │    CELERY WORKER     │
│ - Esquema Relacional │  │ - Caché de Objetos   │  │ - Ingesta externa    │
│ - Índices Trigram/GIN│  │ - Channel Layer (WS) │  │ - Descarga portadas  │
│ - Constraints & ACIDs│  │ - Métricas Operativas│  │ - Tareas de Limpieza │
│ - Búsqueda Full-Text │  │ - Rate Limiting Store│  │ - Enriquecimiento IA │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## 3. Módulos y Subsistemas Principales

### 3.1. Gestión de Usuarios y Autenticación (`users`)
- **Modelo de Usuario Personalizado (`CustomUser`):** Amplía `AbstractUser` con soporte para alias único, biografía, avatar validado, fecha de nacimiento, ubicación y niveles de privacidad configurables (`public`, `followers_only`, `private`).
- **Autenticación SimpleJWT:**
  - Token de acceso con caducidad estricta de 15 minutos.
  - Token de actualización (refresh token) rotativo, persistido e invalidado en caso de reutilización o cierre de sesión mediante `OutstandingToken` y `BlacklistedToken`.
  - Middleware de autenticación para WebSockets (`WebSocketJwtMiddleware`) que soporta cookies HTTPOnly, cabecera `Authorization` y query string como último recurso.

### 3.2. Dominio Literario y Catálogo (`books`)
- **Catálogo Global (`Author`, `Category`, `Book`):** Estructura canónica de obras literarias con identificadores normalizados (`isbn`, `google_volume_id`, `openlibrary_work_id`), índices de búsqueda difusa (`idx_book_title_trgm`) y soporte para carátulas locales optimizadas en WebP/JPEG.
- **Biblioteca Personal (`UserBook`):** Rastreo por usuario del ciclo de lectura (`want_to_read`, `reading`, `read`, `abandoned`), progreso por porcentaje y número de página, formato (`digital`/`físico`), libro en propiedad y lista de deseos.
- **Reseñas Comunitarias (`Review`):** Opiniones independientes de la biblioteca personal, con calificación de 1 a 5 estrellas, conteo de votos útiles y prevención de duplicados por usuario y libro.
- **Listas de Lectura (`ReadingList`):** Agrupaciones temáticas personalizadas con visibilidad pública o privada.

### 3.3. Interacción Social y Mensajería (`messages_app`)
- **Red Social:** Sistema de seguimiento unidireccional (`followers`), bloqueo de cuentas, feed cronológico agregado con optimización de consultas (`select_related`, `prefetch_related`) para evitar problemas de N+1.
- **Mensajería en Tiempo Real:** Canales de conversación uno a uno mediante `ChatConsumer` con eventos asíncronos (`chat.message`, `message.read`, `typing.indicator`) respaldados por el Channel Layer de Redis.

### 3.4. Motor de Recomendaciones y Estadísticas
- **Algoritmo Híbrido:** Pondera la afinidad de géneros leídos por el usuario con calificaciones altas ($\ge 4$ estrellas), el solapamiento con obras populares de la comunidad y el descarte de títulos ya leídos o descartados.
- **Ciclo de Retroalimentación:** Endpoint `/api/v1/books/recommendations/feedback/` para registrar interacciones del usuario (`accepted`, `dismissed`, `read`) y afinar recomendaciones futuras.
- **Estadísticas de Lectura:** Agregaciones eficientes de libros completados, páginas leídas por año/mes, distribución de calificaciones y autores predilectos.

### 3.5. Subsistema de Inteligencia Artificial Contextual (`ai`)
- **Arquitectura Segura y Compatible:** Diseñada como capa de abstracción desacoplada que puede conectarse con proveedores compatibles con la API de OpenAI o modelos locales.
- **Mitigación de Inyección de Prompts:** Filtros estrictos de validación de entradas (`PromptSecurityService`), limitación de longitud y desinfección de comandos no autorizados.
- **Funcionalidades:** Resúmenes automáticos de libros, análisis de sentimiento de reseñas y búsqueda semántica mediante incrustaciones vectoriales (embeddings).

### 3.6. Observabilidad y Métricas Centralizadas (`mybookconnect.observability`)
- **Trazabilidad Distribuida:** Middleware `StructuredLoggingMiddleware` que inyecta y propaga la cabecera `X-Request-ID` a lo largo de todo el ciclo HTTP.
- **Logging Estructurado en JSON:** Formateador `StructuredJsonFormatter` sin acoplamientos que enmascara automáticamente contraseñas, tokens JWT, refresh tokens y claves API reemplazándolos por `***REDACTED***`.
- **Servicio de Métricas (`ObservabilityMetricsService`):** Recolector en Redis que calcula latencia media y percentil $p95$, ratios de error 5xx y 4xx, volumen de consultas SQL a PostgreSQL, fallos en tareas Celery y conexiones WebSocket concurrentes.
- **Endpoint Administrativo:** `GET /api/v1/observability/metrics/` protegido mediante permisos de administrador (`IsAdminUser`).

---

## 4. Redes y Despliegue en Contenedores

En el entorno de producción (`docker-compose.prod.yml`):
- Los puertos de base de datos (`5432`) y de caché (`6379`) **nunca se exponen a Internet**. Residen estrictamente en la red interna tipo bridge (`mybookconnect_default`).
- El tráfico entrante se gestiona a través de un reverse proxy con certificados SSL y cabeceras de seguridad (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`).
- Las imágenes de backend y frontend utilizan construcciones multi-etapa (multi-stage builds) minimizando el tamaño final y la superficie de ataque.
