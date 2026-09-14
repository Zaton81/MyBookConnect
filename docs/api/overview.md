# Visión General de la API REST

## 1. Convenciones y Estándares
- **Protocolo:** HTTPS obligatorio en producción.
- **Prefijo de Versión:** `/api/v1/`
- **Formato de Carga Útil:** JSON (`Content-Type: application/json`).
- **Codificación de Caracteres:** UTF-8.
- **Esquema OpenAPI 3.1:** Documentación generada con `drf-spectacular` accesible en:
  - Swagger UI: `/api/schema/swagger-ui/`
  - ReDoc: `/api/schema/redoc/`
  - Descarga YAML: `/api/schema/`

## 2. Cabeceras Estándar
| Cabecera | Tipo | Descripción |
|---|---|---|
| `Authorization` | Requerida en endpoints protegidos | Formato: `Bearer <access_token>` |
| `X-Request-ID` | Opcional (entrada) / Obligatoria (salida) | UUID de trazabilidad distribuida propagado en cada petición |
| `Content-Type` | Requerida en POST/PUT/PATCH | `application/json` |

## 3. Formato Canónico de Respuestas de Error
En caso de fallo, la API responde con códigos de estado HTTP estándar y un objeto estructurado:
```json
{
  "detail": "Descripción del error o motivo del rechazo.",
  "code": "error_code_identifier"
}
```

Para errores de validación en formularios (HTTP 400 Bad Request):
```json
{
  "campo": ["Descripción del error de validación en el campo."]
}
```

## 4. Códigos de Estado Comunes
- `200 OK`: Petición procesada con éxito.
- `201 Created`: Recurso creado satisfactoriamente.
- `204 No Content`: Eliminación completada sin contenido que devolver.
- `400 Bad Request`: Error de validación en parámetros o datos enviados.
- `401 Unauthorized`: No autenticado o token JWT inválido/expirado.
- `403 Forbidden`: Autenticado pero sin privilegios suficientes (p. ej., perfil privado).
- `404 Not Found`: Recurso inexistente.
- `429 Too Many Requests`: Se ha excedido la cuota de peticiones permitida (Rate Limit).
- `500 Internal Server Error`: Excepción no controlada registrada en el sistema de observabilidad.
