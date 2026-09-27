# Arquitectura de Caché y Resiliencia (Fase 8)

Documento técnico que detalla la arquitectura de almacenamiento en caché distribuido, jerarquía de TTLs, matriz de invalidaciones reactivas en cascada, mitigación de estampidas (*cache stampede*) y resiliencia ante indisponibilidad de Redis en MyBookConnect.

---

## 1. Inventario de Caché y Convenciones de Claves

Todas las claves de caché siguen una nomenclatura canónica con namespaces explícitos para evitar colisiones y permitir invalidación precisa:

| Entidad / Namespace | Patrón de Clave | TTL Predeterminado | Propósito |
| :--- | :--- | :--- | :--- |
| **Detalle de Libro** | `book:{id}` | `900s` (15 min) | Metadatos completos de un libro, agregaciones de calificación y autores. |
| **Perfil de Usuario** | `user:{id}` | `900s` (15 min) | Perfil público/privado con campos filtrados por políticas de privacidad. |
| **Recomendaciones** | `recommendations:{user_id}:{engine}` | `900s` (15 min) | Recomendaciones personalizadas de usuario por motor (`hybrid`, `content`, `collaborative`). |
| **Recomendaciones de Libro** | `book_recommendations:{book_id}` | `900s` (15 min) | Libros similares o recomendaciones satélite basadas en un libro semilla. |
| **Feed Social** | `feed:{user_id}` | `300s` (5 min) | Feed de actividades personalizadas de las entidades y usuarios seguidos. |
| **Búsqueda Unificada** | `search:{mode}:{query}:{page}` | `300s` (5 min) | Resultados de consultas de texto o búsqueda semántica paginados. |
| **Tendencias** | `trending:{period}` | `900s` (15 min) | Rankings de libros y actividad en tendencia (`day`, `week`, `month`). |
| **Estadísticas de Lectura** | `user:{id}:stats` | `900s` (15 min) | Métricas agregadas de retos, libros leídos y páginas del usuario. |
| **Detalle de Reseña** | `review:{id}` | `900s` (15 min) | Contenido, votaciones y comentarios de una reseña. |

---

## 2. Jerarquía de TTLs Estándar

Los tiempos de vida en caché se definen centralizadamente en `books.cache_utils`:

- `TTL_BOOK_DETAIL = 900` (15 minutos)
- `TTL_USER_PROFILE = 900` (15 minutos)
- `TTL_RECOMMENDATIONS = 900` (15 minutos)
- `TTL_FEED = 300` (5 minutos)
- `TTL_SEARCH = 300` (5 minutos)
- `TTL_TRENDING = 900` (15 minutos)
- `TTL_STATS = 900` (15 minutos)

---

## 3. Matriz de Invalidaciones Reactivas ante Eventos Clave

Para garantizar consistencia eventual estricta sin arrastrar datos obsoletos (*stale data*), el sistema dispara invalidaciones en cascada ante 5 eventos del ciclo de vida de la plataforma:

### 3.1. Creación o Actualización de Reseñas (`Review created/updated/deleted`)
- **Disparador:** Señal `post_save` / `post_delete` en el modelo `Review`.
- **Acción:** `cascade_review_invalidation(review)`
- **Claves Invalidadas:**
  - `review:{review.id}`
  - `book:{review.book_id}` (actualiza promedios de calificación y conteo de reseñas)
  - `feed:{review.user_id}`
  - `user:{review.user_id}:stats`
  - `trending:day`, `trending:week`, `trending:month`

### 3.2. Seguir o Dejar de Seguir (`Follow created/deleted`)
- **Disparador:** Endpoints `/api/v1/users/{id}/follow/` y `/api/v1/users/{id}/unfollow/`.
- **Acción:** `cascade_follow_invalidation(follower_id, followed_id)`
- **Claves Invalidadas:**
  - `feed:{follower_id}` (recalcular feed al cambiar la red de seguidos)
  - `user:{follower_id}` y `user:{followed_id}` (conteo de seguidores/seguidos)
  - `recommendations:{follower_id}:*` (ajustar grafos sociales de recomendación)

