# Estrategia de Pruebas de Backend y Suite de Regresión (Fase 11)

Este documento describe la arquitectura, tipología, directrices de ejecución y suite de regresión del backend de BookSocial / MyBookConnect, garantizando cobertura estricta y blindaje continuo.

---

## 1. Tipología de Pruebas Implementada

### 1.1. Pruebas Unitarias (Servicios Puros)
- **Ámbito:** Funciones y métodos utilitarios sin dependencias de base de datos ni I/O volátil.
- **Componentes cubiertos:**
  - `normalize_isbn`: Normalización estricta de códigos ISBN-10 e ISBN-13 eliminando caracteres no alfanuméricos.
  - `_clean_goodreads_value`: Limpieza de formatos de fórmulas Excel/Goodreads (`="978..."`).
  - `_parse_date`: Detección multiformato de fechas (`YYYY/MM/DD`, `YYYY-MM-DD`, `DD/MM/YYYY`, `YYYY`).
  - `_map_goodreads_status`: Traducción semántica de estanterías (`read`, `currently-reading`, `to-read`, `abandoned`).
  - `CSVFormatDetector`: Detección automática de dialectos CSV (Goodreads, Calibre, Genérico).

### 1.2. Pruebas de Integración (Django + PostgreSQL + Redis)
- **Ámbito:** Interacción real entre la capa ORM de Django, la base de datos PostgreSQL y el servidor de caché Redis.
- **Componentes cubiertos:**
  - Transacciones atómicas y aislamiento: Verificación de rollback ante fallos en transacciones concurrentes.
  - Caché de Redis e invalidación reactiva: Almacenamiento seguro (`safe_cache_set`), lectura defensiva (`safe_cache_get`) y borrado atómico (`safe_cache_delete`).

### 1.3. Pruebas de Endpoints de API Críticos
- **Ámbito:** Contrato HTTP, autenticación, códigos de respuesta y serialización de endpoints centrales.
- **Componentes cubiertos:**
  - `GET /api/v1/auth/profile/`: Perfil autenticado.
  - `POST & GET /api/v1/books/user/books/`: Biblioteca personal.
  - `GET /api/v1/books/statistics/`: Estadísticas agregadas de lectura.
  - `POST /api/v1/books/import/csv/preview/` y `confirm/`: Flujo de importación masiva.

### 1.4. Pruebas de Seguridad y Control de Acceso
- **IDOR (Insecure Direct Object References):** Un usuario autenticado no puede alterar ni eliminar registros pertenecientes a otro usuario (`UserBook`, `Review`).
- **Permisos y Privacidad:** Perfiles configurados como privados (`private`) o amigos mutuos (`friends_only`) restringen el acceso a usuarios no autorizados (403/404).
- **Control de Bloqueos:** Los usuarios bloqueados no pueden consultar el perfil ni interactuar con el bloqueador.
- **Autenticación JWT:** Peticiones sin token o con credenciales inválidas reciben 401 Unauthorized de forma inmediata.
- **Seguridad en IA y Sanitización:** Detección de prompt injection (`detect_prompt_injection`) y neutralización de tokens especiales (`sanitize_untrusted_input`).

### 1.5. Suite de Regresión (Regression Suite)
Cada incidente o discrepancia corregida se convierte en una prueba automatizada permanente:
- **Goodreads Import Payload Compatibility:** Validación de que la previsualización y confirmación devuelvan de forma tolerante tanto `raw_items_payload` como `preview_items`, y las métricas de recuento de libros nuevos, en catálogo y existentes en estantería.
- **Gamification Token & Streak Logging:** Procesamiento adecuado de registros de lectura diaria (`/api/v1/gamification/log/`) y objetivos anuales (`/api/v1/gamification/goals/`) bajo sesiones autenticadas.

---

## 2. Ejecución de la Suite de Pruebas

```bash
# Ejecutar suite específica de la Fase 11
docker compose exec -T backend pytest tests/test_phase11_backend_testing.py -v

# Ejecutar suite de regresión histórica Fases 1 a 11
docker compose exec -T backend pytest tests/test_phase0*.py tests/test_phase11*.py -q
```
