# ADR-005: Estrategia de Autenticación y Seguridad con JWT

## Estado
Aceptado

## Contexto
El desacoplamiento del frontend SPA y los canales WebSocket requiere un mecanismo de autenticación sin estado en servidor web, seguro contra robos de sesión, que funcione tanto en peticiones HTTP REST como en handshakes de WebSocket.

## Decisión
Implementar autenticación basada en JSON Web Tokens mediante `djangorestframework-simplejwt` con una política de endurecimiento estricta:
1. **Vida Útil Reducida del Access Token:** Expiración fijada en **15 minutos** para minimizar la ventana de oportunidad en caso de interceptación.
2. **Rotación Obligatoria de Refresh Tokens:** Cada solicitud de refresco genera un nuevo `refresh_token` y revoca el anterior.
3. **Lista Negra Persistente:** Uso de la aplicación `token_blacklist` para persistir los tokens invalidados (`OutstandingToken` y `BlacklistedToken`), impidiendo su reutilización.
4. **Cierre de Sesión Seguro:** Endpoint explícito `/api/v1/auth/logout/` que bloquea inmediatamente el refresh token enviado.

## Consecuencias
### Positivas
- Autenticación interoperable entre peticiones REST y conexiones persistentes WebSocket.
- Cero almacenamiento de sesiones en memoria de servidores WSGI, facilitando el escalado horizontal.
- Control total sobre revocaciones inmediatas en caso de compromiso de credenciales.

### Negativas / Retos
- Requiere que el frontend gestione de forma transparente el refresco de tokens antes de la expiración de los 15 minutos.
