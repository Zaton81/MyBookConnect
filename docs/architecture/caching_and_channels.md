# Estrategia de Caché y Comunicación en Tiempo Real

## 1. Almacenamiento en Caché con Redis

MyBookConnect utiliza Redis como capa de aceleración de lectura de baja latencia:

### Patrones de Claves de Caché
- **Detalle de Libro:** `book:{id}` (TTL: 1 hora).
- **Libros en Tendencia:** `books:trending` (TTL: 10 minutos).
- **Recomendaciones de Usuario:** `books:recommendations:{user_id}` (TTL: 30 minutos).
- **Respuestas de APIs Externas:** `books:google:{isbn}` y `books:openlibrary:{isbn}` (TTL: 24 horas).
- **Métricas de Observabilidad:** `mbc:metrics:*` (contadores en tiempo real).

### Política de Invalidación
La invalidación se ejecuta de forma proactiva mediante señales (`post_save`, `post_delete`) o métodos explícitos en la capa de servicios:
- La creación, edición o borrado de una reseña o libro elimina inmediatamente la clave de detalle (`cache.delete(f"book:{id}")`).
- Las modificaciones en las lecturas de un usuario invalidan las recomendaciones cacheadas de dicho usuario.

---

## 2. Capa en Tiempo Real (Django Channels + WebSockets)

### Arquitectura ASGI
Daphne actúa como servidor ASGI para gestionar las conexiones WebSocket persistentes sobre la ruta `/ws/chat/<conversation_id>/`.

### Autenticación en el Handshake
El middleware `WebSocketJwtMiddleware` valida el token JWT durante la negociación de la conexión (handshake) inspeccionando:
1. Cookie HTTPOnly `access_token`.
2. Cabecera `Authorization: Bearer <token>`.
3. Parámetro query string `?token=<token>` (fallback para clientes sin soporte de cabeceras en WebSockets).

### Transporte con `channels-redis`
El Channel Layer utiliza Redis como broker de mensajería para permitir que múltiples instancias de Daphne o workers de background envíen eventos a grupos de salas de chat (`chat_<conversation_id>`) de forma no bloqueante.
