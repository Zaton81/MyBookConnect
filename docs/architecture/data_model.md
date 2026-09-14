# Modelo de Datos e Integridad Relacional

## 1. Esquema de Entidades Principales

### `users.CustomUser`
- Identificador primario `id` (BigAutoField).
- Credenciales: `username` (único), `email` (único, normalizado), `password` (hasheada con PBKDF2/Argon2).
- Perfil: `biography`, `avatar` (con validación de formato y tamaño), `birth_date`, `location`.
- Privacidad: `privacy_level` (`public`, `followers_only`, `private`).
- Relaciones sociales: `followers` (Many-to-Many asimétrico mediante `Follow`), `blocked_users` (`Block`).

### `books.Author`
- `name`: Nombre del autor (con índice GIN de trigramas para búsqueda difusa).
- `biography`: Biografía enriquecida automáticamente desde Wikipedia/OpenLibrary.
- `photo`: Imagen del autor validada.
- `enrichment_attempted`: Bandera booleana para evitar consultas externas redundantes.

### `books.Book`
- `title`: Título de la obra (índice B-tree y GIN trigram `idx_book_title_trgm`).
- `author`: Clave foránea nullable con `ON DELETE SET NULL`.
- Identificadores: `isbn` normalizado (10/13 dígitos), `google_volume_id`, `openlibrary_work_id`.
- `description`: Sinopsis con índice GIN `idx_book_desc_trgm`.
- `categories`: Many-to-Many con `Category`.
- `average_rating`: Puntuación media precalculada.

### `books.UserBook`
- Representa la relación personal y privada entre un lector y un libro.
- Clave única compuesta: `unique_together = ('user', 'book')`.
- `status`: Enum de lectura (`want_to_read`, `reading`, `read`, `abandoned`).
- `progress`: Entero de 0 a 100 con validadores de rango `MinValueValidator(0)` y `MaxValueValidator(100)`.
- `current_page`: Página actual de lectura.
- Banderas: `is_read`, `is_digital`, `owned`, `wishlist`.
- Índices compuestos: `idx_userbook_read_updated` e `idx_userbook_status_updated`.

### `books.Review`
- Representa la valoración u opinión pública de un lector sobre un libro.
- Restricción de unicidad: un usuario sólo puede publicar una reseña por libro.
- `rating`: Valor entero de 1 a 5 estrellas con `MinValueValidator(1)` y `MaxValueValidator(5)`.
- `text`: Cuerpo de la reseña.
- `is_spoiler`: Indica si contiene revelaciones de la trama.
- Índices: `idx_review_book_created`, `idx_review_user_created`, `idx_review_created_at`.

### `messages_app.Conversation` y `Message`
- `Conversation`: Agrupa dos participantes en una sala de chat privada.
- `Message`: Mensaje individual con `sender`, `text`, `is_read`, `created_at` con índice de cursor.
