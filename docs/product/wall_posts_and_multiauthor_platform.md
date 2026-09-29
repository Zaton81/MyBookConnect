# Soporte Multi-autor, Reseñas en Perfil y Muro Social (Fase 32)

Este documento describe la arquitectura, modelos de datos, endpoints y experiencia de usuario implementados para dar soporte a libros con múltiples autores, visualización integral de reseñas en el perfil de usuario y el sistema de muro social de publicaciones interactivas.

---

## 1. Soporte Multi-autor en Libros (`Book.authors`)

### 1.1. Motivación y Principio de Compatibilidad
Existen obras literarias fruto de colaboraciones entre dos o más autores (por ejemplo, *Good Omens* de Terry Pratchett y Neil Gaiman, antologías o traducciones especializadas). 

Para garantizar **100% de compatibilidad retroactiva** con el ecosistema existente:
1. Se conserva el campo `author = ForeignKey(Author, null=True, blank=True, on_delete=SET_NULL, related_name='books')` como autor principal (*lead author*).
2. Se añade la relación Many-to-Many `authors = ManyToManyField(Author, related_name='all_books', blank=True)`.
3. Al guardar un libro (`save()`), si `self.author` existe, se añade automáticamente a `self.authors`.
4. El método `book.get_author_names()` devuelve la cadena formateada de todos los autores (ej. *"Neil Gaiman, Terry Pratchett"*).

### 1.2. Serialización y API
En `BookSerializer`:
- **Lectura:**
  - `authors`: Lista de autores completos `[{ id, name, photo, ... }]`.
  - `author`: Objeto del autor principal para clientes existentes.
- **Escritura:**
  - `author_ids`: Lista de IDs de autores existentes (`[1, 2]`).
  - `author_names`: Lista de nombres de autores en texto plano (`["Neil Gaiman", "Terry Pratchett"]`), creándolos dinámicamente si no existen en catálogo.

### 1.3. Frontend
En [BookDetail.tsx](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/books/pages/BookDetail.tsx):
- Se itera sobre `book.authors` renderizando cada nombre como enlace individual a su ficha `/authors/:id`.
- Se transfieren todos los nombres combinados a componentes auxiliares como [AmazonAdSlot.tsx](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/components/ui/AmazonAdSlot.tsx).

---

## 2. Reseñas en el Perfil de Usuario

### 2.1. Endpoints y Privacidad
El lector puede consultar todas las opiniones emitidas por un usuario:
- `GET /api/v1/reviews/?user=<user_id>` (o `?username=<username>`).
- `GET /api/v1/users/<user_id>/reviews/`.

**Políticas de Privacidad Aplicadas:**
- `filter_visible_reviews(request.user, queryset)`:
  - Respeta el nivel de privacidad del perfil (`public`, `followers`, `private`).
  - Aplica bloqueos bidireccionales (`PrivacyService.are_mutually_blocked`): si existe bloqueo, retorna 404 para no filtrar información.
  - Excluye reseñas eliminadas o moderadas.

### 2.2. Frontend: Pestaña "Reseñas"
En [Profile.tsx](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/profile/pages/Profile.tsx):
- Pestaña accesible desde el menú superior o haciendo clic en el contador de reseñas de las estadísticas.
- Tarjeta de reseña con:
  - Portada del libro con enlace a `/books/:id`.
  - Título y autor(es).
  - Puntuación en estrellas 1 a 5 (`StarRating`).
  - Título y cuerpo de la reseña.
  - Métricas de me gusta y comentarios.
  - Fecha formateada.

---

## 3. Muro Social y Publicaciones de Usuario (`UserPost`)

### 3.1. Esquema de Datos
En `users/models.py`:
- **`UserPost`:**
  - `author`: Usuario que escribe la publicación.
  - `target_user`: Usuario dueño del muro donde se publica.
  - `content`: Texto de la publicación (hasta 2000 caracteres, sanitizado contra XSS/HTML malicioso).
  - `book`: Libro opcional vinculado a la publicación (para recomendar o comentar una lectura).
  - `likes_count`: Contador desnormalizado para consultas O(1).
  - `comments_count`: Contador de comentarios en la publicación.
  - `is_pinned`: Permite fijar publicaciones destacadas en la parte superior.
  - `created_at`, `updated_at`.
- **`UserPostLike`:**
  - Registra qué usuarios han dado me gusta a un post con constraint de unicidad `('post', 'user')`.
- **`UserPostComment`:**
  - Hilo de debate y respuestas dentro de cada publicación del muro.

### 3.2. Sincronización con el Feed Social
Al publicar en el muro, se dispara automáticamente la creación de un evento `Activity`:
- `type = ActivityType.POST_CREATED` ("Publicó en el muro").
- La publicación se distribuye en el feed social cronológico e inteligente ([FeedView](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/users/views.py)) de los seguidores del autor.

### 3.3. Endpoints del Muro
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users/<user_id>/posts/` | Listar publicaciones del muro con autor, libro, likes y comentarios. |
| `POST` | `/api/v1/users/<user_id>/posts/` | Crear una nueva publicación en el muro. |
| `DELETE` | `/api/v1/users/posts/<post_id>/` | Eliminar publicación (autor del post o dueño del muro). |
| `POST` | `/api/v1/users/posts/<post_id>/like/` | Alternar me gusta (*like* / *unlike*). |
| `GET` | `/api/v1/users/posts/<post_id>/comments/` | Listar comentarios de una publicación. |
| `POST` | `/api/v1/users/posts/<post_id>/comments/` | Añadir un comentario a la publicación. |

---

## 4. Fase 32: Escalabilidad de Recomendaciones Multi-autor

En [recommendation_service.py](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/books/services/recommendation_service.py):
1. **Ponderación de afinidad (`_calculate_user_affinity`):**
   - Evalúa tanto `book.author_id` como cada coautor en `book.authors.all()`.
   - Si un usuario lee o valora positivamente una obra en colaboración, la afinidad acumulada beneficia a ambos autores por igual.
2. **Recomendaciones Item-to-Item (`get_book_recommendations`):**
   - Al buscar libros relacionados a partir de una obra, el conjunto de candidatos expande la búsqueda hacia cualquiera de los coautores registrados (`author_id__in=source_author_ids | authors__in=source_author_ids`).
   - El impulso de puntuación de afinidad por autor se activa si el candidato comparte cualquiera de los autores de la obra de origen.
