# Autenticación y Autorización con JWT

## 1. Estrategia de Tokens JWT
MyBookConnect implementa `djangorestframework-simplejwt` con rotación obligatoria de credenciales temporales:

### Parámetros de Ciclo de Vida
- **Access Token:**
  - Vida útil: **15 minutos**.
  - Propósito: Acompañar cada petición HTTP en la cabecera `Authorization: Bearer <access_token>`.
  - Contiene: `user_id`, `username`, `exp`, `jti`.
- **Refresh Token:**
  - Vida útil: **7 días**.
  - Propósito: Solicitar nuevos tokens de acceso sin exigir al usuario reintroducir sus credenciales.
  - Rotación: Cada vez que se usa el refresh token para generar un nuevo access token, el refresh token anterior se invalida y se emite uno nuevo (`ROTATE_REFRESH_TOKENS = True`).
  - Blacklisting: Los refresh tokens rotados o revocados al cerrar sesión se añaden a la tabla de revocación (`BLACKLIST_AFTER_ROTATION = True`).

---

## 2. Endpoints de Autenticación

### Iniciar Sesión (Obtención de Par de Tokens)
```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "lector1",
  "password": "Password123!"
}
```
**Respuesta:**
```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi..."
}
```

### Refrescar Token de Acceso
```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJhbGciOi..."
}
```
**Respuesta:**
```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi..."
}
```

### Cerrar Sesión y Revocación
```http
POST /api/v1/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh": "eyJhbGciOi..."
}
```
**Respuesta:** `HTTP 200 OK` (el refresh token queda bloqueado en la base de datos).
