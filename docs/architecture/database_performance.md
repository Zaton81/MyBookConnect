# Arquitectura de Base de Datos, Optimización de Consultas y Rendimiento (Fase 9)

Documento técnico que detalla la auditoría y erradicación de consultas N+1, catálogo de índices compuestos en PostgreSQL, estrategias de paginación uniforme y presupuestos de rendimiento (*Performance Budgets*) de MyBookConnect.

---

## 1. Auditoría y Erradicación de Consultas N+1

Se realizó una auditoría profunda sobre las consultas emitidas por los endpoints transaccionales y de lectura frecuente para asegurar un número constante y acotado de queries $O(1)$ independiente del volumen de datos $N$:

### 1.1. Perfil de Usuario (`UserProfileView` y `UserSerializer`)
- **Problema previo:** La serialización del perfil de usuario invocaba 4 consultas separadas de agregación `COUNT(*)` (`reviews.count`, `user_books.count`, `following.count`, `followers.count`) debido a la evaluación impaciente de los argumentos por defecto en llamadas `getattr(obj, '...', obj....count())`. Además, para usuarios autenticados que consultaban su propio perfil, se disparaban 4 comprobaciones innecesarias de relaciones consigo mismos (`is_following`, `is_blocked`, `am_i_blocked`, `is_muted`).
- **Solución implementada:**
  - `UserProfileView.get_object()` anota en una única consulta SQL los cuatro contadores (`reviews_count`, `books_read_count`, `following_count`, `followers_count`) mediante `Count(..., filter=..., distinct=True)` y pre-carga las claves Many-to-Many de seguidores/seguidos (`prefetch_related('following', 'followers')`).
  - `UserSerializer` utiliza guardas condicionales `if hasattr(obj, '..._count')` evitando invocar consultas de conteo, y devuelve inmediatamente `False` si el visor consulta su propio perfil en las relaciones sociales.
- **Impacto:** Reducción de 10+ consultas SQL a 3 consultas acotadas y estables.

### 1.2. Listado de Conversaciones de Chat (`ConversationViewSet` y `ConversationSerializer`)
- **Problema previo:** Para cada conversación del usuario autenticado, `ConversationSerializer` ejecutaba una consulta SQL independiente para obtener el último mensaje (`last_message`) y otra consulta SQL para contabilizar mensajes no leídos (`unread_count`), generando $2N + 1$ consultas en el listado.
- **Solución implementada:**
  - `ConversationViewSet.get_queryset()` anota `annotated_unread_count` usando `Count('messages', filter=Q(read=False, ...) & ~Q(sender=user))` y pre-carga ordenadamente los mensajes mediante `Prefetch('messages', queryset=Message.objects.filter(...).order_by('-created_at'), to_attr='prefetched_messages')`.
  - `ConversationSerializer` consume los datos ya residentes en memoria sin disparar consultas secundarias a PostgreSQL.
- **Impacto:** Reducción de $2N + 1$ consultas a exactamente 4 consultas SQL (conteo de paginación + conversaciones + participantes + mensajes recientes).

### 1.3. Estado de Seguimiento (`CheckFollowStatusView`)
- **Problema previo:** Se evaluaba la relación de seguimiento en memoria de Python con `target_user in request.user.following.all()`, lo que obligaba al ORM a volcar todos los usuarios seguidos a memoria.
- **Solución implementada:** Sustituido por consultas indexadas `request.user.following.filter(id=user_id).exists()` y `request.user.followers.filter(id=user_id).exists()`, que ejecutan un `SELECT 1 ... LIMIT 1` directo en base de datos.

### 1.4. Comentarios de Reseñas (`ReviewCommentListCreateView`)
- **Problema previo:** El endpoint `/api/v1/books/reviews/{id}/comments/` volcaba la totalidad de comentarios de una reseña a memoria sin paginar.
- **Solución implementada:** Incorporado soporte para paginación estándar con `StandardResultsSetPagination` cuando se envía `?page=X` o `?paginate=true`, y límite de seguridad de 100 elementos como tope en peticiones no paginadas para prevenir ataques de denegación de servicio por memoria.

---

## 2. Catálogo de Índices Compuestos en PostgreSQL

Para respaldar las consultas críticas y permitir escaneos de índice puros (*Index-Only Scans*), se generó y aplicó la migración `books.0024_book_idx_book_author_created_and_more`:

| Tabla / Modelo | Nombre del Índice | Campos Indexados | Propósito y Consulta Optimizada |
| :--- | :--- | :--- | :--- |
| **`Book`** | `idx_book_author_created` | `(author, -created_at)` | Acelera la obtención de obras de un autor ordenadas cronológicamente en páginas de autor y recomendaciones. |
| **`Review`** | `idx_review_book_rating` | `(book, rating)` | Permite *Index-Only Scan* en PostgreSQL para promedios de calificación (`AVG(rating)`) y distribución por estrellas. |
| **`Review`** | `idx_review_user_book` | `(user, book)` | Búsqueda instantánea de la reseña emitida por un usuario sobre un libro determinado. |
| **`UserBook`** | `idx_userbook_book_status` | `(book, status)` | Agregaciones eficientes de lectores leyendo, queriendo leer o habiendo terminado un libro. |

### Inspección con `EXPLAIN ANALYZE`
Todas las consultas sobre estos índices fueron validadas mediante `QueryProfiler.explain_analyze()` (`backend/mybookconnect/query_profiler.py`), confirmando tiempos de ejecución en base de datos sustancialmente inferiores al umbral crítico de 100 ms.

---

## 3. Paginación Uniforme en la Plataforma

Para evitar la descarga de colecciones ilimitadas:

1. **Seguidores y Seguidos:** Paginación con `StandardResultsSetPagination` (`PAGE_SIZE = 20`).
2. **Catálogo de Libros:** Paginado con `StandardResultsSetPagination` (`PAGE_SIZE = 20`).
3. **Mensajes de Chat:** Paginación mediante cursor temporal (`StandardCursorPagination`) sobre `created_at` para garantizar estabilidad ante inserciones concurrentes en tiempo real.
4. **Comentarios de Reseña:** Paginación con `StandardResultsSetPagination` y límite de seguridad.

---

## 4. Presupuestos de Rendimiento (*Performance Budgets*)

Se integraron objetivos de nivel de servicio en `ObservabilityMetricsService` (`backend/mybookconnect/observability.py`), expuestos a través de `/api/v1/observability/metrics/`:

```json
{
  "latency_ms": {
    "average": 45.2,
    "p95": 120.5,
    "p99": 280.1,
    "sample_size": 200
  },
  "performance_budgets": {
    "api_p95_budget_ms": 500.0,
    "api_p99_budget_ms": 1500.0,
    "critical_queries_budget_ms": 100.0,
    "is_within_budget": true,
    "status": "within_budget"
  }
}
```

- **API p95:** Máximo 500 ms.
- **API p99:** Máximo 1500 ms (1.5 s).
- **Consultas Críticas SQL:** Máximo 100 ms.
- **Estado Operativo:** El servicio marca automáticamente `'breached'` si cualquiera de los percentiles sobrepasa el presupuesto estipulado, permitiendo alertas automatizadas de observabilidad.
