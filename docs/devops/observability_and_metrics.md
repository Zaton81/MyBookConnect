# Observabilidad, Métricas y Sistema de Alertas — MyBookConnect

## 1. Visión General

La arquitectura de observabilidad de MyBookConnect está diseñada conforme a la **Fase 14 de RoadmapV2.md** (Sección 19) para ofrecer telemetría en tiempo real, trazabilidad de solicitudes de extremo a extremo, monitoreo de métricas operativas y de producto, y un motor de alertas preventivas sin comprometer la privacidad ni filtrar secretos.

El sistema se compone de tres módulos principales:

```text
[ Tráfico HTTP / Eventos ]
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    StructuredLoggingMiddleware                  │
│  - Propaga / inyecta 'X-Request-ID'                             │
│  - Mide latencia y consultas SQL por ciclo                      │
│  - Emite logs estructurados en JSON vía StructuredJsonFormatter │
│  - Aplica sanitización estricta antes de serializar             │
└──────────────────┬──────────────────────────────┬───────────────┘
                   │                              │
                   ▼                              ▼
┌─────────────────────────────────────┐ ┌─────────────────────────┐
│     ObservabilityMetricsService     │ │  ProductMetricsService  │
│  (Métricas de Backend y Fiabilidad) │ │ (KPIs de Producto)      │
│  - Conteo total y ratios 4xx / 5xx  │ │ - DAU, WAU, MAU         │
│  - Percentiles latencia: p50/p95/p99│ │ - Retención estimada    │
│  - DB latency & Redis latency       │ │ - Libros en estanterías │
│  - Profundidad de cola Celery       │ │ - Reseñas activas       │
│  - Conexiones activas de WebSocket  │ │ - Seguimiento y chat    │
└──────────────────┬──────────────────┘ └────────────┬────────────┘
                   │                                 │
                   └────────────────┬────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SystemAlertsEvaluator                      │
│  - Evalúa umbrales de salud operativa en tiempo real            │
│  - Detecta: 5xx elevado, DB/Redis caído, Celery backlog, etc.   │
│  - Clasificación: HEALTHY, DEGRADED, CRITICAL                   │
└───────────────────────────────────┬─────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│            GET /api/v1/observability/metrics/ (Admin)           │
│  - Cuadro de mando unificado para monitorización y SRE          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Formato de Logs JSON y Sanitización (19.1)

### 2.1. Campos Obligatorios del Registro
Todos los logs emitidos por la aplicación son serializados en JSON mediante `StructuredJsonFormatter` e incluyen formalmente los 7 campos requeridos por la especificación:

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `timestamp` | `string` (ISO-8601 UTC) | Momento exacto de emisión del evento. |
| `request_id` | `string` (UUID v4) | Identificador único de trazabilidad distribuida (`X-Request-ID`). |
| `user_id` | `integer` o `null` | ID del usuario autenticado (o `null` para peticiones anónimas). |
| `method` | `string` | Verbo HTTP (`GET`, `POST`, `PUT`, `DELETE`, etc.). |
| `path` | `string` | Ruta solicitada (ej. `/api/v1/books/`). |
| `status` | `integer` | Código de estado HTTP de respuesta (`200`, `400`, `404`, `500`, etc.). |
| `duration` | `float` | Duración del procesamiento en milisegundos (`duration_ms`). |

### 2.2. Campos Complementarios de Diagnóstico
- `db_queries`: Número de consultas SQL ejecutadas durante la petición.
- `db_duration_ms`: Tiempo acumulado invertido en consultas de base de datos.
- `level`, `logger`, `message`, `module`, `funcName`, `line`, `process`, `thread`.

### 2.3. Sanitización y Redaction de Secretos
La función `sanitize_sensitive_data` inspecciona recursivamente todas las cargas útiles antes de su serialización:
- **Contraseñas:** Campos como `password`, `passwd`, `pwd`, `confirm_password` se reemplazan por `***REDACTED***`.
- **Tokens de Autenticación y JWT:** Campos `token`, `access_token`, `refresh_token` o cualquier cadena con formato JWT (`eyJ...`) se reemplazan por `***REDACTED***`.
- **Cabeceras de Autorización:** Cabeceras con esquema Bearer (`Bearer eyJ...`) se enmascaran conservando el tipo de esquema (`Bearer ***REDACTED***`).
- **Claves de API y Secretos:** Campos como `api_key`, `secret_key`, `credit_card`, `cvv` quedan revocados e ilegibles en cualquier salida de log.

---

## 3. Métricas de Backend (19.2)

Disponibles bajo la clave `backend_metrics` en `ObservabilityMetricsService`:

1. **Solicitudes HTTP (`requests`):**
   - `total`: Conteo total acumulado en Redis.
   - `status_5xx_count` y `status_5xx_rate_pct`: Conteo y porcentaje de errores 5xx.
   - `status_4xx_count` y `status_4xx_rate_pct`: Conteo y porcentaje de errores de cliente 4xx.
2. **Latencia (`latency_ms`):**
   - `average`: Latencia media de la ventana de muestreo.
   - `p50`: Percentil 50 (mediana).
   - `p95`: Percentil 95 (presupuesto SLA: ≤ 500 ms).
   - `p99`: Percentil 99 (presupuesto SLA: ≤ 1500 ms).
3. **Base de Datos (`database`):**
   - `total_queries`: Consultas totales ejecutadas.
   - `avg_queries_per_request`: Promedio de consultas por petición HTTP.
   - `latency_ms`: Medición en milisegundos de un `SELECT 1;`.
   - `status`: `healthy` o `unhealthy`.
4. **Caché y Mensajería (`redis`):**
   - `latency_ms`: Medición en milisegundos de ida y vuelta (round-trip) con Redis.
   - `status`: `healthy` o `unhealthy`.
5. **Tareas en Segundo Plano e Integraciones (`background_and_integrations`):**
   - `celery_queue_depth`: Profundidad actual de la cola de Celery (`LLEN celery`).
   - `celery_failures_total`: Total acumulado de fallos en tareas asíncronas.
   - `active_websocket_connections`: Conexiones activas concurrentes a Channels/Daphne.
   - `external_api_errors_total`: Fallos en APIs externas (OpenLibrary, Google Books, IA).

---

## 4. Métricas de Producto y Engagement (19.2)

Calculadas por `ProductMetricsService` y almacenadas en caché con TTL de 60 segundos para evitar saturación de la base de datos:

- `dau` (Daily Active Users): Usuarios con actividad o `last_login` en las últimas 24 horas.
- `wau` (Weekly Active Users): Usuarios activos en los últimos 7 días.
- `mau` (Monthly Active Users): Usuarios activos en los últimos 30 días.
- `retention_rate_pct`: Ratio porcentual de retención (`wau / mau * 100`).
- `books_added`: Total de libros registrados en estanterías de usuarios (`UserBook`).
- `reviews`: Total de reseñas activas publicadas (`Review` con `deleted_at__isnull=True`).
- `follows`: Conexiones y seguimientos sociales activos entre usuarios.
- `messages`: Mensajes enviados a través de las conversaciones de chat.
- `recommendation_interactions`: Feedback y valoraciones sobre recomendaciones.

---

## 5. Motor de Alertas Operativas (19.3)

El componente `SystemAlertsEvaluator` analiza periódicamente o bajo demanda los siguientes 7 criterios críticos:

| Alerta | Criterio de Disparo | Severidad | Acción Requerida |
| :--- | :--- | :--- | :--- |
| `high_5xx_rate` | Tasa de errores 5xx > 1.0% (con ≥10 peticiones) | `CRITICAL` | Revisar excepciones recientes en logs estructurados. |
| `db_unavailable` | PostgreSQL no responde a la sonda de lectura | `CRITICAL` | Comprobar conectividad y estado del contenedor `db`. |
| `redis_unavailable` | Redis no responde a la sonda de ping/set | `CRITICAL` | Comprobar contenedor `cache` y memoria asignada. |
| `celery_backlog` | Cola de Celery con > 100 tareas pendientes | `WARNING` | Escalar concurrencia o workers de Celery. |
| `disk_usage_high` | Uso de almacenamiento en disco > 85.0% | `WARNING` | Purgar volcados antiguos en `/app/backups` o ampliar volumen. |
| `memory_usage_high`| Uso de memoria RAM > 85.0% | `WARNING` | Analizar fugas de memoria o aumentar límites de contenedor. |
| `high_error_rate` | Tasa combinada de errores (4xx + 5xx) > 5.0% | `WARNING` | Inspeccionar patrones de peticiones cliente erróneas o ataques. |

---

## 6. Acceso al Endpoint de Métricas

El endpoint administrativo seguro está disponible en:
```http
GET /api/v1/observability/metrics/
Authorization: Bearer <TOKEN_ADMIN>
```

### Respuestas:
- `200 OK`: Retorna payload consolidado con `backend_metrics`, `product_metrics`, `system_alerts` y `performance_budgets`.
- `401 Unauthorized`: Si la petición no incluye token de sesión válido.
- `403 Forbidden`: Si el usuario autenticado no posee permisos de staff/administrador.
