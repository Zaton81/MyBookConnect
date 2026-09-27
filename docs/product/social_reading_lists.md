# Listas Sociales y Colecciones de Lectura (Fase 21)

## 1. Visión General

La **Fase 21 — Listas Sociales** evoluciona las listas de libros desde un repositorio personal hacia un espacio comunitario y participativo, donde los lectores pueden crear, organizar, debatir, seguir y clonar colecciones temáticas con control granular de privacidad.

---

## 2. Arquitectura de Privacidad

Las listas cuentan con tres niveles de visibilidad (`ReadingListPrivacy`):
- `public`: Visible para cualquier lector en la plataforma y en perfiles públicos. Permite comentarios y duplicado.
- `followers`: Visible únicamente para usuarios que siguen al creador.
- `private`: Visible exclusivamente para el autor.

---

## 3. Funcionalidades y Acciones Principales

### 3.1 Clonar / Duplicar Lista (`clone`)
- **Endpoint:** `POST /api/v1/books/reading-lists/<id>/clone/` (Autenticado).
- **Comportamiento:** Crea una nueva lista con nombre `Copia de <nombre>`, visibilidad `private` por defecto y replica de forma atómica todos los `ReadingListItem` preservando posiciones y notas personales.

### 3.2 Comentarios y Debate en Listas (`comments`)
- **Modelo:** `ReadingListComment(SoftDeleteModel)` con campos `user`, `reading_list`, `content`, `is_moderated` e índices compuestos.
- **Endpoints:**
  - `GET /api/v1/books/reading-lists/<id>/comments/`: Listado de comentarios activos no moderados.
  - `POST /api/v1/books/reading-lists/<id>/comments/`: Publicación de comentario sanitizado.
  - `DELETE /api/v1/books/reading-lists/<id>/comments/<comment_id>/`: Eliminación suave (solo autor o staff).

### 3.3 Métricas y Aperturas (`views_count`)
- Al consultar el detalle de una lista ajena, el campo `views_count` se incrementa automáticamente mediante `F('views_count') + 1`.
- El serializador `ReadingListSerializer` expone `items_count`, `followers_count`, `comments_count`, `views_count` e `is_following`.

### 3.4 Compartición Rápida
- Generación de enlace permanente `${origin}/reading-lists?id=<id>` con soporte de copiado al portapapeles y alerta visual de confirmación.
