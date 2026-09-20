# Definition of Done (Criterios de Aceptación)

Este documento establece la **Definition of Done (DoD)** oficial para **MyBookConnect**.

Ninguna funcionalidad, corrección o refactorización se considera terminada (*done*) ni puede ser integrada en las ramas `develop` o `main` sin satisfacer **la totalidad** de los 13 criterios aquí definidos.

---

## Los 13 Criterios de Calidad

```text
[x] 1. Modelo
[x] 2. Migración
[x] 3. Serializer
[x] 4. API
[x] 5. Permisos
[x] 6. Tests backend
[x] 7. Cliente frontend
[x] 8. UI
[x] 9. Tests frontend
[x] 10. Documentación
[x] 11. OpenAPI
[x] 12. CI
[x] 13. Logs si son necesarios
```

---

### 1. Modelo (Data Modeling & Integrity)
- **Diseño sin duplicidad:** No debe haber solapamiento conceptual entre entidades (ej. separación clara entre `UserBook`, `Review` y `ReadingStatus`).
- **Restricciones explícitas:** Uso de `UniqueConstraint` (ej. combinación única `user` + `book` en reseñas), `CheckConstraint` o validadores de rango.
- **Indexación eficiente:** Declarar `db_index=True` o `models.Index` en campos de búsqueda difusa, ordenación, claves foráneas o filtros frecuentes.
- **Preservación histórica:** Incorporar soft-delete (`SoftDeleteModel`) o marcas temporales (`created_at`, `updated_at`) según corresponda.

---

### 2. Migración (Safe & Reversible Migrations)
- **Generación limpia:** No deben existir migraciones pendientes (`makemigrations --check --dry-run`).
- **Operaciones no bloqueantes:** Evitar añadir columnas sin `default` o sin `null=True` en tablas de gran volumen.
- **Reversibilidad probada:** La migración debe poder desaplicarse y reaplicarse sin pérdida de datos inesperada (`python manage.py migrate app 00XX`).
- **Resolución de conflictos:** Si dos ramas generan migraciones concurrentes, deben fusionarse limpiamente con `makemigrations --merge`.

---

### 3. Serializer (Validation & Security)
- **Sanitización XSS estricta:** Todos los campos de texto enriquecido o plano generados por el usuario (UGC) deben sanitizarse en backend usando `mybookconnect.html_sanitizer` (`sanitize_html`, `sanitize_plain_text` con `nh3`).
- **Prevención de consultas N+1:** Los métodos de cálculo o campos relacionados deben apoyarse en queries optimizadas con `select_related` o `prefetch_related`.
- **Validaciones de negocio:** Uso de validadores de campo (`validate_<fieldname>`) y de objeto (`validate`) con mensajes de error descriptivos.

---

### 4. API (REST Standards & Error Contracts)
- **URLs canónicas:** Rutas con barra final (`/`) e identificadores consistentes (`/api/v1/.../`).
- **Códigos HTTP semánticos:**
  - `200 OK`: Consulta o actualización exitosa con contenido.
  - `201 Created`: Recurso creado exitosamente (con cabecera `Location` o payload).
  - `204 No Content`: Eliminación exitosa sin cuerpo de respuesta.
  - `400 Bad Request`: Error de validación de sintaxis o datos de entrada.
  - `401 Unauthorized`: Token JWT ausente, expirado o revocado.
  - `403 Forbidden`: Usuario autenticado pero sin privilegios sobre el recurso.
  - `404 Not Found`: Recurso no encontrado.
  - `409 Conflict`: Violación de restricción única o colisión de estado.
  - `429 Too Many Requests`: Rate limit superado.
- **Contrato de errores unificado:** Respuestas de error estandarizadas siguiendo el formato RFC 7807 (`code`, `detail`, `field_errors`, `timestamp`, `path`).

---

### 5. Permisos (Authorization & Privacy)
- **Defensa en profundidad:** Ninguna vista sensible debe confiar en el permiso global permisivo por defecto.
- **Permisos por objeto (`HasObjectPermission`):** Validar explícitamente que el usuario autenticado sea el propietario del recurso (`obj.user == request.user`) antes de permitir edición o borrado.
- **Respeto a la privacidad:** Aplicar las restricciones de visibilidad de perfil y listas configuradas por el usuario (`public`, `followers`, `private`).

