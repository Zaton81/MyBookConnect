# Modelo de Dominio e Integridad de Datos — MyBookConnect

> **Documento de especificación técnica de dominio (Fase 1 - RoadmapV2)**  
> Versión: 1.0.0  
> Estado: Aprobado y en vigor  
> Fuente de verdad: PostgreSQL 16 + Django ORM

---

## 1. Separación Conceptual: `UserBook` vs `Review`

Para evitar ambigüedades y divergencias en el estado de la aplicación, el dominio separa estrictamente la experiencia de lectura personal de la opinión pública:

### 1.1. `UserBook` (Estado Personal de Lectura)
- **Definición**: *"Mi relación personal con este libro"*.
- **Propósito**: Gestión del ciclo de lectura privado o compartido según privacidad (quiero leer, leyendo, leído, abandonado), progreso porcentual, número de páginas leídas, formato físico/digital, fechas de inicio y fin, notas privadas y lista de deseos (`wishlist`).
- **Principio clave**: **`UserBook` NO es la fuente del rating público**. Aunque almacena un rating personal legacy opcional (1..5), este no computa directamente en el rating agregado de la obra ni en el feed de reseñas públicas.

### 1.2. `Review` (Opinión Pública)
- **Definición**: *"Mi opinión pública y calificada sobre este libro"*.
- **Propósito**: Reseña comunitaria que alimenta el cálculo de promedio del libro (`Book.average_rating`), el feed social, las interacciones sociales (likes, comentarios) y la moderación comunitaria.
- **Campos**: `user`, `book`, `rating` (1..5 obligatorio), `title`, `text` (sanitizado contra XSS), `spoiler`, `likes_count`, `comments_count`, timestamps y campos de soft-delete (`is_deleted`, `deleted_at`).

---

## 2. Escala de Calificación Unificada (SemVer 1..5)

El sistema impone de manera homogénea la escala de **1 a 5 estrellas** en todas las capas del stack:

```text
1 <= rating <= 5  (Entero: 1, 2, 3, 4, 5)
```

### 2.1. Nivel Base de Datos (PostgreSQL)
- `CheckConstraint(check=Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5")`
- `CheckConstraint(check=Q(rating__gte=1, rating__lte=5), name="userbook_rating_1_to_5")`
- `PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])`

### 2.2. Nivel Serializador y API (Django REST Framework)
- `ReviewSerializer` y `UserBookSerializer` validan explícitamente `min_value=1` y `max_value=5`.
- Respuestas con códigos estándar `400 Bad Request` ante valores fuera de rango o tipos inválidos.

### 2.3. Nivel Frontend (React + TypeScript)
- **Esquema Zod (`reviewSchemas.ts`)**:
  ```typescript
  rating: z.number().int().min(1, 'La puntuación mínima es 1').max(5, 'La puntuación máxima es 5')
  ```
- **Componentes de Interfaz (`BookReviewsSection.tsx`, `StarRating.tsx`)**:
  - Renderizado estricto de 5 estrellas interactivas.
  - Selección visual restringida a enteros de 1 a 5.

---

## 3. Integridad Referencial y Restricciones de Unicidad

PostgreSQL actúa como la autoridad suprema de integridad.

| Modelo | Restricción / Índice | Tipo | Propósito |
| :--- | :--- | :--- | :--- |
| `Review` | `unique_active_user_book_review` | `UniqueConstraint` (parcial: `deleted_at__isnull=True`) | Impide que un usuario tenga múltiples reseñas activas simultáneas sobre el mismo libro, permitiendo recrear reseñas tras soft-delete. |
| `Review` | `review_rating_1_to_5` | `CheckConstraint` (`1 <= rating <= 5`) | Garantiza a nivel de motor SQL la imposibilidad de ratings anómalos o fuera de escala. |
| `UserBook` | `unique_together = ('user', 'book')` | `UniqueConstraint` | Un usuario solo puede tener una entrada en su biblioteca por libro. |
| `UserBook` | `userbook_rating_1_to_5` | `CheckConstraint` (`1 <= rating <= 5`) | Valida el rating personal en base de datos. |
| `ReviewLike` | `unique_together = ('user', 'review')` | `UniqueConstraint` | Idempotencia en likes de reseñas; previene duplicados concurrentes. |
| `ReadingListBook` | `unique_together = ('reading_list', 'book')` | `UniqueConstraint` | Un libro no puede repetirse en la misma lista de lectura. |

---

## 4. Política de Soft Delete

MyBookConnect implementa `SoftDeleteModel` para entidades con actividad social o auditoría relevante:

### 4.1. Modelos con Soft Delete
- `Review`: Las reseñas borradas no se destruyen físicamente en cascada para preservar auditoría de moderación y evitar inconsistencias en hilos de comentarios o reportes.
- `ReviewComment`: Comentarios borrados se marcan con soft-delete.

### 4.2. Comportamiento Operativo
- `objects`: Manager por defecto que filtra automáticamente `deleted_at__isnull=True`. Oculto para APIs y consultas normales.
- `all_objects`: Manager administrativo y de auditoría que incluye registros eliminados.
- `delete()`: Marca `is_deleted = True` y `deleted_at = timezone.now()`.
- `hard_delete()`: Eliminación física en PostgreSQL restringida a comandos de mantenimiento o solicitudes GDPR / derecho al olvido.

---

## 5. Atomicidad en Operaciones Compuestas (`transaction.atomic`)

Toda operación que involucre modificaciones multientidad o efectos secundarios críticos se ejecuta bajo transacciones atómicas de base de datos:

1. **Creación de Reseñas y Gamificación**:
   - Creación de `Review` + disparo de evaluación de badges (`GamificationService.evaluate_user_badges`) + invalidación de caché reactiva. Si la transacción falla, se ejecuta rollback total.
2. **Interacciones Sociales (Likes y Comentarios)**:
   - Inserción de `ReviewLike` / `ReviewComment` + creación de `Notification` social hacia el autor. Si la notificación falla, el like o comentario se cancela limpiamente devolviendo error controlado.
3. **Bloqueo y Desconexión de Usuarios**:
   - Adición a `blocked_users` + eliminación bidireccional de relaciones `following` + registro en log de auditoría.
4. **Importación de Libros**:
   - Inserción de autor + creación de libro + asociación M2M de categorías + generación de embedding.

---

## 6. Verificación y Pruebas Automatizadas

La integridad del dominio se valida mediante una suite completa y reproducible:
- **Test Suite Dedicada**: `backend/tests/test_phase01_domain_integrity.py`
- **Comprobaciones de Regresión**:
  - `tests/test_phase41_postgres_redis.py` (constraints de BD)
  - `tests/test_phase63_transactions.py` (rollbacks atómicos)
  - `tests/test_phase64_concurrency.py` (concurrencia y bloqueos)
  - `tests/test_phase65_cache_invalidation.py` (cascada de caché)