### 3.3. Cambio en Privacidad del Usuario (`User privacy changed`)
- **Disparador:** Endpoint de actualización de perfil `/api/v1/auth/profile/update/` y señales en modelo `User`.
- **Acción:** `cascade_privacy_invalidation(user_id)`
- **Claves Invalidadas:**
  - `user:{user_id}`
  - `feed:{user_id}`
  - `recommendations:{user_id}:*`
  - Caché de búsquedas activas de usuarios.

### 3.4. Actualización de Catálogo de Libro (`Book updated/deleted`)
- **Disparador:** Señal `post_save` / `post_delete` en el modelo `Book`.
- **Acción:** `cascade_book_invalidation(book_id)`
- **Claves Invalidadas:**
  - `book:{book_id}`
  - `book_recommendations:{book_id}`
  - `trending:day`, `trending:week`, `trending:month`

### 3.5. Cambio de Estado de Lectura (`Reading status changed`)
- **Disparador:** Señal `post_save` / `post_delete` en el modelo `UserBook`.
- **Acción:** `cascade_reading_status_invalidation(user_id, book_id)`
- **Claves Invalidadas:**
  - `user:{user_id}`
  - `user:{user_id}:stats`
  - `recommendations:{user_id}:*`
  - `feed:{user_id}`
  - `book:{book_id}`

---

## 4. Protección contra Estampidas de Caché (*Cache Stampede*)

Cuando un elemento de alto tráfico expira o se invalida simultáneamente para miles de peticiones concurrentes, una consulta pesada a PostgreSQL o al motor de IA podría colapsar la infraestructura (*thundering herd problem*).

Para prevenirlo, `books.cache_utils.get_or_set_stampede_protected` implementa un patrón de bloqueo distribuido con doble verificación (*Double-Checked Locking*):

1. **Lectura Segura:** Comprueba si la clave está en caché. Si existe, retorna el valor inmediatamente.
2. **Adquisición Atómica del Candado:** Si la clave expiró, intenta adquirir un candado distribuido `lock:{key}` usando `cache.add()` (equivalente a `SETNX` de Redis con TTL corto de 10s para evitar deadlocks).
3. **Double Check:** Tras adquirir el lock, vuelve a verificar si otro hilo/proceso ya pobló la clave mientras competía por el lock.
4. **Cálculo y Población:** Si sigue vacía, ejecuta el `computation_fn()`, almacena el resultado con `safe_cache_set(key, result, timeout=ttl)` y libera el candado `cache.delete(lock_key)`.
5. **Fallback Concurrente:** Si otro proceso posee el lock, espera un breve lapso (*backoff*) y vuelve a intentar leer de la caché o computa si el lock expira.

---

## 5. Resiliencia y Modo Degradado ante Caídas de Redis

Si Redis no está disponible, la plataforma continúa operativa sin arrojar errores `HTTP 500` a los clientes:

1. **Wrappers Defensivos de Caché:**
   - `safe_cache_get(key, default=None)`: Captura cualquier `Exception` de conexión o timeout a Redis, emite un aviso de logging estructurado y retorna el valor predeterminado.
   - `safe_cache_set(key, value, timeout)`: Captura excepciones y retorna `False` sin romper el flujo de ejecución.
   - `safe_cache_delete(key)`: Captura excepciones de borrado y retorna `False`.
2. **Throttling Resiliente (`mybookconnect.throttling`):**
   - Las clases estándar de DRF (`AnonRateThrottle`, `UserRateThrottle`, `SimpleRateThrottle`) acceden a la caché para contar peticiones. Si Redis caía, DRF lanzaba un 500 no capturado en `check_throttles`.
   - Se implementó `ResilientThrottleMixin`, `ResilientAnonRateThrottle`, `ResilientUserRateThrottle` y `ResilientSimpleRateThrottle`.
   - Si Redis no responde, el mixin registra un aviso en los logs y autoriza la petición (`allow_request` retorna `True`), permitiendo que el tráfico continúe hacia la base de datos de manera transparente.
3. **Observabilidad Resiliente:**
   - El middleware `ObservabilityMiddleware` y los colectores de métricas en memoria / Redis capturan silenciosamente los errores de Redis y no interrumpen el ciclo petición/respuesta.
