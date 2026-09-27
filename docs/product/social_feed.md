# Muro Social de Actividad y Feed (Fase 22)

Este documento describe la arquitectura técnica, controles de privacidad y flujo funcional del **Feed Social y Actividad** de MyBookConnect, conforme a las Secciones 27 y 7.4 de `RoadmapV2.md`.

---

## 1. Tipos de Eventos y Actividades

El muro social registra y expone 9 tipos de eventos literarios y de interacción comunitaria:

| Tipo | Clave `ActivityType` | Disparador | Metadatos Asociados |
| :--- | :--- | :--- | :--- |
| **Libro añadido** | `BOOK_ADDED` | Creación de entrada en biblioteca | `status` |
| **Comenzó lectura** | `BOOK_STARTED` | Transición a `ReadingStatus.READING` | `progress` |
| **Lectura completada** | `BOOK_FINISHED` | Transición a `ReadingStatus.READ` | `rating` |
| **Calificación** | `BOOK_RATED` | Asignación de puntuación sin reseña | `rating` |
| **Reseña publicada** | `REVIEW_CREATED` | Creación de `Review` | `rating`, `title` |
| **Seguimiento** | `USER_FOLLOWED` | Acción de seguir a un lector | `target_user` |
| **Lista creada** | `LIST_CREATED` | Creación de `ReadingList` pública o para seguidores | `list_id`, `name`, `privacy` |
| **Like en reseña** | `REVIEW_LIKED` | Reacción de me gusta en una reseña | `review_id`, `rating`, `target_user` |
| **Comentario en reseña** | `COMMENT_ADDED` | Comentario en una reseña | `comment_id`, `review_id`, `target_user` |

---

## 2. Controles de Privacidad y Bloqueo (Roadmap 7.4)

Toda consulta al feed (`GET /api/v1/users/feed/`) atraviesa el filtro `PrivacyService.filter_visible_activities`:

1. **Bloqueo Bidireccional Estricto:**
   - Si `A bloquea B` o `B bloquea A`, las publicaciones de ambos son mutuamente invisibles tanto en `user` como en `target_user`.
2. **Usuarios Silenciados (`muted_users`):**
   - Si un usuario silencia a otro (`POST /api/v1/auth/users/<id>/mute/`), todas las actividades de ese usuario desaparecen de su feed personal.
3. **Publicaciones Ocultadas Individualmente (`HiddenActivity`):**
   - El usuario puede descartar publicaciones específicas de su feed (`POST /api/v1/auth/feed/<id>/hide/`), persistiendo la exclusión sin afectar al resto de lectores.
4. **Nivel de Privacidad de Actividad (`activity_privacy_level`):**
   - Si el autor configura su privacidad en `private`, sus actividades no se muestran a nadie más.
   - Si la configura en `friends`, solo se muestran a usuarios a los que sigue recíprocamente o seguidores admitidos.
5. **Cuentas Eliminadas:**
   - Se excluyen automáticamente cuentas con `deleted_at__isnull=False` (RGPD Art. 17).

---

## 3. Modos y Agrupación Temática

### Parámetros de Consulta:
- **Modo:**
  - `?mode=smart` (por defecto): Ordenación multi-factor (`SmartFeedRankingEngine`: recencia, afinidad social, tipo de evento y afinidad con lista de deseos/géneros).
  - `?mode=chronological`: Orden cronológico estricto (`-created_at`).
- **Filtro por Categoría:**
  - `?category=reads`: Actividades de lectura (`BOOK_STARTED`, `BOOK_FINISHED`, `BOOK_ADDED`, `BOOK_RATED`).
  - `?category=reviews`: Reseñas e interacciones de opinión (`REVIEW_CREATED`, `REVIEW_LIKED`, `COMMENT_ADDED`).
  - `?category=lists`: Creación y difusión de listas (`LIST_CREATED`).
  - `?category=social`: Conexiones comunitarias (`USER_FOLLOWED`, `REVIEW_LIKED`, `COMMENT_ADDED`).
- **Filtro Exacto:**
  - `?type=<ActivityType>`

---

## 4. Endpoints REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users/feed/` | Listado paginado de actividades del feed social. |
| `GET` | `/api/v1/books/feed/` | Alias canónico del feed de actividades. |
| `POST` | `/api/v1/auth/feed/<id>/hide/` | Oculta la actividad del feed del usuario autenticado. |
| `POST` | `/api/v1/auth/feed/<id>/unhide/` | Restaura la actividad en el feed del usuario autenticado. |
| `POST` | `/api/v1/auth/users/<id>/mute/` | Silencia a un usuario para no ver su contenido en el feed. |
| `POST` | `/api/v1/auth/users/<id>/unmute/` | Deshace el silenciamiento social del usuario. |
| `POST` | `/api/v1/auth/users/<id>/unfollow/` | Deja de seguir a un usuario. |
| `POST` | `/api/v1/auth/users/<id>/block/` | Bloquea a un usuario y rompe relaciones de seguimiento. |
