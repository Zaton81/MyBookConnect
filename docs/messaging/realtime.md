# Arquitectura de Mensajería y Tiempo Real (Fase 4 - RoadmapV2)

## 1. Resumen Ejecutivo
La Fase 4 moderniza la infraestructura de mensajería privada y tiempo real de MyBookConnect, garantizando alta resiliencia en conexiones inestables, deduplicación de mensajes, control de estados de lectura por participante y seguridad mediante tickets efímeros.

---

## 2. Componentes Clave

### 2.1 Autenticación Efímera de WebSockets (Tickets de uso único)
- **Endpoint**: `POST /api/v1/auth/ws-ticket/`
- **Mecanismo**: Genera un ticket criptográfico (`secrets.token_urlsafe(32)`) firmado y guardado en Redis (`ws_ticket:{ticket}`) con TTL de 30 segundos.
- **Ventaja**: Previene la exposición de tokens JWT en los logs de URLs/proxies y garantiza que el ticket solo pueda consumirse una vez (`redis_client.delete(key)` al conectarse).

### 2.2 Heartbeat y Ciclo de Vida Resiliente
- **Frontend (`useChatWebSocket.ts`)**:
  - Emite periódicamente `{ "action": "ping" }` cada 30 segundos.
  - Recibe `{ "event": "pong", "timestamp": <iso_date> }` del servidor.
  - Si la conexión se pierde, inicia reconexión automática mediante **backoff exponencial con jitter**:
    $$\text{delay} = \min(1000 \times 1.5^{\text{retry}} + \text{random}(0, 500), 15000)\text{ ms}$$
- **Backend (`ChatConsumer`)**:
  - Responde inmediatamente a los eventos `ping` sin golpear la base de datos.
  - Asegura que los sockets zombis sean recolectados y desconectados limpiamente.

### 2.3 Idempotencia y Deduplicación (`client_message_id`)
- **Propósito**: Prevenir mensajes duplicados causados por timeouts de red, reconexiones instantáneas o pulsaciones repetidas del botón de enviar.
- **Implementación**:
  - En el modelo `Message`, se incluye `client_message_id = models.UUIDField(null=True, blank=True, db_index=True)` con un índice compuesto `('conversation', 'client_message_id')`.
  - **En WebSocket (`_create_message`)**: Si ya existe un mensaje con ese `client_message_id` en la conversación, se recupera el existente y se marca como `is_duplicate: True`, evitando volver a persistir o disparar notificaciones push/campana.
  - **En REST (`MessageViewSet.create`)**: Si se recibe un `client_message_id` preexistente, la API responde HTTP `200 OK` con el mensaje original en lugar de error o duplicación.
  - **Frontend**: `useChatWebSocket.sendMessage()` genera automáticamente un UUID v4 antes de enviar el paquete.

### 2.4 Modelo de Lectura por Participante (`ConversationParticipant`)
- **Problema Anterior**: El modelo tradicional con un booleano `Message.read` no escala bien para auditoría de lecturas independientes por participante.
- **Nuevo Modelo**:
  ```python
  class ConversationParticipant(models.Model):
      conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
      user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_participations')
      last_read_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
      last_read_at = models.DateTimeField(null=True, blank=True)
      joined_at = models.DateTimeField(auto_now_add=True)
  ```
- **Sincronización**: Al invocar la acción `mark_read` vía WebSocket:
  1. Se actualiza `Message.read = True` para los mensajes no leídos del interlocutor (mantiene retrocompatibilidad).
  2. Se actualiza `ConversationParticipant.last_read_message` al último mensaje leído y `last_read_at = timezone.now()`.
  3. Se emite un broadcast a la conversación con el evento `messages_read` conteniendo `last_read_message_id` y `reader_id`.

---

## 3. Matriz de Verificación y Cobertura

| Módulo / Test | Objetivo | Resultado |
|---|---|---|
| `test_phase04_messaging_realtime.py` | Heartbeat `ping/pong`, Idempotencia WS & REST, `ConversationParticipant` tracking | **PASSED (5/5)** |
| `test_chat_websockets.py` | Tickets efímeros de uso único, permisos directos, broadcast de mensajes | **PASSED (7/7)** |
| `frontend/src/hooks/useChatWebSocket.ts` | Typecheck (`tsc --noEmit`), backoff exponencial, generación de UUIDs idempotentes | **PASSED** |
