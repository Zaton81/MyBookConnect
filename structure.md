# Estructura actual y roadmap de MyBookConnect

## Backend
- **apps:**
  - `users`: modelo de usuario extendido, registro, perfil, edición, autenticación JWT
  - `books`: modelos de libros, autores, reseñas, UserBook (estado por usuario)
  - `app`: (legacy o utilidades, revisar si se usa)
- **modelos principales:**
  - User: username, email, bio, avatar, birth_date, location, privacy_level, following, first_name, last_name
  - Author: name, biography
  - Book: title, author (FK), isbn, cover, description, average_rating, created_at
  - UserBook: user (FK), book (FK), is_read, rating, is_digital, owned, wishlist, notes, updated_at
  - Review: user (FK), book (FK), rating, text, created_at
- **serializers:** DRF para todos los modelos
- **views:** API REST para registro, perfil, edición, libros, autores, userbooks, reseñas
- **urls:**
  - `/api/v1/auth/` (registro, login, perfil, edición)
  - `/api/v1/books/` (libros, autores, userbooks, reseñas)
- **migraciones:**
  - users y books migrados
- **media:**
  - avatars y covers gestionados por MEDIA_ROOT

## Frontend
- **pages:**
  - Login, Register, Home, Profile, EditProfile, Library, AddBook
- **components:**
  - header, footer, AuthBox, EditProfile, ProtectedRoute, logo
- **store:**
  - Zustand para auth y perfil
- **servicios:**
  - api.ts para llamadas a backend
- **tipos:**
  - User, AuthState, RegisterData, LoginData
- **funcionalidad actual:**
  - Registro/login con JWT
  - Edición de perfil básica (bio, privacidad, avatar, fecha, ubicación)
  - Biblioteca: muestra libros del usuario (sin orden ni filtros avanzados)
  - Añadir libro: formulario minimal

## Roadmap y mejoras a incorporar
- **Biblioteca avanzada:**
  - Ordenar por fecha, nota, lista de deseos, formato, propiedad, alfabético
  - Filtrar por estado (leído, wishlist, digital/físico, etc)
  - Mostrar solo algunos (paginación, top N, etc)
  - Cada libro con enlace a su perfil
- **Edición de perfil completa:**
  - Editar todos los campos: nombre, apellidos, email, bio enriquecida (CKEditor), avatar, fecha, ubicación, privacidad
  - Soporte para texto enriquecido en biografía
- **Perfil de libro:**
  - Página dedicada para cada libro con detalles, reseñas, usuarios que lo tienen, etc
- **Reseñas:**
  - Añadir y mostrar reseñas por usuario/libro
- **Mejoras UI:**
  - Cards, paginación, filtros, orden
  - Subida de imágenes (avatar, portada)
- **Admin:**
  - Gestión avanzada de usuarios/libros/autores

---

Este archivo se irá actualizando conforme se incorporen nuevas funcionalidades y modelos.
