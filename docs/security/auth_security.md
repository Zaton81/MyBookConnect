# Seguridad de Autenticación, Autorización y WebSockets

> **Documento de Arquitectura y Seguridad — Fase 3**  
> Última actualización: Septiembre 2026  
> Estado: Implementado y verificado (P0/P1)

---

## 1. Visión General

La Fase 3 de MyBookConnect establece un perímetro de defensa en profundidad para autenticación y autorización, cubriendo:

1. **Ciclo de vida de tokens JWT con revocación inmediata:** Solución al problema de persistencia de access tokens tras logout o cambio de contraseña.
2. **WebSocket Handshake Seguro (RFC 6455 / OWASP):** Transición de tokens JWT en URL hacia tickets efímeros de un solo uso.
3. **Flujo de Verificación de Correo Electrónico:** Remitente oficial `noreply@mybooksocial.com`, configurable por entorno (`REQUIRE_EMAIL_VERIFICATION`).
4. **Google OAuth 2.0 Full-Stack:** Flujo unificado en backend y componentes accesibles en el frontend (`GoogleLoginButton`).
5. **Protección IDOR y Anti-Enumeración:** Validación de permisos a nivel de objeto y respuestas `404 Not Found` ante usuarios o recursos privados/bloqueados.
6. **Cabeceras de Seguridad:** Políticas de referencia (`strict-origin-when-cross-origin`), `nosniff`, `DENY` en framing y cookies seguras.

---

## 2. JWT y Revocación Inmediata de Sesiones

### 2.1. El problema tradicional de SimpleJWT
En arquitecturas JWT estándar, los *access tokens* son apátridas (stateless). Al invocar un cierre de sesión ("Revoke All Sessions") o al cambiar la contraseña, la biblioteca SimpleJWT añade los *refresh tokens* a la tabla `BlacklistedToken`, pero los *access tokens* previamente emitidos siguen siendo aceptados durante su tiempo de vida remanente (15 minutos).

### 2.2. Solución implementada: RevocationCheckingJWTAuthentication
Se ha implementado una clase de autenticación personalizada (`users.authentication.RevocationCheckingJWTAuthentication`):

```text
[Cliente API] ──(Bearer <access_token>)──> [DRF / API]
                                                 │
                                                 ├── 1. Validar firma y expiración JWT
                                                 ├── 2. Extraer claim 'iat' (issued at)
                                                 └── 3. Consultar Redis:
                                                        cache.get(f"user_jwt_revoked_at_{user.id}")
                                                               │
                                         ┌─────────────────────┴─────────────────────┐
                                         ▼                                           ▼
                                 iat >= revoked_at                           iat < revoked_at
                                  (Sesión válida)                         (401 Unauthorized:
                                                                          code='session_revoked')
```

Al llamar a `revoke_user_sessions(user)`, `PasswordChangeView` o `PasswordResetConfirmView`:
- Todos los refresh tokens van a la lista negra (`BlacklistedToken`).
- Se registra en Redis `user_jwt_revoked_at_{user.id} = timezone.now().timestamp()` con un TTL de 7 días.
- Cualquier petición posterior con un access token previo es rechazada instantáneamente.

---

## 3. WebSocket Handshake Seguro (Tickets Efímeros)

### 3.1. Riesgo de tokens en Query String
Pasar tokens de sesión en URLs (`ws://...?token=<jwt>`) provoca que el token quede expuesto en:
- Registros de acceso de NGINX, balanceadores y proxies inversos.
- Herramientas de telemetría y APM.
- Historiales y capturas de red.

### 3.2. Mecanismo de Tickets de Uso Único
Se implementó el patrón de tickets temporales (RFC 6455):

```text
[Frontend Autenticado]
        │
        ├── 1. POST /api/v1/auth/ws-ticket/ (Header: Bearer <jwt>)
        │      Backend genera ticket criptográfico (32 bytes urlsafe)
        │      Almacena en Redis: ws_ticket_{ticket} -> user.id (TTL 60s)
        │
        ├── 2. Retorna: { "ticket": "<ticket>", "expires_in": 60 }
        │
        └── 3. Conexión WebSocket:
               ws://.../ws/chat/{id}/?ticket=<ticket>
                       │
                       └── JwtAuthMiddleware:
                           - Lee ticket de query params
                           - Obtiene user_id de Redis
                           - Borra la clave inmediatamente (single-use)
                           - Inyecta user autenticado en scope["user"]
```

Si el ticket ya fue utilizado o expira, el usuario queda como `AnonymousUser()` y el canal rechaza la conexión.

---

## 4. Verificación de Correo Electrónico

- **Remitente oficial:** `noreply@mybooksocial.com`.
- **Comportamiento por entorno:**
  - **Desarrollo (`DEBUG=True`):** `REQUIRE_EMAIL_VERIFICATION = False` por defecto para agilizar desarrollo local. `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` muestra los enlaces de verificación en logs/consola.
  - **Producción / Test (`REQUIRE_EMAIL_VERIFICATION=True`):** Al autenticarse en `/api/v1/auth/token/`, si `is_email_verified = False`, la API responde con `403 Forbidden` (`code: 'email_not_verified'`).
  - **Confirmación:** Endpoint `POST /api/v1/auth/email/verify/` recibe `uid` y `token`, validándolos con `email_verification_token_generator` y marcando `is_email_verified = True`.

---

## 5. Prevención de IDOR y Anti-Enumeración

| Endpoint | Recurso | Política IDOR | Comportamiento si no autorizado |
|---|---|---|---|
| `GET /api/v1/users/{id}/` | Perfil de usuario | Si existe bloqueo mutuo | `404 Not Found` (anti-enumeración) |
| `GET /api/v1/books/reading-lists/{id}/` | Lista privada de terceros | Visibilidad filtrada en queryset | `404 Not Found` (anti-enumeración) |
| `POST /api/v1/books/reading-lists/{id}/add-book/` | Lista ajena | Solo propietario o staff | `403 Forbidden` (o `404` si es privada) |
| `POST /api/v1/books/reading-lists/{id}/reorder/` | Lista ajena | Solo propietario o staff | `403 Forbidden` (o `404` si es privada) |
| `PATCH /api/v1/books/reading-lists/{id}/` | Lista ajena | Solo propietario o staff | `403 Forbidden` (o `404` si es privada) |
| `DELETE /api/v1/books/reading-lists/{id}/` | Lista ajena | Solo propietario o staff | `403 Forbidden` (o `404` si es privada) |
| `PATCH /api/v1/user-books/{id}/` | Lectura personal | Acoplado a `user=request.user` | `404 Not Found` |
| `PATCH /api/v1/reviews/{id}/` | Reseña pública | Solo autor de la reseña | `403 Forbidden` |

---

## 6. Cabeceras de Seguridad HTTP

Configuradas centralmente en `mybookconnect/settings.py`:
- `SECURE_CONTENT_TYPE_NOSNIFF = True` (`X-Content-Type-Options: nosniff`)
- `X_FRAME_OPTIONS = 'DENY'` (Protección anti-Clickjacking)
- `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'` (Protección de rutas internas en cabecera Referer)
- `SECURE_HSTS_SECONDS = 31536000` (Activo en producción con `includeSubDomains` y `preload`)
