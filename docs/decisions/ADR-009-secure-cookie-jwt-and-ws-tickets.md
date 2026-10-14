# ADR-009: Mitigación de XSS mediante Cookies HttpOnly y Handshake WebSocket por Tickets Efímeros

## Estado
Aceptado (Actualiza y refuerza ADR-005)

## Contexto
El almacenamiento de tokens JWT en el almacenamiento local del navegador (`localStorage`) exponía las credenciales a exfiltración mediante ataques Cross-Site Scripting (XSS). Asimismo, la autenticación de WebSockets mediante query parameters (`/ws/chat/?token=...`) filtraba tokens confidenciales en logs de proxies inversos, balanceadores e historiales de navegador.

## Decisión
1. **Emisión de JWT en Cookies Seguras (`HttpOnly`):**
   - Los endpoints de login, OAuth, refresco y registro emiten `access_token` y `refresh_token` como cookies con atributos `HttpOnly`, `Secure` (en staging/producción) y `SameSite=Lax` (o `Strict` para operaciones críticas).
   - El cliente frontend (`useAuthStore`) almacena únicamente el perfil público del usuario (`partialize`), garantizando que ningún token sensible resida en `localStorage` o `sessionStorage`.
2. **Prohibición de Tokens en Query Parameters de WebSocket:**
   - Se bloquea en el middleware de ASGI (`TokenAuthMiddleware`) cualquier intento de handshake WebSocket que proporcione tokens JWT en query params.
3. **Mecanismo de Tickets Efímeros de Un Solo Uso:**
   - Para conectar WebSockets autenticados se implementa el endpoint `/api/v1/auth/ws-ticket/`.
   - El cliente realiza una petición HTTP autenticada con sus cookies `HttpOnly` para obtener un ticket efímero de 60 segundos de vigencia.
   - El ticket es canjeado y revocado inmediatamente en Redis durante el handshake del canal WebSocket (`/ws/chat/?ticket=...`), impidiendo su reutilización.

## Consecuencias
### Positivas
- Inmunidad de los tokens de sesión frente a cualquier intento de robo vía JavaScript malicioso (XSS).
- Cero fugas de credenciales en logs de Nginx, Daphne o herramientas de observabilidad perimetral.
- Revocación instantánea y trazabilidad de conexiones en tiempo real.

### Negativas / Retos
- Requiere configuración precisa de `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` y `credentials: 'include'` en el cliente Axios/Fetch.
- Flujo de conexión WebSocket en dos fases (solicitud previa de ticket antes de abrir el socket).