---

### 6. Tests Backend (Test Coverage & Isolation)
- **Suite automatizada:** Pruebas con `pytest-django` cubriendo el camino feliz (*happy path*), casos límite y caminos de error (400, 401, 403, 404, 409).
- **Aislamiento total:** Ningún test debe realizar llamadas HTTP reales hacia internet. Servicios externos (Google Books, Open Library) y tareas de Celery deben aislarse mediante `unittest.mock.patch`.
- **Ejecución rápida:** Uso de `--reuse-db` para mantener tiempos de feedback reducidos.

---

### 7. Cliente Frontend (Typed API Client)
- **Tipado estricto:** El cliente de API en TypeScript debe consumir exclusivamente los tipos autogenerados por OpenAPI (`src/types/api.ts`).
- **TanStack Query:** Uso de queries y mutaciones con manejo explícito de estados (`isLoading`, `isError`, `error`, `data`).
- **Invalidación de caché:** Las mutaciones deben invalidar de forma precisa las queries relacionadas (`queryClient.invalidateQueries`).

---

### 8. UI (User Experience & Accessibility)
- **Diseño responsivo:** Implementación *mobile-first* fluida con TailwindCSS, adaptada a pantallas móviles, tablets y escritorio.
- **Feedback de estados:** Indicadores de carga (*skeletons* o *spinners*), estados vacíos (*empty states*) informativos y notificaciones toast ante éxitos o errores.
- **Accesibilidad básica (a11y):** Elementos interactivos con etiquetas `aria-label`, contraste de color suficiente y navegación por teclado operativa.

---

### 9. Tests Frontend (Component Testing)
- **Pruebas unitarias y de integración:** Pruebas de componentes con Vitest y React Testing Library.
- **Comportamiento interactivo:** Simular interacciones de usuario (`@testing-library/user-event`) verificando que la UI reacciona y actualiza la vista.

---

### 10. Documentación (Code & Architectural Docs)
- **Docstrings:** Clases, métodos de servicio y vistas documentados explicando propósito y argumentos.
- **Guías técnicas:** Actualizar la documentación en `docs/` (`api/`, `architecture/`, `deployment/`, `development/`) si se introducen nuevos flujos o componentes.
- **Changelog:** Registrar cambios bajo `[Unreleased]` en `CHANGELOG.md` siguiendo *Keep a Changelog 1.1.0*.

---

### 11. OpenAPI (Schema & Type Synchronization)
- **Anotaciones DRF Spectacular:** Vistas anotadas con `@extend_schema(summary=..., description=..., responses=...)`.
- **Validación del esquema:** `python manage.py spectacular --validate --fail-on-warn` debe ejecutarse sin errores ni advertencias.
- **Sincronización de tipos:** `npm run generate:types` en frontend debe regenerar `src/types/api.ts` sin discrepancias.

---

### 12. CI (Continuous Integration)
- **Pipelines en verde:** Todo commit o Pull Request debe superar las pruebas de CI:
  - `ruff check` sin advertencias.
  - `tsc --noEmit` con cero errores de TypeScript.
  - Tests de backend y frontend pasando al 100%.

---

### 13. Logs si son necesarios (Observability & Privacy)
- **Logging estructurado:** `logger = logging.getLogger(__name__)`.
- **Niveles adecuados:**
  - `INFO`: Eventos clave de negocio (registro de usuario, checkout, creación de libro).
  - `WARNING`: Reintentos de conexión, rate limiting alcanzado, fallos transitorios.
  - `ERROR`: Excepciones no controladas con `exc_info=True`.
- **Privacidad estricta:** Prohibido registrar contraseñas en texto claro, tokens JWT, números de tarjeta o datos personales sensibles (PII).

---

## Herramienta de Verificación Automatizada

Para comprobar de forma automatizada los criterios mecánicos de la DoD antes de solicitar la fusión de una rama:

```bash
bash scripts/verify_dod.sh
```
