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

### Cerrar Sesión y Revocación Individual
```http
POST /api/v1/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh": "eyJhbGciOi..."
}
```
**Respuesta:** `HTTP 200 OK` (el refresh token queda bloqueado en la base de datos).

---

## 3. Seguridad de Contraseñas y Gestión de Credenciales (Fase 47)

### 3.1 Mitigación de Fuerza Bruta y Credential Stuffing
Los endpoints de autenticación están blindados con limitadores de tasa estricta respaldados por Redis:
- **`LoginRateThrottle` (10 peticiones/minuto):** Aplica por IP y par `IP + username` para neutralizar ataques de diccionario o prueba automatizada de contraseñas.
- **`PasswordResetRateThrottle` (5 peticiones/minuto):** Protege contra spam y saturación de enlaces de restablecimiento.
- **`AuthAnonRateThrottle` (10 peticiones/minuto):** Limita la creación de cuentas masivas no deseadas.

### 3.2 Cambio Autenticado de Contraseña
Permite a usuarios autenticados renovar su clave. Comprueba la clave anterior, aplica validadores de complejidad (`AUTH_PASSWORD_VALIDATORS`), actualiza el hash e invalida de inmediato todas las demás sesiones activas.
```http
POST /api/v1/auth/password/change/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "StrongOldPass123!",
  "new_password": "NewSuperPass2026#",
  "new_password2": "NewSuperPass2026#",
  "revoke_other_sessions": true
}
```

### 3.3 Restablecimiento Seguro de Contraseña (Anti-Enumeración)
- **Solicitud (`POST /api/v1/auth/password/reset/`):** Genera un token criptográfico efímero mediante `PasswordResetTokenGenerator`. Responde siempre con `200 OK` idéntico exista o no el correo para prevenir fugas de privacidad y enumeración de usuarios.
- **Confirmación (`POST /api/v1/auth/password/reset/confirm/`):** Valida `uid` y `token`. Tras fijar la nueva clave, revoca automáticamente todas las sesiones abiertas (*outstanding tokens*) asociadas al usuario para expulsar accesos no autorizados.

### 3.4 Verificación de Correo Electrónico
- **Solicitud (`POST /api/v1/auth/email/verify-request/`):** Envía un enlace seguro con token generado por `EmailVerificationTokenGenerator`.
- **Confirmación (`POST /api/v1/auth/email/verify/`):** Valida el token y marca `is_email_verified = True`. El token se invalida de inmediato tras su uso.

### 3.5 Revocación Global de Sesiones
Invalida todos los refresh tokens pendientes de un usuario en todos sus navegadores y dispositivos móviles:
```http
POST /api/v1/auth/sessions/revoke-all/
Authorization: Bearer <access_token>
```
Responde con el conteo de tokens bloqueados (`"revoked_count": N`).

### 3.6 Autenticación Federada con Google OAuth
```http
POST /api/v1/auth/google/
Content-Type: application/json

{
  "id_token": "<google_id_token>"
}
```
Verifica la firma y vigencia del token de Google Sign-In, provisiona una cuenta con contraseña no utilizable y `is_email_verified=True`, emitiendo el par JWT de acceso y refresco.

