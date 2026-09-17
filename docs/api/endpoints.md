# Catálogo de Endpoints Principales

Resumen de las rutas REST y recursos expuestos por la API de MyBookConnect:

## 0. Autenticación y Credenciales (`/api/v1/auth/`)
- `POST /api/v1/auth/token/`: Inicio de sesión con mitigación de fuerza bruta (`LoginRateThrottle`).
- `POST /api/v1/auth/token/refresh/`: Rotación estricta de refresh tokens (detección de reuso y lista negra).
- `POST /api/v1/auth/register/`: Registro de usuarios con validación de complejidad de contraseña (`AUTH_PASSWORD_VALIDATORS`).
- `POST /api/v1/auth/logout/`: Cierre de sesión y revocación del refresh token activo.
- `POST /api/v1/auth/password/change/`: Cambio autenticado de contraseña con revocación de otras sesiones.
- `POST /api/v1/auth/password/reset/`: Solicitud de restablecimiento vía correo con protección anti-enumeración.
- `POST /api/v1/auth/password/reset/confirm/`: Confirmación de restablecimiento con token efímero y revocación total de sesiones.
- `POST /api/v1/auth/email/verify-request/`: Solicitud de confirmación de correo electrónico.
- `POST /api/v1/auth/email/verify/`: Validación de token efímero de correo y activación de `is_email_verified`.
- `POST /api/v1/auth/sessions/revoke-all/`: Cierre de sesión global en todos los dispositivos (*OutstandingToken* blacklist).
- `POST /api/v1/auth/google/`: Autenticación federada con Google Sign-In (provisión o enlace automático).

## 1. Libros y Catálogo (`/api/v1/books/`)
- `GET /api/v1/books/`: Lista paginada del catálogo de libros con filtros y búsqueda textual (`?search=...`, `?author=...`, `?category=...`).
- `POST /api/v1/books/`: Creación de una nueva obra literaria (requiere autenticación).
- `GET /api/v1/books/{id}/`: Detalle completo de un libro con autor, categorías y promedio de calificación.
- `GET /api/v1/books/{id}/recommendations/`: Libros similares basados en categorías y autores.
- `GET /api/v1/books/trending/`: Libros con mayor interacción en los últimos 30 días.
- `GET /api/v1/books/statistics/`: Cuadro estadístico del lector (libros leídos, páginas, distribución de notas).

## 2. Biblioteca Personal (`/api/v1/books/user/books/`)
- `GET /api/v1/books/user/books/`: Biblioteca personal del usuario autenticado con filtros (`?status=reading`, `?is_digital=true`, etc.).
- `POST /api/v1/books/user/books/`: Añadir un libro a la biblioteca personal con estado inicial y progreso.
- `GET /api/v1/books/user/books/{id}/`: Detalle de entrada personal de lectura.
- `PATCH /api/v1/books/user/books/{id}/`: Actualizar progreso de lectura, páginas, formato o notas.
- `DELETE /api/v1/books/user/books/{id}/`: Eliminar libro de la biblioteca personal.

## 3. Reseñas (`/api/v1/books/reviews/`)
- `GET /api/v1/books/reviews/?book={id}`: Listado público de reseñas de un libro con paginación por cursor.
- `POST /api/v1/books/reviews/`: Publicar una reseña (1 a 5 estrellas y texto; máx 1 por usuario y libro).
- `PATCH /api/v1/books/reviews/{id}/`: Editar reseña propia.
- `DELETE /api/v1/books/reviews/{id}/`: Eliminar reseña propia.

## 4. Red Social e Interacción (`/api/v1/books/feed/` & `/api/v1/users/`)
- `GET /api/v1/books/feed/`: Feed de actividad de los lectores seguidos por el usuario.
- `POST /api/v1/users/{id}/follow/`: Seguir a un usuario.
- `POST /api/v1/users/{id}/unfollow/`: Dejar de seguir a un usuario.
- `POST /api/v1/users/{id}/block/`: Bloquear a un usuario (oculta interacciones y previene mensajes).

## 5. Asistente con IA (`/api/v1/books/ai/`)
- `GET /api/v1/books/ai/status/`: Estado de disponibilidad del servicio de Inteligencia Artificial.
- `POST /api/v1/books/{id}/ai/summary/`: Generación de resumen contextual de un libro.
- `POST /api/v1/books/ai/semantic-search/`: Búsqueda por lenguaje natural basada en significado.

## 6. Observabilidad y Salud (`/api/v1/`)
- `GET /api/v1/health/`: Sonda de liveness (disponibilidad de proceso Django/Daphne sin dependencias externas).
- `GET /api/v1/ready/`: Sonda de readiness (comprobación activa de dependencias críticas: PostgreSQL y Redis).
- `GET /api/v1/observability/metrics/`: Cuadro de mando consolidado (latencias, p95, 5xx rate, consultas SQL). Solo administradores.
