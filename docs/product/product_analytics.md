# Product Analytics & Telemetry — MyBookConnect

## 1. Visión General
El módulo de analítica de producto (`analytics`) recopila telemetría de uso y eventos clave dentro de la plataforma MyBookConnect. Su propósito es alimentar métricas de producto, calcular la conversión en los embudos (funnels) de usuarios y medir la retención y actividad lectora sin comprometer la privacidad individual de los usuarios.

---

## 2. Eventos Canónicos (13 Eventos)
El sistema define y procesa 13 eventos canónicos a través del modelo `ProductAnalyticsEvent`:

1. **`signup`**: Registro completado con éxito.
2. **`login`**: Inicio de sesión exitoso.
3. **`book_view`**: Visualización de ficha o detalle de un libro.
4. **`book_added`**: Adición de un libro a la biblioteca personal.
5. **`reading_started`**: Inicio de una lectura (cambio de estado o progreso).
6. **`reading_finished`**: Finalización de la lectura de un libro.
7. **`review_created`**: Creación y publicación de una reseña de libro.
8. **`follow_created`**: Un usuario sigue a otro autor o lector.
9. **`list_created`**: Creación de una lista de lectura temática o personalizada.
10. **`recommendation_shown`**: Visualización de una recomendación de IA o catálogo en interfaz.
11. **`recommendation_clicked`**: Clic/interacción con una recomendación sugerida.
12. **`recommendation_dismissed`**: Descarte u omisión explícita de una recomendación sugerida.
13. **`message_sent`**: Envío de un mensaje directo o en sala de lectura.

---

## 3. Modelo de Datos y Privacidad por Diseño (RGPD)
- **Desvinculación en Supresión (`on_delete=models.SET_NULL`)**:
  En cumplimiento del RGPD (Art. 17 - Derecho al Olvido), el modelo vincula `user` mediante `SET_NULL`. Al anonimizar o eliminar la cuenta de un usuario, los eventos de telemetría histórica persisten para métricas agregadas disociando el ID del usuario (`user_id=null`).
- **Pseudonimización de Direcciones IP**:
  La dirección IP no se almacena en texto plano. Se procesa mediante un hash criptográfico SHA-256 truncado a 16 caracteres (`hash_ip_address`), imposibilitando la reidentificación directa del visitante.
- **Sesiones Anónimas**:
  Para visitantes no autenticados, se soporta `session_key` para rastrear eventos de funnel previos al registro (`book_view`, etc.).
- **Metadatos Sin PII**:
  El campo JSON `metadata` almacena exclusivamente identificadores técnicos o métricas contextuales (`book_id`, `category`, `source`, `duration_seconds`), prohibiendo correos, nombres o datos identificables.

---

## 4. Endpoints y Arquitectura de Ingesta

### 4.1 Ingesta Asíncrona (`/api/v1/analytics/collect/`)
- **Método**: `POST`
- **Permisos**: `AllowAny` (visitantes y usuarios autenticados).
- **Parámetros**:
  ```json
  {
    "event_type": "book_view",
    "metadata": {
      "book_id": 42,
      "source": "recommendation"
    },
    "path": "/books/42/",
    "session_key": "anon_session_xyz"
  }
  ```
- **Procesamiento**: Encolado asíncrono vía Celery task (`record_analytics_event_task`) con fallback síncrono si Celery no está activo.

### 4.2 Métricas de Embudo (`/api/v1/analytics/funnel/`)
- **Método**: `GET`
- **Permisos**: `IsAdminUser`
- **Parámetros Opcionales**: `days` (por defecto 30 días).
- **Estructura del Funnel**:
  - `visit`: Eventos iniciales de visualización y exploración (`book_view`).
  - `signup`: Registros completados (`signup`).
  - `activation`: Libros añadidos a biblioteca (`book_added`).
  - `reading_activity`: Lecturas iniciadas o terminadas (`reading_started`, `reading_finished`).
  - `social_interaction`: Reseñas, seguidos, listas y mensajes (`review_created`, `follow_created`, `list_created`, `message_sent`).
- **Respuesta**:
  ```json
  {
    "timeframe_days": 30,
    "funnel": {
      "visit": { "count": 1250, "conversion_from_previous": 1.0 },
      "signup": { "count": 310, "conversion_from_previous": 0.248 },
      "activation": { "count": 215, "conversion_from_previous": 0.6935 },
      "reading_activity": { "count": 160, "conversion_from_previous": 0.7442 },
      "social_interaction": { "count": 95, "conversion_from_previous": 0.5938 }
    }
  }
  ```

### 4.3 Resumen Agregado (`/api/v1/analytics/summary/`)
- **Método**: `GET`
- **Permisos**: `IsAdminUser`
- **Respuesta**: Conteo consolidado agrupado por `event_type` en el intervalo de días seleccionado.
