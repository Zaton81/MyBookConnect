# Plan de Implementación — RoadmapV3: Sprint 1 (Seguridad e Integridad — P0)

**Fecha:** 2 de octubre de 2026  
**Rama:** `develop`  
**Estado:** En progreso  
**Objetivo:** Endurecer la seguridad, integridad y estabilidad de los componentes críticos identificados en la Sección 1 de [RoadmapV3.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV3.md) antes de avanzar en infraestructura y en el nuevo subsistema de autores.

---

## 1. Contexto y Objetivos del Sprint 1

Tras completar exitosamente las 38 fases de [RoadmapV2.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV2.md) y alcanzar la versión GA `1.0.0`, [RoadmapV3.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV3.md) establece los requisitos finales de producción ordenados en 6 Sprints.

El **Sprint 1 (Seguridad e Integridad — P0)** aborda deudas de seguridad prioritarias:
1. **Notificaciones seguras:** Eliminar la creación arbitraria de notificaciones por HTTP POST en la API pública para prevenir falsificaciones e IDOR.
2. **Observabilidad protegida:** Asegurar que `/api/v1/observability/metrics/` esté estrictamente restringido a administradores y libre de filtraciones de datos o credenciales.
3. **Robustez de WebSockets:** Proteger `ChatConsumer` ante payloads malformados (`JSONDecodeError`), denegación de servicio por mensajes masivos (límite de 64 KB), acciones no reconocidas y flooding (rate limiting).
4. **Sondas de salud desacopladas:** Asegurar que `/api/v1/health/` (liveness) y `/api/v1/ready/` (readiness) respondan de forma determinista con 200 y 503 sin exponer trazas internas.
5. **Alineación de Base de Datos en Entorno de Desarrollo:** Homogeneizar `docker-compose.yml` con `docker-compose.prod.yml` fijando PostgreSQL 16 con `pgvector`.

---

## 2. Tareas Detalladas de Implementación

### 2.1. Blindaje del Sistema de Notificaciones (Sección 1.1 RoadmapV3)
- **Eliminar `POST` en `/api/v1/users/notifications/`:**
  - Modificar `NotificationListView` en `backend/users/views.py` para heredar de `generics.ListAPIView` en lugar de soportar `POST`.
  - Desactivar o redirigir `NotificationCreateView` y retirar `NotificationCreateSerializer` de las vistas públicas.
  - Asegurar que cualquier intento de enviar `POST /api/v1/users/notifications/` devuelva `405 Method Not Allowed`.
  - Comprobar que los endpoints de acción existentes (`read/`, `read-all/`, `clear-read/`, `preferences/`, `unread-count/`) se mantengan operativos.
  - Verificar que todas las emisiones de notificaciones del backend continúan canalizándose exclusivamente a través de `NotificationService.send_notification(...)`.

### 2.2. Robustez y Endurecimiento de WebSockets (Sección 1.3 RoadmapV3)
- **Mejoras en `ChatConsumer` (`backend/messages_app/consumers.py`):**
  - **Captura de `json.JSONDecodeError`:** Capturar payloads JSON inválidos y responder con evento `error` estructurado (`{"event": "error", "code": "malformed_json", "detail": "Payload JSON malformado."}`) sin provocar crash del consumer.
  - **Límite de tamaño de mensaje:** Establecer `MAX_WS_MESSAGE_SIZE = 65536` (64 KB). Si el payload recibido excede este tamaño, rechazarlo inmediatamente con evento `error` (`code: "payload_too_large"`).
  - **Validación de acción obligatoria y control de desconocidas:** Si falta la clave `action` o contiene un valor no contemplado (`ping`, `send_message`, `mark_read`), devolver evento de error controlado (`code: "unknown_action"`).
  - **Rate Limiting / Backpressure:** Limitar a un máximo de 10 mensajes por segundo por conexión/usuario en el WebSocket mediante control de tasa en memoria/Redis para mitigar ataques de inundación.

### 2.3. Auditoría de Observabilidad y Permisos (Sección 1.2 RoadmapV3)
- **Verificación de `ObservabilityMetricsView` (`backend/mybookconnect/observability.py`):**
  - Reafirmar `permission_classes = [permissions.IsAdminUser]`.
  - Asegurar que un usuario anónimo reciba `401 Unauthorized`.
  - Asegurar que un usuario autenticado no administrador reciba `403 Forbidden`.
  - Verificar que el payload JSON resultante contenga únicamente agregaciones estadísticas y no exponga variables de entorno, claves secretas, contraseñas ni identificadores personales (PII).

### 2.4. Sondas de Salud `/health/` y `/ready/` (Sección 1.4 RoadmapV3)
- **Revisión de `HealthLiveView` y `HealthReadyView`:**
  - `/api/v1/health/` (Liveness): 200 OK estricto y ultraligero sin acceder a PostgreSQL ni Redis.
  - `/api/v1/ready/` (Readiness): 200 OK si PostgreSQL y Redis responden; 503 Service Unavailable ante fallo, registrando el error detallado en el logger de observabilidad sin devolver la excepción interna en el payload JSON.

### 2.5. Corrección de Discrepancia PostgreSQL en Docker Compose (Sección 2.2 RoadmapV3)
- **Actualizar `docker-compose.yml`:**
  - Cambiar el servicio `db` de `postgres:15` a `pgvector/pgvector:pg16` para eliminar la discrepancia con `docker-compose.prod.yml` y la documentación técnica.

---

## 3. Plan de Pruebas Automatizadas

Crear la suite de pruebas unitarias y de integración `backend/tests/test_sprint1_security.py` cubriendo:
1. **Notificaciones:**
   - Intentar `POST /api/v1/users/notifications/` con usuario autenticado -> Retorna `405 Method Not Allowed`.
   - Listar notificaciones `GET /api/v1/users/notifications/` -> Funciona correctamente para el usuario autenticado.
   - Marcar leídas y eliminar notificaciones propias -> Funciona correctamente.
   - Comprobar que un usuario no puede marcar ni eliminar notificaciones de terceros (IDOR -> 404 Not Found).
2. **Observabilidad:**
   - Acceso anónimo -> 401.
   - Acceso usuario regular -> 403.
   - Acceso staff/superadmin -> 200 con estructura de métricas y sin campos sensibles.
3. **WebSockets:**
   - Envío de texto no-JSON malformado -> Retorna evento de error sin desconexión abrupta.
   - Envío de mensaje superior a 64 KB -> Retorna evento de error `payload_too_large`.
   - Envío de acción desconocida -> Retorna evento de error `unknown_action`.
   - Rate limiting de mensajes repetidos.
4. **Health probes:**
   - Liveness 200.
   - Readiness 200 en estado saludable.

---

## 4. Criterios de Aceptación (Definition of Done)

- [ ] La creación de notificaciones por `POST` queda totalmente deshabilitada en la API pública.
- [ ] `ChatConsumer` maneja excepciones de decodificación JSON, tamaño excesivo y acciones inválidas sin fallar.
- [ ] La endpoint de métricas de observabilidad bloquea accesos no autorizados con 401/403.
- [ ] Las sondas `/health/` y `/ready/` cumplen con la separación de responsabilidades y códigos HTTP 200/503.
- [ ] `docker-compose.yml` está alineado con PostgreSQL 16 `pgvector`.
- [ ] La suite completa de pruebas pasa al 100% sin regresiones.
- [ ] Commit semántico en `develop` y push al repositorio remoto.
