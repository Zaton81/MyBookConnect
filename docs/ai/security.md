# Arquitectura de IA Segura y Controlada (Fase 5 - RoadmapV2)

## 1. Resumen Ejecutivo
La Fase 5 consolida el subsistema de Inteligencia Artificial de MyBookConnect como una capa completamente desacoplada, opcional, auditable y segura. La IA deja de ser un vector potencial de denegación de servicio o fuga presupuestaria, operando con límites estrictos, rate limiting multinivel en Redis, registro inmutable de consumo y blindaje contra prompt injection.

---

## 2. Componentes y Arquitectura

### 2.1 Abstracción de Proveedores y Resiliencia HTTP (10.1 y 10.3)
- **Interfaz Base (`AIProvider`)**: Define el contrato estándar para proveedores locales y en la nube (`OpenAIProvider`, `OpenRouterProvider`, `OllamaProvider`).
- **Resiliencia HTTP**: Cada cliente inicializa una sesión `requests.Session()` montada con un adaptador `HTTPAdapter` y política de reintentos exponenciales con jitter (`Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])`).
- **Fallback Determinista**: Ante indisponibilidad temporal o error del proveedor configurado, la API conmuta limpiamente a respuestas asistidas deterministas basadas en el catálogo local (`rule-based`), garantizando disponibilidad ininterrumpida.

### 2.2 Validación Estricta de Entradas y Parámetros (10.2)
- **Roles Permitidos**: La API solo acepta mensajes con roles `user` y `assistant`. La inyección de roles reservados (`system`, `developer`, `tool`, `root`) es bloqueada con `400 Bad Request`.
- **Restricción de Parámetros**: El cliente jamás puede controlar directamente:
  - `system_prompt` / `system`
  - `tools`
  - `provider`
  - `model`
  - `temperature`
  - `max_tokens`
- Cualquier intento de envío de estos parámetros es neutralizado por `validate_forbidden_client_parameters()`, respondiendo `400 Bad Request`.

### 2.3 Límites Defensivos de Longitud y Contexto (10.3)
- **Límite por mensaje**: Acotado defensivamente a `3000` caracteres (`MAX_MESSAGE_LENGTH`).
- **Historial máximo**: Hasta `20` mensajes (`MAX_MESSAGES_COUNT`).
- **Longitud acumulada total**: Acotada a `12000` caracteres (`MAX_TOTAL_MESSAGES_LENGTH`). Si el cliente envía un historial masivo, el backend poda automáticamente los mensajes más antiguos conservando la coherencia reciente.

### 2.4 Rate Limiting Multinivel en Redis (10.4)
Para proteger el presupuesto y evitar abusos de peticiones masivas, se aplican concurrentemente tres ventanas temporales por usuario:
1. **Minuto**: 20 peticiones/minuto (`AI_RATE_LIMIT_PER_MINUTE`).
2. **Hora**: 100 peticiones/hora (`AI_RATE_LIMIT_PER_HOUR`).
3. **Día**: 500 peticiones/día (`AI_RATE_LIMIT_PER_DAY`).

Al exceder cualquier cuota, la API responde HTTP `429 Too Many Requests` con la cabecera `Retry-After` calculada con el TTL restante de la ventana superada.

### 2.5 Presupuesto, Métricas y Observabilidad (`AIUsageLog`) (10.5)
Cada interacción (exitosa o fallida) se registra de forma atómica en el modelo persistente `AIUsageLog`:
- `user`: Usuario solicitante (o null para anónimos/batch).
- `request_id`: ID correlativo único propagado en cabecera `X-Request-ID`.
- `provider` y `model`: Identificadores del motor.
- `prompt_tokens`, `completion_tokens` y `total_tokens`: Conteo exacto reportado por el proveedor.
- `estimated_cost_usd`: Cálculo de coste estimado según la tarifa por millón de tokens configurada (OpenAI, OpenRouter, o 0.0 para Ollama local).
- `duration_ms`: Latencia total de la llamada en milisegundos.
- `success` y `error`: Estado de resultado y detalle del error si ocurrió.

### 2.6 Protección contra Prompt Injection y Sanitización de Contexto (10.6)
- **Detección Heurística**: `detect_prompt_injection()` identifica patrones de anulación de directivas (`ignore previous instructions`, `DAN mode`, `system override`, etc.).
- **Neutralización de Tokens Especiales**: Se reemplazan secuencias de control como `<|im_start|>`, `[INST]`, `<<SYS>>`.
- **Sanitización de Libros (`sanitize_book_context`)**: El contenido externo (descripciones, reseñas, metadatos) es desarmado antes de ser concatenado en los prompts del sistema para impedir que el contenido de un libro ejecute comandos pasivos.

### 2.7 Control de Herramientas Seguras (Tool Calling) (10.7)
- **Allowlist Estricta**: Solo herramientas formalmente registradas (`catalog_search`, `book_detail`, `user_reading_status`, `add_to_wishlist`) son ejecutables.
- **Autorización por Herramienta**: Validación previa de permisos del usuario (`validate_permissions`).
- **Rate Limit por Herramienta**: Cuota individual por minuto en Redis (`ai:tool:ratelimit:{tool}:{user_id}`).
- **Auditoría**: Traza de registro de argumentos, duración y resultado (`tool.audit`).

---

## 3. Matriz de Cobertura y Pruebas

| Suite | Objetivos Verificados | Resultado |
|---|---|---|
| `tests/test_phase05_ai_security.py` | Métricas de tokens, rechazo de parámetros prohibidos, Rate limiting multinivel, `AIUsageLog`, blindaje contra inyección y auditoría de herramientas | **PASSED (14/14)** |
| `tests/test_phase26_ai.py` | Factoría de proveedores, clientes, similitud coseno y endpoints de IA | **PASSED (19/19)** |
| `tests/test_phase27_ai_security.py` | Detección de inyección, políticas conversacionales y ejecución controlada de herramientas | **PASSED (19/19)** |
| `tests/test_phase01_domain_integrity.py` a `test_phase04_messaging_realtime.py` | Regresión completa de dominios, privacidad, autenticación y mensajería | **PASSED (33/33)** |
